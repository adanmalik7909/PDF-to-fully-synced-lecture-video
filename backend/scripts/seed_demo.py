"""Seed demo data for SmartStudyInstructor

Creates demo users, a demo content record, and populates a ChromaDB collection
with sample chunks so the RAG endpoints return results during demos.
"""
import os
from pathlib import Path
import json

from app.database.db import init_db, SessionLocal
from app.database.models import User, Content, KnowledgeBase
from app.auth.password_utils import hash_password
from app.rag.rag_service import get_rag_service
from app.config import settings


def ensure_env():
    # ensure required directories exist
    Path(settings.UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(settings.PDF_UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)
    Path(settings.CHROMA_DB_PATH).mkdir(parents=True, exist_ok=True)


def create_demo_user(db):
    user = db.query(User).filter(User.username == 'demo_student').first()
    if user:
        print('[seed] demo_student already exists (id=%s)' % user.id)
        return user
    pwd = hash_password('password123')
    user = User(username='demo_student', email='demo@student.local', password_hash=pwd, role='student')
    db.add(user)
    db.commit()
    db.refresh(user)
    print('[seed] created demo_student id=%s' % user.id)
    return user


def create_demo_content(db):
    content = db.query(Content).filter(Content.filename == 'demo_content.txt').first()
    demo_path = os.path.join(settings.PDF_UPLOAD_FOLDER, 'demo_content.txt')
    if content:
        print('[seed] demo content already exists (id=%s)' % content.id)
        return content, demo_path

    sample_text = (
        "This is demo content for SmartStudyInstructor.\n"
        "Chapter 1: Introduction to algebra. Quadratic equations and formula.\n"
        "Chapter 2: Solving linear equations. Examples and practice problems.\n"
        "Chapter 3: Functions and graphs. Key concepts and summaries."
    )

    # ensure file exists
    with open(demo_path, 'w', encoding='utf-8') as fh:
        fh.write(sample_text)

    content = Content(
        user_id=1 if db.query(User).count() > 0 else None,
        filename='demo_content.txt',
        filepath=demo_path,
        file_size=os.path.getsize(demo_path),
        file_type='txt'
    )
    db.add(content)
    db.commit()
    db.refresh(content)
    print('[seed] created content id=%s' % content.id)
    return content, demo_path


def populate_chroma(db, content, demo_path):
    rag = get_rag_service()
    with open(demo_path, 'r', encoding='utf-8') as fh:
        text = fh.read()

    chunks = rag.chunk_text(text, chunk_size=512, overlap=50)
    embeddings = rag.embed_chunks(chunks)
    collection_name = f"demo_content_{content.id}"
    chroma_name = rag.store_in_chromadb(collection_name, chunks, embeddings, metadata={'content_id': str(content.id)})

    # Create or update KnowledgeBase record
    kb = db.query(KnowledgeBase).filter(KnowledgeBase.content_id == content.id).first()
    if kb:
        kb.collection_name = collection_name
        kb.chroma_collection_id = chroma_name
        kb.total_chunks = len(chunks)
    else:
        kb = KnowledgeBase(
            content_id=content.id,
            collection_name=collection_name,
            chroma_collection_id=chroma_name,
            total_chunks=len(chunks)
        )
        db.add(kb)
    db.commit()
    print(f"[seed] populated chroma collection: {collection_name} ({len(chunks)} chunks)")


def main():
    print('[seed] initializing DB...')
    init_db()
    ensure_env()
    db = SessionLocal()
    try:
        user = create_demo_user(db)
        content, demo_path = create_demo_content(db)
        populate_chroma(db, content, demo_path)
        print('[seed] Done. You can now run the backend and try /tuition endpoints')
    finally:
        db.close()


if __name__ == '__main__':
    main()
