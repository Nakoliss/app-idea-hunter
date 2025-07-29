from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel


class Error(SQLModel, table=True):
    __tablename__ = "errors"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    source: str = Field(max_length=50, nullable=False)
    url: Optional[str] = None
    error_message: Optional[str] = None
    error_type: Optional[str] = Field(max_length=100)
    occurred_at: datetime = Field(default_factory=datetime.utcnow)
    retry_count: int = Field(default=0)