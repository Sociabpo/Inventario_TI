"""
Módulo Gestión de Compras y Facturas.

Contiene los 9 modelos del flujo de compras/alquileres:
  Proveedor → SolicitudCompra → (SolicitudItem) → OrdenCompra
            → Factura / Recepcion → (RecepcionItem) → Activo/Accesorio
            → ContratoAlquiler

Convenciones (espejo del resto del proyecto):
  - PK UUID String(36)
  - FK String(36) hacia tablas existentes
  - Estados como String (no ENUM SQL), validados en los schemas Pydantic
  - Relaciones HACIA modelos existentes (Empresa, UsuarioSistema, Activo, Accesorio)
    son unidireccionales (sin back_populates) para no modificar esos archivos.
  - Relaciones ENTRE los modelos nuevos son bidireccionales con back_populates.
"""
from sqlalchemy import (
    Column, String, Boolean, DateTime, Date, Integer, Numeric, Text,
    ForeignKey, UniqueConstraint, Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid
import json


def _uuid():
    return str(uuid.uuid4())


# ── TABLA 1: proveedores ──────────────────────────────────
class Proveedor(Base):
    __tablename__ = "proveedores"

    id              = Column(String(36), primary_key=True, default=_uuid)
    # GLOBAL / transversal: un proveedor es una entidad única del sistema, no de una
    # empresa. Referenciado por órdenes/cotizaciones/facturas/contratos de cualquier empresa.
    nombre          = Column(String(150), nullable=False)
    nit             = Column(String(30), nullable=True)
    tipo            = Column(String(20), nullable=False)  # vendedor, arrendador, fabricante
    contacto_nombre = Column(String(100), nullable=True)
    telefono        = Column(String(30), nullable=True)
    correo          = Column(String(100), nullable=True)
    ciudad          = Column(String(100), nullable=True)
    # Catálogo compartido: a qué MÓDULOS aplica este proveedor (JSON array de strings,
    # ej. ["compras","impresoras"]). Mismo patrón que empresas.sedes. NULL/[] = solo compras
    # por retrocompatibilidad (ver modulos_list).
    modulos         = Column(Text, nullable=True)
    activo          = Column(Boolean, default=True)
    created_at      = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("nit", name="uq_proveedor_nit"),
    )

    @property
    def modulos_list(self) -> list:
        """Módulos como lista de strings (parseando el JSON). Vacío/NULL → ['compras']
        para que los proveedores existentes sigan visibles en compras."""
        if not self.modulos:
            return ["compras"]
        try:
            v = json.loads(self.modulos)
            return [str(m) for m in v] if isinstance(v, list) else ["compras"]
        except (ValueError, TypeError):
            return ["compras"]

    # Relaciones internas (bidireccionales)
    ordenes   = relationship("OrdenCompra",      back_populates="proveedor")
    facturas  = relationship("Factura",          back_populates="proveedor")
    contratos = relationship("ContratoAlquiler", back_populates="proveedor")


