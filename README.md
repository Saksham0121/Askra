# Askra — Enterprise 7-Layer Agentic RAG System

> **Askra** is an enterprise-grade, privacy-first Agentic RAG (Retrieval-Augmented Generation) & Multimodal Parsing Platform. Powered by a 7-Layer Agentic Pipeline, dual dense-sparse hybrid retrieval, cross-encoder reranking, real-time reflection loops, and state-of-the-art local document OCR (**Unlimited-OCR**).

---

## 📐 7-Layer Agentic Pipeline Architecture

Askra processes every query through a modular 7-layer agentic architecture designed for maximum accuracy, hallucination prevention, safety, and performance.

```
                    ┌────────────────────────────────────────┐
                    │               User Query               │
                    └───────────────────┬────────────────────┘
                                        │
                                        ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ L0 · Safety Guardrail & Sanitization                                         │
│ └─ Blocks jailbreaks, prompt injections, and unsafe keywords                 │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ L1 · Intent Classifier                                                       │
│ └─ Fast rule-based matching (GREETING, CODE, DOCUMENT, OCR_SCAN, UNSAFE)     │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ L2 · Decision Router                                                         │
│ └─ Dispatches query to the optimal execution tool                            │
└───────┬───────────────────┬───────────────────┬───────────────────┬──────────┘
        │ (Document Query)  │ (Scan Request)    │ (Code Query)      │ (General Chat)
        ▼                   ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ L3 · RAG Tool │   │ L3 · OCR Tool │   │L3 · Code Tool │   │L3 · Chat Tool │
│ ├─ Query      │   │ └─ Unlimited- │   │ └─ Groq Code  │   │ └─ Groq Chat  │
│    Rewriter   │   │    OCR Client │   │    Model      │   │    Model      │
│ ├─ Hybrid     │   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
│    Search     │           │                   │                   │
│ ├─ Reranker   │           │                   │                   │
│ └─ Synthesis  │           │                   │                   │
└───────┬───────┘           │                   │                   │
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ L4 · NLI Validation Layer (LLM-as-Judge)                                     │
│ └─ Evaluates correctness, completeness, and citation grounding (Score: 0-10) │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ├──────────────────────┐ (Score < Threshold)
                                    ▼ (Score ≥ Threshold)  ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ L5 · Reflection & Self-Correction Loop                                       │
│ └─ Re-queries and refines answer up to 2 iterations                           │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ L6 · Response Assembly & Streaming                                           │
│ └─ Attaches confidence badge, citations, latency stats & streams via SSE     │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Pipeline Layers & Detailed Workflow

### **Layer 0: Safety Guardrail & Sanitization**
- **Purpose**: Prevents prompt injection attacks, system prompt leakage, and unsafe content execution.
- **Mechanism**: Evaluates input queries against hard-block rules, heuristic scoring thresholds, and safety regex patterns. Normalizes query text before forwarding down the pipeline.

### **Layer 1: Intent Classifier**
- **Purpose**: Low-latency classification of incoming queries.
- **Intents**:
  - `GREETING` → General welcome messages.
  - `DOCUMENT` → Private document and policy questions.
  - `CODE` → Programming, scripting, and technical queries.
  - `OCR_SCAN` → Image-to-text, PDF scan, and OCR parsing requests.
  - `UNSAFE` / `JAILBREAK` → Instantly blocked by L0.
  - `UNKNOWN` → Escalated to LLM fallback routing.

### **Layer 2: Decision Router**
- **Purpose**: Fast-path query dispatching to specialized tools, bypassing unnecessary vector searches for general chat or coding tasks.
- **Routing Table**:
  - `DOCUMENT` / `UNKNOWN` ➔ **RAG Tool**
  - `OCR_SCAN` ➔ **OCR Tool**
  - `CODE` ➔ **Code Tool**
  - `GREETING` / `GENERAL_CHAT` ➔ **Chat Tool**

### **Layer 3: Multi-Tool Execution**

#### 📄 **1. RAG Tool (Hybrid Retrieval + Reranking)**
- **Query Rewriter**: Expands short or ambiguous user queries using Groq `llama-3.1-8b-instant` to optimize vector recall.
- **Dense Vector Search**: `all-MiniLM-L6-v2` embeddings (384 dimensions) indexed in FAISS vector store.
- **Sparse Keyword Search**: BM25 search over tokenized document chunks.
- **Hybrid Fusion**: Combines FAISS (70% weight) and BM25 (30% weight) scores to fetch top 10 candidates.
- **Cross-Encoder Reranking**: Uses `cross-encoder/ms-marco-MiniLM-L-6-v2` to score candidate passages and retain top 5 context passages.
- **Context Synthesis**: Assembles retrieved passages into a structured prompt for grounded LLM answer generation.

#### 🔍 **2. OCR Tool (Unlimited-OCR)**
- Communicates directly with the local **Unlimited-OCR** SGLang inference server.
- Supports single-image scanning (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`) and multi-page PDF rendering via PyMuPDF (`fitz`).
- Parses dense tables, complex document layouts, and handwritten text into clean markdown.
- **100% On-Premise Privacy**: Operates entirely on the local machine (`http://127.0.0.1:10000`). Zero data is transmitted externally.

