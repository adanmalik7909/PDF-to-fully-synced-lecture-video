"""RAG Query Routes - Retrieval for Q&A"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from typing import List, Optional
from app.database.db import get_db
from app.database.models import Content, KnowledgeBase
from app.auth.dependencies import get_current_user
from app.utils.logger import log_info, log_error, log_debug
from app.rag.rag_service import get_rag_service

router = APIRouter(prefix="/api/rag", tags=["rag"])

# ============ Request/Response Models ============

class RAGQueryRequest(BaseModel):
    """Query request for RAG retrieval"""
    content_id: int
    query: str
    num_results: int = 5

class RetrievedChunk(BaseModel):
    """Retrieved text chunk with metadata"""
    text: str
    distance: float  # Similarity score (lower is more similar)
    metadata: dict

class RAGQueryResponse(BaseModel):
    """Response with retrieved context"""
    query: str
    content_id: int
    chunks: List[RetrievedChunk]
    total_chunks_available: int

# ============ Query Content ============

@router.post("/query", response_model=RAGQueryResponse)
async def query_content(
    req: RAGQueryRequest,
    current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Query a content's knowledge base using semantic search
    
    Returns:
    - Query text
    - Retrieved relevant chunks
    - Similarity scores
    - Total available chunks
    """
    try:
        # Verify content ownership
        content = db.query(Content).filter(
            and_(Content.id == req.content_id, Content.user_id == current_user.id)
        ).first()
        
        if not content:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Content not found"
            )
        
        # Get knowledge base
        kb = db.query(KnowledgeBase).filter(
            KnowledgeBase.content_id == req.content_id
        ).first()
        
        if not kb or not kb.chroma_collection_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Knowledge base not ready yet. Please wait for ingestion to complete."
            )
        
        log_info(f"Querying content_id={req.content_id}: '{req.query}'")
        
        # Retrieve from ChromaDB
        rag_service = get_rag_service()
        retrieved_chunks = rag_service.retrieve_context(
            collection_name=kb.collection_name,
            query=req.query,
            num_results=req.num_results
        )
        
        # Format response
        chunks = [
            RetrievedChunk(
                text=chunk["text"],
                distance=chunk["distance"],
                metadata=chunk["metadata"]
            )
            for chunk in retrieved_chunks
        ]
        
        log_debug(f"Retrieved {len(chunks)} chunks for query")
        
        return RAGQueryResponse(
            query=req.query,
            content_id=req.content_id,
            chunks=chunks,
            total_chunks_available=kb.total_chunks
        )
    
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"Query error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query failed"
        )

# ============ Health Check for RAG ============

@router.get("/health")
async def rag_health():
    """Check RAG service health and available collections"""
    try:
        rag_service = get_rag_service()
        collections = rag_service.list_collections()
        
        return {
            "status": "healthy",
            "embeddings_model": "sentence-transformers/all-MiniLM-L6-v2",
            "vector_store": "chromadb",
            "collections_count": len(collections),
            "collections": collections[:10]  # Show first 10
        }
    except Exception as e:
        log_error(f"RAG health check error: {str(e)}")
        return {
            "status": "error",
            "error": str(e)
        }
