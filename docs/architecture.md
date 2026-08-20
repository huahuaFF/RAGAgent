# RAGAgent Architecture

This document defines the intended module boundaries for RAGAgent. The product goal is a paper research agent: users talk to one assistant, while the system can retrieve local papers, search arXiv, download papers, update the vector database, and expose RAG internals for debugging and evaluation.

## Product Shape

The user-facing experience should be one chat workspace:

```text
Frontend Chat -> Agent Runtime -> Tools -> RAG / arXiv / Knowledge Import / Web Search
```

Pure RAG remains available, but as an internal/debug path for retrieval inspection and evaluation, not as the main product entry.

## Principles

1. Frontend chat uses the Agent by default.
2. RAG is a capability/tool and a debug target, not a parallel product surface.
3. All knowledge ingestion paths must share one import pipeline.
4. Agent context management is a first-class module, not ad hoc prompt stuffing.
5. Tool calls must be observable: log tool name, arguments, result summary, and errors.
6. Retrieval and answer quality should be measurable through dedicated evaluation APIs.

## Target Modules

```text
src/
  api/
    app.py
    schemas.py
    routes/
      chat.py
      knowledge.py
      rag_debug.py
      evaluation.py

  agent/
    runtime.py
    context.py
    tools/
      registry.py
      rag_tool.py
      arxiv_tool.py
      web_search_tool.py
      knowledge_tool.py
      middleware.py

  knowledge/
    import_service.py
    file_registry.py
    document_store.py
    schemas.py

  RAG/
    ingestion/
      paper_ingestor.py
    vector_store_service.py
    rag_service.py
    retriever.py

  evals/
    retrieval_eval.py
    datasets.py
    metrics.py

  config/
  model/
  utils/
```

The current code does not need to be moved all at once. This is the destination structure for incremental refactoring.

## API Boundaries

Main product chat:

```text
POST /chat
POST /chat/stream
```

These should call the Agent Runtime.

RAG debug and evaluation:

```text
POST /rag/chat
POST /rag/chat/stream
GET  /retrieval/preview
POST /eval/retrieval
```

Knowledge management:

```text
GET  /files
POST /files/upload
POST /knowledge/import
GET  /knowledge/documents
GET  /knowledge/imports/{import_id}
```

The last two can be added later when file/index status tracking exists.

## Agent Layer

The Agent layer decides which tools to call. It should not contain PDF parsing, vector database details, or file upload details.

Current tools:

```text
rag_summarize
arxiv_search
arxiv_download
arxiv_download_and_import
import_paper_to_vector_store
web_search
```

Target tool grouping:

```text
RAG tools:
  rag_summarize

Literature discovery tools:
  arxiv_search
  web_search

Knowledge update tools:
  arxiv_download
  arxiv_download_and_import
  import_paper_to_vector_store
```

Tool registration should eventually move to `agent/tools/registry.py` so `runtime.py` does not import every tool manually.

## Context Management

Current implementation: the Agent uses LangGraph `InMemorySaver` as a checkpointer. The frontend sends a `session_id`, and the backend uses it as LangGraph `thread_id` to restore short-term conversation state.

Target minimal design:

```text
ConversationSession
  session_id
  messages[]
  tool_traces[]
  created_at
  updated_at
```

Short-term implementation:

- Frontend creates one `session_id` per page session.
- Each `/chat` request sends `query + session_id`.
- Backend passes `session_id` as LangGraph `thread_id`.
- `InMemorySaver` stores short-term conversation state until the backend restarts.

Later persistent implementation:

- Replace `InMemorySaver` with SQLite/Postgres checkpointer.
- Persist message history and tool traces across backend restarts.
- Add session list/delete APIs if needed.

## Knowledge Layer

Current problem: importing can be triggered from local scripts, upload endpoints, and agent tools. They should not each implement their own import behavior.

Target service:

```python
KnowledgeImportService.import_files(
    paths: list[str] | None,
    reset: bool = False,
    reindex: bool = False,
) -> ImportStats
```

