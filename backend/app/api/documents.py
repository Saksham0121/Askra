"""
Documents API — upload, list, delete.
"""
from __future__ import annotations
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from bson import ObjectId
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from app.auth.dependencies import get_current_user, require_admin
from app.auth.models import UserInDB, Role
from app.config import get_settings
from app.database import documents_collection
from app.pipeline_bridge import get_pipeline_bridge

from app.auth.rbac import PolicyEngine, Action, require_permission, AccessScope

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form("general"),
    description: str = Form(""),
    current_user: UserInDB = Depends(require_permission(Action.DOCUMENT_UPLOAD)),
):
    if not _allowed(file.filename or ""):
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    settings = get_settings()
    upload_dir = Path(settings.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / file.filename

    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Insert DB record
    doc = {
        "filename": file.filename,
        "filepath": str(dest),
        "department": department.lower(),
        "description": description,
        "uploaded_by": str(current_user.id),
        "uploaded_by_name": current_user.full_name,
        "status": "processing",
        "created_at": datetime.now(timezone.utc),
        "size_bytes": dest.stat().st_size,
    }
    result = await documents_collection().insert_one(doc)
    doc_id = str(result.inserted_id)

    # Trigger pipeline ingestion
    try:
        bridge = get_pipeline_bridge()
        from pipeline.ingestion.pdf_loader import PDFDocumentLoader
        from pipeline.preprocessing.chunking_service import ChunkingService
        from pipeline.preprocessing.text_cleaner import TextCleaner
        from pipeline.models import Document, DocumentContent, PageContent, DocumentMetadata
        from pipeline.models.enums import DocumentStatus

        cleaner = TextCleaner()
        chunker = ChunkingService()

        ext = dest.suffix.lower()
        if ext == '.pdf':
            loader = PDFDocumentLoader()
            doc_content = loader.load(str(dest))
        else:
            with open(dest, 'r', encoding='utf-8', errors='ignore') as f:
                raw_text = f.read()
            doc_content = DocumentContent(
                metadata=DocumentMetadata(
                    title=file.filename,
                    author=None,
                    subject=None,
                    keywords=[],
                    publication_date=None,
                    effective_date=None,
                    version=None,
                    language="en"
                ),
                pages=[PageContent(page_number=1, text=raw_text)]
            )

        # Clean document content using pipeline TextCleaner
        cleaned_doc_content = cleaner.clean(doc_content)

        doc_obj = Document(
            document_id=doc_id,
            filename=file.filename,
            file_hash="",
            upload_timestamp=datetime.now(timezone.utc),
            indexed_timestamp=datetime.now(timezone.utc),
            publication_date=None,
            effective_date=None,
            document_version=None,
            total_pages=len(cleaned_doc_content.pages),
            total_chunks=0,
            language="en",
            embedding_model="all-MiniLM-L6-v2",
            embedding_version="1.0",
            index_version="1.0",
            status=DocumentStatus.INDEXED
        )

        chunks = chunker.chunk_document(doc_obj, cleaned_doc_content)

        # Embed and add to FAISS + BM25
        texts = [c.text for c in chunks]
        if texts:
            embeddings = bridge.embedding_manager.embed_batch(texts)
            bridge.faiss_manager.add_chunks(chunks, embeddings)
            bridge.bm25_manager.add_documents(chunks, embeddings)

        await documents_collection().update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"status": "ready", "chunk_count": len(chunks)}},
        )
    except Exception as exc:
        await documents_collection().update_one(
            {"_id": ObjectId(doc_id)},
            {"$set": {"status": "error", "error": str(exc)}},
        )
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}")

    return {"id": doc_id, "filename": file.filename, "status": "ready", "chunks": len(chunks)}


@router.get("")
async def list_documents(current_user: UserInDB = Depends(require_permission(Action.DOCUMENT_READ))):
    """List documents with declarative RBAC scope evaluation."""
    permitted_depts = PolicyEngine.get_permitted_departments(current_user)
    query: dict = {}
    if "all" not in permitted_depts:
        query["department"] = {"$in": permitted_depts}

    cursor = documents_collection().find(query, {"hashed_password": 0}).sort("created_at", -1)
    docs = await cursor.to_list(length=200)
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"documents": docs}


@router.delete("/{doc_id}")
async def delete_document(doc_id: str, current_user: UserInDB = Depends(get_current_user)):
    try:
        doc = await documents_collection().find_one({"_id": ObjectId(doc_id)})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid document ID format")

    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Evaluate RBAC policy for deletion
    decision = PolicyEngine.evaluate(current_user, Action.DOCUMENT_DELETE, resource=doc)
    if not decision.allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Access Denied: {decision.reason}")

    filepath = doc.get("filepath", "")
    if filepath and os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass

    await documents_collection().delete_one({"_id": ObjectId(doc_id)})

    # Purge vector index entries
    try:
        bridge = get_pipeline_bridge()
        bridge.faiss_manager.delete_by_document_id(doc_id)
        bridge.bm25_manager.delete_by_document_id(doc_id)
    except Exception:
        pass

    return {"message": "Document deleted successfully", "id": doc_id}
