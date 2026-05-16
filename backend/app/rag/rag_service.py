"""RAG Service - PDF Processing, Embeddings, and ChromaDB Integration

This module provides a full RAGService when dependencies are available.
If environment variable `DEMO_MODE` is set, a lightweight demo RAGService
implementation is used to avoid heavy binary dependencies during local demos.
"""
print("DEBUG: RAGService: Starting imports...")
import os
import sys
import hashlib
from typing import Optional, List, Dict
import json

from app.config import settings
from app.utils.logger import log_info, log_error, log_debug, log_warning
print("DEBUG: RAGService: standard imports done")
from sqlalchemy.orm import Session
from app.database.models import Content, KnowledgeBase
print("DEBUG: RAGService: DB models imported")
from app.rag.llm_client import get_llm_client
print("DEBUG: RAGService: LLM client imported")

# Check DEMO_MODE first
DEMO_MODE = os.environ.get("DEMO_MODE", "false").lower() in ("1", "true", "yes")
print(f"DEBUG: RAGService: Initial DEMO_MODE={DEMO_MODE}")

FITZ_AVAILABLE = False
RAG_DEPS_AVAILABLE = False

if not DEMO_MODE:
    try:
        print("DEBUG: RAGService: importing fitz...")
        import fitz  # PyMuPDF
        FITZ_AVAILABLE = True
        print("DEBUG: RAGService: fitz imported")
    except ImportError as e:
        log_warning(f"RAGService: fitz (PyMuPDF) not found: {e}")
        FITZ_AVAILABLE = False

    try:
        print("DEBUG: RAGService: importing chromadb...")
        import chromadb
        print("DEBUG: RAGService: chromadb imported")
        print("DEBUG: RAGService: importing sentence_transformers...")
        from sentence_transformers import SentenceTransformer
        print("DEBUG: RAGService: sentence_transformers imported")
        RAG_DEPS_AVAILABLE = True
    except ImportError as e:
        log_warning(f"RAGService: heavy dependencies (chromadb/sentence_transformers) not found: {e}")
        RAG_DEPS_AVAILABLE = False

    # If deps missing, force demo mode
    if not (FITZ_AVAILABLE and RAG_DEPS_AVAILABLE):
        print("DEBUG: RAGService: Missing dependencies, forcing DEMO_MODE")
        DEMO_MODE = True

log_info(f"RAG Service Config: FITZ={FITZ_AVAILABLE}, RAG_DEPS={RAG_DEPS_AVAILABLE}, DEMO_MODE={DEMO_MODE}")

