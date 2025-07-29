from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column, JSON


class Idea(SQLModel, table=True):
    __tablename__ = "ideas"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    complaint_id: UUID = Field(foreign_key="complaints.id")
    idea_text: str = Field(nullable=False)
    score_market: int = Field(ge=1, le=10)
    score_tech: int = Field(ge=1, le=10)
    score_competition: int = Field(ge=1, le=10)
    score_monetisation: int = Field(ge=1, le=10)
    score_feasibility: int = Field(ge=1, le=10)
    score_overall: int = Field(ge=1, le=10)
    raw_response: Optional[Dict] = Field(default=None, sa_column=Column(JSON))
    tokens_used: Optional[int] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    is_favorite: bool = Field(default=False)