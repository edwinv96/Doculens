from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from backend.rag.formatting import collect_citations, format_answer_with_sources, select_evidence


@dataclass
class FakeDocument:
    page_content: str
    metadata: dict[str, Any]


class RagFormattingTest(unittest.TestCase):
    def test_collect_citations_deduplicates_source_and_page(self) -> None:
        documents = [
            FakeDocument("First chunk", {"source": "guide.pdf", "page": 0}),
            FakeDocument("Duplicate chunk", {"source": "guide.pdf", "page": 0}),
            FakeDocument("Second page", {"source": "guide.pdf", "page": 1}),
        ]

        citations = collect_citations(documents)

        self.assertEqual([citation.label for citation in citations], ["guide.pdf (p.1)", "guide.pdf (p.2)"])

    def test_format_answer_adds_stable_source_labels_and_previews(self) -> None:
        documents = [
            FakeDocument("A   short\nsource excerpt.", {"source": "notes.pdf", "page": 2})
        ]

        output = format_answer_with_sources("The answer.", documents)

        self.assertIn("The answer.", output)
        self.assertIn("[1] notes.pdf (p.3): A short source excerpt.", output)

    def test_format_answer_without_documents_returns_plain_answer(self) -> None:
        self.assertEqual(format_answer_with_sources("  No context.  ", []), "No context.")

    def test_select_evidence_filters_below_threshold_and_caps_count(self) -> None:
        documents = [
            FakeDocument("relevant", {"source": "a.pdf"}),
            FakeDocument("weak", {"source": "b.pdf"}),
            FakeDocument("also relevant", {"source": "c.pdf"}),
        ]

        selected = select_evidence(
            [(documents[0], 0.8), (documents[1], 0.2), (documents[2], 0.7)],
            minimum_score=0.5,
            max_documents=1,
        )

        self.assertEqual(selected, [documents[0]])

    def test_select_evidence_rejects_invalid_configuration(self) -> None:
        with self.assertRaises(ValueError):
            select_evidence([], minimum_score=1.1, max_documents=3)
        with self.assertRaises(ValueError):
            select_evidence([], minimum_score=0.5, max_documents=0)


if __name__ == "__main__":
    unittest.main()