if not DEMO_MODE:
    class RAGService:
        """Service for RAG pipeline - PDF processing, embeddings, and retrieval"""
        
        def __init__(self):
            """Initialize RAG service with lazy loading"""
            self._chroma_client = None
            self._embedding_model = None

        @property
        def chroma_client(self):
            if self._chroma_client is None:
                log_info("Initializing ChromaDB client...")
                try:
                    self._chroma_client = chromadb.PersistentClient(
                        path=settings.CHROMA_DB_PATH
                    )
                except Exception as e:
                    log_error(f"Failed to initialize ChromaDB: {e}")
                    raise
            return self._chroma_client

        @property
        def embedding_model(self):
            if self._embedding_model is None:
                log_info("Loading sentence-transformers model...")
                try:
                    self._embedding_model = SentenceTransformer(
                        "sentence-transformers/all-MiniLM-L6-v2"
                    )
                    log_info("✓ Sentence-transformers model loaded")
                except Exception as e:
                    log_error(f"Failed to load embedding model: {e}")
                    raise
            return self._embedding_model
        
        def extract_text_from_pdf(self, filepath: str) -> str:
            try:
                log_debug(f"Extracting text from PDF: {filepath}")
                
                document = fitz.open(filepath)
                text = ""
                
                for page_num in range(len(document)):
                    page = document[page_num]
                    page_text = page.get_text()
                    if page_text:
                         text += page_text
                
                document.close()
                
                log_info(f"✓ Extracted {len(text)} characters from {filepath}")
                return text
            
            except Exception as e:
                log_error(f"Error extracting PDF text: {str(e)}", exc_info=True)
                raise
        
        def extract_images_from_pdf(self, filepath: str, output_dir: str = "static/uploads/diagrams") -> List[str]:
            """Extracts images from PDF and returns their local paths."""
            try:
                log_debug(f"Extracting images from PDF: {filepath}")
                os.makedirs(output_dir, exist_ok=True)
                document = fitz.open(filepath)
                saved_paths = []
                import uuid
                
                for page_num in range(len(document)):
                    page = document[page_num]
                    image_list = page.get_images(full=True)
                    
                    for img_index, img in enumerate(image_list):
                        xref = img[0]
                        base_image = document.extract_image(xref)
                        image_bytes = base_image["image"]
                        image_ext = base_image["ext"]
                        
                        img_filename = f"diagram_{uuid.uuid4().hex[:8]}.{image_ext}"
                        img_path = os.path.join(output_dir, img_filename)
                        
                        with open(img_path, "wb") as f:
                            f.write(image_bytes)
                        saved_paths.append(img_path)
                        
                document.close()
                log_info(f"✓ Extracted {len(saved_paths)} images from {filepath}")
                return saved_paths
            except Exception as e:
                log_error(f"Error extracting PDF images: {str(e)}", exc_info=True)
                return []

        
        def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
            try:
                chunks = []
                step = chunk_size - overlap
                
                for i in range(0, len(text), step):
                    chunk = text[i:i + chunk_size]
                    if chunk.strip():
                        chunks.append(chunk)
                
                log_info(f"✓ Created {len(chunks)} chunks (size={chunk_size}, overlap={overlap})")
                return chunks
            
            except Exception as e:
                log_error(f"Error chunking text: {str(e)}", exc_info=True)
                raise
        
        def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
            try:
                log_debug(f"Embedding {len(chunks)} chunks...")
                
                # Model is accessed via property, triggering lazy load if needed
                embeddings = self.embedding_model.encode(chunks)
                
                log_info(f"✓ Generated embeddings for {len(chunks)} chunks")
                return embeddings.tolist()
            
            except Exception as e:
                log_error(f"Error generating embeddings: {str(e)}", exc_info=True)
                raise
        
        def store_in_chromadb(
            self,
            collection_name: str,
            chunks: List[str],
            embeddings: List[List[float]],
            metadata: Optional[Dict] = None
        ) -> str:
            try:
                log_debug(f"Storing {len(chunks)} chunks in ChromaDB collection: {collection_name}")
                
                # Get or create collection
                collection = self.chroma_client.get_or_create_collection(
                    name=collection_name,
                    metadata={"hnsw:space": "cosine"}
                )
                
                # Prepare data for ChromaDB
                ids = [f"{collection_name}_chunk_{i}" for i in range(len(chunks))]
                
                # Prepare metadata (ChromaDB requires dict of lists)
                if metadata is None:
                    metadata = {}
                
                metadatas = [
                    {
                        **metadata,
                        "chunk_index": str(i),
                        "chunk_size": str(len(chunk))
                    }
                    for i, chunk in enumerate(chunks)
                ]
                
                # Add documents to collection
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    documents=chunks,
                    metadatas=metadatas
                )
                
                log_info(f"✓ Stored {len(chunks)} chunks in ChromaDB")
                return collection.name
            
            except Exception as e:
                log_error(f"Error storing in ChromaDB: {str(e)}", exc_info=True)
                raise
        
        def retrieve_context(
            self,
            collection_name: str,
            query: str,
            num_results: int = 5
        ) -> List[Dict]:
            try:
                collection = self.chroma_client.get_collection(name=collection_name)
                results = collection.query(
                    query_texts=[query],
                    n_results=num_results,
                    include=["documents", "distances", "metadatas"]
                )
                formatted_results = []
                if results and results["documents"] and len(results["documents"]) > 0:
                    for i, doc in enumerate(results["documents"][0]):
                        formatted_results.append({
                            "text": doc,
                            "distance": results["distances"][0][i] if results["distances"] else 0,
                            "metadata": results["metadatas"][0][i] if results["metadatas"] else {}
                        })
                log_debug(f"Retrieved {len(formatted_results)} chunks for query")
                return formatted_results
            except Exception as e:
                log_error(f"Error retrieving context: {str(e)}", exc_info=True)
                return []
        
        def process_pdf(
            self,
            content_id: int,
            filepath: str,
            collection_name: str,
            db: Session,
            chunk_size: int = 512,
            chunk_overlap: int = 50
        ) -> bool:
            try:
                log_info(f"Starting RAG pipeline for content_id={content_id}")
                text = self.extract_text_from_pdf(filepath)
                chunks = self.chunk_text(text, chunk_size, chunk_overlap)
                embeddings = self.embed_chunks(chunks)
                metadata = {"content_id": str(content_id), "source_file": os.path.basename(filepath)}
                chroma_collection_id = self.store_in_chromadb(collection_name, chunks, embeddings, metadata)
                knowledge_base = db.query(KnowledgeBase).filter(KnowledgeBase.content_id == content_id).first()
                if knowledge_base:
                    knowledge_base.chroma_collection_id = chroma_collection_id
                    knowledge_base.total_chunks = len(chunks)
                else:
                    knowledge_base = KnowledgeBase(
                        content_id=content_id,
                        collection_name=collection_name,
                        chroma_collection_id=chroma_collection_id,
                        embedding_model="sentence-transformers/all-MiniLM-L6-v2",
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        total_chunks=len(chunks)
                    )
                    db.add(knowledge_base)
                db.commit()
                log_info(f"[OK] RAG pipeline completed for content_id={content_id}")
                log_info(f"  - Chunks: {len(chunks)}")
                log_info(f"  - Collection: {chroma_collection_id}")
                return True
            except Exception as e:
                log_error(f"RAG pipeline failed: {str(e)}", exc_info=True)
                db.rollback()
                return False

