"""Project 2: batch sentiment inference with a local transformer model."""

from __future__ import annotations

import os
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/sentiment", tags=["2 · Sentiment API"])
MODEL_NAME = os.getenv("SENTIMENT_MODEL", "cardiffnlp/twitter-roberta-base-sentiment-latest")


class SentimentInput(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class BatchInput(BaseModel):
    texts: list[str] = Field(min_length=1, max_length=32)


@lru_cache(maxsize=1)
def classifier():
    try:
        from transformers import pipeline
    except ImportError as exc:
        raise RuntimeError("Install the ml extra: pip install '.[ml]'") from exc
    return pipeline("text-classification", model=MODEL_NAME, top_k=None, truncation=True, max_length=512)


def predict(text: str) -> dict:
    try:
        raw = classifier()(text)
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
    if raw and isinstance(raw[0], list):
        raw = raw[0]
    probabilities = {str(item["label"]).lower(): round(float(item["score"]), 6) for item in raw}
    label = max(probabilities, key=probabilities.get)
    return {"label": label, "score": probabilities[label], "probabilities": probabilities, "model": MODEL_NAME}


@router.post("/predict")
def predict_one(body: SentimentInput) -> dict:
    return predict(body.text)


@router.post("/batch")
def predict_batch(body: BatchInput) -> dict:
    if any(not text.strip() or len(text) > 5000 for text in body.texts):
        raise HTTPException(422, "Each text must contain 1–5000 characters")
    return {"predictions": [predict(text) for text in body.texts]}


@router.get("/model")
def model_details() -> dict:
    return {"model": MODEL_NAME, "task": "text-classification", "note": "Scores are model outputs; validate on your own domain before interpreting them as calibrated probabilities."}
