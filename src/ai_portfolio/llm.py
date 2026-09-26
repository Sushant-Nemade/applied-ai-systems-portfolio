"""One bounded, injectable interface to OpenAI Responses."""

from __future__ import annotations

from dataclasses import dataclass

import httpx
from openai import AsyncOpenAI

from .settings import settings


class ModelUnavailable(RuntimeError):
    pass


@dataclass
class Generated:
    text: str
    sources: list[dict[str, str]]


async def generate(instructions: str, prompt: str, *, web_search: bool = False, max_output_tokens: int = 1200) -> Generated:
    if settings.llm_provider == "ollama":
        if web_search:
            raise ModelUnavailable("Web search is available only with the OpenAI provider")
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "options": {"num_predict": max_output_tokens},
        }
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(settings.ollama_base_url + "/api/chat", json=payload)
                response.raise_for_status()
                return Generated(text=response.json()["message"]["content"], sources=[])
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            raise ModelUnavailable("Local Ollama is unavailable; install Ollama and pull the configured model") from exc
    if not settings.openai_api_key:
        raise ModelUnavailable("Set OPENAI_API_KEY to enable model-backed features")
    client = AsyncOpenAI(api_key=settings.openai_api_key, timeout=60.0, max_retries=2)
    options = {
        "model": settings.openai_model,
        "instructions": instructions,
        "input": prompt,
        "max_output_tokens": max_output_tokens,
    }
    if web_search:
        options["tools"] = [{"type": "web_search"}]
    response = await client.responses.create(**options)
    citations: dict[str, str] = {}
    for item in response.output:
        for part in getattr(item, "content", []) or []:
            for annotation in getattr(part, "annotations", []) or []:
                if getattr(annotation, "type", "") == "url_citation":
                    url = getattr(annotation, "url", "")
                    if url:
                        citations[url] = getattr(annotation, "title", "") or url
    return Generated(text=response.output_text, sources=[{"url": u, "title": t} for u, t in citations.items()])
