"""One self-hosted FastAPI deployment exposing eight independent projects."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI
from fastapi.responses import FileResponse

from .apps import guardrails, local_voice, news, pdf_chat, pr_review, rag_eval, research, sentiment
from .auth import require_api_token
from .pr_jobs import jobs
from .settings import settings
from .storage import index


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate()
    index.initialize()
    jobs.initialize()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Applied AI Systems Portfolio",
        description="Eight independent applied AI projects with a shared authenticated API. Set up Ollama and optional model packages for local inference.",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.middleware("http")
    async def add_security_headers(request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/health/live", tags=["Operations"])
    def live() -> dict:
        return {"status": "alive"}

    @app.get("/health/ready", tags=["Operations"])
    def ready() -> dict:
        with index.connect() as connection:
            connection.execute("SELECT 1")
        return {"status": "ready", "llm_provider": settings.llm_provider}

    @app.get("/", tags=["Operations"])
    def catalogue() -> dict:
        return {
            "projects": [
                "pdf-chatbot", "sentiment-api", "news-extractor", "pr-review-bot",
                "deep-research", "local-voice", "rag-evaluation", "llm-guardrails",
            ],
            "docs": "/docs",
            "security": "Send X-API-Key on all project endpoints except signed GitHub webhooks",
        }

    @app.get("/ui", include_in_schema=False)
    def dashboard():
        return FileResponse(Path(__file__).parent / "static" / "index.html")

    protected = [pdf_chat.router, sentiment.router, news.router, research.router, local_voice.router, rag_eval.router, guardrails.router]
    for router in protected:
        app.include_router(router, dependencies=[Depends(require_api_token)])
    app.include_router(pr_review.router)
    return app


app = create_app()