All import entry points should call this service:

```text
scripts/import_knowledge.py
POST /knowledge/import
import_paper_to_vector_store tool
arxiv_download_and_import tool
```

Later additions:

- document registry with file hash, source, title, path, import status
- import job status for long-running imports
- per-document deletion and reindexing

## RAG Layer

The RAG layer should stay deterministic and testable:

```text
paper file -> parser -> chunks + metadata -> embeddings -> vector store
query -> retriever -> context -> answer prompt -> model response
```

RAG services should expose enough internals for evaluation:

```text
retrieve(query, k) -> chunks
answer(query, chunks) -> answer
answer_with_retrieval(query) -> answer + references
```

Avoid hiding retrieval details inside a single `rag_summarize()` method forever; it makes quality evaluation harder.

## Evaluation Layer

Evaluation should focus on retrieval first, because bad retrieval leads to bad answers.

Initial retrieval metrics:

```text
hit@k
source coverage
page/section correctness
duplicate chunk rate
empty/low-information chunk rate
```

Initial answer metrics:

```text
citation/source presence
answer groundedness check
unsupported claim count
```

The first practical API can be:

```text
POST /eval/retrieval
```

Input:

```json
{
  "items": [
    {
      "query": "What is the mathematical definition of flow matching?",
      "expected_files": ["2210.02747v2.pdf"],
      "expected_keywords": ["velocity field", "probability path"]
    }
  ],
  "k": 8
}
```

Output:

```json
{
  "total": 1,
  "hit_at_k": 1.0,
  "items": [
    {
      "query": "...",
      "hit": true,
      "top_sources": ["2210.02747v2.pdf"],
      "matched_keywords": ["velocity field"]
    }
  ]
}
```

## Frontend Boundaries

Target frontend views:

```text
Chat Workspace
  main user experience, calls /chat/stream

Knowledge Manager
  upload/select/import/reindex files

Retrieval Debug Panel
  calls /retrieval/preview

Evaluation Dashboard
  runs saved retrieval test sets
```

Do not expose every backend tool as a button. The Agent should decide tool usage inside the chat path. Expose debug/eval controls only where they help diagnose quality.

## Refactor Roadmap

### Phase 1: Stabilize Current Product Boundary

Phase 1 implementation status: frontend chat calls /chat/stream, /chat is backed by the Agent, pure RAG is available under /rag/*, and short-term context is passed as recent frontend messages. Server-side persistent sessions are still future work.


- `/chat` and `/chat/stream` call Agent Runtime.
- `/rag/chat` and `/rag/chat/stream` remain pure RAG debug paths.
- Frontend chat stays simple and calls `/chat/stream`.
- Use LangGraph `InMemorySaver` with frontend `session_id` as `thread_id`.

### Phase 2: Centralize Knowledge Import

- Create `src/knowledge/import_service.py`.
- Move vector-store import orchestration out of API/tool/script call sites.
- Make script, API, and agent tools call the same service.

### Phase 3: Agent Runtime Cleanup

- Create `src/agent/runtime.py`.
- Create `src/agent/tools/registry.py`.
- Add context manager and tool trace normalization.
- Keep tool descriptions strict and task-oriented.

### Phase 4: RAG Debug and Evaluation

- Split retrieval from answer generation in the RAG service.
- Add retrieval evaluation endpoint.
- Add frontend evaluation/debug view only after backend metrics are useful.

### Phase 5: Document Registry and Import Jobs

- Track imported documents by hash, source, title, and path.
- Add document-level delete/reindex.
- Add async import job status if imports become slow.

## Current Technical Debt

- Some modules still use capitalized `src/RAG`; standardize later if the package structure is stable.
- Agent does not yet have robust session persistence.
- Tool registration is manual in `react_agent.py`.
- `rag_summarize()` hides retrieval and answer generation behind one method.
- Chroma state and `md5.text` are runtime artifacts; avoid committing them.
- arXiv integration depends on `arxiv<3` because current LangChain community wrapper expects the older `Search.results()` API.