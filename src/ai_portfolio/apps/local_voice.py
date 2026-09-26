"""Project 6: fully local file-based voice pipeline (VAD → STT → LLM → TTS)."""

from __future__ import annotations

import asyncio
import base64
import io
import math
import os
import sys
import tempfile
import wave
from array import array
from functools import lru_cache

from fastapi import APIRouter, File, HTTPException, UploadFile

from ..llm import ModelUnavailable, generate

router = APIRouter(prefix="/voice", tags=["6 · Local voice pipeline"])
MAX_AUDIO_BYTES = 10_000_000


def speech_present(wav_bytes: bytes, minimum_rms: int = 125) -> bool:
    """Simple local energy gate. It is a transparent VAD baseline, not speech recognition."""
    try:
        with wave.open(io.BytesIO(wav_bytes), "rb") as audio:
            if audio.getnchannels() != 1 or audio.getsampwidth() != 2:
                raise ValueError("Use 16-bit mono WAV audio")
            frames = audio.readframes(min(audio.getnframes(), audio.getframerate() * 30))
        samples = array("h")
        samples.frombytes(frames)
        if sys.byteorder == "big":
            samples.byteswap()
        return bool(samples) and math.sqrt(sum(value * value for value in samples) / len(samples)) >= minimum_rms
    except (wave.Error, EOFError) as exc:
        raise ValueError("Invalid WAV file") from exc


@lru_cache(maxsize=1)
def stt_model():
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise RuntimeError("Install the voice extra: pip install '.[voice]'") from exc
    return WhisperModel(os.getenv("VOICE_STT_MODEL", "base"), device="cpu", compute_type="int8")


def transcribe_audio(wav_bytes: bytes) -> str:
    if not speech_present(wav_bytes):
        return ""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temporary:
        temporary.write(wav_bytes)
        path = temporary.name
    try:
        segments, _ = stt_model().transcribe(path, vad_filter=True)
        return " ".join(segment.text.strip() for segment in segments).strip()
    finally:
        os.unlink(path)


def synthesize(text: str) -> bytes:
    try:
        import pyttsx3
    except ImportError as exc:
        raise RuntimeError("Install the voice extra: pip install '.[voice]'") from exc
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temporary:
        path = temporary.name
    try:
        engine = pyttsx3.init()
        engine.save_to_file(text, path)
        engine.runAndWait()
        with open(path, "rb") as generated:
            audio = generated.read()
        if not audio.startswith(b"RIFF"):
            raise RuntimeError("System TTS did not produce WAV output")
        return audio
    finally:
        os.unlink(path)


async def read_wav(file: UploadFile) -> bytes:
    if not file.filename or not file.filename.lower().endswith(".wav"):
        raise HTTPException(400, "Upload a mono 16-bit WAV file")
    data = await file.read(MAX_AUDIO_BYTES + 1)
    if len(data) > MAX_AUDIO_BYTES or not data.startswith(b"RIFF"):
        raise HTTPException(400, "Invalid WAV or file exceeds 10 MB")
    return data


@router.post("/transcribe")
async def transcribe(file: UploadFile = File(...)) -> dict:
    data = await read_wav(file)
    try:
        text = await asyncio.to_thread(transcribe_audio, data)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"transcript": text, "speech_detected": bool(text)}


@router.post("/respond")
async def respond(file: UploadFile = File(...)) -> dict:
    data = await read_wav(file)
    try:
        transcript = await asyncio.to_thread(transcribe_audio, data)
        if not transcript:
            return {"transcript": "", "answer": "", "audio_base64": None, "speech_detected": False}
        answer = await generate("Reply helpfully and briefly to the user's spoken request.", transcript, max_output_tokens=300)
        speech = await asyncio.to_thread(synthesize, answer.text)
    except ModelUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"transcript": transcript, "answer": answer.text, "audio_base64": base64.b64encode(speech).decode(), "speech_detected": True}
