"""Run with `python -m ai_portfolio.worker` beside the API service."""

from __future__ import annotations

import asyncio
from urllib.parse import quote

import httpx

from .apps.pr_review import ReviewInput, review_diff
from .pr_jobs import jobs
from .settings import settings


async def process_job(job: dict) -> dict:
    if not settings.github_token:
        raise RuntimeError("GITHUB_TOKEN is required for webhook processing")
    repository = job["repository"]
    if repository.lower() not in settings.github_allowed_repositories:
        raise RuntimeError("Repository is no longer allowlisted")
    owner, name = repository.split("/", 1)
    pr_url = f"https://api.github.com/repos/{quote(owner)}/{quote(name)}/pulls/{job['pull_number']}"
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github.diff",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(pr_url, headers=headers)
        response.raise_for_status()
        diff = response.text[:100_000]
        review = await review_diff(ReviewInput(diff=diff, filename=repository, include_model=True))
        if settings.auto_post_reviews:
            summary = "## Applied AI review\n\n"
            for item in review["deterministic_findings"]:
                summary += f"- **{item['rule']}** (diff line {item['diff_line']}): {item['message']}\n"
            if review["model_review"]:
                summary += "\n### Model review\n" + review["model_review"][:8000]
            if not review["deterministic_findings"] and not review["model_review"]:
                summary += "No findings from the configured checks."
            post_headers = {**headers, "Accept": "application/vnd.github+json"}
            posted = await client.post(
                f"https://api.github.com/repos/{quote(owner)}/{quote(name)}/issues/{job['pull_number']}/comments",
                headers=post_headers,
                json={"body": summary},
            )
            posted.raise_for_status()
            review["comment_url"] = posted.json().get("html_url")
    return review


async def main() -> None:
    settings.validate()
    jobs.initialize()
    while True:
        job = jobs.claim()
        if job:
            try:
                result = await process_job(job)
                jobs.finish(job["delivery_id"], result=result)
            except Exception as exc:
                jobs.finish(job["delivery_id"], error=str(exc)[:500])
        await asyncio.sleep(3)


if __name__ == "__main__":
    asyncio.run(main())
