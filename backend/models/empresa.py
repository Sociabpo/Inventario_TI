from sqlalchemy import Column, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid
import json

class Empresa(Base):
    __tablename__ = "empresas"

    id               = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    nit              = Column(String(20), unique=True, nullable=False)
    nombre_empresa   = Column(String(200), nullable=False)
    prefijo          = Column(String(5), nullable=False)  # ← NUEVO: SC, AA, etc.
    direccion        = Column(String(300))
    ciudad           = Column(String(100))
    telefono         = Column(String(30))
    correo           = Column(String(150))
    sedes            = Column(Text)  # JSON array de nombres de sede, ej: ["Bogotá","Medellín"]
    activo           = Column(Boolean, default=True)
    created_at       = Column(DateTime, server_default=func.now())
    updated_at       = Column(DateTime, server_default=func.now(), onupdate=func.now())

    @property
    def sedes_list(self) -> list:
        """Devuelve las sedes como lista de strings (parseando el JSON)."""
        if not self.sedes:
            return []
        try:
            v = json.loads(self.sedes)
            return [str(s) for s in v] if isinstance(v, list) else []
        except (ValueError, TypeError):
            return []

    # Relaciones
    usuarios     = relationship("Usuario",   back_populates="empresa")
    activos      = relationship("Activo",    back_populates="empresa")
    accesorios   = relationship("Accesorio", back_populates="empresa")
    consecutivos = relationship("Consecutivo", back_populates="empresa")