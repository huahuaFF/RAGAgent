# RAGAgent

Paper-oriented RAG service with a FastAPI backend and a Vite React frontend.

## Layout

- `src/api/`: backend API routes and request/response schemas.
- `src/RAG/`: paper parsing, chunking, vector storage, retrieval, and answer generation.
- `front/`: React frontend.
- `scripts/`: local development and knowledge import commands.
- `prompts/`: prompt templates.
- `data/papers/`: local papers imported by script.
- `data/uploads/`: files uploaded from the web UI.
- `chroma_db/` and `md5.text`: local vector database state, ignored by git.

More detail is in `docs/project-structure.md`.

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