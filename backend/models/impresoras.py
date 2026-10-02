from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import uuid


class Impresora(Base):
    """Impresora ALQUILADA (rentada) — inventario aparte (como servidores/redes),
    NO es un activo. Fase 1: inventario + catálogo ciudad.

    - empresa_id: empresa-scoped como todo módulo.
    - sede_catalogo_id: reutiliza el catálogo per-empresa Catalogo categoria='sede'.
    - ciudad_catalogo_id: catálogo GLOBAL Catalogo categoria='ciudad'.
    - proveedor_id: catálogo GLOBAL de proveedores (flag modulo='impresoras').
    Fase 2 añadirá reemplazo-con-historial (reemplaza_a / tabla de historial) — el
    PK UUID estable deja espacio para engancharlo sin migraciones extra. NO se
    construye reemplazo ahora.
    """
    __tablename__ = "impresoras"

    id                 = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    empresa_id         = Column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    sede_catalogo_id   = Column(String(36), ForeignKey("catalogos.id"), nullable=True, index=True)   # categoria='sede' (per-empresa)
    ciudad_catalogo_id = Column(String(36), ForeignKey("catalogos.id"), nullable=True, index=True)   # categoria='ciudad' (global)
    dependencia        = Column(String(150), nullable=True)
    modelo             = Column(String(150), nullable=True)
    tipo               = Column(String(20),  nullable=True)   # color | monocromatica
    serial             = Column(String(100), nullable=True, index=True)
    ip                 = Column(String(45),  nullable=True)
    estado             = Column(String(20),  nullable=False, default="en_servicio", server_default="en_servicio")
    # en_servicio | inactiva | en_reparacion  (fase 2 añadirá 'reemplazada')
    correo_escaneo     = Column(String(150), nullable=True)
    proveedor_id       = Column(String(36), ForeignKey("proveedores.id"), nullable=True, index=True)
    activo             = Column(Boolean, nullable=False, default=True, server_default="1")  # soft-delete
    created_at         = Column(DateTime, server_default=func.now())
    created_by         = Column(String(36), nullable=True)

    # ── Fase 2: reemplazo-con-historial ──
    # La NUEVA impresora apunta a la que reemplaza (self-FK). La VIEJA guarda el
    # motivo/fecha/autor del reemplazo y pasa a estado='reemplazada' (terminal).
    reemplaza_a        = Column(String(36), ForeignKey("impresoras.id"), nullable=True, index=True)
    motivo_reemplazo   = Column(String(300), nullable=True)
    reemplazado_at     = Column(DateTime, nullable=True)
    reemplazado_by     = Column(String(36), nullable=True)

    empresa   = relationship("Empresa")
    # Dos FKs a catalogos → foreign_keys explícito para desambiguar el join.
    sede      = relationship("Catalogo", foreign_keys=[sede_catalogo_id])
    ciudad    = relationship("Catalogo", foreign_keys=[ciudad_catalogo_id])
    proveedor = relationship("Proveedor")
    # Self-FK: la impresora que ESTA reemplaza (la vieja). remote_side desambigua.
    anterior  = relationship("Impresora", remote_side=[id], foreign_keys=[reemplaza_a])
