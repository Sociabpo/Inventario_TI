from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class Asignacion(Base):
    __tablename__ = "asignaciones"

    id                = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id        = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    id_activo         = Column(String(36), ForeignKey("activos.id"), nullable=False)
    id_usuario        = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    fecha_asignacion  = Column(DateTime, server_default=func.now())
    fecha_devolucion  = Column(DateTime, nullable=True)
    estado            = Column(String(20), default="activa")  # activa, devuelta, anulada
    asignado_por      = Column(String(150), nullable=False)
    recibido_por      = Column(String(150))
    observaciones     = Column(Text)
    created_at        = Column(DateTime, server_default=func.now())

    # Relaciones ORM
    empresa  = relationship("Empresa")
    activo   = relationship("Activo")
    usuario  = relationship("Usuario")