from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class Rol(Base):
    __tablename__ = "roles"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nombre      = Column(String(50), unique=True, nullable=False)
    descripcion = Column(String(200))
    activo      = Column(Boolean, default=True)
    created_at  = Column(DateTime, server_default=func.now())

    permisos      = relationship("Permiso",    secondary="rol_permisos", back_populates="roles")
    usuario_roles = relationship("UsuarioRol", back_populates="rol")
