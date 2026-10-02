from sqlalchemy import Column, String, Integer, Numeric, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.sql import func
from database import Base
import uuid


class CambioEstado(Base):
    __tablename__ = "cambios_estado"

    id              = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tipo_recurso    = Column(String(20), nullable=False)   # "activo" | "accesorio"
    recurso_id      = Column(String(36), nullable=False)
    placa           = Column(String(50), nullable=True)
    empresa_id      = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    estado_anterior = Column(String(30), nullable=False)
    estado_nuevo    = Column(String(30), nullable=False)
    ubicacion       = Column(String(100), nullable=True)
    # Mantenimiento
    tipo_mantenimiento   = Column(String(20),  nullable=True)  # "preventivo" | "correctivo"
    cubierto_garantia    = Column(Boolean,     default=False)
    cubre_garantia       = Column(String(20),  nullable=True)  # "proveedor" | "fabricante"
    tiempo_estimado_dias = Column(Integer,     nullable=True)
    responsable_mant     = Column(String(150), nullable=True)
    descripcion          = Column(Text,        nullable=True)
    # Salida de mantenimiento
    resultado_mant       = Column(String(30),  nullable=True)  # "exitoso" | "sin_solucion" | "requiere_baja"
    costo_real           = Column(Numeric(14, 2), nullable=True)
    # Acta de devolución (si estaba asignado)
    genero_acta          = Column(Boolean,     default=False)
    acta_id              = Column(String(36),  nullable=True)
    # Usuario al que estaba asignado el recurso al entrar a mantenimiento SIN devolución
    # (genero_acta=False). Permite restaurar el estado "asignado" al finalizar.
    usuario_previo       = Column(String(36),  nullable=True)
    # Auditoría
    realizado_por_id     = Column(String(36),  nullable=False)
    fecha                = Column(DateTime,    server_default=func.now())