#### 💻 **3. Code Tool**
- Specialized coding assistance powered by Groq LLM.

#### 💬 **4. Chat Tool**
- General knowledge & conversational tool with history context management.

### **Layer 4: NLI Validation Layer (LLM-as-Judge)**
- **Purpose**: Eliminates hallucinations by verifying generated answers against retrieved context.
- **Evaluation Criteria**:
  - Correctness (50% weight)
  - Completeness (30% weight)
  - Citation Grounding (20% weight)
- Produces a confidence score between `0.0` and `10.0`. Fast-paths (Chat, Code, OCR) receive pre-validated passing scores to reduce latency.

### **Layer 5: Reflection & Self-Correction Loop**
- If an answer score falls below the configured confidence threshold (e.g., `< 5.5`), the Reflector enters a self-correction loop (up to 2 iterations):
  - Analyzes validation reasoning and missing details.
  - Rewrites the retrieval prompt and context query.
  - Re-executes L3 and L4 until a passing score is achieved.

### **Layer 6: Response Assembly & Streaming**
- Formats final response with:
  - Markdown-rendered answer text
  - Source citations (document filenames & page numbers)
  - Confidence Badges: 🟢 **High** (≥7.5), 🟡 **Medium** (≥5.0), 🔴 **Low** (<5.0)
  - Execution metadata: total latency (ms), reflection iterations, answer source label.
- Supports both synchronous JSON (`POST /api/chat`) and real-time SSE streaming (`GET /api/chat/stream`).

---

## 📥 Document Ingestion & Auto-OCR Workflow

Askra features an intelligent ingestion pipeline for processing enterprise documents and images:

```
[ Upload Document ] ──► [ Extension Check ]
                             │
            ┌────────────────┴────────────────┐
            ▼                                 ▼
    [ Image File ]                     [ PDF / Text File ]
            │                                 │
            ▼                                 ▼
   [ OCR Loader ]                     [ PyMuPDF Text Extract ]
            │                                 │
            │                  ┌──────────────┴──────────────┐
            │                  ▼                             ▼
            │            [ Normal Text ]            [ Low Text / Scanned ]
            │                  │                     (Avg < 50 chars/page)
            │                  │                             │
            ▼                  ▼                             ▼
   └────────┴────────► [ Text Cleaning ] ◄───────────────────┘
                               │
                               ▼
                      [ Chunking Service ]
                               │
                               ▼
                  [ Embeddings (MiniLM-L6) ]
                               │
                ┌──────────────┴──────────────┐
                ▼                             ▼
          [ FAISS Store ]              [ BM25 Store ]
```

- **Auto-Detection for Scanned PDFs**: When a PDF is uploaded, PyMuPDF attempts text extraction. If text extraction yields an average of `< 50 characters per page`, Askra automatically routes the PDF to `OCRDocumentLoader` for full-page vision OCR.
- **User Override**: Users can explicitly enforce OCR during upload by setting `use_ocr=true`.

---

## 🛠️ Technology Stack

| Domain | Component / Library | Description |
|---|---|---|
| **LLM Inference** | Groq API (`llama-3.1-8b-instant`) | Low-latency synthesis, rewriting, & validation |
| **Vision OCR** | Unlimited-OCR (Baidu) + SGLang | Multimodal long-horizon document parsing |
| **Embedding Model** | `all-MiniLM-L6-v2` | 384-dimensional dense vector embeddings |
| **Vector Index** | FAISS (`faiss-cpu`) | Fast dense vector similarity search |
| **Sparse Index** | BM25 (`rank-bm25`) | Lexical keyword search |
| **Reranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Passages reranking model |
| **Backend Framework**| FastAPI + Uvicorn | Async REST API & SSE streaming server |
| **Database** | MongoDB + Motor | Async document, session, and message persistence |
| **Auth & Security** | PyJWT + Passlib (bcrypt) | Token authentication & password hashing |
| **RBAC** | Declarative Policy Engine | Granular Role & Department access control |
| **PDF Processing** | PyMuPDF (`fitz`) | High-speed PDF page rendering & text extraction |
| **Frontend UI** | React 18 + Vite | Modern dashboard with real-time SSE streaming |

---

## 🔒 Security & Role-Based Access Control (RBAC)

Askra implements strict Attribute & Role-Based Access Control (RBAC):

| Role | Scope | Allowed Actions |
|---|---|---|
| **Employee** | Department-Level | Chat, stream answers, and view documents in assigned department |
| **Manager** | Department / Cross-Dept | All Employee actions + Upload documents & access Analytics dashboard |
| **Admin** | System-Wide | All actions + User management, role assignment, and audit logs |

---