# ── TABLA 2: solicitudes_compra ───────────────────────────
class SolicitudCompra(Base):
    __tablename__ = "solicitudes_compra"

    id                = Column(String(36), primary_key=True, default=_uuid)
    empresa_id        = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    numero_solicitud  = Column(String(20), nullable=False, server_default="")  # autogenerado: SC-YYYY-NNN
    titulo            = Column(String(200), nullable=False, server_default="")  # título corto descriptivo
    # Trazabilidad para reportes: sede + área a nivel de la solicitud. Nullable
    # en BD (filas antiguas) pero requeridas por la API/UI en creación/edición.
    # Alimentadas por los catálogos per-empresa "sede" y "area".
    sede              = Column(String(150), nullable=True)
    area              = Column(String(150), nullable=True)
    solicitante_id    = Column(String(36), ForeignKey("usuarios_sistema.id"), nullable=False)
    justificacion     = Column(Text, nullable=False)
    estado            = Column(String(30), default="borrador", index=True)
    # borrador, pendiente_aprobacion, aprobada, rechazada, en_proceso, recibida, completada, cancelada
    aprobado_por_id   = Column(String(36), ForeignKey("usuarios_sistema.id"), nullable=True)
    fecha_aprobacion  = Column(DateTime, nullable=True)
    motivo_rechazo    = Column(Text, nullable=True)
    motivo_cancelacion = Column(Text, nullable=True)
    observaciones     = Column(Text, nullable=True)
    created_at        = Column(DateTime, server_default=func.now())
    updated_at        = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones externas (dos FKs al mismo target → foreign_keys explícito)
    empresa      = relationship("Empresa")
    solicitante  = relationship("UsuarioSistema", foreign_keys=[solicitante_id])
    aprobado_por = relationship("UsuarioSistema", foreign_keys=[aprobado_por_id])

    # Relaciones internas
    items   = relationship("SolicitudItem", back_populates="solicitud",
                           cascade="all, delete-orphan")
    ordenes = relationship("OrdenCompra", back_populates="solicitud")
    cotizaciones = relationship("Cotizacion", back_populates="solicitud",
                                cascade="all, delete-orphan")


# ── TABLA 2b: cotizaciones ────────────────────────────────
class Cotizacion(Base):
    __tablename__ = "cotizaciones"

    id             = Column(String(36), primary_key=True, default=_uuid)
    solicitud_id   = Column(String(36), ForeignKey("solicitudes_compra.id"), nullable=False, index=True)
    proveedor_id   = Column(String(36), ForeignKey("proveedores.id"), nullable=False)
    referencia     = Column(String(100), nullable=True)   # n.º/referencia de la cotización (opcional)
    valor_total    = Column(Numeric(14, 2), nullable=True)
    fecha          = Column(Date, nullable=True)
    observaciones  = Column(Text, nullable=True)
    es_ganadora    = Column(Boolean, default=False, index=True)
    # Adjunto (Opción A: en disco; la BD solo guarda la referencia)
    archivo_nombre = Column(String(255), nullable=True)   # nombre original (para mostrar)
    archivo_path   = Column(String(400), nullable=True)   # ruta server-relative (storage/cotizaciones/...)
    archivo_tipo   = Column(String(100), nullable=True)   # mime/categoría
    created_at     = Column(DateTime, server_default=func.now())

    # Relaciones
    solicitud = relationship("SolicitudCompra", back_populates="cotizaciones")
    proveedor = relationship("Proveedor")


# ── TABLA 3: solicitud_items ──────────────────────────────
class SolicitudItem(Base):
    __tablename__ = "solicitud_items"

    id                      = Column(String(36), primary_key=True, default=_uuid)
    solicitud_id            = Column(String(36), ForeignKey("solicitudes_compra.id"), nullable=False, index=True)
    descripcion             = Column(String(300), nullable=False)
    tipo_item               = Column(String(20), nullable=False)  # activo, accesorio
    tipo_adquisicion        = Column(String(20), nullable=False)  # compra, alquiler
    cantidad                = Column(Integer, nullable=False, default=1)
    valor_unitario_estimado = Column(Numeric(14, 2), nullable=True)
    created_at              = Column(DateTime, server_default=func.now())

    solicitud = relationship("SolicitudCompra", back_populates="items")


