from sqlalchemy import Column, String, DateTime, Date, Boolean, Integer, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class Accesorio(Base):
    __tablename__ = "accesorios"

    id                   = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_placa_accesorio   = Column(String(20), nullable=False)
    empresa_id           = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    id_usuario           = Column(String(36), ForeignKey("usuarios.id"), nullable=True)
    # Custodio: empleado responsable mientras el recurso está DISPONIBLE (no es estado).
    custodio_id          = Column(String(36), ForeignKey("usuarios.id"), nullable=True)

    tipo_accesorio       = Column(String(50), nullable=False)
    # Mouse, Teclado, Diadema, Guaya, Hub, Bolso, Cargador, etc.
    marca                = Column(String(100))
    modelo               = Column(String(100))
    serial               = Column(String(100))
    estado               = Column(String(30), default="disponible")
    # disponible, asignado, mantenimiento_preventivo, mantenimiento_correctivo,
    # en_reparacion, en_garantia, retirado
    ubicacion            = Column(String(150))  # requerida cuando estado != asignado

    observaciones        = Column(Text)

    # Préstamo temporal (loan): el recurso sigue "asignado", sin estado nuevo.
    fecha_limite_devolucion    = Column(Date, nullable=True)        # fecha límite opcional del préstamo
    es_prestamo                = Column(Boolean, default=False)     # flag: asignación temporal
    alerta_vencimiento_enviada = Column(Boolean, default=False)     # evita correos duplicados

    # Garantía simple (info de garantía por recurso, fijada al crear; editable)
    garantia_meses       = Column(Integer, nullable=True)   # duración de garantía en meses
    garantia_fin         = Column(Date, nullable=True)      # fin de garantía (auto-calculado, editable)

    # Alquiler (rental): el recurso NO es propiedad — pertenece a un contrato de alquiler
    es_alquiler          = Column(Boolean, default=False)
    contrato_alquiler_id = Column(String(36), ForeignKey("contratos_alquiler.id"), nullable=True)

    created_at           = Column(DateTime, server_default=func.now())
    updated_at           = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    empresa   = relationship("Empresa",  back_populates="accesorios")
    # Dos FKs hacia usuarios (id_usuario, custodio_id) → foreign_keys explícito
    usuario   = relationship("Usuario",  foreign_keys=[id_usuario], back_populates="accesorios")
    custodio  = relationship("Usuario",  foreign_keys=[custodio_id])
    historial = relationship("HistorialMovimiento", back_populates="accesorio")