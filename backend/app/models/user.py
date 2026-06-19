from sqlalchemy import Boolean, Column, DateTime, Integer, String

from backend.app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=True)
    google_id = Column(String, unique=True, index=True, nullable=True)
    credits = Column(Integer, nullable=True, server_default="5")
    subscription_tier = Column(String, nullable=True, server_default="trial")
    subscription_status = Column(String, nullable=True, server_default="inactive")
    razorpay_customer_id = Column(String, unique=True, index=True, nullable=True)
    razorpay_subscription_id = Column(String, index=True, nullable=True)
    subscription_auto_renew = Column(Boolean, nullable=True, server_default="false")
    subscription_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, nullable=True)
    last_login = Column(DateTime, nullable=True)
    is_active = Column(Boolean, nullable=True, server_default="true")
