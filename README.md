# RAGAgent

Paper-oriented RAG service with a FastAPI backend and a Vite React frontend.

## Layout

- `src/api/`: backend API routes and request/response schemas.
- `src/RAG/`: paper parsing, chunking, vector storage, retrieval, and answer generation.
- `src/agent/`: agent and research tools, including arXiv and optional web search tools.
- `front/`: React frontend.
- `scripts/`: local development and knowledge import commands.
- `prompts/`: prompt templates.
- `data/papers/`: local papers imported by script and arXiv downloads.
- `data/uploads/`: files uploaded from the web UI.
- `chroma_db` and `md5.text`: local vector database state, ignored by git.

Architecture and module boundaries are documented in `docs/architecture.md`. Current directory layout is in `docs/project-structure.md`.

## Setup

```powershell
uv sync
Copy-Item .env.example .env
cd front
npm install
```

Fill in `DEEPSEEK_API_KEY` and `DashScopeAPI` in `.env`.

## Local Import

Put papers in `data/papers/`, then run:

```powershell
uv run python scripts/import_knowledge.py
```

Import selected files:

```powershell
uv run python scripts/import_knowledge.py data/papers/example.pdf
```

Force rebuild selected files:

```powershell
uv run python scripts/import_knowledge.py --reindex data/papers/example.pdf
```

Clear the collection and import again:

```powershell
uv run python scripts/import_knowledge.py --reset
```

## API Boundaries

Frontend chat uses the Agent entry by default:

```text
POST /chat
POST /chat/stream
```

Pure RAG is kept for debugging and evaluation:

```text
POST /rag/chat
POST /rag/chat/stream
GET  /retrieval/preview
```

This keeps the product behavior as one paper research agent, while still allowing direct RAG evaluation.

Short-term memory uses LangGraph `InMemorySaver`, keyed by a frontend-generated `session_id`. Refreshing the page creates a new session; backend restart clears in-memory sessions. Persistent checkpointer storage is planned later.

## Agent Research Tools

The agent tool layer currently includes:

- `rag_summarize`: answer from the local imported paper knowledge base.
- `arxiv_search`: search arXiv through LangChain `ArxivQueryRun`.
- `arxiv_download`: download one arXiv PDF by ID or URL into `data/papers` or the configured `data_path`.
- `arxiv_download_and_import`: download one arXiv PDF and immediately import it into Chroma.
- `import_paper_to_vector_store`: incrementally import a local PDF/TXT file into Chroma.
- `web_search`: lightweight public web search for non-paper background.

## Development

Start the backend:

```powershell
.\scripts\dev_backend.ps1
```

Start the frontend in another terminal:

```powershell
.\scripts\dev_frontend.ps1
```

Open:

```text
http://127.0.0.1:5173
```

The frontend calls FastAPI through the Vite `/api` proxy.