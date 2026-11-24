import streamlit as st
import requests
import json
import os
import time
import uuid
import base64
import re
import hashlib
from pathlib import Path

FRONTEND_DIR = Path(__file__).resolve().parent

# --- 1. API Config ---
# Read from Environment Variable for Cloud Deployment
BACKEND_URL = os.environ.get("BACKEND_URL", "http://127.0.0.1:8000")
STREAM_ENDPOINT = f"{BACKEND_URL}/chat/stream"
UPLOAD_ENDPOINT = f"{BACKEND_URL}/upload_file"
HEALTH_ENDPOINT = f"{BACKEND_URL}/health"
DOCUMENTS_ENDPOINT = f"{BACKEND_URL}/documents"
EVALUATION_ENDPOINT = f"{BACKEND_URL}/evaluation/run"
DEMO_DOCUMENT_PATH = FRONTEND_DIR.parent / "demo" / "DocuLens_Demo.pdf"

# --- 2. Page Config & Style ---
st.set_page_config(
    page_title="DocuLens",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
def load_css(file_path):
    try:
        with open(file_path, encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass

load_css(FRONTEND_DIR / "style.css")

# --- 3. Session State Management ---
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "Welcome to DocuLens. Add a PDF in the knowledge panel, choose a search scope, and ask a question. I’ll cite matching passages and page numbers."
    })

def reset_chat():
    st.session_state.thread_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": "A new conversation is ready. Choose a PDF in the knowledge panel and ask a question. I’ll show the passages I use."
    })
    # Clear file uploader if possible, though Streamlit file_uploader state is tricky to clear programmatically without a key hack.
    # For now we just reset chat history.

# --- 4. Sidebar & Navigation ---
with st.sidebar:
    st.title("DocuLens")
    st.caption("Intelligent Knowledge & Research Assistant")

    if st.button("New conversation", type="primary"):
        reset_chat()
        st.rerun()

    page = st.radio(
        "Workspace",
        ["Research Assistant", "Knowledge Base", "Evaluation", "Settings"],
        label_visibility="collapsed",
    )

    try:
        health_response = requests.get(HEALTH_ENDPOINT, timeout=3)
        health_response.raise_for_status()
        health = health_response.json()
        st.caption("● Backend connected")
        provider_state = health.get("provider", {}).get("state", "unknown")
        provider_label = "credentials present" if provider_state == "configured" else "credentials missing"
        st.caption(f"● Provider {provider_label}")
    except requests.RequestException:
        health = None
        st.caption("○ Backend unavailable")

    if page in ("Research Assistant", "Knowledge Base"):
        try:
            documents_response = requests.get(DOCUMENTS_ENDPOINT, timeout=10)
            documents_response.raise_for_status()
            indexed_documents = documents_response.json().get("documents", [])
        except requests.RequestException:
            indexed_documents = []
            st.caption("Document index unavailable")

        st.caption(f"Knowledge base · {len(indexed_documents)} document(s)")

    st.markdown("---")
    with st.expander("Session details"):
        st.caption(f"Session ID: `{st.session_state.thread_id}`")

if page == "Knowledge Base":
    st.title("Knowledge Base")
    st.caption("Documents confirmed as indexed by the backend appear here. Upload new PDFs from the Research Assistant workspace.")
    try:
        response = requests.get(DOCUMENTS_ENDPOINT, timeout=10)
        response.raise_for_status()
        documents = response.json().get("documents", [])
        if not documents:
            st.info("No documents have been indexed yet. Open Research Assistant to upload a PDF.")
        for document in documents:
            with st.container(border=True):
                st.markdown(f"**{document['filename']}**")
                details = [document.get("source_type", "unknown"), f"{document.get('chunk_count', 0)} chunks"]
                if document.get("file_size") is not None:
                    details.append(f"{document['file_size'] / 1024:.1f} KB")
                if document.get("uploaded_at"):
                    details.append(str(document["uploaded_at"]))
                st.caption(" · ".join(details))
                st.caption(f"Status: {document.get('status', 'unknown')}")
    except requests.RequestException:
        st.error("The document index is unavailable. Check the backend and try again.")
    if DEMO_DOCUMENT_PATH.is_file():
        st.download_button(
            "Download the demo PDF",
            DEMO_DOCUMENT_PATH.read_bytes(),
            file_name=DEMO_DOCUMENT_PATH.name,
            mime="application/pdf",
        )
    st.stop()

