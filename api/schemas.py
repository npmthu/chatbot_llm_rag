from pydantic import BaseModel, Field
from typing import Optional


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=512, description="User question")
    session_id: Optional[str] = Field(None, description="Optional session identifier")


class SourceDocument(BaseModel):
    id: str
    score: float
    text: str
    metadata: dict


class ChatResponse(BaseModel):
    answer: str
    session_id: Optional[str] = None
    sources: list[SourceDocument] = []


class HealthResponse(BaseModel):
    status: str
    app_name: str
    version: str
    llm_provider: str
    llm_model: str
    vector_db: str
    collection: str
