# DocuLens 60-second demo

## Prerequisites

- Windows 10/11 with Python 3.11 or 3.12.
- A virtual environment with `requirements.txt` installed.
- One provider configured in `backend/.env` for model-backed chat.
- The bundled original document at `demo/DocuLens_Demo.pdf`.

## Configure and start

From the repository root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
notepad backend\.env
```

Set `GOOGLE_API_KEY` (or the OpenAI-compatible provider values) in
`backend/.env`. Then either start both services in separate terminals:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\start_backend.ps1
```

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\start_frontend.ps1
```

Or use `scripts/start_demo.ps1` to launch both services in the background.
The UI is at <http://localhost:8501>; backend health is at
<http://127.0.0.1:8000/health>.

## Prepare the knowledge base

Upload `demo/DocuLens_Demo.pdf` from the sidebar and wait for the
backend's indexed confirmation. The document inventory should then show the
filename, file size, ingestion time, and chunk count. Evaluation expects this
exact source filename.

## Recording sequence (about 60 seconds)

1. **0–8 seconds:** Open the Research Assistant and identify the document
   upload and Knowledge Base navigation.
2. **8–15 seconds:** Show the already indexed `DocuLens_Demo.pdf` in the
   Knowledge Base.
3. **15–35 seconds:** Ask: “Explain how RAG works and identify the role of
   embeddings, vector search and reranking.” Wait for the answer.
4. **35–48 seconds:** Expand “Sources and retrieved evidence” in the assistant
   response; point to the source filename, page, and excerpt.
5. **48–55 seconds:** Expand the agent execution status to show the actual
   retrieval tool activity.
6. **55–60 seconds:** Briefly show the architecture diagram in
   `docs/ARCHITECTURE.md` or the README.

## Example questions

- “Explain how RAG works and identify the role of embeddings, vector search
  and reranking.”
- “What does a vector database store in this architecture?”
- “Which agent events should the interface show, and what should remain
  hidden?”
- Out of scope: “Which country won the 2024 European football championship?”
  The sample document does not contain that information; the RAG tool should
  return the explicit insufficient-evidence message.

## Evaluation

Index the demo PDF, open **Evaluation**, and choose **Run evaluation**. The
backend evaluates the cases in `evaluation/rag_cases.demo.jsonl` against the
current Chroma index. The UI shows metrics only after a successful run. This
small, single-document dataset is for workflow demonstration, not a broad
retrieval benchmark.

## Recovery

- **Backend is unavailable:** Check the backend terminal or
  `.runtime/backend.stderr.log`, then rerun `scripts/start_backend.ps1`.
- **Provider is missing:** Add the key to `backend/.env` and restart the
  backend. The UI reports configuration state but does not test provider
  reachability.
- **No indexed document:** Upload the bundled PDF and wait for the success
  response. Use the exact original filename so evaluation source matching
  remains valid.
- **Stream was interrupted:** Check backend logs and retry. SSE reports a
  generic failure and closes the request; the chat session can be continued.
