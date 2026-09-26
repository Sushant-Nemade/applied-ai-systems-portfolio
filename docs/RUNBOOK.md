# Single-node operations runbook

## Before starting

1. Create `.env` from `.env.example` and set a random `PORTFOLIO_API_TOKEN` of at least 32 characters.
2. Use `APP_ENV=production` for a deployed service. Set `LLM_PROVIDER=ollama` for local inference. Pull the selected model before model-backed requests.
3. Set `ALLOWED_FETCH_HOSTS` only to domains you are permitted to process.
4. Keep port 8000 bound to localhost. Use a TLS reverse proxy and edge rate limits for remote access.
5. Allocate enough disk for model weights and enough RAM for the selected transformer, Whisper, and Ollama models.

## Health and logs

- `/health/live` confirms the API process is responding.
- `/health/ready` confirms local database access; it does not test model weights or external websites.
- `docker compose logs -f api worker ollama` shows service logs.
- `GET /pr-review/jobs/{delivery_id}` shows a webhook job result or failure.

## Backup and restore

Stop the API and worker before copying the `portfolio_data` volume. The volume holds `documents.db` and `pr_jobs.db`; include SQLite `-wal` and `-shm` files if copying while running. For an online backup, use SQLite's backup API. Restore into a new volume and validate `/health/ready` plus document search before moving traffic.

## Incidents

- **Model unavailable:** Check `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, Ollama service status, and whether the model has been pulled. The API returns 503 for unavailable generation.
- **Article fetch rejected:** Check HTTPS URL, domain allowlist, redirects, content type, and DNS result. Do not disable the public-IP checks to make a source work.
- **Webhook returns 401:** Verify `GITHUB_WEBHOOK_SECRET` and the GitHub App webhook secret are identical. Never log the secret or signature payload.
- **Job failed:** Inspect `/pr-review/jobs/{id}`. Confirm the repo is allowlisted and `GITHUB_TOKEN` has only the permissions needed for that repo.
- **Disk full:** Stop ingestion, back up databases, delete unwanted PDFs via the API, and expand storage. The original PDFs are not persisted, but extracted text is.

## Updates

Run `pytest -q`, review dependency and model release notes, build the image, and test against a staging volume. Use a new container image and keep a backup of the existing data volume for rollback.
