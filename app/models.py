from datetime import datetime, timezone
from typing import Optional
from sqlmodel import Field, SQLModel


class Incident(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True, unique=True)
    title: str
    description: str
    resolution: str
    department: str = Field(default="all", index=True)
    status: str = Field(default="resolved")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class SupportTicket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ticket_id: str = Field(index=True, unique=True)
    user_id: str = Field(index=True)
    department: str = Field(default="all", index=True)
    title: str
    description: str
    priority: str = Field(default="medium")  # low, medium, high, critical
    status: str = Field(default="open")  # open, in_progress, resolved, closed
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class ConversationMessage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conversation_id: str = Field(index=True)
    user_id: str = Field(index=True)
    role: str  # user, assistant, system, tool
    content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
