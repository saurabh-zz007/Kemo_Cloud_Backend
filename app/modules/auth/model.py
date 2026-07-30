from sqlalchemy import Column, String, DateTime, UUID
from app.core.database import Base
import uuid

class userModel(Base):
    __tablename__='users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
