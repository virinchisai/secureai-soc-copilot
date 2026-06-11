# SecureAI SOC Copilot

SecureAI SOC Copilot is a beginner-friendly MVP for asking grounded questions
over cybersecurity logs and reports. It combines a FastAPI API, Streamlit UI,
LangChain retrieval pipeline, FAISS vector storage, JWT authentication, and
SQLite audit logging.

## What the MVP does

- Signs a demo analyst in with a JWT access token.
- Accepts `.txt`, `.log`, and text-based `.pdf` files up to a configurable size.
- Extracts and chunks text, creates OpenAI embeddings, and persists a per-user
  FAISS index.
- Persists each original upload under a per-user, per-document directory and
  records its size and SHA-256 checksum.
- Retrieves relevant chunks and asks either OpenAI or Claude to answer only
  from those excerpts.
- Returns citation labels and the exact retrieved source snippets.
- Blocks common prompt-injection phrases before they reach the model.
- Records every question outcome in a local SQLite audit table.
- Runs locally or as two Docker Compose services.

## Architecture

```text
Browser
  |
  v
Streamlit UI :8501
  |
  | JWT-authenticated HTTP requests
  v
FastAPI :8000
  |-- Auth and upload validation
  |-- Text/PDF extraction and LangChain chunking
  |-- OpenAI embeddings -> per-user FAISS index
  |-- Retrieval -> grounded OpenAI or Claude answer
  `-- SQLite document metadata and audit logs
```

Data is stored under `DATA_DIR` and survives Docker restarts through the
`soc_data` volume.

```text
data/
|-- soc_copilot.db
|-- uploads/
|   `-- <user>/<document-id>/<original-filename>
`-- faiss/
    `-- <user>/
        |-- index.faiss
        `-- index.pkl
```

## Project structure

```text
.
|-- backend
|   |-- app
|   |   |-- api              # Auth, documents, chat, and audit routes
|   |   |-- core             # Settings, JWT/password helpers, SQLite
|   |   |-- services         # Extraction, guard, FAISS, and RAG logic
|   |   |-- dependencies.py
|   |   |-- main.py
|   |   `-- schemas.py
|   |-- tests
|   |-- Dockerfile
|   |-- requirements.txt
|   `-- requirements-dev.txt
|-- frontend
|   |-- app.py
|   |-- Dockerfile
|   `-- requirements.txt
|-- .env.example
`-- docker-compose.yml
```

## Quick start with Docker

1. Create the environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set:

   - `JWT_SECRET_KEY` to a long random value.
   - `DEMO_USERNAME` and `DEMO_PASSWORD`.
   - `OPENAI_API_KEY` to a valid API key.
   - `LLM_PROVIDER` to `openai` or `anthropic`.
   - `ANTHROPIC_API_KEY` when using Claude.

3. Build and start:

   ```bash
   docker compose up --build
   ```

   Compose can parse the project without a `.env` file, but the backend will
   stop with a clear error until `OPENAI_API_KEY` is configured.

4. Open:

   - Streamlit UI: <http://localhost:8501>
   - FastAPI docs: <http://localhost:8000/docs>

5. Sign in using the `DEMO_USERNAME` and `DEMO_PASSWORD` from `.env`.

## Run locally without Docker

Python 3.10 or newer is recommended.

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements-dev.txt
pip install -r frontend/requirements.txt
```

Start the API from the repository root:

```bash
PYTHONPATH=backend uvicorn app.main:app --reload --port 8000
```

In a second terminal, using the same virtual environment:

```bash
streamlit run frontend/app.py
```

## Demo flow

1. Upload a small authentication log, incident report, or threat report.
2. Wait for the UI to confirm the number of indexed chunks.
3. Ask a question such as:

   - `Which IP addresses generated failed login attempts?`
   - `Summarize the incident timeline.`
   - `What evidence suggests credential compromise?`
4. Expand the returned sources to inspect the exact supporting excerpts.
5. Review audit records through `GET /api/audit` in the FastAPI docs.

Example log:

```text
2026-06-11T13:05:01Z auth failure user=jsmith src_ip=192.0.2.44
2026-06-11T13:05:12Z auth failure user=jsmith src_ip=192.0.2.44
2026-06-11T13:06:02Z auth success user=jsmith src_ip=192.0.2.44
```

## API endpoints

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `POST` | `/api/auth/token` | Sign in and receive a JWT |
| `GET` | `/api/documents` | List the current user's documents |
| `POST` | `/api/documents/upload` | Extract, chunk, embed, and index a file |
| `POST` | `/api/chat/ask` | Ask a grounded question |
| `GET` | `/api/audit` | List the current user's question audit records |
| `GET` | `/health` | Container/API health check |

## Tests

```bash
PYTHONPATH=backend pytest backend/tests
ruff check backend frontend
```

The unit tests cover file extraction, JWT/password helpers, and the
prompt-injection guard, provider construction, FAISS retrieval, grounded
prompting, and citation validation without making model API calls.

## MVP security notes

- This project intentionally uses one environment-configured demo account.
  Replace it with a user database and registration/admin workflow before
  production use.
- FAISS indexes are isolated by authenticated user ID. LangChain's FAISS loader
  uses Python deserialization, so only indexes created by this application
  should ever be placed in `DATA_DIR`.
- The prompt-injection guard is deliberately simple and cannot guarantee
  detection. The grounded system prompt also treats retrieved text as
  untrusted data.
- Use HTTPS, a secrets manager, rate limiting, malware scanning, stronger file
  inspection, OCR sandboxing, retention rules, and centralized audit storage
  before handling real sensitive evidence.
- Uploaded source files, FAISS indexes, document metadata, checksums, and audit
  records are persisted under `DATA_DIR`.

## Troubleshooting

- **Indexing fails:** verify `OPENAI_API_KEY` and outbound network access.
- **A PDF has no text:** scanned/image-only PDFs require an OCR step, which is
  outside this MVP.
- **Login fails:** confirm the demo credentials in the running service's `.env`.
- **Old data behaves unexpectedly:** stop the app and remove the local `data/`
  directory, or recreate the Docker volume with
  `docker compose down --volumes`.