## 🚀 Quickstart & Setup Guide

### 1. Prerequisites
- Python 3.12+
- Node.js 18+
- MongoDB running locally or a MongoDB Atlas URI
- GPU / SGLang server (optional, for local Unlimited-OCR vision parsing)

### 2. Backend Setup
```bash
cd backend

# Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment Variables (.env is pre-configured with defaults)
# Start FastAPI backend
uvicorn app.main:app --reload --port 8000
```
- API Documentation: `http://localhost:8000/docs`

### 3. OCR Server Setup (Optional for Vision OCR)
To enable local vision OCR via Unlimited-OCR:
```bash
# Launch SGLang server on port 10000
python -m sglang.launch_server \
    --model baidu/Unlimited-OCR \
    --served-model-name Unlimited-OCR \
    --host 127.0.0.1 \
    --port 10000
```

### 4. Frontend Setup
```bash
cd frontend

# Install dependencies & run Vite dev server
npm install
npm run dev
```
- Application Web Interface: `http://localhost:5173`

### 🐳 5. Docker Deployment (One-Command Launch)
To launch the entire stack (MongoDB + Backend + Frontend/Nginx) with container optimization:
```bash
# Build and launch all services in production mode
docker compose up --build -d
```
- Frontend UI: `http://localhost`
- Backend API Docs: `http://localhost:8000/docs`

---

## 📡 API Reference Endpoint Overview

| Category | Method | Path | Auth | Description |
|---|---|---|---|---|
| **Auth** | `POST` | `/auth/register` | Public | Register new user |
| | `POST` | `/auth/login` | Public | Authenticate user & return JWT tokens |
| | `POST` | `/auth/refresh` | Public | Refresh JWT access token |
| | `GET` | `/auth/me` | User | Get current profile & department permissions |
| **Chat** | `POST` | `/api/chat` | User | Synchronous 7-layer pipeline chat |
| | `GET` | `/api/chat/stream` | User | Real-time SSE streaming chat with status updates |
| | `GET` | `/api/chat/sessions` | User | List user chat sessions |
| | `GET` | `/api/chat/sessions/{id}/messages` | User | Get conversation history for a session |
| **Documents**| `POST` | `/api/documents/upload` | Manager+ | Upload & ingest document (supports `use_ocr`) |
| | `GET` | `/api/documents` | User | List documents accessible to user |
| | `DELETE`| `/api/documents/{id}` | Admin/Owner | Delete document & purge vector index |
| **OCR** | `GET` | `/api/ocr/health` | User | Health check for Unlimited-OCR server |
| | `POST` | `/api/ocr/scan` | User | Direct REST endpoint to scan image or PDF |
| **Analytics**| `GET` | `/api/analytics/overview` | Manager+ | Overview metrics (queries, latency, tool stats) |
| | `GET` | `/api/analytics/query-trends` | Manager+ | Time-series query volume trends |
| **Admin** | `GET` | `/api/admin/users` | Admin | List all registered users |
| | `PATCH` | `/api/admin/users/{id}` | Admin | Update user role / department assignments |
| | `DELETE`| `/api/admin/users/{id}` | Admin | Delete user account |

---

## 📁 Repository Structure

```
Askra/
├── backend/                  # FastAPI Backend Application
│   ├── app/                  # REST Controllers, Auth, Security, Database
│   │   ├── api/              # API Route Handlers (chat, documents, ocr, analytics, admin)
│   │   ├── auth/             # JWT Authentication & RBAC Policy Engine
│   │   ├── config.py         # Application Configuration
│   │   ├── database.py       # MongoDB Connection Manager
│   │   ├── main.py           # FastAPI Lifespan & Entry Point
│   │   └── pipeline_bridge.py# Bridge wiring FastAPI to Pipeline Layer
│   └── pipeline/             # 7-Layer Agentic Pipeline Core
│       ├── agent/            # Base Tool & Agent Router
│       ├── context/          # Prompt Context Builder
│       ├── embeddings/       # SentenceTransformers Embedding Manager
│       ├── ingestion/        # PDF Loader, OCR Document Loader, Metadata Extractor
│       ├── llm/              # Groq LLM API Wrapper
│       ├── models/           # Data Models & Schemas
│       ├── pipeline/         # Agentic & Online RAG Orchestrators
│       ├── preprocessing/    # Text Cleaner & Chunking Services
│       ├── reflection/       # Reflector Self-Correction Engine
│       ├── reranking/        # Cross-Encoder Reranker
│       ├── retrieval/        # FAISS Dense + BM25 Sparse Hybrid Retrievers
│       ├── services/         # OCR Service (SGLang Client)
│       ├── tools/            # Chat, Code, RAG, and OCR Tools
│       └── validation/       # Safety Guardrail, Intent Classifier & NLI Validator
├── frontend/                 # React 18 + Vite Dashboard UI
├── OCR_tool/                 # Unlimited-OCR model scripts & reference documentation
├── .gitignore
└── README.md
```