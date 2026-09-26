import io
import struct
import wave

from ai_portfolio.apps.local_voice import speech_present
from ai_portfolio.apps.rag_eval import AnswerCase, EvalCase, evaluate_answers, evaluate_retrieval
from ai_portfolio.apps.research import cited_ids


def make_wav(amplitude):
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16000)
        audio.writeframes(struct.pack("<1600h", *([amplitude] * 1600)))
    return buffer.getvalue()


def test_voice_energy_gate():
    assert speech_present(make_wav(1000))
    assert not speech_present(make_wav(0))


def test_research_citation_extraction():
    assert cited_ids("One claim [S1], another [S12], and repeat [S1].") == {1, 12}


def test_rag_metrics():
    cases = [EvalCase(question="Where is retention?", relevant_document_ids=["a"], relevant_pages=[2])]
    report = evaluate_retrieval(cases, 5, lambda query, limit: [{"document_id": "a", "page": 2}])
    assert report["recall_at_k"] == 1.0
    assert report["mean_reciprocal_rank"] == 1.0


def test_answer_metrics_detect_bad_citations_and_abstention():
    cases = [
        AnswerCase(question="How long?", expected_answer="Thirty days", predicted_answer="Thirty days [source 1] [2]", valid_source_numbers=[1]),
        AnswerCase(question="What happened?", expected_answer="No evidence", predicted_answer="I cannot determine this from the evidence.", should_abstain=True),
    ]
    report = evaluate_answers(cases)
    assert report["cases"] == 2
    assert report["abstention_accuracy"] == 1.0
    assert report["citation_validity"] == 0.5
    assert report["details"][0]["answer_token_f1"] > 0
