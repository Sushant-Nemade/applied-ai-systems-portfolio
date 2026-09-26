import asyncio
from dataclasses import replace

from fastapi.testclient import TestClient

from ai_portfolio.api import app
from ai_portfolio.apps import news, research
from ai_portfolio.fetch import FetchRejected, validate_url
from ai_portfolio.llm import Generated
from ai_portfolio import fetch


def test_eight_project_route_families():
    with TestClient(app) as client:
        paths = client.get("/openapi.json").json()["paths"]
        for prefix in ["/pdf", "/sentiment", "/news", "/pr-review", "/research", "/voice", "/rag-eval", "/guardrails"]:
            assert any(path.startswith(prefix) for path in paths)
        assert client.post("/guardrails/scan", json={"text": "safe text"}).json()["decision"] == "allow"
        assert client.get("/ui").status_code == 200
        assert "Eight applied AI projects" in client.get("/ui").text
        answer_report = client.post("/rag-eval/answers", json={"cases": [{"question": "How long?", "expected_answer": "30 days", "predicted_answer": "30 days [source 1]", "valid_source_numbers": [1]}]})
        assert answer_report.status_code == 200
        assert answer_report.json()["citation_validity"] == 1.0


def test_fetch_allowlist_and_public_dns(monkeypatch):
    monkeypatch.setattr(fetch, "settings", replace(fetch.settings, allowed_fetch_hosts=("example.com",)))
    monkeypatch.setattr(fetch.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("93.184.215.14", 443))])
    assert validate_url("https://example.com/article")
    for url in ["http://example.com/article", "https://other.example/article", "https://example.com:bad/article"]:
        try:
            validate_url(url)
        except FetchRejected:
            pass
        else:
            raise AssertionError(f"Unsafe URL accepted: {url}")
    monkeypatch.setattr(fetch.socket, "getaddrinfo", lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 443))])
    try:
        validate_url("https://example.com/article")
    except FetchRejected:
        pass
    else:
        raise AssertionError("Private IP accepted")


def test_research_report_with_citations(monkeypatch):
    async def fake_generate(instructions, prompt, **kwargs):
        if "subquestions" in instructions:
            return Generated("What changed?\nWhat evidence exists?\nWhat remains uncertain?", [])
        return Generated("Finding [S1]. Counterpoint [S2].", [])

    async def fake_collect(topic, seeds, limit, queries):
        return [
            {"title": "One", "url": "https://example.com/one", "text": "Evidence one."},
            {"title": "Two", "url": "https://example.com/two", "text": "Evidence two."},
        ]

    monkeypatch.setattr(research, "generate", fake_generate)
    monkeypatch.setattr(research, "collect_sources", fake_collect)
    with TestClient(app) as client:
        response = client.post("/research/report", json={"topic": "How have products changed?"})
    assert response.status_code == 200, response.text
    assert len(response.json()["sources"]) == 2
    assert not response.json()["citation_warnings"]


def test_news_summary_is_source_bounded(monkeypatch):
    async def fake_load(url):
        return {"url": url, "title": "Update", "text": "The product has a new feature.", "keywords": ["product"]}

    async def fake_generate(instructions, prompt, **kwargs):
        assert "The product has a new feature" in prompt
        return Generated("- A new feature was announced.", [])

    monkeypatch.setattr(news, "load_article", fake_load)
    monkeypatch.setattr(news, "generate", fake_generate)
    with TestClient(app) as client:
        response = client.post("/news/summarize", json={"url": "https://example.com/update"})
    assert response.status_code == 200
    assert response.json()["title"] == "Update"
