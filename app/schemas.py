from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    user_id: str = Field(default="user_default", description="ID of the user making the query")
    department: str = Field(default="all", description="Department scope (e.g. engineering, it, hr, sales, finance, all)")
    message: str = Field(..., min_length=1, description="User question or issue description")
    conversation_id: str = Field(default="default", description="Conversation session ID for multi-turn history")


class Citation(BaseModel):
    source: str
    text: str


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation] = Field(default_factory=list)
    tools_used: List[str] = Field(default_factory=list)
    escalated_ticket_id: Optional[str] = None


class TicketCreateRequest(BaseModel):
    user_id: str
    department: str = "all"
    title: str
    description: str
    priority: str = "medium"


class TicketResponse(BaseModel):
    ticket_id: str
    user_id: str
    department: str
    title: str
    description: str
    priority: str
    status: str
    created_at: datetime


class IncidentResponse(BaseModel):
    ticket_id: str
    title: str
    description: str
    resolution: str
    department: str
    status: str


class ServiceStatusItem(BaseModel):
    service: str
    status: str
    message: str
    latency_ms: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    database: str
    chroma_chunks: int
    version: str
