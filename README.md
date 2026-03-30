# NMK Architects Chatbot

RAG-based chatbot for **Nguyen Minh Khang Architects** — a Vietnamese architecture and interior design company. Answers questions about company services, projects, contact information, and design styles using semantic search over a curated knowledge base, grounded by a local LLM.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Data Ingestion](#data-ingestion)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Frontend](#frontend)
- [Module Reference](#module-reference)
- [Docker Deployment](#docker-deployment)
- [Deploy to Render (Production)](#deploy-to-render-production)
- [Environment Variables](#environment-variables)

---

## Architecture Overview

```
User (Browser / CLI)
        │
        ▼
┌───────────────────┐
│   FastAPI Backend  │  POST /api/chat
│   (api/main.py)   │  GET  /api/health
└────────┬──────────┘
         │
         ▼
┌────────────────────────────────────────┐
│              RAG Pipeline              │
│                                        │
│  1. Embed query (multilingual-e5-small)│
│  2. Search Qdrant (cosine, top-5)      │
│  3. Build context from results         │
│  4. Generate answer via Ollama         │
└──────┬─────────────────────┬───────────┘
       │                     │
       ▼                     ▼
┌─────────────┐    ┌──────────────────┐
│   Qdrant    │    │  Ollama LLM      │
│ Vector DB   │    │  (qwen2.5:3b)    │
│ port 6333   │    │  port 11434      │
└─────────────┘    └──────────────────┘
       ▲
       │  (one-time ingestion)
┌──────────────────────────────────────┐
│  Ingestion Pipeline                  │
│  data/raw/ → chunk → embed → upsert  │
└──────────────────────────────────────┘
```

**RAG flow per request:**
1. User question → embed with `intfloat/multilingual-e5-small` (384-dim)
2. Qdrant returns top-5 chunks with cosine score ≥ 0.3
3. Chunks formatted as numbered context blocks
4. Ollama (`qwen2.5:3b`) generates a grounded Vietnamese answer
5. Answer + source documents returned to UI

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Web framework** | FastAPI + Uvicorn |
| **LLM** | Ollama — `qwen2.5:3b` |
| **Embedding** | `intfloat/multilingual-e5-small` (SentenceTransformers) |
| **Vector DB** | Qdrant |
| **Data validation** | Pydantic v2 |
| **HTML parsing** | BeautifulSoup4 |
| **Config** | YAML + environment variables |
| **Frontend** | Vanilla HTML / CSS / JavaScript |
| **Container** | Docker + Docker Compose |

---

## Project Structure

```
chatbot/
├── api/                        # FastAPI application
│   ├── main.py                 # App factory, CORS, static files
│   ├── schemas.py              # Pydantic request/response models
│   └── routes/
│       ├── chat.py             # POST /api/chat
│       └── health.py           # GET  /api/health
│
├── core/                       # Shared utilities
│   ├── schema.py               # RetrievedDocument dataclass
│   ├── settings_loader.py      # YAML config + env var overrides
│   └── logging_setup.py        # logging.config from YAML
│
├── llm/                        # LLM interface
│   ├── generator.py            # generate_answer() via Ollama
│   └── prompt.py               # System prompt + build_prompt()
│
├── retrieval/
│   └── retriever.py            # retrieve() — embed + Qdrant search
│
├── embedding/
│   ├── embedder.py             # embed_texts() — SentenceTransformers
│   └── batch_embed.py          # batch_embed_texts() — batched ingestion
│
├── vectorstore/
│   ├── qdrant.py               # Qdrant client + ensure_collection()
│   ├── index.py                # build_qdrant_points()
│   └── upsert.py               # upsert_chunks()
│
├── ingestion/
│   ├── pipeline.py             # run_ingestion_pipeline() orchestrator
│   ├── load_data.py            # JSON export → per-table files
│   └── chunking/               # One module per data type
│       ├── companyInfo.py
│       ├── projects.py
│       ├── news.py
│       ├── InteriorStyles.py
│       ├── newCategories.py
│       ├── projectCategories.py
│       ├── heroSlides.py
│       └── architectureTypes.py
│
├── frontend/                   # Web UI (served by FastAPI)
│   ├── index.html
│   ├── style.css
│   └── app.js
│
├── config/
│   ├── settings.yaml           # Master configuration
│   └── logging.yaml            # Logging handlers & formatters
│
├── data/
│   ├── raw/                    # Original DB export
│   └── processed/              # Per-table JSON files
│
├── logs/                       # application.log written here
├── chat.py                     # Standalone CLI chat
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

---

## Setup & Installation

### Prerequisites

| Tool | Version | Notes |
|---|---|---|
| Python | 3.11+ | |
| Ollama | latest | Must be running locally |
| Docker + Compose | latest | For containerized setup |

### 1. Install Ollama and pull the model

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5:3b
```

### 2. Clone and install Python dependencies

```bash
cd "LLM course/chatbot"
pip install -r requirements.txt
```

### 3. Start Qdrant

```bash
# With Docker
docker run -d -p 6333:6333 -p 6334:6334 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant

# Or via docker-compose (qdrant service only)
docker-compose up qdrant -d
```

### 4. Run the ingestion pipeline

```bash
# From the chatbot/ directory
python -m ingestion.pipeline
```

This reads `data/raw/database_export_*.json`, splits it into per-table files in `data/processed/`, chunks each entity, embeds the chunks, and upserts them into Qdrant.

### 5. Start the API server

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

---

## Configuration

All settings live in `config/settings.yaml`. Any value can be overridden at runtime with an environment variable (see [Environment Variables](#environment-variables)).

```yaml
app:
  name: NMK-chatbot-app
  version: 1.0.0-beta
  env: production

embedding:
  model: intfloat/multilingual-e5-small   # 384-dim, multilingual
  batch_size: 64
  device: cpu                              # "cuda" for GPU

vector_database:
  type: qdrant
  host: localhost
  port: 6333
  url: http://localhost:6333               # takes priority over host:port
  api_key: null                            # set for Qdrant Cloud
  collection_name: nmk_chatbot_collection
  distance: cosine
  vector_size: 384

llm:
  provider: ollama
  model_name: qwen2.5:3b
  base_url: http://localhost:11434
  temperature: 0.2
  max_tokens: 1024
  timeout: 60

retrieval:
  top_k: 5                  # max documents to retrieve
  score_threshold: 0.3      # min cosine similarity

chunking:
  chunk_size: 512
  chunk_overlap: 50
```

---

## Data Ingestion

The ingestion pipeline is a one-time (or on-demand) operation that populates the vector database.

### Step 1 — Load raw data

```bash
python -m ingestion.load_data
```

Reads the database export from `data/raw/` and writes individual JSON files to `data/processed/`:

| File | Content |
|---|---|
| `companyInfo.json` | Company name, slogan, description, contacts, hours |
| `projects.json` | Portfolio projects with category, style, location, area |
| `news.json` | Articles with HTML content |
| `newsCategories.json` | News taxonomy |
| `projectCategories.json` | Project taxonomy |
| `interiorStyles.json` | Interior design style names |
| `architectureTypes.json` | Architecture type names and descriptions |
| `heroSlides.json` | Website hero section content |

### Step 2 — Chunk, embed, and upsert

```bash
python -m ingestion.pipeline
```

Each chunker follows this pattern:
1. Load the processed JSON file
2. Validate required fields
3. Format a Vietnamese text description per entity
4. Attach metadata (`type`, `source`, entity IDs, slugs)
5. Return `{"text": str, "metadata": dict}` objects

All chunks are then:
- Embedded in batches of 64 with `intfloat/multilingual-e5-small`
- Upserted into Qdrant as `PointStruct` objects (UUID, vector, payload)

### Chunk payload structure

```json
{
  "text": "Công ty Nguyen Minh Khang Architects ...",
  "type": "company_info",
  "source": "companyInfo",
  "company_id": 3,
  "company_name": "Nguyen Minh Khang Architects"
}
```

---

## Running the Application

### Development

```bash
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

- API docs (Swagger): http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Web UI: http://localhost:8000

### CLI mode

```bash
python chat.py
```

Interactive REPL in the terminal. Type `exit`, `quit`, or `thoát` to stop.

---

## API Reference

### `POST /api/chat`

Send a question and receive a grounded answer.

**Request body**

```json
{
  "question": "Công ty NMK có những dịch vụ gì?",
  "session_id": "optional-uuid-string"
}
```

| Field | Type | Required | Constraints |
|---|---|---|---|
| `question` | string | Yes | 1–512 characters |
| `session_id` | string | No | Returned in response for tracking |

**Response**

```json
{
  "answer": "Nguyen Minh Khang Architects cung cấp dịch vụ ...",
  "session_id": "a1b2c3d4-...",
  "sources": [
    {
      "id": "f3a1...",
      "score": 0.87,
      "text": "Công ty Nguyen Minh Khang ...",
      "metadata": {
        "type": "company_info",
        "source": "companyInfo",
        "company_id": 3
      }
    }
  ]
}
```

**No-results response** (when Qdrant returns nothing above threshold):

```json
{
  "answer": "Tôi không tìm thấy thông tin phù hợp trong dữ liệu hiện có.",
  "session_id": "...",
  "sources": []
}
```

---

### `GET /api/health`

Returns service configuration and connectivity status.

**Response**

```json
{
  "status": "ok",
  "app_name": "NMK-chatbot-app",
  "version": "1.0.0-beta",
  "llm_provider": "ollama",
  "llm_model": "qwen2.5:3b",
  "vector_db": "qdrant",
  "collection": "nmk_chatbot_collection"
}
```

---

## Frontend

The web UI is a single-page application served as static files by FastAPI at `http://localhost:8000`.

### Features

- **Chat interface** — message bubbles for user and bot, timestamps
- **Typing indicator** — animated three-dot loader while waiting for response
- **Source documents** — collapsible accordion under each bot reply showing chunk text and relevance score
- **Sidebar** — 6 suggested questions, company contact info, live API health status
- **Session tracking** — maintains `session_id` across messages in the same tab
- **Clear conversation** — resets the session and returns to the welcome screen
- **Mobile responsive** — sidebar overlays on screens narrower than 700px
- **Keyboard shortcuts** — `Enter` sends, `Shift+Enter` inserts a newline

### Design system

| Token | Value | Usage |
|---|---|---|
| Primary dark | `#1C2B3A` | Sidebar, user bubbles, headings |
| Accent gold | `#C8A96E` | Logo, buttons, highlights |
| Background | `#F4F3EF` | Page, chat area |
| Surface | `#FFFFFF` | Bot bubbles, header, input bar |
| Error | `#D64C4C` | Error messages |
| Success | `#4CAF7D` | Health dot when connected |

Font: [Be Vietnam Pro](https://fonts.google.com/specimen/Be+Vietnam+Pro) — optimized for Vietnamese.

### File layout

```
frontend/
├── index.html   # HTML shell — sidebar, header, messages, input
├── style.css    # Design system, layout, animations, responsive
└── app.js       # State, API calls, rendering, event handlers
```

---

## Module Reference

### `core/settings_loader.py` — `load_settings() -> dict`

Merges `config/settings.yaml` with environment variable overrides. Always call this at module level and cache the result.

### `core/schema.py` — `RetrievedDocument`

```python
@dataclass
class RetrievedDocument:
    id: str
    score: float
    text: str
    metadata: dict[str, any]
```

### `embedding/embedder.py` — `embed_texts(texts: list[str]) -> list[list[float]]`

Embeds a list of strings and returns L2-normalised 384-dim vectors. The model is loaded once on first call.

### `embedding/batch_embed.py` — `batch_embed_texts(texts: list[str]) -> list[list[float]]`

Same as `embed_texts` but processes in batches of 64. Use this for ingestion.

### `retrieval/retriever.py` — `retrieve(query: str) -> list[RetrievedDocument]`

Embeds the query and searches Qdrant. Returns up to `top_k` documents with score ≥ `score_threshold`. Returns `[]` on Qdrant connection error.

### `llm/generator.py` — `generate_answer(context: str, question: str) -> str`

Sends the formatted prompt to Ollama and returns the answer string. Returns a Vietnamese error message on Ollama connection or response errors.

### `llm/prompt.py` — `build_prompt(context: str, question: str) -> str`

Combines the system prompt with context and question. The system prompt instructs the model to:
- Only use information from the provided context
- Answer in Vietnamese only
- Not synthesize or make suggestions beyond the context

### `vectorstore/qdrant.py` — `get_qdrant_client()` / `ensure_collection()`

`get_qdrant_client()` returns a singleton `QdrantClient`. `ensure_collection()` creates the collection with the configured vector params if it does not already exist.

### `ingestion/pipeline.py` — `run_ingestion_pipeline()`

Calls every chunking module in sequence, concatenates all chunks, then calls `upsert_chunks()` once.

---

## Docker Deployment

### Build and start all services

```bash
docker-compose up --build
```

This starts:
- **qdrant** — vector database on ports 6333 (HTTP) and 6334 (gRPC), with persistent volume
- **chatbot** — FastAPI app on port 8000, connected to the qdrant service

### Services

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333", "6334:6334"]
    volumes: [qdrant_data:/qdrant/storage]

  chatbot:
    build: .
    ports: ["8000:8000"]
    depends_on: [qdrant]
    environment:
      QDRANT_URL: http://qdrant:6333
      LLM_BASE_URL: http://host.docker.internal:11434
```

> **Note:** Ollama runs on the host machine. The chatbot container reaches it via `host.docker.internal:11434` (works on Docker Desktop for Mac/Windows). On Linux, use the host's LAN IP or `--add-host=host.docker.internal:host-gateway`.

### Run ingestion inside the container

```bash
docker-compose exec chatbot python -m ingestion.pipeline
```

---

## Deploy to Render (Production)

Deploy the full stack for free using **Render** (FastAPI + frontend) + **Qdrant Cloud** (vector DB) + **Groq** (LLM API).

### Why these services?

| Service | Why |
|---|---|
| **Render** | Runs the FastAPI app + serves the frontend. Free tier web service supports Docker. |
| **Qdrant Cloud** | Managed vector DB. Free tier: 1 GB storage, no credit card needed. |
| **Groq** | Free, fast OpenAI-compatible LLM API. Supports `llama-3.1-8b-instant` with 14,400 req/day free. |

---

### Step 1 — Create a Qdrant Cloud cluster

1. Sign up at **https://cloud.qdrant.io**
2. Create a free cluster (choose any region)
3. Copy the **Cluster URL** (e.g. `https://xxxx.us-east4-0.gcp.cloud.qdrant.io:6333`) and the **API Key**

### Step 2 — Get a Groq API key

1. Sign up at **https://console.groq.com**
2. Go to **API Keys → Create API Key**
3. Copy the key (starts with `gsk_...`)

### Step 3 — Run ingestion against Qdrant Cloud

Before deploying, populate the cloud vector DB from your local machine:

```bash
cd "LLM course/chatbot"

# Point to your Qdrant Cloud cluster
export QDRANT_URL=https://xxxx.us-east4-0.gcp.cloud.qdrant.io:6333
export QDRANT_API_KEY=your-qdrant-api-key

python -m ingestion.pipeline
```

### Step 4 — Push your code to GitHub

```bash
git init
git add .
git commit -m "initial commit"
git remote add origin https://github.com/YOUR_USERNAME/nmk-chatbot.git
git push -u origin main
```

> Make sure `.env` is in `.gitignore` — never commit API keys.

### Step 5 — Create a Render Web Service

1. Go to **https://render.com** → **New → Web Service**
2. Connect your GitHub repository
3. Render will auto-detect `render.yaml` — click **Apply**
4. Go to **Environment** and fill in the four secret variables:

| Key | Value |
|---|---|
| `LLM_API_KEY` | Your Groq API key (`gsk_...`) |
| `QDRANT_URL` | Your Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Your Qdrant Cloud API key |

5. Click **Deploy** — Render builds the Docker image and deploys

### Step 6 — Verify

Once the deployment is live, open:

```
https://nmk-chatbot.onrender.com          # Web UI
https://nmk-chatbot.onrender.com/api/health  # Health check
https://nmk-chatbot.onrender.com/docs        # Swagger UI
```

The health endpoint should return:
```json
{
  "status": "ok",
  "llm_model": "llama-3.1-8b-instant",
  "collection": "nmk_chatbot_collection"
}
```

### LLM provider summary

The `LLM_PROVIDER` env var controls which backend is used:

| `LLM_PROVIDER` | Use case | Key env vars needed |
|---|---|---|
| `ollama` | Local development | `LLM_BASE_URL` (default `http://localhost:11434`) |
| `openai` | Cloud (Groq, OpenAI, Together AI, etc.) | `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL_NAME` |

To switch back to Ollama locally, remove `LLM_PROVIDER` from your env (or set it to `ollama`).

---

## Environment Variables

All variables override the corresponding `config/settings.yaml` value.

| Variable | Default | Description |
|---|---|---|
| `APP_ENV` | `production` | Application environment |
| `QDRANT_URL` | `http://localhost:6333` | Qdrant HTTP URL |
| `QDRANT_API_KEY` | `null` | API key for Qdrant Cloud |
| `QDRANT_COLLECTION_NAME` | `nmk_chatbot_collection` | Collection name |
| `QDRANT_TIMEOUT` | — | Qdrant client timeout (seconds) |
| `EMBEDDING_MODEL` | `intfloat/multilingual-e5-small` | HuggingFace model ID |
| `EMBEDDING_DEVICE` | `cpu` | `cpu` or `cuda` |
| `EMBEDDING_BATCH_SIZE` | `64` | Batch size for ingestion |
| `LLM_PROVIDER` | `ollama` | LLM backend provider |
| `LLM_MODEL_NAME` | `qwen2.5:3b` | Ollama model name |
| `LLM_BASE_URL` | `http://localhost:11434` | Ollama base URL or Groq: `https://api.groq.com/openai/v1` |
| `LLM_API_KEY` | — | API key for `openai` provider (Groq, OpenAI, etc.) |
| `LLM_TEMPERATURE` | `0.2` | Sampling temperature |
| `LLM_MAX_TOKENS` | `1024` | Max tokens to generate |
| `LLM_TIMEOUT` | `60` | LLM request timeout (seconds) |
| `RETRIEVAL_TOP_K` | `5` | Max documents to retrieve |
| `RETRIEVAL_SCORE_THRESHOLD` | `0.3` | Min cosine similarity score |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `MAX_QUERY_LENGTH` | `512` | Max question length (CLI) |
