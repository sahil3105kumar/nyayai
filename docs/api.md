# api

## overview

nyayai exposes a REST API built with FastAPI. PDF processing is slow
(30-60 seconds per document) so the API uses an async job pattern —
upload returns immediately with a job ID, the client polls for status,
then fetches the result when done.

base URL: `http://localhost:8000`

---

## async job flow

```
1. POST /upload
   client sends PDF
   server saves file, enqueues celery task
   server returns job_id immediately (< 100ms)

2. GET /status/{job_id}
   client polls every 2-3 seconds
   server returns current status: queued | processing | done | failed

3. GET /result/{job_id}
   client fetches once status = "done"
   server returns annotated PDF URL + error list + stats
```

---

## endpoints

---

### POST /upload

upload a PDF for processing.

**request:**
```
Content-Type: multipart/form-data

file: <pdf binary>
```

**response 200:**
```json
{
  "job_id": "3f7a2b1c-...",
  "status": "queued",
  "message": "document queued for processing"
}
```

**response 400:**
```json
{
  "error": "invalid_file",
  "message": "only PDF files are accepted"
}
```

**response 413:**
```json
{
  "error": "file_too_large",
  "message": "maximum file size is 50MB"
}
```

**notes:**
- max file size: 50MB (configurable in config/settings.py)
- only PDF accepted, validated by content type and magic bytes
- job_id is a UUID4, used for all subsequent requests

---

### GET /status/{job_id}

poll for job status.

**response 200:**
```json
{
  "job_id": "3f7a2b1c-...",
  "status": "processing",
  "stage": "ocr",
  "progress": 0.35
}
```

**status values:**

| status | meaning |
|---|---|
| `queued` | task waiting for a worker |
| `processing` | worker picked it up, running |
| `done` | completed successfully |
| `failed` | error during processing |

**stage values (when status=processing):**

| stage | meaning |
|---|---|
| `ocr` | extracting text from PDF pages |
| `model` | running InLegalBERT inference |
| `rules` | running citation + entity checks |
| `rendering` | annotating PDF with highlights |

**progress:** float 0.0 to 1.0, approximate

**response 404:**
```json
{
  "error": "job_not_found",
  "message": "no job found with id 3f7a2b1c-..."
}
```

---

### GET /result/{job_id}

fetch the completed result. only valid when status = "done".

**response 200:**
```json
{
  "job_id": "3f7a2b1c-...",
  "status": "done",
  "annotated_pdf_url": "/outputs/3f7a2b1c/annotated.pdf",
  "stats": {
    "total_errors": 7,
    "by_type": {
      "spelling": 2,
      "grammar": 1,
      "citation": 3,
      "entity": 1
    },
    "page_count": 4,
    "processing_time_s": 38.2
  },
  "errors": [
    {
      "text": "Section 302 IPC",
      "error_type": "citation",
      "page_no": 1,
      "bbox": [54.0, 301.0, 210.0, 318.0],
      "suggestion": "Section 103 BNS (IPC repealed, see BNS 2023)",
      "confidence": 0.95,
      "highlight_color": "#FF4444"
    },
    {
      "text": "Rakesh Kumar",
      "error_type": "entity",
      "page_no": 3,
      "bbox": [54.0, 180.0, 190.0, 196.0],
      "suggestion": "should be \"Ramesh Kumar\"",
      "confidence": 0.92,
      "highlight_color": "#AA44FF"
    }
  ]
}
```

**response 400 (job not done yet):**
```json
{
  "error": "job_not_ready",
  "message": "job is still processing. poll /status/{job_id} first."
}
```

**response 404:**
```json
{
  "error": "job_not_found",
  "message": "no job found with id 3f7a2b1c-..."
}
```

---

### GET /outputs/{job_id}/annotated.pdf

download the annotated PDF directly.

**response 200:**
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="annotated.pdf"

<pdf binary>
```

**response 404:** job not found or result not ready

---

### GET /health

system health check. useful for docker/k8s liveness probes.

**response 200:**
```json
{
  "status": "ok",
  "qdrant": "connected",
  "redis": "connected",
  "model_checkpoint": "loaded",
  "gpu_available": true
}
```

**response 503 (degraded):**
```json
{
  "status": "degraded",
  "qdrant": "unreachable",
  "redis": "connected",
  "model_checkpoint": "not_found",
  "gpu_available": true
}
```

degraded means the service is running but some features won't work:
- `qdrant: unreachable` → citation checking disabled
- `model_checkpoint: not_found` → ML error detection disabled (returns
  no spelling/grammar errors until checkpoint is loaded)

---

### GET /debug/spans/{job_id}

**dev only — not exposed in production**

returns the raw list[LineSpan] from the OCR step for a given job.
useful for debugging OCR output before the model runs.

**response 200:**
```json
{
  "job_id": "3f7a2b1c-...",
  "span_count": 89,
  "spans": [
    {
      "text": "First Information Report",
      "page_no": 0,
      "source": "native",
      "bbox": [54.0, 80.0, 280.0, 96.0]
    }
  ]
}
```

---

## error response shape

all error responses follow the same shape:

```json
{
  "error": "snake_case_error_code",
  "message": "human readable description"
}
```

**common error codes:**

| code | http status | meaning |
|---|---|---|
| `invalid_file` | 400 | not a PDF or corrupted |
| `file_too_large` | 413 | exceeds 50MB limit |
| `job_not_found` | 404 | unknown job_id |
| `job_not_ready` | 400 | result requested before job done |
| `processing_failed` | 500 | celery task threw an exception |
| `internal_error` | 500 | unexpected server error |

---

## running the API

**start dependencies first:**
```bash
docker-compose up -d   # starts qdrant + redis
```

**start the API:**
```bash
uv run uvicorn api.main:app --reload --port 8000
```

**start a celery worker:**
```bash
uv run celery -A workers.celery_app worker --loglevel=info
```

all three need to be running for the full pipeline to work.

---

## configuration

all API settings live in `config/settings.py` as a pydantic BaseSettings
class, loaded from `.env`:

```python
class Settings(BaseSettings):
    max_file_size_mb: int = 50
    upload_dir: str = "data/uploads"
    output_dir: str = "data/outputs"
    qdrant_url: str = "http://localhost:6333"
    redis_url: str = "redis://localhost:6379"
    debug: bool = False
    # surya batch sizes
    recognition_batch_size: int = 32
    detector_batch_size: int = 4
```

override any setting via `.env` file or environment variable.

---

## frontend integration

the React frontend talks to this API via `frontend/src/api.js`:

```javascript
// upload
const res = await fetch('/upload', { method: 'POST', body: formData })
const { job_id } = await res.json()

// poll
const poll = setInterval(async () => {
  const status = await fetch(`/status/${job_id}`).then(r => r.json())
  if (status.status === 'done') {
    clearInterval(poll)
    fetchResult(job_id)
  }
}, 2000)

// result
const result = await fetch(`/result/${job_id}`).then(r => r.json())
// result.errors -> passed to HighlightOverlay.jsx
// result.annotated_pdf_url -> passed to PdfCanvas.jsx
```

---

## output file lifecycle

uploaded PDFs: `data/uploads/{job_id}.pdf`
annotated PDFs: `data/outputs/{job_id}/annotated.pdf`
JSON report: `data/outputs/{job_id}/report.json`

both input and output are kept until explicitly deleted. in production,
add a cleanup task (e.g. delete outputs older than 24 hours) to avoid
filling disk. this is not implemented yet — add to roadmap.