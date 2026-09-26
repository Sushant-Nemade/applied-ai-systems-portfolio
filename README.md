# Applied AI Systems Portfolio

Eight original, self-hosted applied AI services in one Python repository. Each project has its own API route and can be used independently. The common FastAPI process provides authentication, configuration, health checks, and OpenAPI documentation.

> **Deployment status:** Source code and automated tests are provided. No public service is hosted from this repository. Model-backed routes need a local Ollama model or an explicitly configured OpenAI API key. The optional sentiment and voice routes need additional local model packages. See [release status](docs/RELEASE_STATUS.md) before calling this production deployed.

## Projects

| # | Project | Entry point | What it demonstrates |
|---|---|---|---|
| 1 | PDF Chatbot | `/pdf` | Text extraction, page-aware FTS retrieval, grounded answers |
| 2 | Sentiment Analysis API | `/sentiment` | Batch local transformer inference and model metadata |
| 3 | News Extractor + Summarizer | `/news` | Allowlists, HTML extraction, keywords, grounded summaries |
| 4 | AI Code Review Bot | `/pr-review` | Diff review, signed webhook ingestion, durable jobs |
| 5 | Deep Research Agent | `/research` | Subquestion planning, source collection, cited reports |
| 6 | Local Voice Pipeline | `/voice` | Audio energy gate, local STT, local LLM, system TTS |
| 7 | RAG Evaluation Suite | `/rag-eval` | Portable retrieval regression metrics |
| 8 | LLM Guardrails | `/guardrails` | PII masking, instruction-override checks, tool allowlist |

The source links in the [original project list](docs/PROJECT_GUIDES.md#upstream-inspiration) are credited as inspiration. This repository does not copy their code.

## Quick start without cloud spending

Requires Python 3.11 or 3.12. Use a virtual environment:

```bash
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install -e '.[dev]'
```

Copy `.env.example` to `.env`. Set `PORTFOLIO_API_TOKEN` to a random value of at least 32 characters. The app loads `.env` automatically. Keep it out of Git.

Install [Ollama](https://ollama.com/download), then download the model selected in `.env`:

```bash
ollama pull llama3.2
uvicorn ai_portfolio.api:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000/ui` for the local dashboard, or `http://127.0.0.1:8000/docs` for the interactive API. Protected endpoints require the `X-API-Key` header. The root catalogue and `/health/*` are public. Ollama runs entirely on the local computer; a model download and suitable memory are required. The application does not silently switch to a paid provider. [Ollama chat API](https://docs.ollama.com/api/chat)

For sentiment and voice models, install the optional extras:

```bash
python -m pip install -e '.[ml,voice,dev]'
```

The first sentiment and transcription calls download model weights. Review the model licenses and hardware requirements before using a model commercially.

## Docker Compose

Docker Compose builds the API and PR worker, runs a local Ollama server, and persists model and document data in named volumes. A token in `.env` is mandatory. Pull the local model once after startup:

```bash
docker compose up -d --build
docker compose exec ollama ollama pull llama3.2
docker compose ps
```

The API is bound to `127.0.0.1:8000`. Add a TLS terminating reverse proxy and network rate limits before exposing it to the public internet. Docker was unavailable in the authoring environment, so the Compose image has not been build-verified; see [release status](docs/RELEASE_STATUS.md).

## Try the endpoints

Set a shell variable `TOKEN` to the same value as `PORTFOLIO_API_TOKEN`.

```bash
curl -H "X-API-Key: $TOKEN" -F "file=@sample.pdf" http://127.0.0.1:8000/pdf/documents
curl -H "X-API-Key: $TOKEN" -H "Content-Type: application/json" \
  -d '{"question":"What is the retention period?"}' http://127.0.0.1:8000/pdf/ask
curl -H "X-API-Key: $TOKEN" -H "Content-Type: application/json" \
  -d '{"text":"The update is useful."}' http://127.0.0.1:8000/sentiment/predict
curl -H "X-API-Key: $TOKEN" -H "Content-Type: application/json" \
  -d '{"topic":"How do open source LLMs affect enterprise software?"}' http://127.0.0.1:8000/research/report
```

See [project guides](docs/PROJECT_GUIDES.md) for the eight workflows, expected inputs, and limitations.

## Engineering design

```text
User / API client
      │ X-API-Key
      ▼
FastAPI catalogue and eight routers
      ├─ PDF index / PR job queue ── SQLite volumes
      ├─ source fetching ──────────── allowlisted HTTPS hosts
      ├─ model gateway ────────────── Ollama by default; OpenAI optional
      └─ PR worker ─────────────────── signed GitHub events and allowlisted repos
```

- **Single tenant:** one shared API token and one local document index. This avoids implying multi-tenant isolation that is not implemented.
- **Local default:** Ollama for generation, a local transformer for sentiment, Faster Whisper for transcription, and OS speech synthesis for replies.
- **Source provenance:** PDF answers return the retrieved document/page excerpts; research reports return source URLs and warn about invalid citation IDs.
- **Bounded inputs:** file, batch, source, context, and output limits control resource use.
- **Webhook isolation:** GitHub deliveries are verified and queued. The worker handles model/API work outside the webhook request. Automatic comment posting is off by default.
- **Portable evaluation:** RAG retrieval cases are JSONL; answer overlap, abstention, and citation validity can be scored through the API without a hosted evaluation platform.

## Tests

```bash
python -m compileall -q src
pytest -q
```

GitHub Actions runs these checks on every push and pull request. The test suite uses local fixtures and does not incur model API fees. Check [release status](docs/RELEASE_STATUS.md) for coverage and unverified integrations.

## Security and data handling

Read [SECURITY.md](SECURITY.md) and [operations runbook](docs/RUNBOOK.md). The news fetcher accepts only configured HTTPS hosts and rejects private IP destinations and redirects. Do not allowlist a domain you do not trust to serve public articles. PDF text and PR review records are kept in local SQLite volumes; back them up or delete them according to your retention policy. `.env`, database files, PDFs, WAV files, and model weights are ignored by Git.

The guardrails module reports inspectable findings. Pattern detection is a baseline and does not guarantee protection against every prompt injection. Keep tool permissions narrow and evaluate against adversarial examples. [OWASP prompt injection guidance](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

## License

MIT for code in this repository. Third-party models and libraries have their own licenses.
