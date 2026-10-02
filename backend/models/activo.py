from sqlalchemy import Column, String, Boolean, DateTime, Date, ForeignKey, Numeric, Text, Integer
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid

class Activo(Base):
    __tablename__ = "activos"

    id                  = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    id_placa_activo     = Column(String(20), nullable=False)
    empresa_id          = Column(String(36), ForeignKey("empresas.id"), nullable=False)
    id_usuario          = Column(String(36), ForeignKey("usuarios.id"), nullable=True)
    # Custodio: empleado responsable mientras el recurso está DISPONIBLE (no es estado).
    custodio_id         = Column(String(36), ForeignKey("usuarios.id"), nullable=True)

    # Identificación
    tipo_activo         = Column(String(50), nullable=False)
    marca               = Column(String(100))
    modelo              = Column(String(100))
    serial              = Column(String(100))
    numero_parte        = Column(String(100))
    codigo_contable     = Column(String(50))

    # Specs técnicas
    procesador          = Column(String(150))
    memoria_ram         = Column(String(50))
    disco_1             = Column(String(100))
    disco_2             = Column(String(100))

    # Pantalla
    resolucion              = Column(String(100))
    tipo_conexion           = Column(String(100))
    tamano_pantalla         = Column(String(50))

    # Móvil
    imei                    = Column(String(20))
    numero_telefono         = Column(String(30))
    capacidad_almacenamiento = Column(String(50))
    color                   = Column(String(50))

    # Impresora / Red
    tipo_impresora          = Column(String(100))
    ip_dispositivo          = Column(String(50))

    # Cámara / DVR
    tipo_camara             = Column(String(100))
    canales_dvr             = Column(Integer)

    # Diadema
    con_microfono           = Column(Boolean)

    # Teléfono fijo
    extension               = Column(String(20))
    linea_telefono          = Column(String(30))
    tipo_telefono           = Column(String(50))

    # UPS
    capacidad_ups           = Column(String(50))
    tiempo_respaldo_ups     = Column(String(50))

    # Ciclo de vida
    fecha_compra        = Column(Date)
    fecha_obsolescencia = Column(Date)
    costo               = Column(Numeric(12, 2))
    estado              = Column(String(30), default="disponible")
    # disponible, asignado, mantenimiento_preventivo, mantenimiento_correctivo,
    # en_reparacion, en_garantia, retirado
    ubicacion           = Column(String(150))  # requerida cuando estado != asignado

    observaciones       = Column(Text)

    # Préstamo temporal (loan): el recurso sigue "asignado", sin estado nuevo.
    fecha_limite_devolucion    = Column(Date, nullable=True)        # fecha límite opcional del préstamo
    es_prestamo                = Column(Boolean, default=False)     # flag: asignación temporal
    alerta_vencimiento_enviada = Column(Boolean, default=False)     # evita correos duplicados

    # Garantía simple (info de garantía por recurso, fijada al crear; editable)
    garantia_meses      = Column(Integer, nullable=True)   # duración de garantía en meses
    garantia_fin        = Column(Date, nullable=True)      # fin de garantía (auto-calculado desde fecha_compra, editable)

    # Alquiler (rental): el recurso NO es propiedad — pertenece a un contrato de alquiler
    es_alquiler          = Column(Boolean, default=False)
    contrato_alquiler_id = Column(String(36), ForeignKey("contratos_alquiler.id"), nullable=True)

    created_at          = Column(DateTime, server_default=func.now())
    updated_at          = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones
    empresa    = relationship("Empresa",  back_populates="activos")
    # Dos FKs hacia usuarios (id_usuario, custodio_id) → foreign_keys explícito
    usuario    = relationship("Usuario",  foreign_keys=[id_usuario], back_populates="activos")
    custodio   = relationship("Usuario",  foreign_keys=[custodio_id])
    actas      = relationship("Acta",     back_populates="activo")
    historial  = relationship("HistorialMovimiento", back_populates="activo")