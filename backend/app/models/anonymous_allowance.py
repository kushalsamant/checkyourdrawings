from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from backend.app.database import Base


class AnonymousAllowance(Base):
    __tablename__ = "anonymous_allowances"

    anon_session_id = Column(String, primary_key=True)
    successful_comparisons = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=True)
