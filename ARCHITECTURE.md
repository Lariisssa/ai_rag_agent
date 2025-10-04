# Architecture Documentation

This document describes the architecture of the RAG PDF/Web QA system.

## Overview

This is a production-ready Retrieval-Augmented Generation (RAG) system that can answer questions based on uploaded PDF documents and web search results. It uses vector embeddings for semantic search and LLMs for natural language understanding and generation.

## Tech Stack

- **Backend**: Python 3.11, FastAPI (async)
- **Database**: PostgreSQL 16 + pgvector extension
- **Vector Embeddings**: OpenAI `text-embedding-3-large` (3072-d)
- **LLMs**: GPT-5 (primary), GPT-5-mini (routing/simple tasks)
- **Frontend**: React, TypeScript, Vite, Tailwind CSS, Framer Motion
- **PDF Processing**: PyMuPDF (fitz)
- **Web Search**: Tavily, Bing, or SerpAPI (pluggable)
- **Testing**: pytest, DeepEval
- **Deployment**: Docker + Docker Compose

## System Components

### 1. Document Ingestion Pipeline

**Flow**: PDF Upload → Text Extraction → Image Extraction → Embedding Generation → Database Storage

#### Key Features:
- Extracts text from each PDF page while preserving reading order
- Detects and extracts images, converting them to standardized JPG format
- Generates 3072-dimensional embeddings for each page's text
- Stores everything in PostgreSQL with pgvector for efficient ANN search
- Handles up to 500 pages per document
- Async processing with proper error handling and rollback

**Implementation**: `backend/app/services/ingestion.py`

### 2. Vector Search & Ranking

**Flow**: Query → Embedding → ANN Search → Ranking → Top-K Pages

#### Key Features:
- Uses pgvector's cosine similarity (`<=>` operator) for fast ANN search
- IVFFlat index for scalable vector search
- Supports filtering by document IDs
- Includes images in search results
- Fallback to basic search when embeddings are unavailable

**Implementation**: `backend/app/services/ranking.py`

### 3. Query Orchestration

**Flow**: User Query → Routing → Retrieval → Multi-Round Batch Processing → Synthesis

#### Multi-Round Batch Processing:
1. **Round 1**: Retrieve top 3 most similar pages
   - Ask LLM: "Can these pages answer the question?"
   - If YES → synthesize answer
   - If NO → proceed to Round 2

2. **Round 2**: Retrieve next 3 pages (pages 4-6)
   - Ask LLM again with new batch
   - If YES → synthesize answer
   - If NO → fallback to web search (if enabled)

3. **Max batches**: Up to 5 batches (15 pages total)

#### Key Features:
- Intelligent routing between docs/web based on user mode and query
- Structured LLM responses with control codes (1=found, 2=need more, 3=use web)
- Citation tracking for both document pages and web sources
- Query rewriting with conversation history
- Streaming token-by-token responses via SSE

**Implementation**: `backend/app/services/orchestrator.py`

### 4. Web Search Integration

Pluggable architecture supporting multiple providers:

- **Tavily AI Search**: Optimized for RAG/LLM use cases (recommended)
- **Bing Web Search API**: Microsoft's search API
- **SerpAPI**: Google Search wrapper
- **Dummy Provider**: For testing without API keys

**Implementation**: `backend/app/services/web_search.py`

### 5. LLM Client

Centralized LLM client with:
- Model routing (gpt-5 vs gpt-5-mini)
- Retry logic with exponential backoff
- Timeout handling
- Token counting and cost estimation
- Structured logging

**Implementation**: `backend/app/services/llm.py`

### 6. Frontend Architecture

Modern React application with:

- **State Management**: React hooks (useState, useEffect, useCallback)
- **API Communication**: Custom SSE streaming client
- **Animations**: Framer Motion for smooth transitions
- **Styling**: Tailwind CSS with gradient themes
- **Components**:
  - `App.tsx`: Main application with chat interface
  - `SourcesPanel.tsx`: Displays document/web sources with images
  - `Dropzone.tsx`: Drag-and-drop file upload

**Implementation**: `frontend/src/`

## Data Model

```
documents
├── id (UUID, PK)
├── title (TEXT)
├── page_count (INT)
└── created_at (TIMESTAMPTZ)

document_pages
├── id (UUID, PK)
├── document_id (UUID, FK → documents)
├── page_number (INT)
├── content (TEXT)
├── embedding (VECTOR(3072))
└── created_at (TIMESTAMPTZ)

document_page_images
├── id (UUID, PK)
├── document_page_id (UUID, FK → document_pages)
├── file_url (TEXT)
├── position (JSONB)
├── dimensions (JSONB)
└── created_at (TIMESTAMPTZ)

chat_entries (optional logging)
├── id (UUID, PK)
├── content (TEXT)
├── role (TEXT: 'user'|'assistant'|'system')
└── created_at (TIMESTAMPTZ)
```

## API Endpoints

### Documents
- `POST /api/documents` - Upload PDFs (multipart/form-data)
- `GET /api/documents` - List all documents
- `GET /api/documents/{id}` - Get document metadata
- `GET /api/documents/{id}/pages` - Get paginated pages with images

