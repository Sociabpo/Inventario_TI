"""
Módulo de Mantenimiento Preventivo (coexiste con el mantenimiento reactivo de
estados.py — no lo reemplaza).

Fase 1: modelo de datos completo del módulo + gestión de PLANES (plantillas).
Las tablas de TAREAS se crean ya (para no acumular migraciones), pero en la
Fase 1 NO tienen endpoints ni lógica.

Convenciones (espejo de reserva.py / compra.py):
  - PK UUID String(36)
  - FK String(36) hacia tablas existentes
  - Estados como String (validados en los schemas)
  - Relaciones ENTRE modelos nuevos son bidireccionales con back_populates.
"""
from sqlalchemy import (
    Column, String, Text, Date, DateTime, Integer, Boolean, ForeignKey, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


def _uuid():
    return str(uuid.uuid4())


# ── PLAN (plantilla GLOBAL — la misma para todas las empresas) ────────────
# La plantilla es un catálogo corporativo: se define una vez por tipo_activo y
# aplica en todas las empresas. Lo per-empresa es la TAREA (del equipo), no el plan.
class PlanMantenimiento(Base):
    __tablename__ = "planes_mantenimiento"

    id                    = Column(String(36), primary_key=True, default=_uuid)
    nombre                = Column(String(150), nullable=False)
    descripcion           = Column(Text, nullable=True)
    periodicidad_meses    = Column(Integer, default=12)
    activo                = Column(Boolean, default=True, index=True)
    # Cabecera del acta (configurable, usada por el PDF en una fase posterior)
    codigo_formato        = Column(String(30), default="FTIN09")
    version_formato       = Column(String(20), default="1.1")
    fecha_emision_formato = Column(Date, nullable=True)
    clasificacion         = Column(String(50), default="Interno")
    proceso               = Column(String(50), default="Servicio")
    created_at            = Column(DateTime, server_default=func.now())
    created_by            = Column(String(36), nullable=True)   # usuarios_sistema.id

    tipos           = relationship("PlanTipoActivo", back_populates="plan",
                                   cascade="all, delete-orphan")
    checklist_items = relationship("PlanChecklistItem", back_populates="plan",
                                   cascade="all, delete-orphan")


# ── Tipos de activo cubiertos por un plan (uno-a-muchos) ──
class PlanTipoActivo(Base):
    __tablename__ = "plan_tipo_activo"

    id          = Column(String(36), primary_key=True, default=_uuid)
    plan_id     = Column(String(36), ForeignKey("planes_mantenimiento.id"), nullable=False, index=True)
    tipo_activo = Column(String(50), nullable=False)   # valor del catálogo global "tipo_activo"

    plan = relationship("PlanMantenimiento", back_populates="tipos")


# ── Ítems de checklist de un plan (plantilla) ─────────────
class PlanChecklistItem(Base):
    __tablename__ = "plan_checklist_items"

    id        = Column(String(36), primary_key=True, default=_uuid)
    plan_id   = Column(String(36), ForeignKey("planes_mantenimiento.id"), nullable=False, index=True)
    seccion   = Column(String(20), nullable=False)   # diagnostico | hardware | software
    tipo_item = Column(String(10), nullable=False)   # check | dato
    texto     = Column(String(300), nullable=False)
    orden     = Column(Integer, default=0)

    plan = relationship("PlanMantenimiento", back_populates="checklist_items")


# ── TAREA (fases posteriores; tabla creada ya, sin endpoints) ──
class TareaMantenimiento(Base):
    __tablename__ = "tareas_mantenimiento"

    id                  = Column(String(36), primary_key=True, default=_uuid)
    empresa_id          = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    activo_id           = Column(String(36), ForeignKey("activos.id"), nullable=False, index=True)
    plan_id             = Column(String(36), ForeignKey("planes_mantenimiento.id"), nullable=False)
    tecnico_id          = Column(String(36), ForeignKey("usuarios_sistema.id"), nullable=True)
    estado              = Column(String(20), default="pendiente", index=True)
    # pendiente | en_ejecucion | completada | cancelada
    origen              = Column(String(20), default="planificacion", index=True)
    # planificacion | devolucion | adhoc  (de dónde nació la tarea)
    fecha_programada    = Column(Date, nullable=True)
    fecha_inicio_ejec   = Column(DateTime, nullable=True)
    fecha_fin_ejec      = Column(DateTime, nullable=True)
    estado_activo_previo = Column(String(30), nullable=True)
    usuario_previo      = Column(String(36), nullable=True)
    observaciones       = Column(Text, nullable=True)
    motivo_cancelacion  = Column(Text, nullable=True)
    url_acta_pdf        = Column(String(300), nullable=True)
    created_at          = Column(DateTime, server_default=func.now())
    created_by          = Column(String(36), nullable=True)

    plan            = relationship("PlanMantenimiento")
    checklist_items = relationship("TareaChecklistItem", back_populates="tarea",
                                   cascade="all, delete-orphan")


# ── Checklist de una tarea (SNAPSHOT del plan al crear la tarea) ──
# Se copia desde plan_checklist_items al crear la tarea → editar el plan luego
# NUNCA altera tareas históricas.
class TareaChecklistItem(Base):
    __tablename__ = "tarea_checklist_items"

    id         = Column(String(36), primary_key=True, default=_uuid)
    tarea_id   = Column(String(36), ForeignKey("tareas_mantenimiento.id"), nullable=False, index=True)
    seccion    = Column(String(20), nullable=False)
    tipo_item  = Column(String(10), nullable=False)
    texto      = Column(String(300), nullable=False)
    orden      = Column(Integer, default=0)
    realizado  = Column(Boolean, nullable=True)      # True=Sí, False=No, NULL=N/A (ítems "check")
    valor_dato = Column(String(200), nullable=True)  # valor capturado (ítems "dato")

    tarea = relationship("TareaMantenimiento", back_populates="checklist_items")
