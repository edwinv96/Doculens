from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


def build_health_status(
    data_dir: Path,
    version: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    env = os.environ if environ is None else environ
    provider = env.get("LLM_PROVIDER", "google").strip().lower()
    if provider == "openai_compatible":
        configured = bool(env.get("OPENAI_API_KEY", "").strip() and env.get("OPENAI_BASE_URL", "").strip())
        model = env.get("OPENAI_MODEL", "gpt-4o-mini")
    elif provider == "google":
        configured = bool(env.get("GOOGLE_API_KEY", "").strip())
        model = env.get("GOOGLE_MODEL", "gemini-2.5-flash")
    else:
        configured = False
        model = "unknown"

    vector_path = data_dir / "vector_store"
    try:
        vector_state = "present" if vector_path.is_dir() and any(vector_path.iterdir()) else "empty"
    except OSError:
        vector_state = "unavailable"
    try:
        relevance_floor = float(env.get("RAG_MIN_RELEVANCE_SCORE", "0.25"))
    except ValueError:
        relevance_floor = 0.25
    if not 0.0 <= relevance_floor <= 1.0:
        relevance_floor = 0.25
    try:
        retrieval_k = int(env.get("RAG_RETRIEVAL_K", "12"))
    except ValueError:
        retrieval_k = 12
    if not 0 < retrieval_k <= 100:
        retrieval_k = 12
    return {
        "status": "ok",
        "version": version,
        "provider": {
            "name": provider if provider in {"google", "openai_compatible"} else "unknown",
            "model": model,
            "state": "configured" if configured else "missing",
        },
        "embeddings": {
            "model": env.get("EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
            "state": "configured",
        },
        "retrieval": {
            "top_k": retrieval_k,
            "minimum_relevance_score": relevance_floor,
            "reranking": env.get("RERANK_ENABLED", "true").strip().lower() not in {"0", "false", "no"},
        },
        "vector_store": {"state": vector_state, "reachability": "not_checked"},
    }
