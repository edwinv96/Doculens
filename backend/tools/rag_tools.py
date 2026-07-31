from __future__ import annotations

import logging

from langchain_core.tools import tool

try:
    from ..langchain_qa_backend import get_retrieval_chain, ingest_file, ingest_url
    from ..rag.formatting import format_answer_with_sources
    from ..runtime_config import RuntimeSettings
except ImportError:  # Supports imports from the backend working directory.
    from langchain_qa_backend import get_retrieval_chain, ingest_file, ingest_url
    from rag.formatting import format_answer_with_sources
    from runtime_config import RuntimeSettings


logger = logging.getLogger(__name__)
runtime_settings = RuntimeSettings.from_env()


@tool
async def ingest_knowledge(source: str, type: str) -> str:
    """Index a public URL or an uploaded PDF in the shared vector store."""
    source_type = type
    if source_type == "url":
        success = await ingest_url(source)
    elif source_type == "file":
        try:
            path = runtime_settings.upload_path(source)
        except ValueError as exc:
            return f"Invalid upload: {exc}"
        if not path.exists():
            return f"Uploaded file not found: {path.name}"
        success = await ingest_file(str(path), path.name)
    else:
        return "Unsupported source_type. Use 'url' or 'file'."

    if success:
        return f"Indexed {source_type} source: {source}"
    return f"Could not index {source_type} source: {source}"


@tool(response_format="content_and_artifact")
async def query_knowledge_base(
    query: str,
    source_filter: str | None = None,
):
    """Answer a question from indexed content and return source documents as artifacts."""
    try:
        response = await get_retrieval_chain(source_filter).ainvoke(
            {"input": query, "chat_history": []}
        )
        answer = str(response.get("answer", "")).strip()
        documents = response.get("context", [])
        content = format_answer_with_sources(answer, documents, max_sources=3)
        return content, documents
    except Exception:
        logger.exception("Knowledge-base query failed")
        return "The knowledge base could not answer this query.", []
