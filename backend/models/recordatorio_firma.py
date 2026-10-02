from sqlalchemy import Column, String, Boolean, DateTime, Integer, ForeignKey
from sqlalchemy.sql import func
from database import Base
import uuid


class RecordatorioFirma(Base):
    __tablename__ = "recordatorios_firma"

    id                  = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    acta_id             = Column(String(36), ForeignKey("actas_entrega.id"), nullable=False)
    token_id            = Column(String(36), ForeignKey("firma_tokens.id"), nullable=True)
    enviado_a           = Column(String(150), nullable=False)
    numero_recordatorio = Column(Integer,  nullable=False, default=1)
    fecha_envio         = Column(DateTime, server_default=func.now())
    escalado_admin      = Column(Boolean,  default=False)
    created_at          = Column(DateTime, server_default=func.now())
