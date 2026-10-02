from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from database import Base
import uuid


class Catalogo(Base):
    __tablename__ = "catalogos"

    id          = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    categoria   = Column(String(50),  nullable=False)
    valor       = Column(String(150), nullable=False)
    descripcion = Column(String(300), nullable=True)
    empresa_id  = Column(String(36),  ForeignKey("empresas.id"), nullable=True)
    activo      = Column(Boolean,     default=True,  nullable=False)
    orden       = Column(Integer,     default=0)
    color       = Column(String(7),   nullable=True)
    icono       = Column(String(50),  nullable=True)
    anios_obsolescencia = Column(Integer, nullable=True)  # solo relevante para categoria="tipo_activo"
    es_red      = Column(Boolean, default=False, nullable=False, server_default="0")  # solo tipo_activo: ¿es un dispositivo de red montable?
    created_at  = Column(DateTime,    server_default=func.now())
    updated_at  = Column(DateTime,    server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("categoria", "valor", "empresa_id",
                         name="uq_catalogo_categoria_valor_empresa"),
    )
