import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.app.database import Base


class Comparison(Base):
    __tablename__ = "comparisons"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, nullable=False, index=True)
    storage_path = Column(String, nullable=False)
    metadata_json = Column("metadata", JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
