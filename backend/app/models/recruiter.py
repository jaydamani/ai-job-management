import uuid
from sqlalchemy import Column, Text
from sqlalchemy.dialects.postgresql import UUID
from app.models.base import Base


class Recruiter(Base):
    __tablename__ = "recruiters"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, nullable=False, unique=True)
    password_hash = Column(Text, nullable=False)
    name = Column(Text, nullable=False)
