# Release status

This file records observed verification, not planned results.

## Verified locally

- Python 3.12 environment installed the base package and developer dependencies.
- Source compiled with `python -m compileall -q src`.
- Seventeen deterministic tests passed for indexing, route wiring, PDF upload, sentiment response mapping, article extraction, guardrail findings, PR rules and webhook signature, durable job deduplication, citation parsing, voice energy gate, and RAG retrieval and answer metrics.
- `pip check` reported no broken requirements.
- Wikipedia source discovery returned real source titles and extracts for an example query.

## Not yet verified end to end

- No Ollama process or local model was installed in the authoring environment. Model-backed answers, reviews, summaries, and research synthesis have not received a live model test.
- Optional transformer, Faster Whisper, and OS TTS packages and model weights have not been run against real input.
- Docker was unavailable locally; Compose build and runtime were not exercised.
- The GitHub webhook has not been installed on a test repository. No review comments have been posted.
- There is no public hosting, load test, uptime target, backup rehearsal, or external security audit.

The code is a documented single-node self-hosted release candidate. It must not be described as a live production deployment until these gates are completed in the target environment.
