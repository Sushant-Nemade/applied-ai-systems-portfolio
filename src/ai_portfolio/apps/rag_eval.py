"""Project 7: portable, deterministic RAG regression metrics."""

from __future__ import annotations

from collections import Counter
import re

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..storage import index

router = APIRouter(prefix="/rag-eval", tags=["7 · RAG evaluation"])


class EvalCase(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    relevant_document_ids: list[str] = Field(default_factory=list)
    relevant_pages: list[int] = Field(default_factory=list)
    answerable: bool = True


class EvalBatch(BaseModel):
    cases: list[EvalCase] = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


class AnswerCase(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    expected_answer: str = Field(min_length=1, max_length=5000)
    predicted_answer: str = Field(min_length=1, max_length=5000)
    valid_source_numbers: list[int] = Field(default_factory=list)
    should_abstain: bool = False


class AnswerBatch(BaseModel):
    cases: list[AnswerCase] = Field(min_length=1, max_length=1000)


def _tokens(value: str) -> Counter[str]:
    return Counter(re.findall(r"[a-z0-9]+", value.lower()))


def _token_f1(expected: str, predicted: str) -> float:
    expected_tokens, predicted_tokens = _tokens(expected), _tokens(predicted)
    overlap = sum((expected_tokens & predicted_tokens).values())
    if not overlap:
        return 0.0
    precision = overlap / sum(predicted_tokens.values())
    recall = overlap / sum(expected_tokens.values())
    return 2 * precision * recall / (precision + recall)


def evaluate_answers(cases: list[AnswerCase]) -> dict:
    details = []
    for case in cases:
        citations = [int(left or right) for left, right in re.findall(r"\[(?:source\s*(\d+)|(\d+))\]", case.predicted_answer, re.I)]
        valid = set(case.valid_source_numbers)
        abstained = bool(re.search(r"\b(?:cannot|can't|could not|insufficient|not enough|unable to)\b", case.predicted_answer, re.I))
        details.append({
            "question": case.question,
            "answer_token_f1": round(_token_f1(case.expected_answer, case.predicted_answer), 4),
            "abstention_correct": abstained == case.should_abstain,
            "citations": citations,
            "citation_validity": round(sum(number in valid for number in citations) / len(citations), 4) if citations else None,
        })
    return {
        "cases": len(cases),
        "mean_answer_token_f1": round(sum(item["answer_token_f1"] for item in details) / len(details), 4),
        "abstention_accuracy": round(sum(item["abstention_correct"] for item in details) / len(details), 4),
        "citation_validity": round(sum(item["citation_validity"] for item in details if item["citation_validity"] is not None) / sum(item["citation_validity"] is not None for item in details), 4) if any(item["citation_validity"] is not None for item in details) else None,
        "details": details,
    }


def evaluate_retrieval(cases: list[EvalCase], top_k: int, search_fn) -> dict:
    details = []
    recalls = []
    reciprocal_ranks = []
    for case in cases:
        hits = search_fn(case.question, top_k)
        relevant = [
            i for i, hit in enumerate(hits, 1)
            if hit["document_id"] in case.relevant_document_ids
            and (not case.relevant_pages or hit["page"] in case.relevant_pages)
        ]
        found = bool(relevant)
        if case.answerable:
            recalls.append(float(found))
            reciprocal_ranks.append(1 / min(relevant) if relevant else 0.0)
        details.append({"question": case.question, "retrieved": len(hits), "relevant_found": found, "first_relevant_rank": min(relevant) if relevant else None})
    return {
        "cases": len(cases),
        "answerable_cases": len(recalls),
        "recall_at_k": round(sum(recalls) / len(recalls), 4) if recalls else None,
        "mean_reciprocal_rank": round(sum(reciprocal_ranks) / len(reciprocal_ranks), 4) if reciprocal_ranks else None,
        "details": details,
    }


@router.post("/run")
def run_evaluation(body: EvalBatch) -> dict:
    return evaluate_retrieval(body.cases, body.top_k, index.search)


@router.post("/answers")
def run_answer_evaluation(body: AnswerBatch) -> dict:
    return evaluate_answers(body.cases)