else:
    # Lightweight DEMO_MODE RAGService to avoid heavy binary deps during demos
    class RAGService:
        def __init__(self):
            log_info("RAGService running in DEMO_MODE (lightweight)")

        def extract_text_from_pdf(self, filepath: str) -> str:
            # Use fitz if available, even in demo mode if possible
            if 'fitz' in globals() or 'fitz' in sys.modules:
                 try:
                    import fitz
                    doc = fitz.open(filepath)
                    text = ""
                    for page in doc:
                        text += page.get_text()
                    doc.close()
                    log_debug(f"Extracted {len(text)} chars using fitz (DEMO_MODE)")
                    return text
                 except Exception as e:
                    log_error(f"Fitz extraction failed in demo mode: {e}")

            try:
                with open(filepath, 'r', encoding='utf-8') as fh:
                    return fh.read()
            except Exception:
                return ""

        def extract_images_from_pdf(self, filepath: str, output_dir: str = "static/uploads/diagrams") -> List[str]:
            if 'fitz' in globals() or 'fitz' in sys.modules:
                try:
                    import fitz
                    import uuid
                    os.makedirs(output_dir, exist_ok=True)
                    document = fitz.open(filepath)
                    saved_paths = []
                    for page_num in range(len(document)):
                        for img in document[page_num].get_images(full=True):
                            xref = img[0]
                            base_image = document.extract_image(xref)
                            image_bytes = base_image["image"]
                            image_ext = base_image["ext"]
                            img_path = os.path.join(output_dir, f"diagram_{uuid.uuid4().hex[:8]}.{image_ext}")
                            with open(img_path, "wb") as f:
                                f.write(image_bytes)
                            saved_paths.append(img_path)
                    document.close()
                    return saved_paths
                except Exception as e:
                    log_error(f"Fitz image extraction failed in demo mode: {e}")
            return []

        def chunk_text(self, text: str, chunk_size: int = 512, overlap: int = 50) -> List[str]:
            if not text:
                return []
            parts = [p.strip() for p in text.replace('\n', ' ').split('. ') if p.strip()]
            chunks = []
            for p in parts:
                if len(p) <= chunk_size:
                    chunks.append(p)
                else:
                    for i in range(0, len(p), chunk_size - overlap):
                        chunks.append(p[i:i+chunk_size])
            return chunks

        def embed_chunks(self, chunks: List[str]) -> List[List[float]]:
            return [[float(len(c) % 7 + 1) for _ in range(8)] for c in chunks]

        def store_in_chromadb(self, collection_name: str, chunks: List[str], embeddings: List[List[float]], metadata: Optional[Dict] = None) -> str:
            log_debug(f"DEMO store_in_chromadb: {collection_name} ({len(chunks)} chunks)")
            return collection_name

        def retrieve_context(self, collection_name: str, query: str, num_results: int = 5) -> List[Dict]:
            if not query:
                return []
            tokens = query.split()
            simulated = []
            for i, t in enumerate(tokens[:num_results]):
                simulated.append({
                    'text': f"Demo context about {t}: short explanation.",
                    'distance': 0.1 + i * 0.05,
                    'metadata': {}
                })
            return simulated

        def process_pdf(self, content_id: int, filepath: str, collection_name: str, db: Session, chunk_size: int = 512, chunk_overlap: int = 50) -> bool:
            try:
                text = self.extract_text_from_pdf(filepath)
                chunks = self.chunk_text(text, chunk_size, chunk_overlap)
                embeddings = self.embed_chunks(chunks)
                kb = db.query(KnowledgeBase).filter(KnowledgeBase.content_id == content_id).first()
                if kb:
                    kb.collection_name = collection_name
                    kb.chroma_collection_id = collection_name
                    kb.total_chunks = len(chunks)
                else:
                    kb = KnowledgeBase(content_id=content_id, collection_name=collection_name, chroma_collection_id=collection_name, total_chunks=len(chunks))
                    db.add(kb)
                db.commit()
                log_info(f"DEMO RAG pipeline completed for content_id={content_id}")
                return True
            except Exception as e:
                log_error(f"DEMO RAG pipeline failed: {e}")
                db.rollback()
                return False

# Global RAG service instance
_rag_service: Optional[RAGService] = None

def get_rag_service() -> RAGService:
    """Get or create RAG service instance (singleton)"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
