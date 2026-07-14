# corpus

## overview

the corpus layer ingests raw Indian legal text (IPC, BNS, BNSS,
Constitution, CPC) into Qdrant so `rules/citation_checker.py` can
verify whether a cited section actually exists and is currently active.

this is a one-time setup step (or re-run when acts are amended).
once ingested, citation checking works in real time without any model
loading — pure exact-field lookup against Qdrant.

---

## acts ingested

| act | full name | status | replaces |
|---|---|---|---|
| IPC | Indian Penal Code, 1860 | partially repealed | — |
| BNS | Bharatiya Nyaya Sanhita, 2023 | active | replaces IPC |
| CrPC | Code of Criminal Procedure, 1973 | repealed | — |
| BNSS | Bharatiya Nagarik Suraksha Sanhita, 2023 | active | replaces CrPC |
| CPC | Code of Civil Procedure, 1908 | active | — |
| Constitution | Constitution of India, 1950 | active | — |

**critical distinction:** BNS ≠ BNSS.
- BNS (Bharatiya Nyaya Sanhita) replaces the IPC — it's the substantive
  criminal law (what acts are crimes, what punishments apply)
- BNSS (Bharatiya Nagarik Suraksha Sanhita) replaces CrPC — it's the
  procedural criminal law (how cases are investigated, tried, appealed)

a document citing "Section 302 IPC" after July 2024 (when BNS came into
force) is citing a repealed provision. the corpus flags this.

---

## sources

raw legal text is sourced from:
- **IndiaCode** (indiacode.nic.in) — official government source for IPC,
  BNS, BNSS, CPC, Constitution PDFs. authoritative, frequently updated.
- **Legislative.gov.in** — gazette notifications for amendments
- **eCourts** for court rules (if needed later)

raw files live in `corpus/sources/` which is gitignored (too large).
processed/chunked output lives in `corpus/sources/processed/` — also
gitignored but worth caching locally since re-processing takes time.

---

## ingestion pipeline

```
corpus/sources/{act}/raw PDFs or text
          │
          ▼
corpus/parser.py
          │  extracts individual sections from raw files
          │  output: list[Section]
          │
          ▼
corpus/chunker.py
          │  splits long sections into overlapping passages
          │  short sections (< 200 tokens) stay as-is
          │  output: list[Passage]
          │
          ▼
corpus/embeddings.py
          │  embeds each passage via sentence embedding model
          │  output: list[numpy array]
          │
          ▼
corpus/uploader.py
          │  pushes to Qdrant with metadata payload
          │  output: confirmation + point count
          │
          ▼
Qdrant collection: "legal_corpus"
```

run the full pipeline:
```bash
uv run python scripts/ingest_corpus.py --act ipc
uv run python scripts/ingest_corpus.py --act bns
uv run python scripts/ingest_corpus.py --act bnss
uv run python scripts/ingest_corpus.py --act constitution
uv run python scripts/ingest_corpus.py --all
```

---

## Section dataclass

```python
@dataclass
class Section:
    section_no: str    # "302", "304A", "21" — string to handle alphanumeric
    act: str           # "IPC", "BNS", "BNSS", "Constitution", "CPC"
    title: str         # "Murder", "Causing death by negligence", etc.
    text: str          # full section text
    status: str        # "active" or "repealed"
    replaced_by: str   # e.g. "Section 103 BNS" for IPC 302, else ""
    effective_date: str  # ISO date when this version became effective
```

## Passage dataclass

```python
@dataclass
class Passage:
    section_no: str
    act: str
    title: str
    status: str
    replaced_by: str
    text: str          # the passage text (subset of Section.text for long sections)
    passage_idx: int   # which passage within the section (0-indexed)
```

---

## Qdrant collection schema

**collection name:** `legal_corpus`

**vector:** 768-dimensional (matches InLegalBERT embedding size if using
InLegalBERT for embeddings, or 384 for sentence-transformers/all-MiniLM)

