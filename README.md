# NyayAI

An AI-powered error detection tool for Indian legal documents (FIRs, contracts,
court notices). NyayAI ingests a PDF, detects spelling, grammar, and semantic
errors — including wrong IPC/BNS section citations and entity inconsistencies
across a document — and returns an annotated PDF with color-coded highlights
plus a structured report.

**Everything runs locally.** No external OCR or LLM APIs — built for courts,
law firms, and legal aid organisations where document confidentiality and
per-document cost both matter.

---

## Status

| Component | Status |
|---|---|
| OCR (`ocr/`) | ✅ done |
| Model scaffold (`model/`) | ✅ done — no fine-tuned weights yet, returns all-`O` labels |
| Corpus (`corpus/`) | 🟡 infra done (schemas, chunker, embeddings, uploader, search) — act-specific parsers in progress |
| Rules (`rules/`) | ✅ done — see known limitations below |
| Pipeline (`pipeline/`) | ✅ done |
| Renderer (`renderer/`) | ✅ done |
| API + workers (`api/`, `workers/`, `services/`) | ✅ done |
| Frontend (`frontend/`) | 🟡 scaffolded — running against mock data, not yet wired to the real API |
| Fine-tuning (`train/`) | ⬜ not started |


---

## Architecture

Each module has one job. Folder structure is frozen — see `docs/architecture.md`
for the full layout.

```
PDF in
  │
  ▼
ocr/            extract(pdf_path) -> list[LineSpan]
  │
  ▼
pipeline/engine.py
  ├─▶ model/            InLegalBERT token classification -> ErrorSpan
  ├─▶ rules/            citation_checker (via corpus.search), entity_checker
  └─▶ merge -> deduplicate -> reading-order sort
  │
  ▼
renderer/        annotated PDF + JSON report + HTML report
  │
  ▼
services/analysis.py   orchestrates the above for one job_id
  │
  ▼
workers/tasks.py (Celery)  ◀── api/routes/upload.py enqueues
  │
  ▼
api/routes/jobs.py   poll /status/{job_id}, fetch /result/{job_id}
  │
  ▼
frontend/        PDF.js canvas + highlight overlay + margin rail
```

`corpus/` is a separate pipeline that populates Qdrant ahead of time (IPC,
BNS, BNSS, CPC, Constitution) so `rules/citation_checker.py` can do exact
lookups — see `corpus/search.py`. Rules code never talks to Qdrant directly.

---

## Async job processing — no Redis

The API and the Celery worker are separate processes. Rather than adding
Redis as a required service just for task queuing, Celery is configured with:

- **Broker:** the filesystem transport (queued tasks are files under
  `data/celery/broker/`)
- **Result backend:** SQLite via SQLAlchemy (`data/celery/results.sqlite`)

Both are local files — nothing else to run. This is a one-line config swap
to `redis://` or `amqp://` later if this ever needs to scale past one
machine; nothing in `workers/` or `api/` depends on which broker is
configured.

**Two things that matter if you touch this:**
- Every path in `config/settings.py`'s Celery/storage settings must be
  **absolute**, anchored to a `BASE_DIR` derived from the settings file's
  own location — not a relative path. The API process and the worker
  process won't reliably share a working directory, and a relative path
  resolves differently per-process, silently pointing at two different
  physical folders. A task can sit "enqueued" forever with no error if this
  is wrong.
- A Celery worker only consumes queues it's explicitly told to with `-Q`.
  Routing a task to a custom queue (see `workers/queues.py`) doesn't make a
  worker listen on it automatically.

---

## Setup

### Prerequisites
- Python 3.10 (pinned — see dependency table below)
- `uv` package manager
- Node.js (for the frontend)
- Docker (for Qdrant)
- NVIDIA GPU with CUDA, 6GB+ VRAM (for OCR/model inference)

### Install
```bash
uv sync
cp .env.example .env   # fill in as needed
```

### Start Qdrant
```bash
docker-compose up -d qdrant
```

### Run the API
```bash
uv run uvicorn api.main:app --reload
```

### Run a Celery worker
```bash
uv run celery -A workers.celery_app worker --loglevel=info -Q pdf_processing
```
The `-Q pdf_processing` is required — see the note above.

### Run the frontend
```bash
cd frontend
npm install
npm run dev
```

### Ingest the legal corpus (one-time, or after an act is amended)
```bash
uv run python scripts/ingest_corpus.py --all
```

---

## Dependency versions (frozen)

| package | version | reason |
|---|---|---|
| surya-ocr | 0.9.3 | 0.20+ needs vllm, too heavy for dev setup |
| transformers | 4.48.0 | newer versions break surya's `SuryaOCRConfig` |
| torch | 2.4.1+cu124 | stable on RTX 4050, cu124 wheel confirmed working |
| qdrant-client | 1.18.0 | `query_points` API |
| qdrant (server) | v1.15.5 | current stable at time of writing |

---

## Known limitations

- **OCR:** surya is slow (~10s/scanned page on RTX 4050) and frozen at
  0.9.3, 18+ months behind current. Async processing hides the latency;
  the version pin isn't worth revisiting until it causes a real
  correctness problem.
- **Entity checker:** `en_core_web_sm` mislabels entity *types*
  inconsistently across sentences for Indian names — e.g. the same person's
  name tagged `PERSON` in one line and `GPE` in another, which sends it to
  the wrong clustering bucket and it never gets compared against its other
  spelling. Confirmed against real test cases, not just a documented
  assumption. Needs a fine-tuned Indian legal NER model; not planned yet.
- **Model:** no fine-tuned weights — `predict.py` returns all-`O` labels
  until `train/` exists and produces a checkpoint. No correction
  suggestions for ML-detected errors (citations have suggestions, from
  corpus payload).
- **Corpus:** IPC → BNS mappings only come from verified sources
  (`corpus/data/ipc_bns_mapping.py`) — never fabricated or interpolated.
  Corpus is static; amendments after ingestion need re-ingestion.
- **Corpus parsers:** IPC's real PDF has real-world noise a naive parser
  misses — a 13-page table of contents with no dash after section titles,
  footnote reference markers stuck directly against bracket-wrapped
  amended sections (e.g. `7[5. Certain laws...`), at least one section
  missing its period entirely, and repealed sections that simply don't
  appear in the body text at all. In progress.
- **General:** no authentication (fine for local use, must be added before
  any deployment), no output cleanup task yet, English-language documents
  only.

---

## Repository layout

See `docs/architecture.md` for the full frozen folder structure.

this is the updated readme, now compare