from pathlib import Path
import io

from fastapi.testclient import TestClient
from reportlab.pdfgen import canvas

from ai_portfolio.api import app
from ai_portfolio.storage import DocumentIndex, split_chunks


def test_chunking_and_fts_search(tmp_path: Path):
    db = DocumentIndex(tmp_path / "test.db")
    db.initialize()
    doc = db.add_document("policy.pdf", ["The retention period is thirty days.", "The support team answers questions."])
    assert doc["pages"] == 2
    assert doc["chunks"] == 2
    hits = db.search("retention period")
    assert hits[0]["page"] == 1
    assert hits[0]["document_id"] == doc["document_id"]
    assert db.delete_document(doc["document_id"])
    assert db.search("retention") == []


def test_chunking_preserves_tail():
    text = " ".join(f"word{i}" for i in range(600))
    chunks = split_chunks(text, width=200, overlap=20)
    assert len(chunks) > 5
    assert "word599" in chunks[-1]


def test_routes_and_empty_pdf_answer():
    with TestClient(app) as client:
        assert client.get("/health/live").status_code == 200
        assert len(client.get("/").json()["projects"]) == 8
        response = client.post("/pdf/ask", json={"question": "Where is the missing policy?"})
        assert response.status_code == 200
        assert response.json()["sources"] == []


def test_upload_search_delete_real_pdf():
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer)
    page.drawString(72, 750, "The retention period is thirty days for this policy.")
    page.save()
    with TestClient(app) as client:
        uploaded = client.post("/pdf/documents", files={"file": ("policy.pdf", buffer.getvalue(), "application/pdf")})
        assert uploaded.status_code == 200, uploaded.text
        document_id = uploaded.json()["document_id"]
        found = client.post("/pdf/search", json={"question": "retention period"})
        assert found.status_code == 200
        assert any(hit["document_id"] == document_id for hit in found.json()["results"])
        assert client.delete(f"/pdf/documents/{document_id}").status_code == 200
