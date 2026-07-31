from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Protocol, Sequence


class DocumentLike(Protocol):
    page_content: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SourceCitation:
    source: str
    preview: str
    page: int | None = None

    @property
    def label(self) -> str:
        if self.page is None:
            return self.source
        return f"{self.source} (p.{self.page + 1})"


def _preview(text: str, limit: int = 160) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 1].rstrip() + "…"


def collect_citations(
    documents: Sequence[DocumentLike],
    max_sources: int = 3,
) -> list[SourceCitation]:
    citations: list[SourceCitation] = []
    seen: set[tuple[str, int | None]] = set()
    for document in documents:
        source = str(document.metadata.get("source", "unknown")).strip() or "unknown"
        raw_page = document.metadata.get("page")
        page = raw_page if isinstance(raw_page, int) and raw_page >= 0 else None
        key = (source, page)
        if key in seen:
            continue
        seen.add(key)
        citations.append(
            SourceCitation(
                source=source,
                page=page,
                preview=_preview(document.page_content),
            )
        )
        if len(citations) >= max_sources:
            break
    return citations


def format_answer_with_sources(
    answer: str,
    documents: Sequence[DocumentLike],
    max_sources: int = 3,
) -> str:
    citations = collect_citations(documents, max_sources=max_sources)
    if not citations:
        return answer.strip()

    lines = [answer.strip(), "", "Sources:"]
    for index, citation in enumerate(citations, start=1):
        lines.append(f"[{index}] {citation.label}: {citation.preview}")
    return "\n".join(lines)


def source_names(documents: Sequence[DocumentLike], k: int | None = None) -> list[str]:
    selected = documents if k is None else documents[:k]
    return [
        str(document.metadata.get("source", "unknown")).strip() or "unknown"
        for document in selected
    ]

