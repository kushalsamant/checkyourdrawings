import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID

from backend.app.database import Base


class ComparisonJob(Base):
    __tablename__ = "comparison_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), nullable=False, default="pending")
    priority = Column(Integer, nullable=False, default=0)
    user_email = Column(String, nullable=True)
    anon_session_id = Column(String, nullable=True)
    platform_user_id = Column(Integer, nullable=True)
    drawing_a_path = Column(Text, nullable=False)
    drawing_b_path = Column(Text, nullable=False)
    drawing_a_name = Column(Text, nullable=False)
    drawing_b_name = Column(Text, nullable=False)
    result = Column(JSONB, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
