# Security policy

Report suspected vulnerabilities privately through GitHub's repository security advisory flow if enabled, or contact the repository owner privately. Do not post secrets, exploit payloads, or private user data in public issues.

## Boundaries

- The API is single tenant. All project endpoints except the signed GitHub webhook require the same `X-API-Key` token. Use a random token of at least 32 characters and terminate TLS at an ingress before public exposure.
- `ALLOWED_FETCH_HOSTS` limits news and seed URL ingestion. Only HTTPS is accepted; redirects and private IP answers are rejected. DNS can change between validation and connection, so use an outbound firewall or proxy for stronger SSRF protection.
- Uploaded PDFs are parsed locally. File and page caps reduce resource abuse, but the parser is not an isolation sandbox. Run the container as a non-root user and avoid accepting uploads from untrusted public users without further isolation.
- The PR webhook verifies `X-Hub-Signature-256`, requires a repository allowlist, and deduplicates deliveries by `X-GitHub-Delivery`. Use a GitHub App or token with only the required repository permissions.
- `AUTO_POST_REVIEWS=false` by default. Inspect generated reviews before enabling automated comments.
- Guardrail regexes are a first layer, not a proof of safety. Never give retrieved text authority to choose tools or access private data.

## Deployment controls still required

Public deployment needs HTTPS, edge rate limiting, secret management, backups, dependency updates, and a retention policy. A shared API token is suitable only for one operator or trusted team; add per-user identity and authorization before serving multiple customers.
