from sqlalchemy import Text
import pytz
from nanoid import generate
from sqlalchemy import Boolean, Column, ForeignKey, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy import Float
from datetime import datetime
from app.core.database import Base
from app.core.config import settings
from pgvector.sqlalchemy import Vector

key = settings.DB_SECRET_KEY

class Document(Base):
    __tablename__ = "documents"
    id = Column(String(40), primary_key=True, default=generate)
    filename = Column(StringEncryptedType(String(200), key), index=True)
    upload_date = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.utc))
    content_hash = Column(StringEncryptedType(String(200), key), unique=True, index=True)    
    vector_data = Column(Vector(384), nullable=False)
    deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc))
    
    user_id = Column(String(40), ForeignKey("users.id"))
    user = relationship("User", back_populates="documents", lazy="joined")

class History(Base):
    __tablename__ = "history"
    id = Column(String(40), primary_key=True, default=generate)
    query_text = Column(StringEncryptedType(Text, key), nullable=False)
    response_text = Column(StringEncryptedType(Text, key), nullable=False)    
    deleted = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(pytz.utc), onupdate=lambda: datetime.now(pytz.utc))
    
    user_id = Column(String(40), ForeignKey("users.id"))
    user = relationship("User", back_populates="histories", lazy="joined")