if page == "Evaluation":
    st.title("Retrieval Evaluation")
    st.caption("Run the included demonstration questions against documents currently in the vector store. Metrics are calculated from actual retrievals.")
    st.markdown(
        "- **Hit Rate@K:** questions with an expected source in the top K results.\n"
        "- **MRR:** average reciprocal rank of the first expected source.\n"
        "- **Expected Source Recall@K:** expected sources found in the top K results."
    )
    k_value = st.slider("K", min_value=1, max_value=10, value=5)
    if st.button("Run evaluation", type="primary"):
        with st.spinner("Retrieving documents for each evaluation question…"):
            try:
                response = requests.post(EVALUATION_ENDPOINT, json={"k": k_value}, timeout=180)
                if response.ok:
                    st.session_state.last_evaluation = response.json()
                    st.session_state.pop("evaluation_error", None)
                else:
                    try:
                        detail = response.json().get("detail", "Evaluation failed.")
                    except ValueError:
                        detail = "Evaluation failed."
                    st.session_state.evaluation_error = detail
            except requests.RequestException:
                st.session_state.evaluation_error = "The backend could not complete evaluation. Check that it is running and try again."
    if st.session_state.get("evaluation_error"):
        st.error(st.session_state.pop("evaluation_error"))
    result = st.session_state.get("last_evaluation")
    if result:
        st.success(f"{result['status'].capitalize()} · {result['evaluated_cases']} cases · K={result['k']} · {result['dataset']}")
        columns = st.columns(3)
        metrics = result["metrics"]
        columns[0].metric("Hit Rate@K", f"{metrics['hit_rate_at_k']:.3f}")
        columns[1].metric("MRR", f"{metrics['mean_reciprocal_rank']:.3f}")
        columns[2].metric("Expected Source Recall@K", f"{metrics['expected_source_recall_at_k']:.3f}")
    else:
        st.info("No evaluation results are available yet. Index the demo PDF, then run evaluation.")
    st.stop()

if page == "Settings":
    st.title("Settings & Service Status")
    st.caption("Provider credentials stay in backend/.env and are never entered or stored in the browser. Presence does not confirm available API quota.")
    if health:
        columns = st.columns(3)
        columns[0].metric("Backend", "Connected")
        provider_state = health.get("provider", {}).get("state", "unknown")
        provider_label = "Credentials present" if provider_state == "configured" else "Credentials missing"
        columns[1].metric("Provider", provider_label)
        columns[2].metric("Vector store", health.get("vector_store", {}).get("state", "unknown").capitalize())
        st.caption(f"Provider: {health.get('provider', {}).get('name', 'unknown')} · Model: {health.get('provider', {}).get('model', 'unknown')}")
        st.caption(f"Embeddings: {health.get('embeddings', {}).get('model', 'unknown')} · Vector-store reachability: {health.get('vector_store', {}).get('reachability', 'unknown')}")
        retrieval = health.get("retrieval", {})
        st.caption(f"Retrieval top K: {retrieval.get('top_k', 'unknown')} · minimum relevance score: {retrieval.get('minimum_relevance_score', 'unknown')} · reranking: {'enabled' if retrieval.get('reranking') else 'disabled'}")
        st.caption(f"Application version: {health.get('version', 'unknown')}")
    else:
        st.error("The backend is unavailable. Start FastAPI and refresh this page.")
    st.markdown("Configure a cloud provider key or a local Ollama endpoint in `backend/.env`, then restart the backend. Local Ollama does not require a paid API key.")
    st.stop()

# --- 5. Three-panel knowledge workspace ---
documents_col, assistant_col = st.columns([0.88, 1.12], gap="large")

