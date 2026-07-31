"""
RAG PDF Chatbot — Streamlit front end.

Lets a user upload one or more PDFs, builds a FAISS vector index over
their content (text + embedded images), and answers questions using
Gemini with retrieval-augmented generation.
"""

import json
from datetime import datetime
from pathlib import Path

import streamlit as st

from src import config
from src.pdf_processor import process_pdf
from src.vector_store import VectorStore

# ----------------------------------------------------------------------
# Page setup
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="RAG PDF Chatbot",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

CUSTOM_CSS = """
<style>
    #MainMenu, footer, header {visibility: hidden;}

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 980px;
    }

    .app-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 0.25rem;
    }

    .app-header h1 {
        font-size: 2.1rem;
        font-weight: 800;
        margin: 0;
        background: linear-gradient(90deg, #4F46E5, #06B6D4);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .app-subtitle {
        color: #6B7280;
        font-size: 0.95rem;
        margin-bottom: 1.25rem;
    }

    .status-pill {
        display: inline-block;
        padding: 0.2rem 0.7rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
        margin-bottom: 0.6rem;
    }

    .status-ok { background: #DCFCE7; color: #166534; }
    .status-warn { background: #FEF3C7; color: #92400E; }

    .metric-card {
        background: linear-gradient(135deg, #EEF2FF 0%, #ECFEFF 100%);
        border: 1px solid #E0E7FF;
        border-radius: 14px;
        padding: 1rem 1.1rem;
        text-align: center;
    }
    .metric-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #3730A3;
        line-height: 1.1;
    }
    .metric-label {
        font-size: 0.78rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-top: 0.15rem;
    }

    .doc-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
        margin-bottom: 0.4rem;
        font-size: 0.85rem;
    }

    .source-card {
        background: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 10px;
        padding: 0.75rem 1rem;
        margin-top: 0.5rem;
        font-size: 0.85rem;
    }

    div[data-testid="stChatMessage"] { border-radius: 14px; }

    .sidebar-section-title {
        font-weight: 700;
        font-size: 0.95rem;
        margin-top: 1.2rem;
        margin-bottom: 0.4rem;
        color: #374151;
    }

    .footer-note {
        text-align: center;
        color: #9CA3AF;
        font-size: 0.78rem;
        margin-top: 2.5rem;
    }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Session state
# ----------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "vector_store" not in st.session_state:
    st.session_state.vector_store = None

if "processed_docs" not in st.session_state:
    st.session_state.processed_docs = []


def get_vector_store():
    """Lazily create (or reuse) the VectorStore for this session."""
    if st.session_state.vector_store is None:
        st.session_state.vector_store = VectorStore()
    return st.session_state.vector_store


def load_manifest() -> list[dict]:
    if config.MANIFEST_PATH.exists():
        try:
            return json.loads(config.MANIFEST_PATH.read_text())
        except Exception:
            return []
    return []


def save_manifest(entries: list[dict]) -> None:
    config.MANIFEST_PATH.write_text(json.dumps(entries, indent=2))


if "manifest_loaded" not in st.session_state:
    st.session_state.processed_docs = load_manifest()
    st.session_state.manifest_loaded = True


# ----------------------------------------------------------------------
# Header
# ----------------------------------------------------------------------
st.markdown(
    '<div class="app-header"><span style="font-size:2.1rem;">📚</span>'
    "<h1>RAG PDF Chatbot</h1></div>",
    unsafe_allow_html=True,
)
st.markdown(
    '<p class="app-subtitle">Ask questions about your PDFs — grounded, '
    "cited answers powered by retrieval-augmented generation.</p>",
    unsafe_allow_html=True,
)

setup_issues = config.check_setup()

# ----------------------------------------------------------------------
# Sidebar — document management
# ----------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Setup")

    if setup_issues:
        st.markdown(
            '<span class="status-pill status-warn">API key missing</span>',
            unsafe_allow_html=True,
        )
        for issue in setup_issues:
            st.warning(issue)
    else:
        st.markdown(
            '<span class="status-pill status-ok">Ready</span>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sidebar-section-title">📄 Document Manager</div>', unsafe_allow_html=True)

    uploaded_files = st.file_uploader(
        "Upload one or more PDFs",
        type=["pdf"],
        accept_multiple_files=True,
        disabled=bool(setup_issues),
        help="Text and embedded images are extracted, chunked, and indexed.",
    )

    process_clicked = st.button(
        "🚀 Process PDF(s)",
        use_container_width=True,
        disabled=bool(setup_issues) or not uploaded_files,
    )

    if process_clicked and uploaded_files:
        manifest = st.session_state.processed_docs
        total_added = 0

        for uploaded_file in uploaded_files:
            dest_path = config.PDF_DIR / uploaded_file.name
            dest_path.write_bytes(uploaded_file.getbuffer())

            with st.spinner(f"Extracting text and images from '{uploaded_file.name}'..."):
                try:
                    chunks = process_pdf(str(dest_path))
                except Exception as exc:
                    st.error(f"Failed to read '{uploaded_file.name}': {exc}")
                    continue

            if not chunks:
                st.error(f"No extractable text or images were found in '{uploaded_file.name}'.")
                continue

            with st.spinner(f"Embedding and indexing {len(chunks)} chunks from '{uploaded_file.name}'..."):
                try:
                    store = get_vector_store()
                    added = store.add_chunks(chunks)
                except Exception as exc:
                    st.error(f"Indexing failed for '{uploaded_file.name}': {exc}")
                    continue

            manifest = [d for d in manifest if d["name"] != uploaded_file.name]
            manifest.append({
                "name": uploaded_file.name,
                "chunks": added,
                "added_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            })
            total_added += added
            st.success(f"Indexed '{uploaded_file.name}' ({added} chunks).")

        save_manifest(manifest)
        st.session_state.processed_docs = manifest
        # Force the chat session to pick up the freshly merged index on
        # the next question, instead of answering from a stale in-memory
        # copy created before these PDFs were indexed.
        st.session_state.pop("chatbot", None)

    st.markdown('<div class="sidebar-section-title">📚 Indexed Documents</div>', unsafe_allow_html=True)
    if st.session_state.processed_docs:
        for doc in list(st.session_state.processed_docs):
            col1, col2 = st.columns([5, 1])
            with col1:
                st.caption(f"📄 {doc['name']} — {doc['chunks']} chunks")
            with col2:
                if st.button("🗑️", key=f"del_{doc['name']}", help=f"Remove '{doc['name']}'"):
                    try:
                        store = get_vector_store()
                        store.delete_source(doc["name"])
                    except Exception as exc:
                        st.error(f"Could not remove '{doc['name']}': {exc}")
                    else:
                        manifest = [d for d in st.session_state.processed_docs if d["name"] != doc["name"]]
                        save_manifest(manifest)
                        st.session_state.processed_docs = manifest
                        st.session_state.pop("chatbot", None)
                        st.rerun()
    else:
        st.caption("No documents indexed yet.")

    st.markdown('<div class="sidebar-section-title">🧹 Maintenance</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Clear chat", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
    with col_b:
        if st.button("Reset all", use_container_width=True, disabled=bool(setup_issues)):
            try:
                store = get_vector_store()
                store.reset()
            except ValueError:
                pass
            st.session_state.messages = []
            st.session_state.processed_docs = []
            save_manifest([])
            st.session_state.vector_store = None
            st.session_state.pop("chatbot", None)
            st.rerun()

    if st.session_state.messages:
        transcript_lines = [
            "# RAG PDF Chatbot — Chat Export",
            f"_{datetime.now().strftime('%Y-%m-%d %H:%M')}_",
            "",
        ]
        for m in st.session_state.messages:
            speaker = "**You**" if m["role"] == "user" else "**Assistant**"
            transcript_lines.append(f"{speaker}: {m['content']}")
            transcript_lines.append("")
        st.download_button(
            "⬇️ Export chat (.md)",
            data="\n".join(transcript_lines),
            file_name=f"chat_export_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.markdown('<div class="sidebar-section-title">ℹ️ Model Info</div>', unsafe_allow_html=True)
    st.caption(f"LLM: `{config.LLM_MODEL}`")
    st.caption(f"Embeddings: `{config.EMBEDDING_MODEL}`")


# ----------------------------------------------------------------------
# Main area
# ----------------------------------------------------------------------
if setup_issues:
    st.info(
        "Add your Gemini API key to get started — see the sidebar for "
        "instructions, or check the README."
    )
    st.stop()

tab_chat, tab_dashboard = st.tabs(["💬 Chat", "📊 Dashboard"])

with tab_dashboard:
    docs = st.session_state.processed_docs
    total_chunks = sum(d.get("chunks", 0) for d in docs)
    total_images = 0
    if config.IMAGE_DIR.exists():
        total_images = len(
            [f for f in config.IMAGE_DIR.iterdir() if f.is_file() and not f.name.startswith(".")]
        )

    c1, c2, c3, c4 = st.columns(4)
    for col, value, label in [
        (c1, len(docs), "Documents"),
        (c2, total_chunks, "Chunks Indexed"),
        (c3, total_images, "Images Extracted"),
        (c4, len(st.session_state.messages), "Chat Messages"),
    ]:
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-value">{value}</div>'
                f'<div class="metric-label">{label}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("&nbsp;", unsafe_allow_html=True)
    st.markdown("#### Indexed Documents")
    if docs:
        for doc in docs:
            st.markdown(
                f'<div class="doc-row">'
                f'<span>📄 <b>{doc["name"]}</b></span>'
                f'<span>{doc["chunks"]} chunks · added {doc.get("added_at", "—")}</span>'
                f"</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("Nothing indexed yet — upload a PDF from the sidebar.")

with tab_chat:
    if not st.session_state.processed_docs:
        st.info("👋 Upload a PDF in the sidebar and click **Process PDF(s)** to begin.")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

            if message["role"] == "assistant" and message.get("sources"):
                with st.expander("📎 Sources"):
                    st.markdown(
                        f"**Pages:** {', '.join(str(p) for p in message['sources'])}  \n"
                        f"**Document(s):** {', '.join(message.get('documents', []))}"
                    )
                    for image_path in message.get("images", []):
                        if Path(image_path).exists():
                            st.image(image_path, use_container_width=True)

    question = st.chat_input("Ask a question about your document(s)...")

    if question:
        st.session_state.messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    from src.chatbot import ChatBot

                    if "chatbot" not in st.session_state:
                        st.session_state.chatbot = ChatBot()

                    response = st.session_state.chatbot.ask(question)
                except Exception as exc:  # noqa: BLE001 - surfaced to the user
                    response = {
                        "answer": f"Something went wrong: {exc}",
                        "sources": [],
                        "images": [],
                        "documents": [],
                    }

            st.markdown(response["answer"])

            if response["sources"]:
                with st.expander("📎 Sources"):
                    st.markdown(
                        f"**Pages:** {', '.join(str(p) for p in response['sources'])}  \n"
                        f"**Document(s):** {', '.join(response['documents'])}"
                    )
                    for image_path in response["images"]:
                        if Path(image_path).exists():
                            st.image(image_path, use_container_width=True)

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": response["answer"],
                "sources": response["sources"],
                "images": response["images"],
                "documents": response["documents"],
            }
        )

st.markdown(
    f'<p class="footer-note">RAG PDF Chatbot v{config.VERSION} · '
    "Built with Streamlit, LangChain, Gemini &amp; FAISS</p>",
    unsafe_allow_html=True,
)
