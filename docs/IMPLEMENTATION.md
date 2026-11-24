# DocuLens implementation record

## Repository audit

The work started from the public `Mootra/TraceRAG` repository, checked out on
`feature/tracerag-studio`. The original MIT `LICENSE` and Git history are
retained. The implementation is a FastAPI + Streamlit application with a
LangGraph ReAct agent, SQLite checkpoints, PDF and public URL ingestion,
Chroma vector search, optional FlashRank reranking, source formatting, and an
offline retrieval evaluator.

### Existing capabilities retained

- `backend/main.py` provides the root health response, synchronous agent chat,
  SSE chat, and bounded PDF upload.
- `backend/agent_service.py` builds a LangGraph agent and uses an SQLite
  checkpointer. Its stream already reports model text and tool start/end.
- `backend/langchain_qa_backend.py` chunks and indexes PDFs and public URLs,
  uses CPU Hugging Face embeddings, and enables FlashRank when available.
- `backend/url_policy.py` rejects credentialed, non-HTTP(S), unresolved, and
  non-public URL destinations.
- `backend/rag/formatting.py` derives citations and excerpts from retrieved
  document metadata; `backend/rag/evaluation.py` calculates Hit Rate@K, MRR,
  and expected-source recall.
- `frontend/app.py` provides a Streamlit chat, new-session action, upload, and
  streaming tool display. `frontend/style.css` is already present.
- `evaluation/rag_cases.example.jsonl` is a template only and refers to
  documents that are not included in the repository.

### Baseline

- `python -m unittest discover -s tests -v`: **18 tests passed**.
- `python -m compileall -q backend tests tools`: **passed**.
- Local Python is 3.10.10. The pinned requirements recommend Python 3.11 or
  3.12. FastAPI and LangGraph are not installed in the active environment;
  installed Streamlit (1.41.1), Chroma (1.1.1), and pypdf (5.1.0) differ from
  the repository pins. Therefore the baseline did not include application
  startup or live retrieval checks.
- No `backend/.env` was present at audit time. Provider-backed chat cannot be
  validated until a key is configured.
- GitHub network access was unavailable from the shell; the source was cloned
  through the connected repository access. No remote changes have been pushed.

## Implementation plan

1. Keep the existing architecture and security controls; avoid dependency
   upgrades and preserve existing API behavior.
2. Move provider configuration to backend environment settings by removing
   API-key collection and transmission from Streamlit. Keep secrets out of
   browser/session state and request bodies.
3. Add a structured health response and read-only document inventory endpoint
   while retaining the existing root response.
4. Add a small original, reusable RAG/agentic-AI sample document and matching
   evaluation cases; provide a UI surface for knowledge-base status and
   evaluation results without fabricated metrics.
5. Improve the demonstration workflow, documentation, and Windows startup
   scripts.
6. Add deterministic tests for new behavior, then rerun the offline suite and
   compilation. Attempt startup checks only if the local dependency state
   permits; report unavailable external credentials honestly.

## Change log

This document records the repository audit, implementation changes, validation,
and remaining runtime requirements.

## Changes completed

- Created branch `feature/tracerag-studio`; retained upstream history and the
  MIT license. No commits were created and nothing was pushed.
- Replaced the inaccurate “99 tools” prompt with grounded, tool-aware
  instructions. Provider and optional integration keys now come from backend
  environment configuration. Streamlit no longer loads `backend/.env`, stores
  API keys in session state, or sends them in chat requests.
- Preserved `/`, `/chat_agent`, `/chat/stream`, and `/upload_file`. Added
  `/health`, `/documents`, and `/evaluation/run`. Missing chat session IDs now
  get fresh IDs instead of sharing `default_thread`.
- Added SHA-256 document IDs, chunk IDs, upload size and timestamp metadata,
  an inventory API, an explicit relevance floor, configurable retrieval and
  chunk settings, and an insufficient-evidence path that skips model
  generation when no chunks clear the floor. RAG now honors either configured
  LLM provider and includes actual source/page labels in model context.
- Hardened public web ingestion: redirects are followed manually and
  revalidated; requests have timeouts, accepted content types, and a bounded
  response size. The implementation indexes one page and does not crawl a
  sitemap or linked pages.
- Added safe health status, UI navigation for Knowledge Base/Evaluation/
  Settings, a citation evidence expander, actual SSE retrieval/reranking
  summaries, generic stream failures, updated styling, a sample source and
  three-page PDF, and a four-case evaluation dataset.
- Added three Windows launch scripts plus their shared helper, and updated
  README, architecture, implementation, and demo documentation. Docker
  Streamlit no longer disables CORS/XSRF protection. Docker Compose now uses
  the mounted persistent data directory, and `.dockerignore` excludes local
  secrets and runtime artifacts from build context.
- No dependencies were added or changed. A local `backend/.env` was created
  from the placeholder template so Docker Compose can be validated. Its
  provider keys remain blank; it is ignored by Git.
- Renamed the product UI, docs, backend title, Docker service, and demo PDF to
  DocuLens while preserving original TraceRAG attribution, license, history,
  and the existing feature branch.

## Validation results

- Baseline: 18 unit tests passed; compile check passed.
- Updated offline suite: 31 unit tests passed, including new API source
  contracts, secret-free health status, evidence threshold selection, SSE
  formatting, web redirect/size/content-type checks, and demo dataset checks.
- `python -m compileall -q backend tests tools`: passed after changes.
- PowerShell parser: all four `.ps1` scripts parsed successfully.
- `git diff --check`: passed (Git reported only LF-to-CRLF working-copy
  warnings for README and CSS).
- Sample PDF: parsed successfully with `pypdf`; it contains three pages and
  extracted text.
- Streamlit frontend smoke check: returned HTTP 200 on a temporary local port;
  the smoke process was stopped afterward.
- Backend startup, live PDF indexing, model chat, live SSE against LangGraph,
  and Chroma retrieval/evaluation were not completed. Docker Compose
  configuration did validate. The active Python is 3.10.10 and lacks FastAPI and LangGraph; the
  installed Streamlit, Chroma, and pypdf versions differ from repository pins.
  No provider key is configured. The required packages and provider-backed
  behavior therefore still need verification in a Python 3.11/3.12 virtual
  environment.

## Outstanding limitations

- No live end-to-end application run has been verified in this environment.
  Model-backed ingestion and chat require the project dependencies, first-time
  embedding model download, and one provider key.
- The UI manages the current conversation and new sessions, but has no
  conversation history picker or delete-session API.
- The demo retrieval dataset has four questions and one expected source; its
  metrics demonstrate the workflow and are not a general quality benchmark.
- Health reports configured provider state and local vector-store file
  presence; it does not probe provider or vector-store reachability.
- There are no fake-provider agent integration tests or live upload/chat/SSE
  API integration tests yet.
- Public URL ingestion now supports one bounded page. DNS validation is done
  before each request/redirect, but the implementation does not pin the
  resolved IP at the HTTP socket layer.
- Authentication, per-user data isolation, production rate limiting, OCR, and
  production deployment hardening remain out of scope.
