"""Run `python -m ai_portfolio.eval_cli path/to/cases.jsonl`."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .apps.rag_eval import EvalCase, evaluate_retrieval
from .storage import index


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m ai_portfolio.eval_cli cases.jsonl")
    cases = [EvalCase.model_validate_json(line) for line in Path(sys.argv[1]).read_text(encoding="utf-8").splitlines() if line.strip()]
    index.initialize()
    print(json.dumps(evaluate_retrieval(cases, 5, index.search), indent=2))


if __name__ == "__main__":
    main()
