"""Pydantic schemas for request/response validation"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

# ============ User Schemas ============
class UserBase(BaseModel):
    username: str
    email: EmailStr
    role: str = "student"

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: int
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ Content Schemas ============
class ContentBase(BaseModel):
    filename: str

class ContentCreate(ContentBase):
    pass

class ContentResponse(ContentBase):
    id: int
    user_id: int
    file_size: Optional[int]
    file_type: Optional[str]
    upload_date: datetime
    
    class Config:
        from_attributes = True

# ============ Knowledge Base Schemas ============
class KnowledgeBaseResponse(BaseModel):
    id: int
    content_id: int
    collection_name: str
    total_chunks: int
    embedding_model: str
    
    class Config:
        from_attributes = True

# ============ Session Schemas ============
class SessionCreate(BaseModel):
    content_id: int
    session_type: str  # classroom, tuition
    session_name: str

class SessionResponse(BaseModel):
    id: int
    user_id: int
    content_id: int
    session_type: str
    session_name: str
    lecture_script: Optional[str]
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    
    class Config:
        from_attributes = True


# ============ Vision Event Schemas ============
class VisionEventResponse(BaseModel):
    id: int
    session_id: int
    event_type: str
    timestamp: datetime
    confidence: float
    snapshot_path: Optional[str]
    is_resolved: bool
    
    class Config:
        from_attributes = True

# ============ Assessment & Question Schemas ============
class QuestionResponse(BaseModel):
    id: int
    assessment_id: int
    question_text: str
    question_type: str
    options: Optional[str]
    difficulty: Optional[str]
    
    class Config:
        from_attributes = True

class AssessmentResponse(BaseModel):
    id: int
    content_id: int
    assessment_name: str
    num_questions: int
    difficulty_level: Optional[str]
    passing_score: int
    
    class Config:
        from_attributes = True

# ============ Submission & Answer Schemas ============
class AnswerCreate(BaseModel):
    question_id: int
    selected_answer: str

class AnswerResponse(BaseModel):
    id: int
    submission_id: int
    question_id: int
    selected_answer: str
    is_correct: Optional[bool]
    points_earned: Optional[int]
    
    class Config:
        from_attributes = True

class SubmissionCreate(BaseModel):
    assessment_id: int

class SubmissionResponse(BaseModel):
    id: int
    student_id: int
    assessment_id: int
    submitted_at: datetime
    total_score: Optional[int]
    percentage_score: Optional[float]
    status: str
    
    class Config:
        from_attributes = True

# ============ Note Schemas ============
class NoteCreate(BaseModel):
    content_id: int
    note_title: Optional[str]
    note_content: str
    note_type: str = "note"  # note, highlight, summary

class NoteResponse(BaseModel):
    id: int
    student_id: int
    content_id: int
    note_title: Optional[str]
    note_content: str
    note_type: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

# ============ Summary Schemas ============
class SummaryResponse(BaseModel):
    id: int
    content_id: int
    summary_type: str
    summary_text: str
    key_points: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True

# ============ Dashboard Schemas ============
class SessionSummaryResponse(BaseModel):
    id: int
    session_name: str
    session_type: str
    started_at: datetime
    ended_at: Optional[datetime]
    status: str
    total_events: int

class EventReportResponse(BaseModel):
    id: int
    timestamp: datetime
    event_type: str
    confidence: float
    snapshot_path: Optional[str]
    is_resolved: bool

class SessionDetailReportResponse(BaseModel):
    session_id: int
    session_name: str
    session_type: str
    started_at: datetime
    ended_at: Optional[datetime]
    total_events: int
    events: List[EventReportResponse]

