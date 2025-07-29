from datetime import datetime
from typing import Optional, Dict
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Column, JSON


class Source(SQLModel, table=True):
    __tablename__ = "sources"
    
    id: Optional[UUID] = Field(default_factory=uuid4, primary_key=True)
    source_type: str = Field(max_length=50, nullable=False)
    source_identifier: str = Field(nullable=False)
    last_scraped: Optional[datetime] = None
    is_active: bool = Field(default=True)
    config: Optional[Dict] = Field(default=None, sa_column=Column(JSON))