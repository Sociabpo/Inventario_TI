from sqlalchemy import Column, String, Integer, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class Consecutivo(Base):
    __tablename__ = "consecutivos"

    empresa_id    = Column(String(36), ForeignKey("empresas.id"), primary_key=True)
    tipo          = Column(String(20), primary_key=True)  # ACTIVO, ACCESORIO
    ultimo_numero = Column(Integer, default=0)

    # Relación
    empresa = relationship("Empresa", back_populates="consecutivos")