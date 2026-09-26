"""Project 8: deterministic controls and inspectable findings for LLM apps."""

from __future__ import annotations

import re

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter(prefix="/guardrails", tags=["8 · LLM guardrails"])

SENSITIVE = {
    "email": re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.I),
    "phone": re.compile(r"(?<!\w)(?:\+?\d[\d .()-]{8,}\d)(?!\w)"),
    "api_key": re.compile(r"\b(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{30,})\b"),
}
INJECTION = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.I),
    re.compile(r"(?:reveal|print|show)\s+(?:the\s+)?(?:system|developer)\s+prompt", re.I),
    re.compile(r"you\s+are\s+now\s+(?:in\s+)?(?:developer|system|admin)\s+mode", re.I),
]
ALLOWED_TOOLS = {"search_documents", "extract_article", "read_public_source"}


class ScanInput(BaseModel):
    text: str = Field(min_length=1, max_length=50_000)
    origin: str = Field(default="user", pattern="^(user|retrieved|tool)$")


class ToolInput(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    arguments: dict = Field(default_factory=dict)


def scan_text(text: str, origin: str) -> dict:
    redacted = text
    findings = []
    for name, pattern in SENSITIVE.items():
        matches = list(pattern.finditer(text))
        if matches:
            findings.append({"kind": name, "count": len(matches), "severity": "high" if name == "api_key" else "medium"})
            redacted = pattern.sub(f"[REDACTED_{name.upper()}]", redacted)
    for pattern in INJECTION:
        if pattern.search(text):
            findings.append({"kind": "possible_prompt_injection", "count": 1, "severity": "high" if origin != "user" else "medium"})
    untrusted_injection = origin != "user" and any(item["kind"] == "possible_prompt_injection" for item in findings)
    decision = "block" if untrusted_injection or any(item["kind"] == "api_key" for item in findings) else "review" if findings else "allow"
    return {"decision": decision, "findings": findings, "redacted_text": redacted}


@router.post("/scan")
def scan(body: ScanInput) -> dict:
    return scan_text(body.text, body.origin)


@router.post("/authorize-tool")
def authorize_tool(body: ToolInput) -> dict:
    return {"allowed": body.name in ALLOWED_TOOLS, "tool": body.name, "reason": "allowlisted" if body.name in ALLOWED_TOOLS else "Tool is not allowlisted"}
