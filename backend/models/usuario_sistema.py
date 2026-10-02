from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class UsuarioSistema(Base):
    __tablename__ = "usuarios_sistema"

    id         = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id = Column(String(36), ForeignKey("empresas.id"), nullable=True)
    # nullable=True para el superadmin que gestiona todas las empresas

    nombre     = Column(String(200), nullable=False)
    email      = Column(String(150), unique=True, nullable=False)
    password   = Column(String(255), nullable=False)  # bcrypt hash
    rol        = Column(String(20), default="visualizador")
    # superadmin, admin, visualizador
    activo     = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    roles = relationship("UsuarioRol", back_populates="usuario_sistema")
