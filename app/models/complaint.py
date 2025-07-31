from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column, JSON


class Complaint(SQLModel, table=True):
    __tablename__ = "complaints"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    source_url: Optional[str] = None
    content: str = Field(nullable=False)
    content_hash: str = Field(max_length=40, unique=True, nullable=False)
    sentiment_score: Optional[float] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    extra_data: Optional[Dict] = Field(default=None, sa_column=Column(JSON))