with documents_col:
    st.markdown("### Upload knowledge")
    st.caption("Add a PDF to your private local index. Answers will cite the source and page when evidence is found.")
    uploaded_file = st.file_uploader("Drop a PDF here or browse files", type=["pdf"], key="file_uploader")
    if uploaded_file:
        file_bytes = uploaded_file.getvalue()
        upload_fingerprint = hashlib.sha256(file_bytes).hexdigest()
        st.caption(f"{uploaded_file.name} · {len(file_bytes) / 1024:.1f} KB")
        if st.session_state.get("last_uploaded_file") != upload_fingerprint:
            with st.spinner("Reading and indexing your PDF…"):
                try:
                    files = {"file": (uploaded_file.name, file_bytes, uploaded_file.type)}
                    response = requests.post(UPLOAD_ENDPOINT, files=files, timeout=120)
                    if response.ok:
                        st.session_state.last_uploaded_file = upload_fingerprint
                        st.session_state.upload_notice = response.json().get("message", "PDF indexed successfully.")
                        st.rerun()
                    try:
                        detail = response.json().get("detail", "Upload failed.")
                    except ValueError:
                        detail = "Upload failed."
                    st.error(detail)
                except requests.RequestException:
                    st.error("The backend could not complete the upload. Check that it is running and try again.")

    upload_notice = st.session_state.pop("upload_notice", None)
    if upload_notice:
        st.success(upload_notice)

    st.markdown("### Knowledge base")
    st.caption(f"{len(indexed_documents)} indexed document(s)")
    if not indexed_documents:
        st.info("Your indexed PDFs will appear here after upload.")
    else:
        for document in indexed_documents:
            with st.container(border=True):
                st.markdown(f"📄 **{document['filename']}**")
                details = [f"{document.get('chunk_count', 0)} passages", document.get("source_type", "PDF")]
                if document.get("file_size") is not None:
                    details.append(f"{document['file_size'] / 1024:.1f} KB")
                st.caption(" · ".join(details))
                st.markdown("🟢 Indexed")

