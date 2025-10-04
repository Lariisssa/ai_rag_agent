# RAG PDF/Web QA - Multimodal Document Intelligence

Production-ready Retrieval-Augmented Generation system for answering questions based on uploaded PDFs (text + images) and web search. Built with modern AI and web technologies.

## Key Features

- 📄 **PDF Ingestion**: Extract text and images from PDFs using PyMuPDF
- 🖼️ **Multimodal Vision**: GPT-4o Vision analyzes images (logos, charts, diagrams)
- 🔍 **Semantic Search**: PostgreSQL + pgvector for efficient vector similarity search
- 🌐 **Web Search Integration**: Hybrid RAG with document + web sources
- ⚡ **Streaming Responses**: Real-time SSE streaming for instant feedback
- 🎨 **Modern UI**: React + TypeScript + TailwindCSS + Framer Motion
- 🐳 **Docker Ready**: Full containerization with Docker Compose

---

## Authors and Purpose

This project is a collaboration for studying modern development and Artificial Intelligence technologies, developed by:

- **Larissa Rodrigues** (AI Engineer) - [LinkedIn](https://www.linkedin.com/in/lari-rodriggs/)
- **Vinicius de Moura** (Fullstack Software Engineer) - [LinkedIn](https://www.linkedin.com/in/deviniciusg/)
- **Sofia Rigonati** (Fullstack Software Engineer) - [LinkedIn](https://www.linkedin.com/in/sofia-rigonati-magalh%C3%A3es-louzada-7405b7250/)

---

## Architecture

```mermaid
flowchart TB
%% ---------- NODES ----------
User([👤 User])

subgraph Frontend["🧭 Frontend (React + Vite)"]
    UI[UI Components]
    Renderer[Message Renderer]
    APIClient[API Client · SSE]
    UI --> Renderer
    UI --> APIClient
end

subgraph Backend["⚙️ Backend (FastAPI)"]
    APIRoutes[API Routes] --> Orchestrator[Orchestrator]
    Orchestrator --> Route{Docs or Web?}

    subgraph DocsPipe["📄 Document Pipeline"]
        Ingestion[PDF Ingestion]
        TextEx[Text Extractor]
        ImgEx[Image Extractor]
        Vector[Vector Search]
        Rerank[Semantic Reranking]

        Ingestion --> TextEx
        Ingestion --> ImgEx
        TextEx --> Vector
        Vector --> Rerank
    end

    subgraph WebPipe["🌐 Web Retrieval"]
        WebSearch[Web Search API]
    end

    Route -->|Docs| Vector
    Route -->|Web| WebSearch

    Rerank --> Synth[Answer Synthesis]
    WebSearch --> Synth
    Synth --> GPT4o[GPT-4o Vision (Multimodal)]
    GPT4o --> Stream[Streamed Response]
end

subgraph Storage["🗄️ Storage"]
    DB[(PostgreSQL + pgvector)]
    Media[(Media Files)]
end

Embeds[OpenAI Embeddings API]

%% ---------- CONNECTIONS ----------
User -->|Upload PDF / Ask Question| Frontend
Frontend -->|HTTP + SSE| Backend

Backend -->|Store pages & embeddings| DB
Backend -->|Save images| Media
Backend -->|Embed text| Embeds

Stream -->|SSE| Frontend
ImgEx -->|Save JPG| Media
TextEx -->|Store pages| DB
Vector -->|Similarity Search| DB
```

### Data Flow

1. **Document Upload**:

   - PDF → PyMuPDF → Text per page + Images (JPG)
   - Text → OpenAI Embeddings (3072-d) → pgvector
   - Images → `/media/` folder

2. **Query Processing**:

   - User question → Route decision (Docs/Web/Hybrid)
   - Vector search (cosine similarity) → Top K pages
   - If visual query (logo, chart, etc.) → Include images
   - GPT-4o processes text + images → Grounded answer
   - Stream response with citations

3. **Multimodal Support**:
   - Detects visual queries: "logo", "gráfico", "imagem", etc.
   - Encodes images as base64 → GPT-4o Vision
   - Renders images in chat using ReactMarkdown

---

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key

### Setup

1. **Clone and configure**:

```bash
git clone <repo-url>
cd ai_rag_agent
cp .env.example .env
```

2. **Edit `.env`**:

```env
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/app
```

3. **Start services**:

```bash
docker compose up -d --build
```

4. **Access**:
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8080
   - API Docs: http://localhost:8080/docs

---

## Repository Structure

```
ai_rag_agent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── config.py            # Settings
│   │   ├── routes/              # API endpoints
│   │   │   ├── chat.py          # SSE streaming chat
│   │   │   └── documents.py     # PDF upload
│   │   ├── services/            # Core business logic
│   │   │   ├── ingestion.py     # PDF → DB + images
│   │   │   ├── orchestrator.py  # RAG orchestration
│   │   │   ├── ranking.py       # Vector search
│   │   │   ├── llm.py           # OpenAI client
│   │   │   └── web_search.py    # Web search
│   │   ├── prompts.py           # LLM prompts
│   │   └── middleware.py        # Request logging
│   ├── migrations/              # Alembic DB migrations
│   ├── tests/                   # pytest tests
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app
│   │   ├── api.ts               # API client
│   │   └── components/          # React components
│   ├── package.json
│   └── vite.config.ts
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Environment Variables

Create `.env` from `.env.example`:

```env
# Required
OPENAI_API_KEY=sk-your-key-here
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/app

# Optional
WEB_SEARCH_PROVIDER=tavily  # or brave, serper
WEB_SEARCH_API_KEY=your-search-api-key
LOG_LEVEL=INFO
MEDIA_ROOT=./media
```

---

## API Endpoints

### Documents

**POST /api/documents**

- Upload PDF files (multipart/form-data)
- Extracts text, images, generates embeddings
- Returns: `{ id, title, page_count }[]`

**GET /api/documents**

- List all uploaded documents
- Returns: `{ id, title, page_count }[]`

**DELETE /api/documents/{id}**

- Delete a document and its pages
- Returns: `{ success: true }`

### Chat

**POST /api/chat**

- Server-Sent Events (SSE) stream
- Request body:

```json
{
  "messages": [{ "role": "user", "content": "What is the logo?" }],
  "document_ids": ["uuid-here"],
  "force_web": false
}
```

- Response stream:
  - Tokens: `data: <token>\n\n`
  - Final envelope: `data: { ... }\n\nevent: end\n\n`

---

## Database Schema

### documents

```sql
CREATE TABLE documents (
  id UUID PRIMARY KEY,
  title TEXT,
  page_count INT,
  created_at TIMESTAMPTZ
);
```

### document_pages

```sql
CREATE TABLE document_pages (
  id UUID PRIMARY KEY,
  document_id UUID REFERENCES documents(id) ON DELETE CASCADE,
  page_number INT,
  content TEXT,
  embedding vector(3072),  -- OpenAI text-embedding-3-large
  created_at TIMESTAMPTZ
);
```

### document_page_images

```sql
CREATE TABLE document_page_images (
  id UUID PRIMARY KEY,
  document_page_id UUID REFERENCES document_pages(id) ON DELETE CASCADE,
  position INT,
  file_url TEXT,  -- /media/<uuid>.jpg
  dimensions JSONB  -- {"width": 1024, "height": 768}
);
```

---

## RAG Pipeline Details

### 1. Routing Decision

```python
# Auto mode: LLM decides based on query
if "investimento" in query or "preço" in query:
    use_docs = True
elif "notícia" in query or "hoje" in query:
    use_web = True
```

### 2. Vector Search

```sql
SELECT *, (embedding <=> query_embedding) AS distance
FROM document_pages
WHERE document_id = ANY($1)
ORDER BY distance ASC
LIMIT 15;
```

### 3. Semantic Reranking

- Deduplicates pages
- Sorts by `similarity DESC, page_number ASC`
- Batches of 3 pages, up to 15 total

### 4. Multimodal Synthesis

```python
# Detect visual queries
visual_keywords = ['logo', 'gráfico', 'imagem', 'foto']
if any(k in query.lower() for k in visual_keywords):
    # Encode images as base64 → GPT-4o Vision
    images_b64 = [encode_image(img) for img in page_images]

# Build multimodal message
messages = [{
    "role": "user",
    "content": [
        {"type": "text", "text": query},
        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}}
        for img in images_b64
    ]
}]

# GPT-4o Vision processes text + images
answer = await llm.chat("gpt-4o", messages)
```

---

## Frontend Features

### Chat Interface

- **Message Types**:
  - User messages: Blue gradient bubble
  - Assistant messages: White with markdown rendering
  - Citations: Blue badges `[1]` `[2]`
  - Images: Inline markdown images

### Mode Selection

- **Docs**: Search only uploaded PDFs
- **Web**: Search only the web
- **Auto**: LLM decides based on query

### Sources Panel

Shows grounded sources:

- Document pages with similarity scores
- Web search results with URLs
- Images from relevant pages

---

## Running Locally (Development)

### Backend

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r backend/requirements.txt

# Run migrations
alembic -c backend/alembic.ini upgrade head

# Start server
uvicorn app.main:app --reload --port 8080 --app-dir backend
```

### Frontend

```bash
cd frontend
npm install
npm run dev  # http://localhost:5173
```

---

## Testing

### Unit Tests (pytest)

```bash
pytest backend/tests/
```

### RAG Evaluation (DeepEval)

```bash
# Set environment
export OPENAI_API_KEY=sk-...
export EVAL_DOCUMENT_ID=<uuid-from-upload>

# Run evaluation
deepeval test run backend/evaluation/test_evaluate_rag.py
```

---

## Troubleshooting

### Images not appearing

- Check `MEDIA_ROOT` is correctly mounted
- Verify images are saved: `ls backend/media/`
- Check browser console for 404 errors

### Poor search results

- Ensure embeddings were generated (check `document_pages.embedding`)
- Try increasing `RETRIEVAL_TOP_K` in config
- Use more specific queries

### "No API key" errors

- Verify `.env` has `OPENAI_API_KEY`
- Restart Docker containers after changing `.env`

---

## Production Checklist

- [ ] Set strong `DATABASE_URL` password
- [ ] Use production-grade PostgreSQL (not Docker for prod)
- [ ] Configure CORS properly in `backend/app/main.py`
- [ ] Set up HTTPS/TLS for frontend and backend
- [ ] Enable rate limiting and authentication
- [ ] Monitor costs (OpenAI API usage)
- [ ] Set up logging aggregation (Datadog, Sentry, etc.)
- [ ] Configure backup strategy for PostgreSQL
- [ ] Review and audit PyMuPDF licensing (AGPL)

---

## Tech Stack

**Backend**:

- FastAPI (async Python web framework)
- PostgreSQL 15+ with pgvector
- SQLAlchemy 2.0 (async ORM)
- PyMuPDF (PDF processing)
- Pillow (image processing)
- OpenAI Python SDK
- structlog (structured logging)

**Frontend**:

- React 18
- TypeScript
- Vite (build tool)
- TailwindCSS (styling)
- Framer Motion (animations)
- react-markdown (markdown rendering)
- Lucide React (icons)

**Infrastructure**:

- Docker + Docker Compose
- Alembic (database migrations)

---

## License

This project is an educational MVP. Dependencies have their own licenses:

- PyMuPDF: AGPL (commercial license available)
- OpenAI API: Usage subject to OpenAI terms

---

## Contributing

This is a study project. For suggestions or issues, please open a GitHub issue or contact the authors.
