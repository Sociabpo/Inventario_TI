from sqlalchemy import Column, String, Numeric, Text, Date, DateTime, ForeignKey
from sqlalchemy.sql import func
from database import Base
import uuid


class BajaActivo(Base):
    __tablename__ = "bajas_activos"

    id                = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    numero_baja       = Column(String(20), nullable=False)   # BAJA-2025-001
    tipo_recurso      = Column(String(20), nullable=False)
    recurso_id        = Column(String(36), nullable=False)
    placa             = Column(String(50), nullable=True)
    empresa_id        = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    # Snapshot del activo al momento de baja
    tipo_activo       = Column(String(50),  nullable=True)
    marca             = Column(String(100), nullable=True)
    modelo            = Column(String(100), nullable=True)
    serial            = Column(String(100), nullable=True)
    fecha_compra      = Column(Date,        nullable=True)
    costo_original    = Column(Numeric(14, 2), nullable=True)
    # Motivo
    motivo            = Column(String(30), nullable=False)  # donado|vendido|destruido|retiro_operacion|hurto|traslado
    justificacion     = Column(Text, nullable=False)
    estado_fisico     = Column(Text, nullable=True)
    # Específico por motivo
    valor_venta        = Column(Numeric(14, 2), nullable=True)
    comprador          = Column(String(200), nullable=True)
    entidad_receptora  = Column(String(200), nullable=True)
    metodo_destruccion = Column(String(200), nullable=True)
    numero_denuncia        = Column(String(100), nullable=True)  # motivo "hurto"
    empresa_destino_id     = Column(String(36), nullable=True)   # motivo "traslado" (FK-like a empresas.id)
    empresa_destino_nombre = Column(String(150), nullable=True)  # snapshot del nombre de la empresa destino
    # Aprobación
    estado_aprobacion = Column(String(20), default="pendiente")  # pendiente|aprobada|rechazada
    solicitado_por_id = Column(String(36), nullable=False)
    aprobado_por_id   = Column(String(36), nullable=True)
    fecha_solicitud   = Column(DateTime, server_default=func.now())
    fecha_aprobacion  = Column(DateTime, nullable=True)
    observaciones_aprobador = Column(Text, nullable=True)
    url_pdf           = Column(String(300), nullable=True)
    created_at        = Column(DateTime, server_default=func.now())
