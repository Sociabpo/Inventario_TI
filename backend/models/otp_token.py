from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


class OtpToken(Base):
    __tablename__ = "otp_tokens"

    id                = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    firma_token_id    = Column(String(36), ForeignKey("firma_tokens.id"), nullable=False)
    codigo            = Column(String(6), nullable=False)
    usado             = Column(Boolean, default=False)
    verificado        = Column(Boolean, default=False)
    intentos_fallidos = Column(Integer, default=0)
    expires_at        = Column(DateTime, nullable=False)
    created_at        = Column(DateTime, server_default=func.now())

    firma_token = relationship("FirmaToken")