with assistant_col:
    assistant_state = "Document search ready" if indexed_documents else "Waiting for a PDF"
    st.markdown(f"### 🟢 AI Assistant · {assistant_state}")
    st.caption("Answers use the selected document set. Open Sources to inspect the passages and page numbers.")
    scope_options = ["All indexed documents", *[item["filename"] for item in indexed_documents]]
    selected_scope = st.selectbox("Search in", scope_options, key="document_scope") if indexed_documents else None
    st.session_state.source_filter = None if not selected_scope or selected_scope == scope_options[0] else selected_scope


    # Helper function to render content with embedded images
    def render_content_with_images(content):
        """
        Render content that may contain embedded base64 images.
        Images are marked as [IMAGE_BASE64:xxx]
        """
        # Check for embedded images
        image_pattern = r'\[IMAGE_BASE64:([A-Za-z0-9+/=]+)\]'
        matches = list(re.finditer(image_pattern, content))

        if not matches:
            # No images, just render markdown
            st.markdown(content)
            return

        # Split content and render parts with images
        last_end = 0
        for match in matches:
            # Render text before the image
            text_before = content[last_end:match.start()]
            if text_before.strip():
                st.markdown(text_before)

            # Render the image
            try:
                image_b64 = match.group(1)
                image_bytes = base64.b64decode(image_b64)
                # Use try/except for Streamlit version compatibility
                try:
                    st.image(image_bytes, caption="📊 Generated Chart", use_container_width=True)
                except TypeError:
                    st.image(image_bytes, caption="📊 Generated Chart", use_column_width=True)
            except Exception as e:
                st.warning(f"Failed to render image: {e}")

            last_end = match.end()

        # Render remaining text after last image
        remaining_text = content[last_end:]
        if remaining_text.strip():
            st.markdown(remaining_text)


    def render_answer_with_evidence(content):
        marker = re.search(r"\n\s*Sources:\s*\n?", content, flags=re.IGNORECASE)
        if marker is None:
            render_content_with_images(content)
            return
        answer = content[:marker.start()]
        evidence = content[marker.end():]
        render_content_with_images(answer.strip())
        with st.expander("Sources · retrieved passages", expanded=False):
            st.markdown(evidence.strip())

    # Display Message History
    history_container = (
        st.container(height=620, border=False)
        if len(st.session_state.messages) > 4
        else st.container(border=False)
    )
    with history_container:
        for msg in st.session_state.messages:
            avatar = "🧑‍💻" if msg["role"] == "user" else "🤖"
            with st.chat_message(msg["role"], avatar=avatar):
                # Try to render JSON content (Paper Analysis / Profile)
                content = msg["content"]
                try:
                    if content.strip().startswith("{") and "type" in content:
                        data_obj = json.loads(content)
                        if data_obj.get("type") == "paper_analysis":
                            d = data_obj.get("data", {})
                            st.markdown(f"### 📄 {d.get('title')}")
                            st.caption(f"**Authors:** {', '.join(d.get('authors', []))}")
                            st.info(d.get("summary"))
                        elif data_obj.get("type") == "linkedin_profile":
                            d = data_obj.get("data", {})
                            st.markdown(f"### 👔 {d.get('full_name')}")
                            st.caption(f"{d.get('headline')} | {d.get('location')}")
                            st.info(d.get("summary"))
                        else:
                            render_content_with_images(content)
                    else:
                        render_answer_with_evidence(content)
                except (ValueError, TypeError, KeyError):
                    render_answer_with_evidence(content)

    # --- 6. Streaming Logic ---
    def stream_generator(prompt):
        """
        Generator that yields chunks from the backend SSE stream.
        Handles both text tokens and tool events.
        All data from backend is base64 encoded to handle newlines safely.
        """

        def decode_sse_data(encoded_data: str) -> str:
            """Decode base64 encoded SSE data."""
            try:
                return base64.b64decode(encoded_data.encode('ascii')).decode('utf-8')
            except Exception:
                # Fallback: return as-is if decoding fails
                return encoded_data

        def render_tool_output(output_str, container):
            """Render tool output, handling embedded images."""
            image_pattern = r'\[IMAGE_BASE64:([A-Za-z0-9+/=]+)\]'
            matches = list(re.finditer(image_pattern, output_str))

            if matches:
                # Has images - render them directly in container
                for match in matches:
                    try:
                        image_b64 = match.group(1)
                        image_bytes = base64.b64decode(image_b64)
                        # Use try/except for Streamlit version compatibility
                        try:
                            container.image(image_bytes, caption="📊 Generated Chart", use_container_width=True)
                        except TypeError:
                            # Fallback for older Streamlit versions
                            container.image(image_bytes, caption="📊 Generated Chart", use_column_width=True)
                    except Exception as e:
                        container.warning(f"Failed to render chart: {e}")

                # Show text output (without image markers) - clean up markdown formatting
                clean_output = re.sub(image_pattern, '', output_str).strip()
                # Remove raw markdown and extra formatting for cleaner display
                clean_output = clean_output.replace('**结果**:', '').replace('**图表已生成并显示在上方**', '')
                clean_output = re.sub(r'```\n?', '', clean_output).strip()
                clean_output = re.sub(r'📊|🖼️', '', clean_output).strip()
                if clean_output and len(clean_output) > 10:
                    container.caption(clean_output[:500])
            else:
                # No images, just show text (truncated)
                if output_str:
                    container.text(output_str[:1500])

        payload = {
            "message": prompt,
            "thread_id": st.session_state.thread_id,
            "source_filter": st.session_state.get("source_filter"),
        }

        try:
            # Only bypass proxies if running locally (localhost/127.0.0.1)
            proxies = {"http": None, "https": None} if "127.0.0.1" in BACKEND_URL or "localhost" in BACKEND_URL else None

            # Headers to ensure proper SSE streaming
            headers = {
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            }

            with requests.post(STREAM_ENDPOINT, json=payload, stream=True, proxies=proxies, headers=headers, timeout=300) as response:
                response.raise_for_status()

                # Streamlit's status container for tool outputs
                status_container = st.status("Searching documents…", expanded=True)
                stream_failed = False

                # SSE Parser: event type is stored and applied to next data line
                event_type = None

                for line in response.iter_lines():
                    if not line:
                        # End of event block (empty line)
                        event_type = None
                        continue

                    decoded_line = line.decode('utf-8')

                    if decoded_line.startswith("event: "):
                        event_type = decoded_line[7:].strip()

                    elif decoded_line.startswith("data: "):
                        raw_data = decoded_line[6:]

                        if event_type == "status":
                            status_container.write(decode_sse_data(raw_data))

                        elif event_type == "error":
                            stream_failed = True
                            message = decode_sse_data(raw_data)
                            status_container.error(message)
                            yield message

                        elif event_type == "text":
                            # Text content - decode base64 and yield for streaming display
                            text_content = decode_sse_data(raw_data)

                            # Filter out Base64 image data from text stream
                            # Images should only be rendered in tool_end results
                            if "[IMAGE_BASE64:" in text_content or "data:image" in text_content.lower():
                                # Check if this looks like base64 data (long alphanumeric string)
                                if len(text_content) > 100 and re.match(r'^[A-Za-z0-9+/=\s]+$', text_content.replace('\n', '')):
                                    continue  # Skip pure base64 chunks
                                # Filter out image markers from mixed content
                                text_content = re.sub(r'\[IMAGE_BASE64:[A-Za-z0-9+/=]+\]', '[图表已在上方工具结果中显示]', text_content)
                                text_content = re.sub(r'!\[.*?\]\(data:image/[^)]+\)', '[图表已生成]', text_content)

                            if text_content.strip():
                                yield text_content

                        elif event_type == "tool_start":
                            # Tool start event - decode and display
                            tool_name = decode_sse_data(raw_data)
                            status_container.write(f"🛠️ Calling Tool: **{tool_name}**...")

                        elif event_type == "tool_end":
                            # Tool end event - decode JSON and display result
                            try:
                                decoded_json = decode_sse_data(raw_data)
                                tool_data = json.loads(decoded_json)
                                tool_name = tool_data.get('name', 'unknown')
                                tool_output = tool_data.get('output', '')

                                status_container.markdown(f"✅ **{tool_name}** finished.")

                                # Render output directly in status_container (no nested expanders)
                                if tool_name in ['create_visualization', 'generate_chart_from_data', 'execute_python_code']:
                                    # Check if output contains image
                                    if "[IMAGE_BASE64:" in tool_output:
                                        render_tool_output(tool_output, status_container)
                                    elif tool_output:
                                        status_container.text(tool_output[:1500])
                                elif tool_output:
                                    status_container.text(tool_output[:1000])
                            except Exception as e:
                                status_container.write(f"Tool finished. (Error: {str(e)[:80]})")

                        elif event_type == "done":
                            # Stream finished signal, don't yield anything
                            pass

                status_container.update(
                    label="Answer failed" if stream_failed else "Answer ready",
                    state="error" if stream_failed else "complete",
                    expanded=stream_failed,
                )

        except requests.RequestException:
            yield "The response stream was interrupted. Check the backend connection and try again."
        except Exception:
            yield "The response could not be completed. Check the backend logs and try again."

    # Suggested questions
    if len(st.session_state.messages) <= 1:
        st.markdown("#### Try a question")
        suggestion_columns = st.columns(3)
        suggestions = [
            "Summarize the main ideas in my indexed document.",
            "What does the document say about its most important topic?",
            "List the key terms and explain them using the document.",
        ]
        for column, suggestion in zip(suggestion_columns, suggestions):
            if column.button(suggestion, use_container_width=True):
                st.session_state.suggested_prompt = suggestion
                st.rerun()

    # Chat Input
    prompt = st.chat_input(
        "Ask about your indexed documents…",
        key="doculens_chat_input",
        submit_mode="stop",
    )
    if not prompt:
        prompt = st.session_state.pop("suggested_prompt", None)
    if prompt:
        st.session_state.messages.append({"role": "user", "content": prompt})
        # Keep a useful transcript if the user stops the running response.
        st.session_state.messages.append(
            {"role": "assistant", "content": "Generation stopped before the answer finished."}
        )
        # Render the active turn inside the same history area, above the composer.
        with history_container:
            with st.chat_message("user", avatar="🧑‍💻"):
                st.markdown(prompt)
            with st.chat_message("assistant", avatar="🤖"):
                full_response = st.write_stream(stream_generator(prompt))
        st.session_state.messages[-1]["content"] = (
            full_response.strip()
            if isinstance(full_response, str) and full_response.strip()
            else "Generation stopped before the answer finished."
        )
        st.rerun()
