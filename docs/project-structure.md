# Project Structure

```text
RAGAgent/
  main.py                  # FastAPI ASGI entry
  pyproject.toml           # Python package and backend dependencies
  uv.lock                  # Locked backend dependencies
  .env.example             # Example runtime configuration
  prompts/                 # Prompt templates
  src/
    api/                   # FastAPI routes and DTO schemas
    RAG/                   # Paper ingestion, vector store, RAG service
    agent/                 # Agent-side tool wrappers
    config/                # Environment-backed configuration
    model/                 # LLM client construction
    utils/                 # File, path, prompt helpers
  front/                   # Vite + React frontend
  scripts/
    import_knowledge.py    # Local paper import command
    dev_backend.ps1        # Backend dev server
    dev_frontend.ps1       # Frontend dev server
  data/
    papers/                # Local papers imported by script
    uploads/               # Files uploaded from the web UI
  chroma_db/               # Local Chroma persistence, ignored by git
  logs/                    # Local logs, ignored by git
```

The backend and frontend are intentionally separated. FastAPI exposes API endpoints only; Vite serves the frontend and proxies `/api/*` requests to FastAPI during development.