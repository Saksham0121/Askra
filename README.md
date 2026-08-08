# Askrab — Intelligent Agentic RAG System

> A 7-layer agentic RAG pipeline with FastAPI backend, React dashboard, and JWT RBAC.

---

## Architecture

```
User Query
  │
  ▼
L0 · Safety Guardrail      ← regex/pattern jailbreak + injection detection
  │
  ▼
L1 · Intent Classifier     ← rule-based (75% conf threshold) + Groq LLM fallback
  │
  ▼
L2 · Decision Router       ← FAISS relevance probe (~50ms) → RAG or LLM path
  │
  ├──(RAG)──────────────────────────────────────────────────────────────────┐
  │                                                                         │
  ▼                                                                         │
L3 · RAG Tool                                                               │
  ├─ Query Rewriter (Groq)                                                  │
  ├─ Hybrid Retrieval: FAISS (0.7) + BM25 (0.3) → Top-10                   │
  ├─ CrossEncoder Reranking → Top-5                                         │
  └─ Groq Answer Generation                                                 │
  │                                                                         │
  ├──(Code)─→ L3 · Code Tool (Groq code model)                             │
  │                                                                         │
  ├──(Chat)─→ L3 · Chat Tool (Groq chat model)                             │
  │                                                                         │
  ▼◄────────────────────────────────────────────────────────────────────────┘
L4 · NLI Validation        ← LLM-as-judge (correctness, completeness, citations)
  │
  ▼ (if score < threshold)
L5 · Reflection Loop       ← up to 2 retries with refined prompt
  │
  ▼
L6 · Response Assembly     ← answer + citations + confidence + tool trace
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| **LLM** | Groq (`llama-3.1-8b-instant`) |
| **Embeddings** | `all-MiniLM-L6-v2` (local) |
| **Vector Store** | FAISS (local) |
| **Keyword Search** | BM25 (`rank-bm25`) |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| **Backend** | FastAPI + Motor (async MongoDB) |
| **Auth** | JWT (access + refresh) + bcrypt |
| **RBAC** | Employee / Manager / Admin |
| **Frontend** | React 18 + Vite + Recharts |
| **Database** | MongoDB |

---

## Quickstart

### Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Make sure MongoDB is running locally
# Edit .env if needed (Groq key is pre-filled)

uvicorn app.main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend at: http://localhost:5173

---

## RBAC Roles

| Role | Permissions |
|---|---|
| **Employee** | Chat, view documents in own department |
| **Manager** | All employee permissions + upload docs + analytics |
| **Admin** | All permissions + user management + audit logs |

---

## API Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | Public | Register new user |
| POST | `/auth/login` | Public | Login → JWT tokens |
| POST | `/auth/refresh` | Public | Refresh access token |
| GET  | `/auth/me` | Any | Current user info |
| POST | `/api/chat` | Any | Sync chat query |
| GET  | `/api/chat/stream` | Any | SSE streaming chat |
| GET  | `/api/chat/history` | Any | Chat history |
| POST | `/api/documents/upload` | Any | Upload + ingest document |
| GET  | `/api/documents` | Any | List documents |
| DELETE | `/api/documents/{id}` | Admin | Delete document |
| GET  | `/api/analytics/overview` | Manager+ | Stats overview |
| GET  | `/api/analytics/query-trends` | Manager+ | Daily query trends |
| GET  | `/api/analytics/tool-usage` | Manager+ | Tool breakdown |
| GET  | `/api/admin/users` | Admin | List all users |
| PATCH | `/api/admin/users/{id}` | Admin | Update user role/dept |
| DELETE | `/api/admin/users/{id}` | Admin | Delete user |

---

## Future Scope

- OCR support via Tesseract/EasyOCR for scanned PDFs
- Department-level FAISS index isolation
- Streaming SSE with proper auth headers (move away from query-param token)
- Multi-modal document support (images, tables)