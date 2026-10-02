from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


class CuartoTecnico(Base):
    """Cuarto técnico (technical room) — nivel 1 del módulo de Redes.

    Pertenece a una empresa y a una *sede* (que reutiliza el catálogo per-empresa
    Catalogo categoria='sede' → sede_catalogo_id → catalogos.id). Contiene racks.
    """
    __tablename__ = "cuartos_tecnicos"

    id               = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id       = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    # Sede = reutiliza el catálogo per-empresa existente (Catalogo categoria='sede').
    sede_catalogo_id = Column(String(36), ForeignKey("catalogos.id"), nullable=False, index=True)
    identificador    = Column(String(100), nullable=False)   # código/identificador del cuarto
    nombre           = Column(String(150), nullable=True)     # nombre amigable
    descripcion      = Column(Text, nullable=True)
    ubicacion_detalle = Column(String(200), nullable=True)    # texto libre: "piso 2, junto a sistemas"
    activo           = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at       = Column(DateTime, server_default=func.now())
    created_by       = Column(String(36), nullable=True)

    empresa = relationship("Empresa")
    sede    = relationship("Catalogo")
    racks   = relationship("Rack", back_populates="cuarto", cascade="all, delete-orphan")


class Rack(Base):
    """Rack dentro de un cuarto técnico — nivel 2. Diseñado para que una futura
    tabla de dispositivos (fase 2) pueda hacer FK a racks.id sin migraciones extra.
    """
    __tablename__ = "racks"

    id                = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    cuarto_tecnico_id = Column(String(36), ForeignKey("cuartos_tecnicos.id"), nullable=False, index=True)
    nombre            = Column(String(100), nullable=False)   # e.g. "Rack A"
    capacidad_u       = Column(Integer, nullable=False, default=42, server_default="42")  # unidades de rack (U)
    descripcion       = Column(String(300), nullable=True)
    orden             = Column(Integer, nullable=True, default=0, server_default="0")     # orden de despliegue
    activo            = Column(Boolean, nullable=False, default=True, server_default="1")
    created_at        = Column(DateTime, server_default=func.now())
    created_by        = Column(String(36), nullable=True)

    cuarto       = relationship("CuartoTecnico", back_populates="racks")
    dispositivos = relationship("DispositivoRed", back_populates="rack")


class DispositivoRed(Base):
    """Montaje de red (rediseño): un Activo EXISTENTE montado en un cuarto técnico,
    ya sea EN un rack (rack_id + posicion_u + tamano_u) o FUERA de rack
    (rack_id nulo + ubicacion_fisica). Nunca ambos.

    Esta tabla es la CAPA DE MONTAJE: referencia al activo (activo_id) y guarda SOLO
    los datos de red/montaje. El consecutivo/marca/modelo/serial/tipo se leen del
    activo — no se duplican aquí.
    """
    __tablename__ = "dispositivos_red"

    id                = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    activo_id         = Column(String(36), ForeignKey("activos.id"), nullable=False, index=True)  # el activo montado
    cuarto_tecnico_id = Column(String(36), ForeignKey("cuartos_tecnicos.id"), nullable=False, index=True)
    rack_id           = Column(String(36), ForeignKey("racks.id"), nullable=True, index=True)  # null = fuera de rack
    posicion_u        = Column(Integer, nullable=True)   # U inicial (requerida solo en rack)
    tamano_u          = Column(Integer, nullable=True, default=1, server_default="1")  # U que ocupa (solo en rack)
    ubicacion_fisica  = Column(String(200), nullable=True)  # texto libre; sobre todo para fuera de rack
    ip_gestion        = Column(String(45), nullable=True)
    num_puertos       = Column(Integer, nullable=True)
    conexion          = Column(String(300), nullable=True)   # texto libre: "SW-ACC-02 puerto 12"
    datos_adicionales = Column(Text, nullable=True)
    activo            = Column(Boolean, nullable=False, default=True, server_default="1")  # soft-delete del MONTAJE
    created_at        = Column(DateTime, server_default=func.now())
    created_by        = Column(String(36), nullable=True)

    equipo = relationship("Activo")   # el activo montado
    cuarto = relationship("CuartoTecnico")
    rack   = relationship("Rack", back_populates="dispositivos")
