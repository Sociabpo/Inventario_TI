from sqlalchemy import Column, String, DateTime, Date, ForeignKey, Text, Boolean, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class Acta(Base):
    __tablename__ = "actas_entrega"

    id                 = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id         = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    id_activo          = Column(String(36), ForeignKey("activos.id"), nullable=True)
    id_usuario         = Column(String(36), ForeignKey("usuarios.id"), nullable=False)
    tipo               = Column(String(20), nullable=False)  # entrega, devolucion
    fecha_entrega      = Column(DateTime, server_default=func.now())
    responsable_entrega = Column(String(150), nullable=False)
    responsable_recibe  = Column(String(150), nullable=False)
    url_pdf            = Column(String(500))
    hash_pdf           = Column(String(64))
    observaciones      = Column(Text)
    firmada            = Column(Boolean, default=False, nullable=False, server_default="0")
    fecha_firma        = Column(DateTime, nullable=True)
    fecha_inicio_vigencia  = Column(Date, nullable=True)
    es_anticipada          = Column(Boolean, default=False, nullable=False, server_default="0")
    recordatorios_enviados = Column(Integer, default=0, nullable=False, server_default="0")
    created_at         = Column(DateTime, server_default=func.now())

    # Relaciones
    empresa   = relationship("Empresa")
    activo    = relationship("Activo",  back_populates="actas")
    usuario   = relationship("Usuario", back_populates="actas")
    detalle   = relationship("ActaDetalle", back_populates="acta")


class ActaDetalle(Base):
    __tablename__ = "acta_detalle"

    id            = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    acta_id       = Column(String(36), ForeignKey("actas_entrega.id"), nullable=False)
    tipo_item     = Column(String(20), nullable=False)  # activo, accesorio
    id_activo     = Column(String(36), ForeignKey("activos.id"),    nullable=True)
    id_accesorio  = Column(String(36), ForeignKey("accesorios.id"), nullable=True)
    observacion   = Column(Text)

    # Relaciones
    acta      = relationship("Acta", back_populates="detalle")
    activo    = relationship("Activo")
    accesorio = relationship("Accesorio")