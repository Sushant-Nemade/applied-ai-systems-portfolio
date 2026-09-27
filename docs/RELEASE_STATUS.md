# Release status

This file records observed verification, not planned results.

## Verified locally

- Python 3.12 environment installed the base package and developer dependencies.
- Source compiled with `python -m compileall -q src`.
- Seventeen deterministic tests passed for indexing, route wiring, PDF upload, sentiment response mapping, article extraction, guardrail findings, PR rules and webhook signature, durable job deduplication, citation parsing, voice energy gate, and RAG retrieval and answer metrics.
- `pip check` reported no broken requirements.
- Wikipedia source discovery returned real source titles and extracts for an example query.
- On 2026-09-27, the full optional package set (`ml`, `voice`, `dev`) installed on Windows with Python 3.12, and all 17 tests passed again.
- A local Ollama 0.34.4 server with the `llama3.2` model answered a real uploaded PDF question through the API; upload, retrieval, answer, and deletion all succeeded.
- The local sentiment transformer returned a scored positive prediction through the API.
- Piper generated WAV output, Faster Whisper transcribed it, and `POST /voice/respond` returned a transcript, Ollama answer, and WAV response through the API.
- A Cloudflare Quick Tunnel exposed `/ui`, `/docs`, and `/health/*` successfully. An unauthenticated protected request returned HTTP 401.

## Not yet verified end to end

- Model-backed reviews, news summaries, and research synthesis have not received a live end-to-end test.
- Docker was unavailable locally; Compose build and runtime were not exercised.
- The GitHub webhook has not been installed on a test repository. No review comments have been posted.
- The public Quick Tunnel is temporary and has no uptime target. There is no durable public hosting, load test, backup rehearsal, or external security audit.

The code is a documented single-node self-hosted release candidate. It must not be described as a live production deployment until these gates are completed in the target environment.
