from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class Usuario(Base):
    __tablename__ = "usuarios"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id      = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    documento       = Column(String(20), nullable=False)
    nombre_completo = Column(String(200), nullable=False)
    cargo            = Column(String(100))
    area             = Column(String(100))
    sede             = Column(String(100))
    unidad_negocio   = Column(String(100))
    correo          = Column(String(150))
    telefono        = Column(String(30))
    estado          = Column(String(20), default="activo")  # activo, inactivo, retirado
    created_at      = Column(DateTime, server_default=func.now())
    updated_at      = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    empresa    = relationship("Empresa",  back_populates="usuarios")
    # back_populates con foreign_keys explícito (id_usuario), ya que custodio_id
    # es una segunda FK hacia usuarios en activos/accesorios.
    activos    = relationship("Activo",    foreign_keys="Activo.id_usuario",    back_populates="usuario")
    accesorios = relationship("Accesorio", foreign_keys="Accesorio.id_usuario", back_populates="usuario")
    actas      = relationship("Acta",     back_populates="usuario")