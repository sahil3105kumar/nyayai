# roadmap

## current status

### done

**phase 1 — ocr pipeline** (`feature/ocr` merged)
- `LineSpan` as the base unit — one object per line, real measured bbox,
  no word-level approximation
- `NativeExtractor` — pdfplumber, handles digitally created PDFs
- `SuryaExtractor` — surya-ocr 0.9.3, handles scanned PDFs, GPU
- `router.py` — one pass: extract native spans + identify scanned pages
- `pipeline.py` — `extract(pdf_path) -> list[LineSpan]`
- chunked batching in surya (4 pages per call) to stay within 6GB VRAM
- tested on real scanned marksheet — OCR working correctly

**phase 2 — model scaffold** (`feature/model` in progress)
- `ErrorSpan` dataclass with BIO label scheme (9 labels including ENT)
- `preprocess.py` — sliding window chunking (512 tokens, 128 stride),
  subword alignment via `word_ids()`, `token_to_span` mapping
- `predict.py` — InLegalBERT inference, dynamic padding, checkpoint
  detection, graceful fallback to all-O labels
- `postprocess.py` — BIO decoding, bbox merging, orphan I-label recovery,
  confidence from softmax probabilities
- `citation_checker.py` — regex extraction (IPC/BNS/BNSS/CrPC/Constitution),
  Qdrant exact-field lookup, graceful degradation if Qdrant down
- `entity_checker.py` — spacy NER, rapidfuzz clustering (threshold=85),
  canonical form detection, deviation flagging
- `pipeline/engine.py` — orchestrates ML + rules, deduplication,
  reading-order sort

**project structure finalised** — frozen, no more restructuring

---

## what's next (in order)

### 1. corpus ingestion (`feature/corpus`)
populate Qdrant with IPC, BNS, BNSS, Constitution, CPC sections.
this unblocks citation checking which currently returns empty because
Qdrant has no data.

files to build:
```
corpus/parser.py
corpus/chunker.py
corpus/embeddings.py
corpus/uploader.py
corpus/schemas.py
corpus/search.py
scripts/ingest_corpus.py
```

done when: `rules/citation_checker.py` correctly flags "Section 999 IPC"
and correctly passes "Section 302 IPC" (with a suggestion to use
Section 103 BNS instead).

### 2. fine-tuning pipeline (`feature/finetune`)
generate synthetic training data and fine-tune InLegalBERT for token
classification. this is the piece that makes ML error detection real.

files to build:
```
train/dataset.py
train/collator.py
train/train.py
train/metrics.py
train/evaluate.py
```

plus a synthetic data generator (separate branch or scripts/):
```
scripts/generate_data.py   # corrupts real legal text into training pairs
```

done when: `model/checkpoint/` is populated with fine-tuned weights and
`predict.py` starts returning real spelling/grammar/citation predictions.

### 3. renderer (`feature/renderer`)
draw highlight boxes on the original PDF and generate reports.
this is what makes the output actually usable.

files to build:
```
renderer/annotate_pdf.py
renderer/colors.py
renderer/report.py
renderer/html_report.py
```

done when: given a real FIR PDF and a list of ErrorSpans, produces an
annotated PDF with colored boxes at the correct positions.

### 4. API + workers (`feature/api`)
FastAPI + Celery + Redis async job processing.

files to build:
```
api/main.py
api/routes/upload.py
api/routes/jobs.py
api/routes/health.py
api/schemas/
workers/celery_app.py
workers/tasks.py
services/analysis.py
services/storage.py
config/settings.py
config/log_config.py
```

done when: can POST a PDF, poll for status, get annotated PDF + error
JSON back via HTTP.

### 5. frontend (`feature/frontend`)
React viewer with PDF canvas and highlight overlay.

files to build:
```
frontend/src/PdfCanvas.jsx
frontend/src/HighlightOverlay.jsx
frontend/src/api.js
frontend/src/App.jsx
frontend/src/UploadPage.jsx
```

done when: upload a PDF in the browser, see it rendered with colored
highlights once the backend finishes.

---

## known limitations

**OCR:**
- surya OCR is slow (~10s per scanned page on RTX 4050). no fix planned
  for now — async processing via Celery hides the latency from the user.
