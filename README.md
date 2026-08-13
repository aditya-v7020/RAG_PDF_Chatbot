# 📚 RAG PDF Chatbot

A Retrieval-Augmented Generation (RAG) chatbot that answers questions
about your PDFs — grounded in the document's own text and images, with
page-level citations, via a modern React interface backed by a FastAPI
API.

**Stack:** PyMuPDF (text + image extraction) → FAISS (vector index) →
Gemini embeddings (`gemini-embedding-001`) → Gemini LLM
(`gemini-flash-latest`) → FastAPI (API) → React + Tailwind CSS (UI).

> The UI was migrated from Streamlit to a React + Tailwind frontend
> talking to a FastAPI backend. All RAG logic in `src/` (PDF parsing,
> chunking, embeddings, FAISS, Gemini calls) is untouched — only the
> presentation layer changed. The original Streamlit app is kept for
> reference as `app_streamlit_legacy.py.bak` but is no longer used.

---

## Features

- 📤 Upload multiple PDFs at once from the sidebar — no manual file placement needed.
- 🖼️ Extracts embedded images per page and links them to the sections that reference them.
- 🔍 Semantic search over chunked document text using FAISS, embedded in batches so large PDFs never hit the API's per-request size limit.
- 💬 Chat-style interface with per-answer source pages, source documents, and inline images.
- 📚 Supports multiple indexed PDFs at once (new PDFs are merged into the existing index).
- 🗑️ Remove a single document from the index without wiping everything else.
- 📊 A **Dashboard** tab with live stats: documents indexed, chunks, extracted images, chat turns.
- ⬇️ Export the current chat transcript as a Markdown file.
- 🧹 Separate "Clear chat" and "Reset all" controls in the sidebar.
- ✅ Automated test suite (`pytest`) that runs fully offline — no API key required to run tests.
- 🛡️ Friendly setup screen instead of a crash when the API key is missing.

---

## 1. Prerequisites

- Python 3.10+ → https://www.python.org/downloads/
- A free Gemini API key → https://aistudio.google.com/apikey

## 2. Install

```bash
# from the project root
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

## 3. Configure your API key

```bash
cp .env.example .env       # Windows: copy .env.example .env
```

Open `.env` and paste your key:

```
GOOGLE_API_KEY=your_real_key_here
```

> ⚠️ **Security note:** `.env` is listed in `.gitignore`, but a real
> `GOOGLE_API_KEY` was found already committed to this repo's git
> history (it was added before `.gitignore` took effect). `.env` has
> now been removed from git tracking going forward, but **anyone with
> access to the git history can still see the old key**. Revoke/rotate
> it immediately at https://aistudio.google.com/apikey, paste the new
> key into your local `.env`, and — if this repo is ever pushed
> publicly — scrub it from history (e.g. `git filter-repo` or BFG
> Repo-Cleaner) before doing so.

## 4. Run — backend (Terminal 1)

```bash
uvicorn api_server:app --reload --port 8000
```

This starts the FastAPI backend at `http://localhost:8000`. Leave it running.

## 5. Run — frontend (Terminal 2)

```bash
cd frontend
npm install
npm run dev
```

Open the URL Vite prints (default `http://localhost:5173`). In dev mode,
Vite proxies `/api` and `/images` straight to the backend on port 8000
(see `frontend/vite.config.js`), so there's nothing else to configure.

Then, in the browser:

1. Upload a PDF in the sidebar.
2. Click **Process PDF(s)** — this extracts text and images and builds/updates the vector index.
3. Ask questions in the chat box. Answers include an expandable **Sources** section with page numbers and any related images.
4. Switch to the **Dashboard** tab for live stats.

### Building the frontend for production

```bash
cd frontend
npm run build
```

This produces static files in `frontend/dist/`. Serve them with any
static file host, and either point `VITE_API_BASE_URL` (in a
`frontend/.env` file) at your deployed FastAPI backend's URL, or serve
`dist/` from behind the same reverse proxy as the API so `/api` and
`/images` resolve correctly.

---

## How it works (RAG pipeline)