# ── TABLA 4: ordenes_compra ───────────────────────────────
class OrdenCompra(Base):
    __tablename__ = "ordenes_compra"

    id                     = Column(String(36), primary_key=True, default=_uuid)
    solicitud_id           = Column(String(36), ForeignKey("solicitudes_compra.id"), nullable=False, index=True)
    proveedor_id           = Column(String(36), ForeignKey("proveedores.id"), nullable=False)
    empresa_id             = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    numero_oc              = Column(String(50), nullable=True)   # número del sistema, auto: OC-YYYY-NNN
    numero_orden_erp       = Column(String(100), nullable=True)  # n.º de orden del ERP/contable (opcional, editable)
    tipo                   = Column(String(20), nullable=False)  # compra, alquiler
    fecha_emision          = Column(Date, nullable=False)
    fecha_entrega_esperada = Column(Date, nullable=True)
    valor_total            = Column(Numeric(14, 2), nullable=True)
    estado                 = Column(String(20), default="emitida", index=True)
    # emitida, parcialmente_recibida, recibida, cancelada
    observaciones          = Column(Text, nullable=True)
    # Campos de alquiler (solo aplican si tipo == "alquiler")
    fecha_inicio_alquiler  = Column(Date, nullable=True)
    fecha_fin_alquiler     = Column(Date, nullable=True)
    valor_mensual_alquiler = Column(Numeric(14, 2), nullable=True)
    created_at             = Column(DateTime, server_default=func.now())
    updated_at             = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones externas
    empresa = relationship("Empresa")

    # Relaciones internas
    solicitud        = relationship("SolicitudCompra", back_populates="ordenes")
    proveedor        = relationship("Proveedor", back_populates="ordenes")
    facturas         = relationship("Factura", back_populates="orden_compra")
    recepciones      = relationship("Recepcion", back_populates="orden_compra")
    contrato_alquiler = relationship("ContratoAlquiler", back_populates="orden_compra",
                                     uselist=False)


# ── TABLA 5: facturas ─────────────────────────────────────
class Factura(Base):
    __tablename__ = "facturas"

    id                = Column(String(36), primary_key=True, default=_uuid)
    orden_compra_id   = Column(String(36), ForeignKey("ordenes_compra.id"), nullable=False, index=True)
    empresa_id        = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    proveedor_id      = Column(String(36), ForeignKey("proveedores.id"), nullable=False)
    numero_factura    = Column(String(100), nullable=False)
    fecha_factura     = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=True)
    subtotal          = Column(Numeric(14, 2), nullable=True)
    iva               = Column(Numeric(14, 2), nullable=True)
    valor_total       = Column(Numeric(14, 2), nullable=False)
    estado            = Column(String(20), default="pendiente", index=True)
    # pendiente, pagada, vencida, anulada
    url_pdf           = Column(String(300), nullable=True)
    observaciones     = Column(Text, nullable=True)
    created_at        = Column(DateTime, server_default=func.now())

    # Relaciones externas
    empresa = relationship("Empresa")

    # Relaciones internas
    orden_compra = relationship("OrdenCompra", back_populates="facturas")
    proveedor    = relationship("Proveedor", back_populates="facturas")


# ── TABLA 6: recepciones ──────────────────────────────────
class Recepcion(Base):
    __tablename__ = "recepciones"

    id              = Column(String(36), primary_key=True, default=_uuid)
    orden_compra_id = Column(String(36), ForeignKey("ordenes_compra.id"), nullable=False, index=True)
    empresa_id      = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    recibido_por_id = Column(String(36), ForeignKey("usuarios_sistema.id"), nullable=False)
    fecha_recepcion = Column(Date, nullable=False)
    estado          = Column(String(30), default="pendiente")
    # pendiente, recibida_parcial, recibida_completa, con_novedad
    observaciones   = Column(Text, nullable=True)
    novedades       = Column(Text, nullable=True)
    created_at      = Column(DateTime, server_default=func.now())

    # Relaciones externas
    empresa      = relationship("Empresa")
    recibido_por = relationship("UsuarioSistema")

    # Relaciones internas
    orden_compra = relationship("OrdenCompra", back_populates="recepciones")
    items        = relationship("RecepcionItem", back_populates="recepcion",
                               cascade="all, delete-orphan")