### Chat
- `POST /api/chat` - Submit query and stream response (SSE)
  - Request body: `{ messages, document_ids?, force_web? }`
  - Response: SSE stream with tokens + final JSON envelope

### Health
- `GET /api/healthz` - Health check

## Middleware Stack

(Order matters - first added = outermost)

1. **ErrorHandlerMiddleware**: Catches all exceptions and returns consistent JSON errors
2. **RequestLoggingMiddleware**: Logs all requests with timing
3. **RateLimitMiddleware**: IP-based rate limiting (100 req/5min default)
4. **CORSMiddleware**: CORS headers for cross-origin requests

## Prompt Engineering

### 1. Routing Prompt (gpt-5-mini)
Decides whether to use docs, web, or both based on:
- User query content
- Document titles and keywords
- Explicit user instructions

### 2. Decision Prompt (gpt-5)
Structured JSON response with:
```json
{
  "code": 1|2|3,
  "text": "answer if code=1"
}
```
- `code=1`: Answer found in provided pages
- `code=2`: Need more pages (continue batching)
- `code=3`: Not in docs, suggest web search

### 3. Grounded Synthesis Prompt (gpt-5)
Generates final answer with:
- Strict grounding to provided sources
- Inline citations in brackets [n]
- Portuguese language output
- Concise, direct responses

**Implementation**: `backend/app/prompts.py`

## Image Handling

1. **Extraction**: PyMuPDF detects images on each page
2. **Standardization**: Convert all images to JPG (quality 85)
3. **Storage**: Save to `/media` with UUID filenames
4. **Serving**: Static file serving in dev, S3/GCS for production
5. **Display**:
   - Thumbnails in sources panel
   - Click to open full-size modal with animations
   - Lazy loading for performance

## Testing Strategy

### 1. Unit Tests (`backend/tests/`)
- `test_orchestrator.py`: Query rewriting, routing logic
- `test_web_search.py`: All search providers
- `test_ranking.py`: ANN search with images
- `test_ingestion.py`: PDF processing and image extraction
- `test_integration.py`: End-to-end flows

### 2. RAG Evaluation (`backend/evaluation/`)
Uses DeepEval framework with metrics:
- **Answer Relevancy**: Measures if answer is relevant to query
- **Faithfulness**: Ensures answer is grounded in sources
- Golden dataset: 10 test cases based on `samples/plano_negocios.pdf`

Run with: `deepeval test run backend/evaluation/test_evaluate_rag.py`

## Performance Optimizations

1. **Async I/O**: All database and API calls are async
2. **Batch Embeddings**: Process multiple pages concurrently
3. **Vector Indexing**: IVFFlat index on embeddings for fast ANN
4. **Streaming Responses**: Server-Sent Events for immediate feedback
5. **Lazy Image Loading**: Images load only when visible
6. **Query Deduplication**: Remove duplicate pages before batching
7. **Smart Batching**: Stop early when answer is found

## Security & Rate Limiting

- IP-based rate limiting (configurable)
- File type validation (PDF only)
- File size limits (25MB default)
- Sanitized filenames for media storage
- CORS protection
- No authentication (public demo) - add auth for production

## Configuration

Environment variables (`.env`):
```bash
OPENAI_API_KEY=
DATABASE_URL=postgresql+asyncpg://...
WEB_SEARCH_PROVIDER=tavily|bing|serpapi|dummy
WEB_SEARCH_API_KEY=
WEB_SEARCH_ENABLED=true
EMBED_BATCH_SIZE=32
LOG_LEVEL=INFO
RATE_LIMIT_PER_5MIN=100
MAX_UPLOAD_MB=25
MEDIA_ROOT=/app/media
```

## Deployment

### Development
```bash
docker-compose up -d --build
```

### Production Considerations
1. Replace in-memory rate limiter with Redis
2. Use S3/GCS for media storage
3. Add authentication & authorization
4. Enable HTTPS
5. Set up monitoring (Prometheus + Grafana)
6. Configure horizontal scaling for FastAPI
7. Use managed PostgreSQL with pgvector
8. Add CDN for frontend assets

## Observability

### Structured Logging
All logs use `structlog` with JSON output:
- Request/response timing
- LLM token counts
- Embedding generation
- Search operations
- Error tracking

### Key Events Logged
- `ingest_start`, `doc_inserted`, `page_inserted`
- `ann_search_params`, `ann_search_pages`
- `batch_try`, `batch_structured_decision`
- `retrieval_sources`
- `synth_answer`, `synth_prompts`
- `request_start`, `request_complete`
- `rate_limit_exceeded`

## Future Enhancements

1. **OCR Support**: Process scanned PDFs with Tesseract
2. **Multi-language**: Support languages beyond Portuguese/English
3. **Conversation Memory**: Redis-backed session storage
4. **Advanced Reranking**: Use cross-encoder models
5. **Hybrid Search**: Combine BM25 + vector search
6. **Document Deletion**: Add endpoints to delete docs
7. **User Accounts**: Multi-tenancy with auth
8. **Real-time Collaboration**: WebSocket support
9. **Export Answers**: PDF/Markdown export
10. **Analytics Dashboard**: Usage metrics and insights
