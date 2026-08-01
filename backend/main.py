from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Callable
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

try:
    from .runtime_config import RuntimeSettings
except ImportError:  # Supports `uvicorn main:app` from the backend directory.
    from runtime_config import RuntimeSettings


logger = logging.getLogger(__name__)
settings = RuntimeSettings.from_env()
settings.ensure_directories()

app = FastAPI(
    title="TraceRAG Backend API",
    description="A traceable RAG agent with document ingestion, source citations, and tool calling.",
    version="7.0.0",
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
    thread_id: str = Field(default="default_thread", min_length=1, max_length=128)
    api_keys: dict[str, str] | None = None


class AgentChatResponse(BaseModel):
    response: str


class FileUploadResponse(BaseModel):
    filename: str
    message: str


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


async def _save_upload(file: UploadFile) -> tuple[str, str]:
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

    return str(destination), destination.name


@app.get("/", tags=["Health Check"])
def read_root() -> dict[str, str]:
    return {"status": "ok", "message": "TraceRAG backend is ready."}


@app.post("/chat/stream", tags=["Agent Chat"])
async def chat_stream_endpoint(request: AgentChatRequest) -> StreamingResponse:
    _, chat_with_agent_stream = _load_agent_functions()
    return StreamingResponse(
        chat_with_agent_stream(
            message=request.message,
            thread_id=request.thread_id,
            api_keys=request.api_keys,
        ),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat_agent", response_model=AgentChatResponse, tags=["Agent Chat"])
async def chat_agent_endpoint(request: AgentChatRequest) -> AgentChatResponse:
    chat_with_agent, _ = _load_agent_functions()
    try:
        response_content = await chat_with_agent(
            message=request.message,
            thread_id=request.thread_id,
            api_keys=request.api_keys,
        )
    except Exception as exc:
        logger.exception("Agent request failed")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The model provider could not complete the request.",
        ) from exc
    return AgentChatResponse(response=response_content)


@app.post("/upload_file", response_model=FileUploadResponse, tags=["File Management"])
async def upload_file_endpoint(file: UploadFile = File(...)) -> FileUploadResponse:
    file_path, safe_name = await _save_upload(file)
    ingest_file = _load_ingest_file()
    if not await ingest_file(file_path, safe_name):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The PDF was uploaded but could not be indexed.",
        )
    return FileUploadResponse(
        filename=safe_name,
        message="The PDF was indexed and is ready for retrieval.",
    )
