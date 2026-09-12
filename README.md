# adv_rag — Enterprise Agentic RAG

A local-first, agentic Retrieval-Augmented Generation (RAG) system for enterprise technical documentation. The stack ingests multi-format documents, indexes them in Qdrant, and answers questions through a LangGraph agent with semantic retrieval, cross-encoder reranking, and LLM gateway routing.

**Domain focus:** Kubernetes, Intel, and networking documentation (extensible to other corpora).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           INGESTION PIPELINE                            │
│  PDF / HTML / TXT / DOCX / PPTX  →  Chunk  →  Embed  →  Qdrant Cloud   │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         LANGGRAPH AGENT (RAG)                           │
│                                                                         │
│   ┌──────────┐    conversational?    ┌───────────┐    ┌───────────┐   │
│   │ Planner  │ ────────────────────► │ Responder │ ──►│   END     │   │
│   └────┬─────┘                       └───────────┘    └───────────┘   │
│        │ technical query                                              │
│        ▼                                                              │
│   ┌──────────┐    top-5 reranked    ┌───────────┐                    │
│   │Retriever │ ───────────────────► │ Responder │ ──► END             │
│   └──────────┘                       └───────────┘                    │
│        │                                                              │
│        ├── Qdrant vector search (top 15)                              │
│        └── FlashRank cross-encoder rerank                             │
└─────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         PORTKEY LLM GATEWAY                             │
│   Groq Llama 3.3 70B  →  fallback Llama 3.1 8B  │  cache  │  retry    │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Current Progress

### Completed

| Module | Status | Description |
|--------|--------|-------------|
| **Document loaders** | Done | PDF (`pypdf` + `pdfplumber` fallback), HTML (`BeautifulSoup`), TXT, Office (`unstructured`) |
| **Chunking** | Done | Paragraph-aware splitter (~1500 char chunks) |
| **Embeddings** | Done | Gemini `gemini-embedding-2-preview` (3072-d) with `all-mpnet-base-v2` fallback (768-d) |
| **Ingestion processor** | Done | Universal directory scanner, local JSON checkpoint, Qdrant upsert |
| **Vector search** | Done | Qdrant `query_points` with cosine similarity |
| **Reranking** | Done | FlashRank local cross-encoder (MS MARCO MiniLM) |
| **Agent graph** | Done | LangGraph: Planner → Retriever → Responder with `MemorySaver` |
| **LLM gateway** | Done | Portkey client with fallback, cache, and retry |
| **Observability (partial)** | Done | Logfire spans across ingestion, retrieval, and agent nodes |

### In Progress

| Module | Status | Notes |
|--------|--------|-------|
| **Gateway config** | WIP | `app/gateway/__init__.py` is empty; `config.py` needs Portkey/Groq slug settings |
| **Agent wiring** | WIP | Graph compiles; no API or UI entry point yet |

### Planned (confirmed targets)

These are declared in `requirements.txt` and represent the next build phases:

| Phase | Target | Purpose |
|-------|--------|---------|
| **API layer** | FastAPI + Uvicorn | REST endpoints for chat and ingestion triggers |
| **Chat UI** | Streamlit dashboard | Interactive chat with plan/status visibility |
| **Guardrails** | NeMo Guardrails | Input/output safety rails for enterprise use |
| **Evaluation** | RAGAS + DeepEval | Faithfulness, relevancy, recall, and pytest-based eval suite |
| **Production monitoring** | Langfuse + LangSmith | Live tracing, user feedback, and LangChain run observability |

---

## Project Structure

```
adv_rag/
├── app/
│   ├── agents/
│   │   ├── graph.py              # LangGraph workflow definition
│   │   ├── state.py              # AgentState TypedDict
│   │   └── nodes/
│   │       ├── planner.py        # Intent routing (conversational vs retrieval)
│   │       ├── retriever.py      # Qdrant search + FlashRank rerank
│   │       └── responder.py      # LLM synthesis via Portkey
│   ├── config.py                 # Environment-based settings
│   ├── gateway/
│   │   └── client.py             # Portkey gateway + LangChain shim
│   ├── ingestion/
│   │   ├── processor.py          # Universal ingestion CLI
│   │   ├── chunking/splitter.py
│   │   └── loaders/              # pdf, html, text, office
│   └── services/retrieval/
│       ├── embedding.py          # Gemini + sentence-transformers
│       ├── qdrant_service.py     # Vector search
│       └── ranking_service.py    # FlashRank reranker
├── DATA/
│   ├── true_data/                # Real Kubernetes docs (HTML)
│   └── noisy_data/               # Synthetic test corpus (TXT, HTML, DOCX, PPTX)
├── processed_data/               # Local ingestion checkpoints (gitignored)
├── requirements.txt
└── README.md
```

