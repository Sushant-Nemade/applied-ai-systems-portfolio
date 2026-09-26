from ai_portfolio.apps import news, sentiment


def test_sentiment_response(monkeypatch):
    monkeypatch.setattr(sentiment, "classifier", lambda: lambda text: [
        {"label": "negative", "score": 0.1},
        {"label": "neutral", "score": 0.2},
        {"label": "positive", "score": 0.7},
    ])
    result = sentiment.predict("Helpful update")
    assert result["label"] == "positive"
    assert result["probabilities"]["positive"] == 0.7


def test_news_extraction_from_supported_html():
    body = " ".join(["The product release includes improved accessibility and new regional controls."] * 8)
    html = f"<html><head><title>Release notes</title></head><body><article><h1>Release notes</h1><p>{body}</p></article></body></html>"
    article = news.extract_article(html, "https://example.com/release")
    assert article["title"] == "Release notes"
    assert "product" in article["text"].lower()
    assert article["keywords"]
