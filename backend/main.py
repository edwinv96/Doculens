from __future__ import annotations

import logging
import uuid
from collections.abc import AsyncIterator, Callable
from typing import Any
from pathlib import Path

from dotenv import load_dotenv

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# Load backend-only settings before creating paths or describing runtime health.
load_dotenv(Path(__file__).with_name(".env"))

try:
    from .runtime_config import RuntimeSettings
    from .health_status import build_health_status
except ImportError:  # Supports `uvicorn main:app` from the backend directory.
    from runtime_config import RuntimeSettings
    from health_status import build_health_status


logger = logging.getLogger(__name__)
settings = RuntimeSettings.from_env()
settings.ensure_directories()

app = FastAPI(
    title="DocuLens Backend API",
    description="A traceable RAG agent with document ingestion, source citations, and tool calling.",
    version="7.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


class AgentChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20_000)
    thread_id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=1, max_length=128)
    source_filter: str | None = Field(default=None, max_length=512)


class AgentChatResponse(BaseModel):
    response: str


class FileUploadResponse(BaseModel):
    filename: str
    message: str


class EvaluationRequest(BaseModel):
    k: int = Field(default=5, ge=1, le=20)


def _load_agent_functions() -> tuple[Callable[..., Any], Callable[..., AsyncIterator[str]]]:
    try:
        from .agent_service import chat_with_agent, chat_with_agent_stream
    except ImportError:
        from agent_service import chat_with_agent, chat_with_agent_stream
    return chat_with_agent, chat_with_agent_stream


def _load_ingest_file() -> Callable[..., Any]:
    try:
        from .langchain_qa_backend import ingest_file
    except ImportError:
        from langchain_qa_backend import ingest_file
    return ingest_file


async def _save_upload(file: UploadFile) -> tuple[str, str, int]:
    try:
        destination = settings.upload_path(file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    total_bytes = 0
    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)
                if total_bytes > settings.max_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Upload exceeds the {settings.max_upload_bytes}-byte limit.",
                    )
                output.write(chunk)
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    return str(destination), destination.name, total_bytes


@app.get("/", tags=["Health Check"])
def read_root() -> dict[str, str]:
    return {"status": "ok", "message": "DocuLens backend is ready."}


@app.get("/health", tags=["Health Check"])
def read_health() -> dict[str, Any]:
    return build_health_status(settings.data_dir, app.version)


def _load_document_inventory() -> list[dict[str, Any]]:
    vector_path = settings.data_dir / "vector_store"
    if not vector_path.is_dir() or not any(vector_path.iterdir()):
        return []
    try:
        from .langchain_qa_backend import get_vector_store
    except ImportError:
        from langchain_qa_backend import get_vector_store

    stored = get_vector_store().get(include=["metadatas"])
    inventory: dict[str, dict[str, Any]] = {}
    for metadata in stored.get("metadatas", []) or []:
        if not metadata:
            continue
        source = str(metadata.get("source", "")).strip()
        if not source:
            continue
        entry = inventory.setdefault(
            source,
            {
                "filename": source,
                "source_type": metadata.get("type", "unknown"),
                "document_id": metadata.get("document_id"),
                "file_size": metadata.get("file_size"),
                "uploaded_at": metadata.get("uploaded_at"),
                "chunk_count": 0,
                "status": "indexed",
            },
        )
        entry["chunk_count"] += 1
    return sorted(inventory.values(), key=lambda item: item["filename"].casefold())


@app.get("/documents", tags=["File Management"])
def list_documents() -> dict[str, Any]:
    try:
        documents = _load_document_inventory()
    except Exception as exc:
        logger.exception("Document inventory could not be read")
        raise HTTPException(status_code=503, detail="The document index is unavailable.") from exc
    return {"documents": documents, "count": len(documents)}


@app.post("/evaluation/run", tags=["Evaluation"])
def run_evaluation(request: EvaluationRequest) -> dict[str, Any]:
    cases_path = Path(__file__).resolve().parent.parent / "evaluation" / "rag_cases.demo.jsonl"
    if not cases_path.is_file():
        raise HTTPException(status_code=404, detail="The demonstration evaluation dataset is missing.")
    try:
        indexed_documents = _load_document_inventory()
    except Exception as exc:
        logger.exception("Evaluation could not inspect the document index")
        raise HTTPException(status_code=503, detail="The document index is unavailable.") from exc
    if not indexed_documents:
        raise HTTPException(status_code=409, detail="Index the demonstration PDF before running evaluation.")

    try:
        try:
            from .langchain_qa_backend import get_vector_store
            from .rag.evaluation import evaluate_retrieval, load_cases
            from .rag.formatting import source_names
        except ImportError:
            from langchain_qa_backend import get_vector_store
            from rag.evaluation import evaluate_retrieval, load_cases
            from rag.formatting import source_names

        cases = load_cases(cases_path)
        vector_store = get_vector_store()
        predictions = {
            case.case_id: source_names(vector_store.similarity_search(case.query, k=request.k), k=request.k)
            for case in cases
        }
        metrics = evaluate_retrieval(cases, predictions, k=request.k)
    except Exception as exc:
        logger.exception("Retrieval evaluation failed")
        raise HTTPException(status_code=503, detail="Retrieval evaluation could not complete.") from exc

    return {
        "dataset": cases_path.name,
        "evaluated_cases": metrics.evaluated_cases,
        "k": request.k,
        "metrics": metrics.as_dict(),
        "status": "completed",
    }


@app.post("/chat/stream", tags=["Agent Chat"])
async def chat_stream_endpoint(request: AgentChatRequest) -> StreamingResponse:
    try:
        _, chat_with_agent_stream = _load_agent_functions()
    except Exception as exc:
        logger.error("Agent service could not be loaded (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="The agent service is unavailable.") from exc
    return StreamingResponse(
        chat_with_agent_stream(
            message=request.message,
            thread_id=request.thread_id,
            source_filter=request.source_filter,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat_agent", response_model=AgentChatResponse, tags=["Agent Chat"])
async def chat_agent_endpoint(request: AgentChatRequest) -> AgentChatResponse:
    try:
        chat_with_agent, _ = _load_agent_functions()
        response_content = await chat_with_agent(
            message=request.message,
            thread_id=request.thread_id,
            source_filter=request.source_filter,
        )
    except Exception as exc:
        logger.error("Agent request failed (%s)", type(exc).__name__)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The model provider could not complete the request.",
        ) from exc
    return AgentChatResponse(response=response_content)


@app.post("/upload_file", response_model=FileUploadResponse, tags=["File Management"])
async def upload_file_endpoint(file: UploadFile = File(...)) -> FileUploadResponse:
    file_path, safe_name, file_size = await _save_upload(file)
    try:
        ingest_file = _load_ingest_file()
    except Exception as exc:
        logger.error("Document ingestion service could not be loaded (%s)", type(exc).__name__)
        raise HTTPException(status_code=503, detail="The document ingestion service is unavailable.") from exc
    if not await ingest_file(file_path, safe_name, {"file_size": file_size}):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The PDF was uploaded but could not be indexed.",
        )
    return FileUploadResponse(
        filename=safe_name,
        message="The PDF was indexed and is ready for retrieval.",
    )
