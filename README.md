# SecureAI SOC Copilot

[![Knowledge Reliability](https://github.com/virinchisai/secureai-soc-copilot/actions/workflows/knowledge-reliability.yml/badge.svg)](https://github.com/virinchisai/secureai-soc-copilot/actions/workflows/knowledge-reliability.yml)

SecureAI SOC Copilot is a beginner-friendly MVP for asking grounded questions
over cybersecurity logs and reports. It combines a FastAPI API, Streamlit UI,
LangChain retrieval pipeline, FAISS vector storage, JWT authentication, and
SQLite audit logging.

## What the MVP does

- Signs a demo analyst in with a JWT access token.
- Accepts `.txt`, `.log`, and text-based `.pdf` files up to a configurable size.
- Extracts and chunks text, creates local Ollama or OpenAI embeddings, and
  persists a per-user FAISS index.
- Persists each original upload under a per-user, per-document directory and
  records its size and SHA-256 checksum.
- Retrieves relevant chunks and asks Ollama, OpenAI, or Claude to answer only
  from those excerpts.
- Returns citation labels and the exact retrieved source snippets.
- Blocks common prompt-injection phrases before they reach the model.
- Records the timestamp, username, retrieved filenames, prompt, status, and
  response summary in a local SQLite audit table.
- Runs locally or as two Docker Compose services.
- Includes GitHub Actions checks for linting, tests, and Compose validation.

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
  |-- Ollama/OpenAI embeddings -> per-user FAISS index
  |-- Retrieval -> grounded Ollama, OpenAI, or Claude answer
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
|-- docs
|   `-- interview-talking-points.md
|-- sample-security-incident.log
|-- .github/workflows/ci.yml
|-- .env.example
`-- docker-compose.yml
```

## Prerequisites

- Docker Desktop with Docker Compose, or Python 3.10+
- Ollama for the default free local mode
- At least 4 GB of available memory for the small local models

Install Ollama from <https://ollama.com/download>. On macOS with Homebrew:

```bash
brew install ollama
```

Download the configured models once:

```bash
ollama pull deepseek-r1:1.5b
ollama pull nomic-embed-text
ollama list
```

Keep the Ollama desktop app running. If you installed only the CLI, run
`ollama serve` in a separate terminal.

## Quick start with Docker

1. Create the environment file:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and set:

   - `JWT_SECRET_KEY` to a long random value.
   - `DEMO_USERNAME` and `DEMO_PASSWORD`.
   - Keep `EMBEDDING_PROVIDER=ollama`.
   - Keep `LLM_PROVIDER=ollama`.

   OpenAI and Anthropic settings are optional and only needed when selecting
   those paid providers.

3. Build and start:

   ```bash
   docker compose up --build -d
   docker compose ps
   ```

   The backend container connects to Ollama running on the host through
   `host.docker.internal`.
   The first local answer may take longer while Ollama loads the model into
   memory; later questions are typically faster.

4. Open:

   - Streamlit UI: <http://localhost:8501>
   - FastAPI docs: <http://localhost:8000/docs>

5. Sign in using the `DEMO_USERNAME` and `DEMO_PASSWORD` from `.env`.

Stop the application without deleting its data:

```bash
docker compose down
```

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

## Provider configuration

The default configuration is fully local and does not require API credit.

| Embeddings | Answer model | Required settings |
| --- | --- | --- |
| Ollama | Ollama | Default; pull both configured Ollama models |
| OpenAI | OpenAI | Set both providers to `openai` and add `OPENAI_API_KEY` |
| OpenAI | Anthropic | Set embeddings to `openai`, chat to `anthropic`, and add both API keys |

To use OpenAI:

```dotenv
EMBEDDING_PROVIDER=openai
LLM_PROVIDER=openai
OPENAI_API_KEY=your-key
```

To use Claude for generation:

```dotenv
EMBEDDING_PROVIDER=openai
LLM_PROVIDER=anthropic
OPENAI_API_KEY=your-openai-key
ANTHROPIC_API_KEY=your-anthropic-key
```

Restart the backend after changing `.env`. Embedding models can have different
vector dimensions, so clear existing data before changing
`EMBEDDING_PROVIDER`.

## Demo flow

1. Sign in and choose **Upload** in the sidebar.
2. Upload the included `sample-security-incident.log`.
3. Wait for the UI to confirm the number of indexed chunks.
4. Choose **Chat** and ask:

   - `Which source IP compromised the account, what privilege escalation occurred, and how was the host contained?`
   - `What suspicious outbound connection occurred, including the source IP, destination IP, port, and amount of data transferred?`
   - `Summarize the incident using only the uploaded evidence.`
5. Expand each source citation to inspect the exact retrieved excerpt.
6. Choose **Audit** to review the username, prompt, evidence files, status, and
   response summary.
7. Return to **Upload** and select **Remove** beside one document, or enable
   **Select all documents** and choose **Remove all selected documents**.

For your own evidence:

1. Upload a small authentication log, incident report, or threat report.
2. Wait for the UI to confirm the number of indexed chunks.
3. Ask a question such as:

   - `Which IP addresses generated failed login attempts?`
   - `Summarize the incident timeline.`
   - `What evidence suggests credential compromise?`
4. Expand the returned sources to inspect the exact supporting excerpts.
5. Review audit records in the UI or through `GET /api/audit`.

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
| `DELETE` | `/api/documents` | Remove all documents owned by the current user |
| `DELETE` | `/api/documents/{document_id}` | Remove one user-owned document and its vectors |
| `POST` | `/api/chat/ask` | Ask a grounded question |
| `GET` | `/api/audit` | List the current user's question audit records |
| `GET` | `/health` | Container/API health check |

## Tests

```bash
PYTHONPATH=backend pytest backend/tests
ruff check backend frontend
```

The test suite covers TXT/LOG/PDF extraction, migration-safe audit storage,
JWT/password helpers, prompt-injection detection, provider construction,
FAISS persistence and retrieval, grounded prompting, structured log answers,
and citation validation without making paid model API calls.

GitHub Actions runs the same lint and test commands for pushes and pull
requests. A separate CodeQL workflow scans Python code on pull requests,
updates to `main`, and a weekly schedule. Dependabot checks backend, frontend,
and GitHub Actions dependencies weekly.

## Check security on GitHub

1. Open the repository's **Security** tab.
2. Review **Code scanning** for CodeQL findings.
3. Review **Dependabot** for vulnerable dependency alerts.
4. Review **Secret scanning** and enable push protection in repository
   **Settings > Security** when available.
5. Open **Actions** and confirm the **CI** and **CodeQL** workflows are green.

For a manual local check:

```bash
ruff check backend frontend
PYTHONPATH=backend pytest -q backend/tests
pip check
git grep -n "sk-" -- .
```

Never commit `.env`, API keys, uploaded evidence, the SQLite database, or FAISS
indexes. See [`SECURITY.md`](SECURITY.md) for vulnerability reporting and the
MVP's security boundaries.

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

- **Indexing fails in local mode:** run `ollama list` and confirm
  `nomic-embed-text` is installed. Also confirm Ollama is running.
- **Chat fails in local mode:** run `ollama list` and confirm
  `deepseek-r1:1.5b` is installed.
- **Docker cannot reach Ollama:** confirm the Ollama desktop app or
  `ollama serve` is running on port `11434`, then restart the backend.
- **A provider was changed after indexing:** embedding dimensions may differ.
  Re-index from a fresh data directory or Docker volume.
- **OpenAI mode fails:** verify `OPENAI_API_KEY` and outbound network access.
- **A PDF has no text:** scanned/image-only PDFs require an OCR step, which is
  outside this MVP.
- **Login fails:** confirm the demo credentials in the running service's `.env`.
- **Old data behaves unexpectedly:** stop the app and remove the local `data/`
  directory, or recreate the Docker volume with
  `docker compose down --volumes`.

Inspect service status and logs:

```bash
docker compose ps
docker compose logs --tail=100 backend frontend
```

## Limitations and roadmap

- Authentication is a single environment-configured demo user, not a user
  database or RBAC system.
- PDFs must contain extractable text; scanned documents need OCR.
- FAISS, SQLite, and uploads are local to one host.
- Ingestion is synchronous and large files can block a request.
- The deterministic prompt-injection guard is a basic first layer, not a
  complete defense.
- Small local language models are private and free to run but can be slower and
  less capable than hosted models.

Production improvements include persistent users and RBAC, hybrid search and
reranking, OCR, asynchronous ingestion, malware scanning, retrieval
evaluation, stronger injection defenses, observability, managed storage, rate
limits, TLS, and deployment hardening.

## License

This project is licensed under the [MIT License](LICENSE).