- surya 0.9.3 is frozen — 18+ months behind current surya. upgrading
  to surya 2.x requires vllm which has Docker + NVIDIA Container Toolkit
  dependencies. not worth it until 0.9.3 causes a real correctness problem.
- `transformers` pinned at `4.48.0` because newer versions break surya
  0.9.3's `SuryaOCRConfig` with `KeyError: 'encoder'`.

**entity checker:**
- `en_core_web_sm` handles Indian names poorly. "Ramesh Kumar" is not
  always detected as a PERSON entity. needs a fine-tuned Indian legal NER
  model (e.g. InLegalBERT fine-tuned on Kalamkar NER corpus).
- greedy clustering misses some same-entity pairs where both forms are
  equally frequent. better: agglomerative clustering with a distance matrix.

**model:**
- no fine-tuned weights yet. ML error detection returns nothing until
  `feature/finetune` is complete.
- no correction suggestions. `ErrorSpan.suggestion` is empty for
  ML-detected errors. citations have suggestions (from corpus payload).
  adding corrections would need a seq2seq model (T5/mT5 fine-tuned on
  legal correction pairs).
- spelling checker via ML is overkill for simple typos. consider adding
  a rule-based spell checker (pyspellchecker with a custom legal dictionary)
  to `rules/` as a complement to the model.

**corpus:**
- IPC → BNS conversion mappings need to be sourced from verified official
  documents only. no fabricated mappings. this slows down corpus building
  but wrong mappings would be worse than no suggestions.
- corpus is static — amendments to BNS/BNSS after ingestion aren't
  reflected until re-ingestion.

**general:**
- no authentication on the API. fine for local use, must be added before
  any deployment.
- no output cleanup. `data/uploads/` and `data/outputs/` will fill disk
  over time. need a periodic cleanup task.
- tested only on English-language legal documents. Hindi/regional language
  support is not planned in current scope.

---

## future ideas (not planned, just worth noting)

**correction suggestions:**
fine-tune a seq2seq model (mT5 or IndicBART) on (erroneous text, corrected
text) pairs to populate `ErrorSpan.suggestion` for spelling/grammar errors.
this is a significant separate project.

**semantic citation search:**
use vector similarity in Qdrant to answer "what BNS section covers the
same offence as IPC 302?" — useful for documents that predate BNS and
need to be updated.

**multi-language support:**
IndicBERT or MuRIL for Hindi/regional language legal documents. FIRs in
Hindi are common in many states. surya OCR already handles Hindi script.

**more rule checkers:**
```
rules/date_checker.py          date formats, logical consistency (date of
                               incident before date of FIR, etc.)
rules/cross_reference.py       "as mentioned in paragraph 3" where
                               paragraph 3 doesn't exist
rules/formatting_checker.py    section numbering, header hierarchy
rules/signature_checker.py     signature/stamp fields missing
```

**document type detection:**
auto-detect document type (FIR, bail application, charge sheet, contract)
and apply type-specific rules. an FIR has different required fields than
a bail application.

**batch processing:**
process multiple documents in one API call. useful for law firms
processing a docket of related documents.

**comparison mode:**
compare two versions of the same document (draft vs amended) and highlight
what changed, not just what's wrong.

---

## dependency decisions (frozen)

these are locked and should not be changed without a specific reason:

| package | version | reason |
|---|---|---|
| surya-ocr | 0.9.3 | 0.20+ needs vllm, too heavy for dev setup |
| transformers | 4.48.0 | newer versions break surya's SuryaOCRConfig |
| torch | 2.4.1+cu124 | stable on RTX 4050, cu124 wheel confirmed working |
| qdrant-client | 1.18.0 | query_points API (not the old search method) |
| rapidfuzz | latest | no breaking changes in this library |
| spacy | latest | en_core_web_sm model version tied to spacy version |

---

## git branch history

```
main
 └─ feature/ocr        merged — OCR pipeline complete
 └─ feature/model      in progress — model scaffold complete
 └─ refactor/structure planned — folder restructure after feature/model merges
 └─ feature/corpus     next — Qdrant population
 └─ feature/finetune   parallel — synthetic data + training
 └─ feature/renderer   after corpus
 └─ feature/api        after renderer
 └─ feature/frontend   last
```