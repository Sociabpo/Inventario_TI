from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class UsuarioRol(Base):
    __tablename__ = "usuario_roles"

    id                 = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    usuario_sistema_id = Column(String(36), ForeignKey("usuarios_sistema.id"), nullable=False)
    rol_id             = Column(String(36), ForeignKey("roles.id"),             nullable=False)
    empresa_id         = Column(String(36), ForeignKey("empresas.id"),          nullable=True)
    activo             = Column(Boolean, default=True)
    created_at         = Column(DateTime, server_default=func.now())

    usuario_sistema = relationship("UsuarioSistema", back_populates="roles")
    rol             = relationship("Rol",            back_populates="usuario_roles")
    empresa         = relationship("Empresa")

    __table_args__ = (
        Index("ix_usuario_roles_usr_emp", "usuario_sistema_id", "empresa_id"),
    )
