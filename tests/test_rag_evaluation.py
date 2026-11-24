from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from backend.rag.evaluation import RetrievalCase, evaluate_retrieval, load_cases


class RetrievalEvaluationTest(unittest.TestCase):
    def test_demo_dataset_uses_the_included_sample_document(self) -> None:
        path = Path(__file__).resolve().parents[1] / "evaluation" / "rag_cases.demo.jsonl"
        cases = load_cases(path)

        self.assertGreaterEqual(len(cases), 3)
        self.assertEqual(
            {source for case in cases for source in case.expected_sources},
            {"DocuLens_Demo.pdf"},
        )

    def test_metrics_measure_hit_rank_and_source_recall(self) -> None:
        cases = [
            RetrievalCase("one", "first question", ("a.pdf",)),
            RetrievalCase("two", "second question", ("b.pdf", "c.pdf")),
        ]
        predictions = {
            "one": ["noise.pdf", "a.pdf"],
            "two": ["c.pdf", "noise.pdf"],
        }

        metrics = evaluate_retrieval(cases, predictions, k=2)

        self.assertEqual(metrics.evaluated_cases, 2)
        self.assertEqual(metrics.hit_rate_at_k, 1.0)
        self.assertEqual(metrics.mean_reciprocal_rank, 0.75)
        self.assertAlmostEqual(metrics.expected_source_recall_at_k, 2 / 3)

    def test_missing_prediction_counts_as_a_miss(self) -> None:
        metrics = evaluate_retrieval(
            [RetrievalCase("missing", "question", ("answer.pdf",))],
            {},
            k=3,
        )

        self.assertEqual(metrics.hit_rate_at_k, 0.0)
        self.assertEqual(metrics.mean_reciprocal_rank, 0.0)

    def test_load_cases_reads_jsonl_and_rejects_invalid_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            valid_path = Path(temp_dir) / "valid.jsonl"
            valid_path.write_text(
                json.dumps(
                    {"id": "case-1", "query": "What?", "expected_sources": ["a.pdf"]}
                )
                + "\n",
                encoding="utf-8",
            )

            cases = load_cases(valid_path)

            self.assertEqual(cases[0].case_id, "case-1")
            self.assertEqual(cases[0].expected_sources, ("a.pdf",))

            invalid_path = Path(temp_dir) / "invalid.jsonl"
            invalid_path.write_text('{"id":"missing-fields"}\n', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_cases(invalid_path)


if __name__ == "__main__":
    unittest.main()