| Step | File | What happens |
|---|---|---|
| Load PDF | `src/pdf_processor.py` | Extracts text and embedded images per page with PyMuPDF |
| Chunk | `src/pdf_processor.py` | Splits text into overlapping ~1000-character chunks, tagged with page, image, and source-file metadata |
| Embed + Store | `src/vector_store.py` | Converts chunks to vectors with Gemini embeddings (in batches) and stores/merges them in a local FAISS index; can also remove a single document's chunks and rebuild |
| Retrieve | `src/vector_store.py` | On each question, finds the most semantically similar chunks |
| Generate | `src/llm.py` | Sends the question + retrieved context to Gemini for a grounded answer |
| Orchestrate | `src/chatbot.py` | Ties retrieval + generation together, collects source pages/images/documents |
| API | `api_server.py` | FastAPI routes: setup status, upload/list/delete/reset documents, dashboard stats, chat |
| UI | `frontend/` | React + Tailwind + React Router interface: upload, process, chat, sources, dashboard, index management |

## Project structure

```
RAG_PDF_Chatbot/
├── api_server.py                 # FastAPI backend (new — replaces app.py as the entrypoint)
├── app_streamlit_legacy.py.bak   # Old Streamlit UI, kept only for reference/no longer used
├── src/
│   ├── config.py                 # Paths, model names, chunk/retrieval settings, setup checks
│   ├── pdf_processor.py          # Text + image extraction, chunking
│   ├── vector_store.py           # FAISS wrapper (create / merge / query / reset)
│   ├── llm.py                    # Gemini chat model wrapper
│   └── chatbot.py                # RAG orchestration
├── frontend/                     # React + Tailwind + React Router UI
│   ├── src/
│   │   ├── api/client.js         # Fetch wrapper for the FastAPI backend
│   │   ├── context/AppContext.jsx# Shared app state (setup, documents, dashboard, chat)
│   │   ├── components/           # Sidebar, DocumentManager, ChatMessage, Layout, etc.
│   │   ├── pages/                # ChatPage, DashboardPage
│   │   ├── App.jsx               # Route definitions
│   │   └── main.jsx              # React entrypoint
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js            # Dev proxy → FastAPI on :8000
│   └── tailwind.config.js
├── tests/                        # Offline pytest suite (fakes the Gemini API)
│   ├── conftest.py
│   ├── test_pdf_processor.py
│   ├── test_vector_store.py
│   └── test_chatbot.py
├── data/
│   ├── pdfs/                     # Uploaded PDFs land here (sample included)
│   └── extracted_images/         # Auto-extracted images
├── faiss_index/                  # Vector index (created/updated automatically)
├── requirements.txt
├── .env.example
└── README.md
```

## Running the tests

```bash
pytest -v
```

All tests run **offline**: the Gemini embeddings and chat model are
replaced with lightweight fakes in `tests/conftest.py`, so no API key
or network access is needed to verify the pipeline's logic (chunking,
indexing, merging, retrieval, and error handling).

## Customizing

- Increase `TOP_K_RESULTS` in `src/config.py` for broader context on long PDFs.
- Adjust `CHUNK_SIZE` / `CHUNK_OVERLAP` in `src/config.py` to tune retrieval granularity.
- `LLM_MODEL` and `EMBEDDING_MODEL` in `src/config.py` use Google's rolling
  aliases (`gemini-flash-latest`, `gemini-embedding-001`) so the app keeps
  working as Google retires older dated model IDs — no code changes needed
  when Google upgrades the underlying model behind an alias.

## Troubleshooting

- **"No GOOGLE_API_KEY found"** — make sure the file is named exactly `.env` (not `.env.example`) and sits in the project root, then restart the backend (`uvicorn api_server:app --reload --port 8000`).
- **Frontend loads but shows "API key missing" even though `.env` is set** — the backend reads `.env` on startup; restart `uvicorn` after editing it.
- **Frontend can't reach the backend** — confirm `uvicorn api_server:app --reload --port 8000` is running in its own terminal; the frontend dev server proxies to `http://127.0.0.1:8000`.
- **No images showing up** — some PDFs store diagrams as vector drawings rather than embedded raster images; PyMuPDF can only extract embedded raster images (JPEG/PNG), not vector graphics.
- **"The information is not available in the document."** — the question wasn't well matched by any indexed chunk; try rephrasing, or confirm the right PDF has been processed.
- **Slow first response** — the first embedding/LLM call in a session pays a one-time network round-trip to Google's API; subsequent calls are faster.

## License

MIT — see `LICENSE`.

# Step 1: 

# Activate virtual environment (Windows)
.\.venv\Scripts\activate
# Install dependencies (if not already installed)
pip install -r requirements.txt

# Step 2: Run Backend Server (Terminal 1)
uvicorn api_server:app --reload --port 8000

# Step 3: Run Frontend React UI (Terminal 2)
cd frontend
npm install
npm run dev

# Website Link
https://rag-pdf-chatbot-ew41.vercel.app/