---

## Prerequisites

- Python 3.11+
- [Qdrant Cloud](https://qdrant.tech/) cluster (or self-hosted Qdrant)
- API keys:
  - **Gemini** — document embeddings
  - **Groq** — LLM inference (via Portkey)
  - **Portkey** — LLM gateway routing
  - **Qdrant** — vector database

---

## Setup

```bash
# Clone and enter the project
cd adv_rag

# Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
# Embeddings
GEMINI_API_KEY=your_gemini_key

# Vector database
QDRANT_API_KEY=your_qdrant_key
QDRANT_CLUSTER_ENDPOINT=https://your-cluster.qdrant.io

# LLM (Groq via Portkey)
GROQ_API_KEY=your_groq_key
PORTKEY_API_KEY=your_portkey_key
GROQ_SLUG=groq
GROQ_SLUG_2=groq
```

> **Note:** `config.py` currently exposes a subset of these variables. The gateway client also expects `PORTKEY_API_KEY`, `GROQ_SLUG`, and `GROQ_SLUG_2` — add them to `Settings` before running the agent.

---

## Usage

### Ingest documents

The processor scans a directory, auto-detects `true` / `noisy` source types from folder names, and indexes chunks into the `adv_rag` Qdrant collection.

```bash
# Ingest everything under DATA/ (true_data + noisy_data)
python -m app.ingestion.processor DATA --wipe

# Ingest a single folder with an explicit source type
python -m app.ingestion.processor DATA/true_data true
```

**Pipeline per file:** parse → chunk → save local JSON → embed → upsert to Qdrant.

Use `--wipe` on first run or after switching embedding models to avoid dimension mismatches (768-d fallback vs 3072-d Gemini).

### Run the agent (programmatic)

```python
from app.agents.graph import rag_agent

config = {"configurable": {"thread_id": "user-session-1"}}
result = rag_agent.invoke(
    {"messages": [{"role": "user", "content": "How does Kubernetes HPA work?"}]},
    config=config,
)
print(result["final_answer"])
```

---

## Data

| Folder | Contents | Purpose |
|--------|----------|---------|
| `DATA/true_data/` | Kubernetes HTML docs (job management, pod autoscaling) | Ground-truth retrieval corpus |
| `DATA/noisy_data/` | Synthetic documents in TXT, HTML, DOCX, PPTX | Parser and indexing stress tests |

Processed chunk metadata is written to `processed_data/<source_type>/` as JSON for debugging and re-embedding without re-parsing.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Orchestration | LangGraph, LangChain |
| LLM | Groq Llama 3.3 70B (via Portkey gateway) |
| Embeddings | Google Gemini Embedding 2 Preview |
| Vector DB | Qdrant Cloud |
| Reranking | FlashRank (local ONNX cross-encoder) |
| Parsing | pypdf, pdfplumber, BeautifulSoup, unstructured |
| Observability | Logfire (active), LangSmith + Langfuse (planned) |
| Safety | NeMo Guardrails (planned) |
| Evaluation | RAGAS + DeepEval (planned) |
| API / UI | FastAPI + Streamlit (planned) |

---

## Development Notes

- **Embedding model migration:** Google retired `text-embedding-004` in Jan 2026. The project now uses `gemini-embedding-2-preview`. If you previously indexed with the 768-d fallback, drop and recreate the Qdrant collection (`--wipe`).
- **Rate limits:** Gemini embedding calls retry up to 4 times with exponential backoff on 429/quota errors.
- **Context window:** The responder truncates retrieved context at ~25,000 characters to stay within Groq TPM limits.
- **Conversational bypass:** The planner routes greetings and memory-only questions directly to the responder, skipping retrieval.

---

## License

Private project — no license specified.
