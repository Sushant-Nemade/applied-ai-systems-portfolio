# Project guides

All project routes are visible at `/docs`. Each route can be called on its own with `X-API-Key`. The API process and configuration are shared so the eight projects can be run with one local command.

## 1. PDF Chatbot

Upload a text-based PDF to `POST /pdf/documents`; the service extracts pages, splits them into overlapping chunks, and indexes them in SQLite FTS5. `POST /pdf/search` shows the passages retrieved for a question. `POST /pdf/ask` sends those passages to the configured local model and returns an answer plus source documents and page numbers. `GET /pdf/documents` lists uploads; `DELETE /pdf/documents/{id}` removes one.

**Why it matters:** a user can inspect the evidence used for an answer. **Limits:** the index is lexical, not semantic; scanned PDFs need OCR; the model can still make mistakes. Test citation correctness before relying on an answer.

## 2. Sentiment Analysis API

`POST /sentiment/predict` classifies one text; `POST /sentiment/batch` accepts up to 32. The transformer is loaded lazily, so startup stays light. `GET /sentiment/model` reports the configured model. Install the `ml` extra before use. The default model can be overridden with `SENTIMENT_MODEL`.

**Why it matters:** a reusable inference API with a defined batch limit. **Limits:** model outputs are not calibrated confidence estimates and a social-media model may perform poorly on news, clinical, or enterprise text. A domain-specific labelled evaluation is required for any real use case.

## 3. News Article Extractor and Summarizer

Set `ALLOWED_FETCH_HOSTS` to domains you may ingest. `POST /news/extract` downloads up to 2 MB of HTML over HTTPS, rejects redirects, extracts title/date/author/body, and returns frequent keywords. `POST /news/summarize` asks the local model for a concise summary using that extracted body only.

**Why it matters:** demonstrates a constrained source ingestion boundary and grounded summarization. **Limits:** extraction varies by publisher and cannot bypass paywalls or usage rules. The service does not republish an article on its own.

## 4. AI Code Review Bot

`POST /pr-review/review` accepts a unified diff. Deterministic rules check newly added lines for dynamic execution, shell use, hard-coded credentials, and unsafe deserialization. The local model optionally adds a short review. For automation, configure a GitHub webhook at `POST /pr-review/webhook`, set `GITHUB_WEBHOOK_SECRET`, `GITHUB_TOKEN`, and `GITHUB_ALLOWED_REPOSITORIES`, then run `python -m ai_portfolio.worker`. Delivery IDs are deduplicated and jobs can be inspected at `GET /pr-review/jobs/{id}`.

**Why it matters:** demonstrates event verification, asynchronous work, and review quality controls. **Limits:** rule matches are prompts for human review, not vulnerability proofs. Automatic GitHub comments require `AUTO_POST_REVIEWS=true`; start with false and inspect results. Do not install this on repositories you cannot authorize.

## 5. Deep Research Agent

`POST /research/report` accepts a topic and optional `seed_urls`. The model creates three subquestions. Without seed URLs, the service uses public Wikipedia search as a free background source. With seed URLs, it extracts permitted articles from the allowlist. The final report includes source IDs such as `[S1]`, a source list, and warnings for unknown or missing citations.

**Why it matters:** shows source-led planning and a traceable report. **Limits:** Wikipedia-only discovery is introductory, not a professional literature review. For a serious domain report, supply high-quality permitted sources and verify every important claim manually. Source count is capped at 20 to bound cost and context.

## 6. Local Voice Pipeline

Install `.[voice]`, download a Piper voice as shown in the README, and set `VOICE_TTS_MODEL` to its `.onnx` file. `POST /voice/transcribe` accepts a mono 16-bit WAV file. A transparent energy gate skips silence; Faster Whisper transcribes speech locally. `POST /voice/respond` adds a local Ollama answer and Piper speech synthesis, returning a transcript, answer, and base64 WAV response.

**Why it matters:** a fully local speech-in → language model → speech-out pipeline. **Limits:** this implementation processes a complete WAV file per request. It does not claim the low-latency streaming behavior of the upstream Hugging Face project. OS TTS needs a speech engine; the Dockerfile includes eSpeak. The STT model downloads on first use. A microphone and real-time latency benchmark were unavailable during development.

## 7. RAG Evaluation Suite

`POST /rag-eval/run` accepts labelled questions with relevant document IDs and optional pages. It runs the PDF index and computes recall at k and mean reciprocal rank, with per-question details. `POST /rag-eval/answers` accepts a labelled expected answer, a generated answer, valid source numbers, and whether the answer should abstain. It computes token F1, abstention accuracy, and citation-number validity. To run a versioned retrieval JSONL dataset from the command line, use `python -m ai_portfolio.eval_cli cases.jsonl`.

**Why it matters:** retrieval and answer behavior can be compared after changing chunking, ranking, or prompting. **Limits:** token overlap and valid citation numbers do not establish that the cited passage supports a claim. Human scoring is still needed before claiming answer faithfulness.

## 8. LLM Guardrails and Defense

`POST /guardrails/scan` finds likely email addresses, phone numbers, API keys, and several common instruction-override strings. It returns a decision, findings, and redacted text. `POST /guardrails/authorize-tool` allows only three named read-only tools; unknown tools are denied.

**Why it matters:** a transparent policy boundary that can be tested and extended. **Limits:** regular expressions miss many attacks and can produce false positives. It is a defense layer, not a complete security guarantee. See [OWASP LLM01](https://genai.owasp.org/llmrisk/llm01-prompt-injection/).

## Upstream inspiration

The eight links from the original post resolve to these projects. They informed scope; no upstream source code was copied:

1. [mayooear/ai-pdf-chatbot-langchain](https://github.com/mayooear/ai-pdf-chatbot-langchain)
2. [curiousily/Deploy-BERT-for-Sentiment-Analysis-with-FastAPI](https://github.com/curiousily/Deploy-BERT-for-Sentiment-Analysis-with-FastAPI)
3. [codelucas/newspaper](https://github.com/codelucas/newspaper)
4. [The-PR-Agent/pr-agent](https://github.com/The-PR-Agent/pr-agent)
5. [assafelovic/gpt-researcher](https://github.com/assafelovic/gpt-researcher)
6. [huggingface/speech-to-speech](https://github.com/huggingface/speech-to-speech)
7. [confident-ai/deepeval](https://github.com/confident-ai/deepeval)
8. [NVIDIA-NeMo/Guardrails](https://github.com/NVIDIA-NeMo/Guardrails)
