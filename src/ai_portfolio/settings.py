"""Runtime configuration. No secrets are stored in source control."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(override=False)


@dataclass(frozen=True)
class Settings:
    environment: str
    api_token: str
    data_dir: Path
    openai_api_key: str
    openai_model: str
    llm_provider: str
    ollama_base_url: str
    ollama_model: str
    allowed_fetch_hosts: tuple[str, ...]
    github_webhook_secret: str
    github_token: str
    github_allowed_repositories: tuple[str, ...]
    auto_post_reviews: bool

    @classmethod
    def from_env(cls) -> "Settings":
        hosts = tuple(
            host.strip().lower()
            for host in os.getenv("ALLOWED_FETCH_HOSTS", "").split(",")
            if host.strip()
        )
        return cls(
            environment=os.getenv("APP_ENV", "production").lower(),
            api_token=os.getenv("PORTFOLIO_API_TOKEN", ""),
            data_dir=Path(os.getenv("DATA_DIR", "./data")).resolve(),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-6-luna"),
            llm_provider=os.getenv("LLM_PROVIDER", "ollama").lower(),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            allowed_fetch_hosts=hosts,
            github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            github_allowed_repositories=tuple(item.strip().lower() for item in os.getenv("GITHUB_ALLOWED_REPOSITORIES", "").split(",") if item.strip()),
            auto_post_reviews=os.getenv("AUTO_POST_REVIEWS", "false").lower() == "true",
        )

    def validate(self) -> None:
        if self.llm_provider not in {"ollama", "openai"}:
            raise RuntimeError("LLM_PROVIDER must be ollama or openai")
        if self.environment == "production" and len(self.api_token) < 32:
            raise RuntimeError("PORTFOLIO_API_TOKEN must be at least 32 characters in production")
        self.data_dir.mkdir(parents=True, exist_ok=True)


settings = Settings.from_env()
