from sqlalchemy import Column, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class HistorialMovimiento(Base):
    __tablename__ = "historial_movimientos"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_activo       = Column(String(36), ForeignKey("activos.id"),    nullable=True)
    id_accesorio    = Column(String(36), ForeignKey("accesorios.id"), nullable=True)
    id_usuario      = Column(String(36), ForeignKey("usuarios.id"),   nullable=True)
    id_acta         = Column(String(36), ForeignKey("actas_entrega.id"), nullable=True)
    tipo_movimiento = Column(String(50), nullable=False)
    # asignacion, devolucion, traslado, mantenimiento, baja, creacion
    fecha_movimiento = Column(DateTime, server_default=func.now())
    responsable     = Column(String(150))
    observaciones   = Column(Text)

    # Relaciones
    activo    = relationship("Activo",   back_populates="historial")
    accesorio = relationship("Accesorio", back_populates="historial")
    usuario   = relationship("Usuario")