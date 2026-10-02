from sqlalchemy import Column, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class FirmaToken(Base):
    __tablename__ = "firma_tokens"

    id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    acta_id      = Column(String(36), ForeignKey("actas_entrega.id"), nullable=False)
    token        = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    usado        = Column(Boolean, default=False)
    expires_at   = Column(DateTime, nullable=True)
    ip_firmante  = Column(String(45), nullable=True)
    firma_base64        = Column(Text, nullable=True)
    nombre_firmante     = Column(String(150), nullable=True)
    entrega_por_tercero  = Column(Boolean, default=False, nullable=False, server_default="0")
    nombre_tercero       = Column(String(150), nullable=True)
    relacion_tercero     = Column(String(150), nullable=True)
    observaciones_firma  = Column(Text, nullable=True)
    correo_movil         = Column(Boolean, nullable=True)
    otp_verificado       = Column(Boolean, nullable=False, server_default="0")
    firmado_at           = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, server_default=func.now())

    acta = relationship("Acta")
