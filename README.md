# Bulk Certificate Generator Backend API

A lightweight, robust backend API built with **Python**, **FastAPI**, **SQLAlchemy 2.x**, and **ReportLab** for asynchronous bulk certificate PDF generation with per-recipient failure isolation.

---

## Features

- **Asynchronous Bulk Generation**: Submits certificate creation jobs and returns immediate `202 Accepted` status while processing recipients in the background.
- **Per-Recipient Failure Isolation**: Errors during processing (such as blank recipient names, invalid emails, or PDF rendering failures) fail only that specific recipient. The overall job continues and finishes with status `completed_with_errors`.
- **ReportLab PDF Engine**: Generates single-page, professionally styled landscape PDF certificates stored at `output/<job_id>/<certificate_id>.pdf`.
- **Bulk & Individual Retrieval**: API endpoints to inspect job progress, list generated certificates, download individual certificate PDFs, or download all completed certificates in a single ZIP file.
- **Configurable Database**: Uses SQLite by default via environment variables (`DATABASE_URL`), easily swappable for PostgreSQL in production.

---

## Project Structure

```text
app/
  main.py            # FastAPI app initialization and lifespan
  config.py          # App settings via Pydantic BaseSettings
  database.py        # SQLAlchemy engine, sessionmaker, and DB dependency
  models.py          # Job and Certificate SQLAlchemy 2.x models
  schemas.py         # Pydantic v2 validation and serialization schemas
  services/
    generator.py     # ReportLab PDF certificate layout and file generation
    jobs.py          # Background worker, recipient validation, and failure handling
  routers/
    jobs.py          # API routes (/jobs endpoints)
tests/
  conftest.py        # Isolated test database and temporary output directory fixtures
  test_generator.py  # Tests for ReportLab PDF creation
  test_jobs.py       # Tests for job submission, progress tracking, and PDF/ZIP downloads
  test_validation.py # Tests for payload validation (422) and per-recipient failure isolation
README.md
requirements.txt
```

---

## Setup & Installation

### 1. Prerequisites
- Python 3.11+ installed.

### 2. Clone repository & install dependencies
```bash
# Clone the repository and navigate into project directory
cd "SDE intern"

# Install dependencies
pip install -r requirements.txt
```

---

## How to Run

Start the FastAPI development server with `uvicorn`:

```bash
uvicorn app.main:app --reload
```

The API will be accessible at `http://127.0.0.1:8000`. You can access the interactive Swagger documentation at `http://127.0.0.1:8000/docs`.

---

## How to Run Tests

Run the full test suite using `pytest`:

```bash
pytest -v
```

---

## Example `curl` Commands

### 1. Submit a New Bulk Generation Job (`POST /jobs`)
```bash
curl -X POST "http://127.0.0.1:8000/jobs" \
     -H "Content-Type: application/json" \
     -d '{
       "certificate_title": "Certificate of Excellence",
       "event_name": "Global AI Hackathon 2026",
       "issue_date": "2026-10-07",
       "recipients": [
         {"name": "Alice Johnson", "email": "alice@example.com"},
         {"name": "Bob Smith", "email": "bob@example.com"},
         {"name": "", "email": "invalid_user@example.com"}
       ]
     }'
```

**Response (`202 Accepted`)**:
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
  "status": "pending",
  "total": 3,
  "succeeded": 0,
  "failed": 0
}
```

### 2. Check Job Status & Progress (`GET /jobs/{job_id}`)
```bash
curl -X GET "http://127.0.0.1:8000/jobs/a1b2c3d4-e5f6-7890-abcd-1234567890ab"
```

**Response (`200 OK`)**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
  "status": "completed_with_errors",
  "total": 3,
  "succeeded": 2,
  "failed": 1,
  "certificate_title": "Certificate of Excellence",
  "event_name": "Global AI Hackathon 2026",
  "issue_date": "2026-10-07",
  "created_at": "2026-10-07T20:25:00Z",
  "certificates": [
    {
      "id": "c1111111-1111-1111-1111-111111111111",
      "job_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
      "recipient_name": "Alice Johnson",
      "recipient_email": "alice@example.com",
      "status": "completed",
      "error": null,
      "file_path": "output/a1b2c3d4-e5f6-7890-abcd-1234567890ab/c1111111-1111-1111-1111-111111111111.pdf",
      "created_at": "2026-10-07T20:25:00Z"
    },
    {
      "id": "c2222222-2222-2222-2222-222222222222",
      "job_id": "a1b2c3d4-e5f6-7890-abcd-1234567890ab",
      "recipient_name": "",
      "recipient_email": "invalid_user@example.com",
      "status": "failed",
      "error": "Recipient name cannot be blank",
      "file_path": null,
      "created_at": "2026-10-07T20:25:00Z"
    }
  ]
}
```

### 3. List Job Certificates (`GET /jobs/{job_id}/certificates`)
```bash
curl -X GET "http://127.0.0.1:8000/jobs/a1b2c3d4-e5f6-7890-abcd-1234567890ab/certificates"
```

### 4. Download Single Certificate PDF (`GET /jobs/{job_id}/certificates/{certificate_id}`)
```bash
curl -X GET "http://127.0.0.1:8000/jobs/a1b2c3d4-e5f6-7890-abcd-1234567890ab/certificates/c1111111-1111-1111-1111-111111111111" \
     --output "Alice_Johnson_certificate.pdf"
```

### 5. Download All Certificates as ZIP (`GET /jobs/{job_id}/download`)
```bash
curl -X GET "http://127.0.0.1:8000/jobs/a1b2c3d4-e5f6-7890-abcd-1234567890ab/download" \
     --output "certificates.zip"
```

---

## Design Decisions & Architectural Trade-offs

### Why FastAPI `BackgroundTasks` Was Chosen
FastAPI's built-in `BackgroundTasks` utility was selected for background job execution in this implementation:
- **Simplicity & Zero Extra Infrastructure**: Executes asynchronously in the same Python process without requiring extra brokers, message queues, or worker daemons (such as Redis, RabbitMQ, or worker processes).
- **Lightweight**: Ideal for small-to-medium volume processing where setup complexity must remain minimal and easy to maintain/explain.

### Trade-offs & Limitations
- **Process Lifetime Dependency**: In-process background tasks run in the ASGI application thread/process pool. If the server process restarts, crashes, or is redeployed during job execution, pending background tasks are aborted.
- **Single Instance Scaling**: Workloads cannot be distributed across multiple independent worker nodes out of the box.

### Production Upgrade Path
For high-volume production deployments or multi-server setups:
- **Celery or RQ with Redis / RabbitMQ**: Migrate background job processing to **Celery** or **RQ** backed by a Redis/RabbitMQ message broker.
- **Benefits**:
  1. **Persistence & Reliability**: Tasks are stored safely in a persistent message broker and survive web server restarts.
  2. **Horizontal Scalability**: Worker instances can scale independently from API server instances.
  3. **Monitoring & Retries**: Built-in support for task retries, dead-letter queues, rate limiting, and monitoring via Flower.
