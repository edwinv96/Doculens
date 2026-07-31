from __future__ import annotations

import unittest
from dataclasses import dataclass
from typing import Any

from backend.rag.formatting import collect_citations, format_answer_with_sources


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


if __name__ == "__main__":
    unittest.main()
