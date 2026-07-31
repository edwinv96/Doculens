from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class RetrievalCase:
    case_id: str
    query: str
    expected_sources: tuple[str, ...]


@dataclass(frozen=True)
class RetrievalMetrics:
    evaluated_cases: int
    hit_rate_at_k: float
    mean_reciprocal_rank: float
    expected_source_recall_at_k: float

    def as_dict(self) -> dict[str, int | float]:
        return asdict(self)


def _normalize_source(value: str) -> str:
    return value.strip().casefold().rstrip("/")


def load_cases(path: Path) -> list[RetrievalCase]:
    cases: list[RetrievalCase] = []
    with path.open("r", encoding="utf-8") as input_file:
        for line_number, raw_line in enumerate(input_file, start=1):
            if not raw_line.strip():
                continue
            payload = json.loads(raw_line)
            case_id = str(payload.get("id", "")).strip()
            query = str(payload.get("query", "")).strip()
            expected = tuple(
                str(source).strip()
                for source in payload.get("expected_sources", [])
                if str(source).strip()
            )
            if not case_id or not query or not expected:
                raise ValueError(f"Invalid retrieval case on line {line_number}.")
            cases.append(RetrievalCase(case_id, query, expected))
    if not cases:
        raise ValueError("The evaluation dataset is empty.")
    return cases


def evaluate_retrieval(
    cases: Sequence[RetrievalCase],
    predictions: dict[str, Sequence[str]],
    k: int,
) -> RetrievalMetrics:
    if k <= 0:
        raise ValueError("k must be positive.")
    if not cases:
        raise ValueError("At least one retrieval case is required.")

    hits = 0
    reciprocal_rank_sum = 0.0
    recalled_sources = 0
    total_expected_sources = 0

    for case in cases:
        expected = {_normalize_source(source) for source in case.expected_sources}
        predicted = [
            _normalize_source(source)
            for source in predictions.get(case.case_id, [])[:k]
        ]
        relevant_ranks = [
            index for index, source in enumerate(predicted, start=1) if source in expected
        ]
        if relevant_ranks:
            hits += 1
            reciprocal_rank_sum += 1.0 / relevant_ranks[0]
        recalled_sources += len(expected.intersection(predicted))
        total_expected_sources += len(expected)

    case_count = len(cases)
    return RetrievalMetrics(
        evaluated_cases=case_count,
        hit_rate_at_k=hits / case_count,
        mean_reciprocal_rank=reciprocal_rank_sum / case_count,
        expected_source_recall_at_k=(
            recalled_sources / total_expected_sources if total_expected_sources else 0.0
        ),
    )

