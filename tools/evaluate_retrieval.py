from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.langchain_qa_backend import get_vector_store  # noqa: E402
from backend.rag.evaluation import evaluate_retrieval, load_cases  # noqa: E402
from backend.rag.formatting import source_names  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate vector retrieval without calling the chat model."
    )
    parser.add_argument("--cases", type=Path, required=True, help="JSONL evaluation cases")
    parser.add_argument("--k", type=int, default=5, help="Number of retrieved chunks")
    args = parser.parse_args()

    cases = load_cases(args.cases)
    vector_store = get_vector_store()
    predictions = {
        case.case_id: source_names(
            vector_store.similarity_search(case.query, k=args.k),
            k=args.k,
        )
        for case in cases
    }
    metrics = evaluate_retrieval(cases, predictions, k=args.k)
    print(json.dumps(metrics.as_dict(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

