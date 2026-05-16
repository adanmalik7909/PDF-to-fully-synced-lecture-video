"""Enhanced SQLAlchemy ORM Models for SmartStudyInstructor"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.db import Base

class User(Base):
    """User model - Admin, Teacher, Student with role-based access control"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default="student")  # admin, teacher, student
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    contents = relationship("Content", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    submissions = relationship("Submission", back_populates="student")
    notes = relationship("Note", back_populates="student")
    logs = relationship("Log", back_populates="user")


class Content(Base):
    """Content model - Uploaded files (PDFs, documents)"""
    __tablename__ = "contents"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(500), nullable=False)
    file_size = Column(Integer)
    file_type = Column(String(50))  # pdf, docx, txt
    content_hash = Column(String(255), unique=True)
    upload_date = Column(DateTime, default=datetime.utcnow, index=True)
    is_deleted = Column(Boolean, default=False)
    
    # Relationships
    user = relationship("User", back_populates="contents")
    knowledge_base = relationship("KnowledgeBase", back_populates="content", uselist=False)
    sessions = relationship("Session", back_populates="content")
    assessments = relationship("Assessment", back_populates="content")
    notes = relationship("Note", back_populates="content")
    summaries = relationship("Summary", back_populates="content")


class KnowledgeBase(Base):
    """Knowledge base model - ChromaDB vector collection mapping"""
    __tablename__ = "knowledge_bases"
    
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), unique=True, nullable=False, index=True)
    collection_name = Column(String(255), unique=True, nullable=False)
    chroma_collection_id = Column(String(255), unique=True)
    embedding_model = Column(String(255), default="sentence-transformers/all-MiniLM-L6-v2")
    chunk_size = Column(Integer, default=512)
    chunk_overlap = Column(Integer, default=50)
    total_chunks = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="knowledge_base")


class Session(Base):
    """Session model - Unified classroom & personal tuition session tracking"""
    __tablename__ = "sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    session_type = Column(String(50), nullable=False, index=True)  # classroom, tuition
    session_name = Column(String(255), nullable=False)
    lecture_script = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    ended_at = Column(DateTime)
    duration_minutes = Column(Integer)
    status = Column(String(50), default="active", index=True)  # active, paused, ended
    session_metadata = Column('metadata', Text)  # JSON for flexible data (attribute renamed to avoid SQLAlchemy reserved name)
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    content = relationship("Content", back_populates="sessions")
    vision_events = relationship("VisionEvent", back_populates="session")


class VisionEvent(Base):
    """Vision event model - Phone detection with evidence snapshots"""
    __tablename__ = "vision_events"
    
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False)  # phone_detected, suspicious_activity
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    confidence = Column(Float, nullable=False)  # 0.0 to 1.0
    snapshot_path = Column(String(500))  # Path to evidence image
    snapshot_size = Column(Integer)  # File size in bytes
    frame_number = Column(Integer)  # Video frame index
    detection_details = Column(Text)  # JSON with detection metadata
    is_resolved = Column(Boolean, default=False, index=True)
    resolution_notes = Column(Text)
    
    # Relationships
    session = relationship("Session", back_populates="vision_events")


class Assessment(Base):
    """Assessment model - Quiz metadata and configuration"""
    __tablename__ = "assessments"
    
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    assessment_name = Column(String(255), nullable=False)
    description = Column(Text)
    num_questions = Column(Integer)
    difficulty_level = Column(String(50))  # easy, medium, hard
    time_limit_minutes = Column(Integer)
    passing_score = Column(Integer, default=70)
    is_published = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="assessments")
    questions = relationship("Question", back_populates="assessment")
    submissions = relationship("Submission", back_populates="assessment")


class Question(Base):
    """Question model - Individual quiz questions"""
    __tablename__ = "questions"
    
    id = Column(Integer, primary_key=True, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # multiple_choice, true_false, short_answer
    options = Column(Text)  # JSON: ["Option A", "Option B", "Option C", "Option D"]
    correct_answer = Column(String(255), nullable=False)
    explanation = Column(Text)  # Explanation for correct answer
    difficulty = Column(String(50))  # easy, medium, hard
    order_index = Column(Integer)  # Question order in assessment
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    assessment = relationship("Assessment", back_populates="questions")
    answers = relationship("Answer", back_populates="question")


class QuizQuestion(Base):
    """Quiz question model - Legacy support"""
    __tablename__ = "quiz_questions"
    
    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    question = Column(Text, nullable=False)
    options = Column(Text)
    correct_answer = Column(String(255))
    question_type = Column(String(50), default="multiple_choice")
    created_at = Column(DateTime, default=datetime.utcnow)


class Submission(Base):
    """Submission model - Student quiz submissions"""
    __tablename__ = "submissions"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    assessment_id = Column(Integer, ForeignKey("assessments.id"), nullable=False, index=True)
    submitted_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime)
    total_score = Column(Integer)
    max_score = Column(Integer)
    percentage_score = Column(Float)  # 0-100
    status = Column(String(50), default="in_progress")  # in_progress, submitted, graded
    time_taken_minutes = Column(Integer)
    
    # Relationships
    student = relationship("User", back_populates="submissions")
    assessment = relationship("Assessment", back_populates="submissions")
    answers = relationship("Answer", back_populates="submission")


class Answer(Base):
    """Answer model - Individual student answers"""
    __tablename__ = "answers"
    
    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True)
    selected_answer = Column(String(255))
    is_correct = Column(Boolean)
    points_earned = Column(Integer)
    answered_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    submission = relationship("Submission", back_populates="answers")
    question = relationship("Question", back_populates="answers")


class StudentResponse(Base):
    """Student response model - Legacy support"""
    __tablename__ = "student_responses"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("quiz_questions.id"), nullable=False)
    selected_answer = Column(String(255))
    is_correct = Column(Boolean)
    answered_at = Column(DateTime, default=datetime.utcnow)


class Note(Base):
    """Note model - Student personal notes and highlights"""
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    note_title = Column(String(255))
    note_content = Column(Text, nullable=False)
    note_type = Column(String(50))  # note, highlight, summary
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_archived = Column(Boolean, default=False)
    
    # Relationships
    student = relationship("User", back_populates="notes")
    content = relationship("Content", back_populates="notes")


class Summary(Base):
    """Summary model - AI-generated content summaries"""
    __tablename__ = "summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    content_id = Column(Integer, ForeignKey("contents.id"), nullable=False, index=True)
    summary_type = Column(String(50))  # ai_generated, extracted
    summary_text = Column(Text, nullable=False)
    key_points = Column(Text)  # JSON array of key points
    estimated_reading_time_minutes = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    content = relationship("Content", back_populates="summaries")


class Log(Base):
    """Log model - System activity logs for auditing"""
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), index=True)
    action = Column(String(255), nullable=False)
    resource_type = Column(String(100))
    resource_id = Column(Integer)
    ip_address = Column(String(50))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    details = Column(Text)  # JSON with additional context
    
    # Relationships
    user = relationship("User", back_populates="logs")


class StudentNote(Base):
    """Student note model - Legacy support"""
    __tablename__ = "student_notes"
    
    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    document_id = Column(Integer, ForeignKey("contents.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