# ── TABLA 7: recepcion_items ──────────────────────────────
class RecepcionItem(Base):
    __tablename__ = "recepcion_items"

    id                  = Column(String(36), primary_key=True, default=_uuid)
    recepcion_id        = Column(String(36), ForeignKey("recepciones.id"), nullable=False, index=True)
    solicitud_item_id   = Column(String(36), ForeignKey("solicitud_items.id"), nullable=True)
    descripcion         = Column(String(300), nullable=False)
    cantidad_esperada   = Column(Integer, nullable=False)
    cantidad_recibida   = Column(Integer, nullable=False, default=0)
    estado              = Column(String(20), default="pendiente")
    # ok, dañado, incompleto, no_recibido
    serial              = Column(String(100), nullable=True)
    observacion         = Column(String(300), nullable=True)
    activo_creado_id    = Column(String(36), ForeignKey("activos.id"), nullable=True)
    accesorio_creado_id = Column(String(36), ForeignKey("accesorios.id"), nullable=True)

    # Relaciones internas / externas (unidireccionales)
    recepcion       = relationship("Recepcion", back_populates="items")
    solicitud_item  = relationship("SolicitudItem")
    activo_creado   = relationship("Activo")
    accesorio_creado = relationship("Accesorio")
    creados         = relationship("RecepcionItemCreado", back_populates="recepcion_item",
                                   cascade="all, delete-orphan")


# ── TABLA 7b: recepcion_items_creados ─────────────────────
# Cada unidad de inventario (activo/accesorio) creada a partir de un ítem de
# recepción. Un ítem con cantidad_recibida=5 genera 5 filas aquí. El conteo de
# filas por recepcion_item = unidades ya creadas (las pendientes = recibida - creadas).
class RecepcionItemCreado(Base):
    __tablename__ = "recepcion_items_creados"

    id                = Column(String(36), primary_key=True, default=_uuid)
    recepcion_item_id = Column(String(36), ForeignKey("recepcion_items.id"), nullable=False, index=True)
    tipo_recurso      = Column(String(20), nullable=False)   # "activo" | "accesorio"
    recurso_id        = Column(String(36), nullable=False)   # id del activo/accesorio creado
    placa             = Column(String(50), nullable=True)
    created_at        = Column(DateTime, server_default=func.now())

    recepcion_item = relationship("RecepcionItem", back_populates="creados")


# ── TABLA 9: contratos_alquiler ───────────────────────────
class ContratoAlquiler(Base):
    __tablename__ = "contratos_alquiler"

    id                       = Column(String(36), primary_key=True, default=_uuid)
    orden_compra_id          = Column(String(36), ForeignKey("ordenes_compra.id"),
                                       nullable=False, unique=True)  # 1:1 con la OC
    empresa_id               = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    proveedor_id             = Column(String(36), ForeignKey("proveedores.id"), nullable=False)
    # Un contrato cubre MUCHOS equipos: el vínculo vive en el equipo
    # (Activo/Accesorio.contrato_alquiler_id), no aquí.
    fecha_inicio             = Column(Date, nullable=False)
    fecha_fin                = Column(Date, nullable=False)
    valor_mensual            = Column(Numeric(14, 2), nullable=False)
    valor_total_contrato     = Column(Numeric(14, 2), nullable=True)
    estado                   = Column(String(20), default="activo", index=True)
    # activo, vencido, terminado_anticipado
    fecha_devolucion_real    = Column(Date, nullable=True)
    observaciones_devolucion = Column(Text, nullable=True)
    created_at               = Column(DateTime, server_default=func.now())
    updated_at               = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # Relaciones externas
    empresa   = relationship("Empresa")
    # Equipos cubiertos por el contrato (uno-a-muchos vía contrato_alquiler_id)
    activos    = relationship("Activo",    foreign_keys="Activo.contrato_alquiler_id")
    accesorios = relationship("Accesorio", foreign_keys="Accesorio.contrato_alquiler_id")

    # Relaciones internas
    orden_compra = relationship("OrdenCompra", back_populates="contrato_alquiler")
    proveedor    = relationship("Proveedor", back_populates="contratos")
