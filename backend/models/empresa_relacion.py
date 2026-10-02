"""
Relación bidireccional entre empresas ("hermanas").

DISEÑO: se guarda UNA sola fila canónica por relación. El par se almacena
ordenado (empresa_a_id = min(id1, id2), empresa_b_id = max(id1, id2)) comparando
los ids como strings, de modo que A↔B y B↔A nunca generan filas duplicadas.
Las consultas SIEMPRE revisan ambas columnas (empresa_a_id OR empresa_b_id), así
la relación es bidireccional sin importar en qué columna quedó cada empresa.

La relación es NO transitiva: A↔B y A↔C no implica B↔C (cada par es una fila
explícita). FK unidireccionales hacia empresas (sin back_populates) para no
modificar el modelo Empresa.
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.sql import func
from database import Base
import uuid


class EmpresaRelacion(Base):
    __tablename__ = "empresa_relaciones"

    id           = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_a_id = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    empresa_b_id = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    created_at   = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("empresa_a_id", "empresa_b_id", name="uq_empresa_relacion"),
    )
