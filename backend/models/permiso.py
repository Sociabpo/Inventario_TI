from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class Permiso(Base):
    __tablename__ = "permisos"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    codigo      = Column(String(100), unique=True, nullable=False)  # "activos.crear"
    descripcion = Column(String(200))
    modulo      = Column(String(50), nullable=False)
    accion      = Column(String(50), nullable=False)
    created_at  = Column(DateTime, server_default=func.now())

    roles = relationship("Rol", secondary="rol_permisos", back_populates="permisos")