**payload fields per point:**

```json
{
  "section_no": "302",
  "act": "IPC",
  "title": "Murder",
  "status": "repealed",
  "replaced_by": "Section 103 BNS",
  "text": "Whoever commits murder shall be punished...",
  "passage_idx": 0,
  "effective_date": "1860-01-01"
}
```

**indexes:** `section_no` and `act` are indexed as keyword fields for
exact-match filtering. this is what makes citation lookup fast — we
filter by exact `section_no` + `act` match, no vector similarity needed
for the basic citation check.

---

## how citation_checker.py queries Qdrant

citation checker does NOT use vector similarity for basic lookup.
it uses exact field filtering:

```python
results = client.query_points(
    collection_name="legal_corpus",
    query_filter=Filter(
        must=[
            FieldCondition(key="section_no", match=MatchValue(value="302")),
            FieldCondition(key="act",        match=MatchValue(value="IPC")),
        ]
    ),
    limit=1,
    with_payload=True,
)
```

if `results.points` is empty → section doesn't exist → flag as CITE error.
if found but `payload["status"] == "repealed"` → flag as CITE error with
suggestion pointing to `payload["replaced_by"]`.

vector similarity search (`search.py`) is reserved for a future feature:
"find the BNS equivalent of this IPC section" — semantic lookup rather
than exact match.

---

## IPC → BNS conversion

some key mappings (not exhaustive — use only verified sources):

| IPC section | offence | BNS equivalent | notes |
|---|---|---|---|
| 302 | Murder | 103 BNS | |
| 304A | Causing death by negligence | 106 BNS | |
| 307 | Attempt to murder | 109 BNS | |
| 376 | Rape | 64 BNS | expanded scope |
| 420 | Cheating | 318 BNS | |
| 498A | Cruelty by husband | 85 BNS | |

**important:** do not fabricate or assume conversion mappings. use only
verified mappings from the official BNS text (indiacode.nic.in) or the
MHA comparative statement. wrong mappings in the corpus would cause the
citation checker to suggest incorrect corrections, which is worse than
not suggesting anything.

---

## embedding model choice

two options, pick one before ingestion:

**option A: `sentence-transformers/all-MiniLM-L6-v2`**
- 384 dimensions, fast, lightweight
- good for general semantic similarity
- doesn't know Indian legal vocabulary specifically
- good enough for passage retrieval

**option B: InLegalBERT embeddings**
- 768 dimensions, slower
- domain-specific — knows legal vocabulary
- CLS token embedding from InLegalBERT as passage vector
- better for legal semantic retrieval at the cost of speed and size

for citation checking (exact field lookup), the embedding model doesn't
matter — we filter by section_no + act, not by vector similarity.
for future semantic features ("find related sections"), option B will
give better results. pick based on whether you want to build semantic
search later.

---

## re-ingestion

when BNS or BNSS gets amended (sections added, renumbered, repealed):

1. download the updated act from IndiaCode
2. run `scripts/ingest_corpus.py --act bns --force` (drops and recreates)
3. verify with `scripts/smoke_test.py --citation "Section 103 BNS"`

`--force` flag drops the existing points for that act before re-ingesting.
other acts in the collection are unaffected.

---

## verifying the corpus

after ingestion, verify a few known sections manually:

```bash
uv run python -c "
from corpus.search import lookup_section
print(lookup_section('302', 'IPC'))   # should show status=repealed
print(lookup_section('103', 'BNS'))   # should show status=active
print(lookup_section('999', 'IPC'))   # should return None (doesn't exist)
print(lookup_section('21',  'Constitution'))  # right to life, active
"
```

---

## Qdrant setup

Qdrant runs via docker-compose. start it before ingestion or citation
checking:

```bash
docker-compose up -d qdrant
```

default ports:
- REST API: `http://localhost:6333`
- gRPC: `localhost:6334`

collection is created automatically on first ingest run if it doesn't
exist. no manual schema setup needed.