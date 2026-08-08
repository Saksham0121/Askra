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

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".txt", ".md"}


def _allowed(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_EXTENSIONS


@router.post("/upload", status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    department: str = Form("general"),
    description: str = Form(""),
    current_user: UserInDB = Depends(get_current_user),
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
        "department": department,
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
        from pipeline.ingestion.pdf_loader import PDFLoader
        from pipeline.preprocessing.chunking_service import ChunkingService
        from pipeline.preprocessing.text_cleaner import TextCleaner

        loader = PDFLoader()
        cleaner = TextCleaner()
        chunker = ChunkingService()

        pages = loader.load(str(dest))
        cleaned = [cleaner.clean(p) for p in pages]
        chunks = chunker.chunk(cleaned, source=file.filename, department=department)

        # Embed and add to FAISS + BM25
        texts = [c.text for c in chunks]
        embeddings = bridge.embedding_manager.embed_batch(texts)
        bridge.faiss_manager.add_chunks(chunks, embeddings)
        bridge.bm25_manager.add_documents(chunks)

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
async def list_documents(current_user: UserInDB = Depends(get_current_user)):
    """List documents. Admins see all; others see their department + general."""
    query: dict = {}
    if current_user.role != Role.ADMIN:
        query["department"] = {"$in": [current_user.department, "general"]}

    cursor = documents_collection().find(query, {"hashed_password": 0}).sort("created_at", -1)
    docs = await cursor.to_list(length=200)
    for d in docs:
        d["_id"] = str(d["_id"])
    return {"documents": docs}


@router.delete("/{doc_id}", dependencies=[Depends(require_admin)])
async def delete_document(doc_id: str):
    doc = await documents_collection().find_one({"_id": ObjectId(doc_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    filepath = doc.get("filepath", "")
    if filepath and os.path.exists(filepath):
        os.remove(filepath)

    await documents_collection().delete_one({"_id": ObjectId(doc_id)})
    return {"message": "Document deleted"}
