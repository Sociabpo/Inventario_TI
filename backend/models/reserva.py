from sqlalchemy import Column, String, Text, Date, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base
import uuid


class Reserva(Base):
    __tablename__ = "reservas"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    numero_alta     = Column(String(100), nullable=False)   # the "alta" / destination text
    descripcion     = Column(Text, nullable=True)           # optional notes (for whom, area, etc.)
    empresa_id      = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    fecha_limite    = Column(Date, nullable=False)
    estado          = Column(String(20), default="activa")  # "activa" | "cancelada" | "vencida" | "completada"
    creado_por_id   = Column(String(36), nullable=False)
    created_at      = Column(DateTime, server_default=func.now())
    fecha_cierre    = Column(DateTime, nullable=True)        # when cancelled/expired/completed


class ReservaItem(Base):
    __tablename__ = "reserva_items"

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    reserva_id    = Column(String(36), ForeignKey("reservas.id"), nullable=False)
    tipo_recurso  = Column(String(20), nullable=False)   # "activo" | "accesorio"
    recurso_id    = Column(String(36), nullable=False)
    placa         = Column(String(50), nullable=True)
    estado        = Column(String(20), default="reservado")  # "reservado" | "liberado" | "asignado"
    # liberado = reservation cancelled/expired; asignado = consumed by an assignment
