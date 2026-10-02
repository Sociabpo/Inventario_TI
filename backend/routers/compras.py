"""
Router del módulo Gestión de Compras y Facturas.
Prefix: /api/compras

Flujo: Solicitud → (aprobación) → Orden de Compra → Factura / Recepción
       → crear inventario (Activo/Accesorio) → Garantía / Contrato de Alquiler.

Todas las listas aplican el filtro multiempresa get_user_empresa_ids()
(mismo patrón que activos.py).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import date, datetime, timedelta
import json

from database import get_db
from models.activo import Activo
from models.accesorio import Accesorio
from models.usuario_sistema import UsuarioSistema
from models.compra import (
    Proveedor, SolicitudCompra, SolicitudItem, OrdenCompra,
    Factura, Recepcion, RecepcionItem, RecepcionItemCreado, ContratoAlquiler,
    Cotizacion,
)
from services.upload_service import guardar_adjunto, ruta_absoluta, eliminar_adjunto
from models.historial import HistorialMovimiento
from models.baja_activo import BajaActivo
from dependencies.rbac import require_permission, require_any_permission
from services.rbac_service import get_user_empresa_ids, user_has_empresa_access
from services.consecutivo_service import generar_placa_activo, generar_placa_accesorio, generar_numero_documento
from services.inventario_service import crear_activo_core, crear_accesorio_core, validar_catalogo_o_400
from routers.activos import ActivoCreate
from routers.accesorios import AccesorioCreate

router = APIRouter(prefix="/api/compras", tags=["Compras"])


# ══════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════
def _scope_empresa(query, model, db: Session, current_user, empresa_id: Optional[str]):
    """Aplica el filtro multiempresa estándar a una query sobre `model`."""
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(model.empresa_id == empresa_id)
        else:
            query = query.filter(model.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(model.empresa_id == empresa_id)
    return query


def _check_empresa_acceso(db: Session, current_user, empresa_id: str):
    """Valida que el usuario pueda escribir en esa empresa (super_admin siempre pasa)."""
    if not user_has_empresa_access(db, current_user.id, empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")


def _f(v):
    """Numeric → float seguro."""
    return float(v) if v is not None else None


def _nombre_us(db: Session, us_id: Optional[str]) -> Optional[str]:
    if not us_id:
        return None
    u = db.query(UsuarioSistema).filter(UsuarioSistema.id == us_id).first()
    return u.nombre if u else None


# ══════════════════════════════════════════════════════════
#  PROVEEDORES
# ══════════════════════════════════════════════════════════
class ProveedorIn(BaseModel):
    # Proveedor GLOBAL: sin empresa_id.
    nombre: str
    nit: Optional[str] = None
    tipo: str = "vendedor"
    contacto_nombre: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    ciudad: Optional[str] = None
    modulos: Optional[List[str]] = None   # catálogo compartido; None → ["compras"]
    activo: Optional[bool] = True


class ProveedorUpdate(BaseModel):
    nombre: Optional[str] = None
    nit: Optional[str] = None
    tipo: Optional[str] = None
    contacto_nombre: Optional[str] = None
    telefono: Optional[str] = None
    correo: Optional[str] = None
    ciudad: Optional[str] = None
    modulos: Optional[List[str]] = None
    activo: Optional[bool] = None


def _proveedor_dict(p: Proveedor) -> dict:
    return {
        "id": p.id, "nombre": p.nombre, "nit": p.nit,
        "tipo": p.tipo, "contacto_nombre": p.contacto_nombre, "telefono": p.telefono,
        "correo": p.correo, "ciudad": p.ciudad, "activo": p.activo,
        "modulos": p.modulos_list,
    }


@router.get("/proveedores")
def listar_proveedores(
    tipo: Optional[str] = None,
    activo: Optional[bool] = None,
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    # Proveedores GLOBALES: sin filtro por empresa. (Un ?empresa_id= entrante se ignora.)
    query = db.query(Proveedor)
    if tipo:
        query = query.filter(Proveedor.tipo == tipo)
    if activo is not None:
        query = query.filter(Proveedor.activo == activo)
    if q:
        query = query.filter(or_(
            Proveedor.nombre.ilike(f"%{q}%"),
            Proveedor.nit.ilike(f"%{q}%"),
        ))
    return [_proveedor_dict(p) for p in query.order_by(Proveedor.nombre).all()]


@router.post("/proveedores", status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    data: ProveedorIn,
    db: Session = Depends(get_db),
    current_user = require_permission("proveedores.gestionar"),
):
    if data.nit:
        dup = db.query(Proveedor).filter(Proveedor.nit == data.nit).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Ya existe un proveedor con NIT {data.nit}")
    payload = data.model_dump(exclude={"modulos"})
    # Creado desde la superficie de compras → por defecto aplica a compras.
    payload["modulos"] = json.dumps(data.modulos if data.modulos else ["compras"])
    p = Proveedor(**payload)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _proveedor_dict(p)


@router.get("/proveedores/{proveedor_id}")
def obtener_proveedor(
    proveedor_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return _proveedor_dict(p)


@router.put("/proveedores/{proveedor_id}")
def actualizar_proveedor(
    proveedor_id: str,
    data: ProveedorUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("proveedores.gestionar"),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if campo == "modulos":
            # lista → JSON string (columna Text). None deja el valor actual sin tocar.
            if valor is not None:
                p.modulos = json.dumps(valor)
            continue
        setattr(p, campo, valor)
    db.commit()
    db.refresh(p)
    return _proveedor_dict(p)


# ══════════════════════════════════════════════════════════
#  SOLICITUDES
# ══════════════════════════════════════════════════════════
class SolicitudItemIn(BaseModel):
    descripcion: str
    tipo_item: str               # activo, accesorio
    tipo_adquisicion: str        # compra, alquiler
    cantidad: int = 1
    valor_unitario_estimado: Optional[float] = None


class SolicitudIn(BaseModel):
    empresa_id: str
    titulo: str
    justificacion: str
    sede: str                      # requerida — validada contra el catálogo de la empresa
    area: str                      # requerida — validada contra el catálogo de la empresa
    observaciones: Optional[str] = None
    items: List[SolicitudItemIn] = []


class AprobarIn(BaseModel):
    observaciones: Optional[str] = None


class RechazarIn(BaseModel):
    motivo_rechazo: str


class CancelarIn(BaseModel):
    motivo_cancelacion: str


def _generar_numero_solicitud(db: Session, empresa_id: str) -> str:
    """'SC-{YYYY}-{NNN}' robusto vía Consecutivo (SELECT FOR UPDATE), por empresa+año."""
    return generar_numero_documento(db, empresa_id, "SOLICITUD", "SC")


def _item_dict(i: SolicitudItem) -> dict:
    return {
        "id": i.id, "descripcion": i.descripcion, "tipo_item": i.tipo_item,
        "tipo_adquisicion": i.tipo_adquisicion, "cantidad": i.cantidad,
        "valor_unitario_estimado": _f(i.valor_unitario_estimado),
    }


def _cotizacion_dict(c: Cotizacion) -> dict:
    return {
        "id": c.id, "solicitud_id": c.solicitud_id, "proveedor_id": c.proveedor_id,
        "proveedor": c.proveedor.nombre if c.proveedor else None,
        "referencia": c.referencia, "valor_total": _f(c.valor_total),
        "fecha": c.fecha, "observaciones": c.observaciones,
        "es_ganadora": bool(c.es_ganadora),
        "archivo_nombre": c.archivo_nombre,
        "tiene_archivo": bool(c.archivo_path),
        "archivo_tipo": c.archivo_tipo,
        "created_at": c.created_at,
    }


def _solicitud_dict(s: SolicitudCompra, db: Session, full: bool = False) -> dict:
    ganadora = next((c for c in s.cotizaciones if c.es_ganadora), None)
    base = {
        "id": s.id, "empresa_id": s.empresa_id,
        "numero_solicitud": s.numero_solicitud, "titulo": s.titulo,
        "justificacion": s.justificacion,
        "sede": s.sede, "area": s.area,
        "estado": s.estado, "observaciones": s.observaciones,
        "solicitante_id": s.solicitante_id, "solicitante": _nombre_us(db, s.solicitante_id),
        "aprobado_por_id": s.aprobado_por_id, "aprobado_por": _nombre_us(db, s.aprobado_por_id),
        "fecha_aprobacion": s.fecha_aprobacion, "motivo_rechazo": s.motivo_rechazo,
        "motivo_cancelacion": s.motivo_cancelacion,
        "nombre_empresa": s.empresa.nombre_empresa if s.empresa else None,
        "items_count": len(s.items),
        "cotizaciones_count": len(s.cotizaciones),
        "tiene_ganadora": ganadora is not None,
        "cotizacion_ganadora_id": ganadora.id if ganadora else None,
        "created_at": s.created_at,
    }
    if full:
        base["items"] = [_item_dict(i) for i in s.items]
        base["ordenes"] = [_orden_dict(o) for o in s.ordenes]
        base["cotizaciones"] = [_cotizacion_dict(c) for c in s.cotizaciones]
        base["recepciones"] = [
            _recepcion_dict(r) for o in s.ordenes for r in o.recepciones
        ]
    return base


@router.get("/solicitudes")
def listar_solicitudes(
    estado: Optional[str] = None,
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    query = _scope_empresa(db.query(SolicitudCompra), SolicitudCompra, db, current_user, empresa_id)
    if estado:
        query = query.filter(SolicitudCompra.estado == estado)
    rows = query.order_by(SolicitudCompra.created_at.desc()).all()
    return [_solicitud_dict(s, db) for s in rows]


@router.post("/solicitudes", status_code=status.HTTP_201_CREATED)
def crear_solicitud(
    data: SolicitudIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    _check_empresa_acceso(db, current_user, data.empresa_id)
    if not data.titulo or not data.titulo.strip():
        raise HTTPException(status_code=400, detail="El título es obligatorio")
    if not data.sede or not data.sede.strip():
        raise HTTPException(status_code=400, detail="La sede es obligatoria")
    if not data.area or not data.area.strip():
        raise HTTPException(status_code=400, detail="El área es obligatoria")
    sede = validar_catalogo_o_400(db, data.empresa_id, "sede", data.sede, "La sede")
    area = validar_catalogo_o_400(db, data.empresa_id, "area", data.area, "El área")
    s = SolicitudCompra(
        empresa_id=data.empresa_id,
        numero_solicitud=_generar_numero_solicitud(db, data.empresa_id),
        titulo=data.titulo.strip(),
        sede=sede,
        area=area,
        solicitante_id=current_user.id,
        justificacion=data.justificacion,
        observaciones=data.observaciones,
        estado="borrador",
    )
    db.add(s)
    db.flush()
    for it in data.items:
        db.add(SolicitudItem(
            solicitud_id=s.id, descripcion=it.descripcion, tipo_item=it.tipo_item,
            tipo_adquisicion=it.tipo_adquisicion, cantidad=it.cantidad,
            valor_unitario_estimado=it.valor_unitario_estimado,
        ))
    db.commit()
    db.refresh(s)
    return _solicitud_dict(s, db, full=True)


class SolicitudEditIn(BaseModel):
    titulo: Optional[str] = None
    justificacion: Optional[str] = None
    sede: Optional[str] = None
    area: Optional[str] = None
    observaciones: Optional[str] = None
    items: Optional[List[SolicitudItemIn]] = None


@router.put("/solicitudes/{solicitud_id}")
def editar_solicitud(
    solicitud_id: str,
    data: SolicitudEditIn,
    db: Session = Depends(get_db),
    current_user = require_any_permission("compras.crear_solicitud", "compras.aprobar"),
):
    """
    Edita justificación, observaciones y/o ítems de una solicitud.
    Permitido mientras no exista una orden de compra (estados:
    borrador, pendiente_aprobacion, aprobada).
    """
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    if s.estado not in ("borrador", "pendiente_aprobacion", "aprobada"):
        raise HTTPException(status_code=400, detail=f"No se puede editar una solicitud en estado '{s.estado}'")
    if s.ordenes:
        raise HTTPException(status_code=400, detail="La solicitud ya tiene una orden de compra; no se puede editar")

    if data.titulo is not None:
        if not data.titulo.strip():
            raise HTTPException(status_code=400, detail="El título no puede quedar vacío")
        s.titulo = data.titulo.strip()
    if data.justificacion is not None:
        if not data.justificacion.strip():
            raise HTTPException(status_code=400, detail="La justificación no puede quedar vacía")
        s.justificacion = data.justificacion.strip()
    if data.sede is not None:
        if not data.sede.strip():
            raise HTTPException(status_code=400, detail="La sede no puede quedar vacía")
        s.sede = validar_catalogo_o_400(db, s.empresa_id, "sede", data.sede, "La sede")
    if data.area is not None:
        if not data.area.strip():
            raise HTTPException(status_code=400, detail="El área no puede quedar vacía")
        s.area = validar_catalogo_o_400(db, s.empresa_id, "area", data.area, "El área")
    if data.observaciones is not None:
        s.observaciones = data.observaciones
    if data.items is not None:
        if not data.items:
            raise HTTPException(status_code=400, detail="La solicitud debe tener al menos un ítem")
        for it in list(s.items):
            db.delete(it)
        db.flush()
        for it in data.items:
            db.add(SolicitudItem(
                solicitud_id=s.id, descripcion=it.descripcion, tipo_item=it.tipo_item,
                tipo_adquisicion=it.tipo_adquisicion, cantidad=it.cantidad,
                valor_unitario_estimado=it.valor_unitario_estimado,
            ))
    db.commit()
    db.refresh(s)
    return _solicitud_dict(s, db, full=True)


@router.get("/solicitudes/{solicitud_id}")
def obtener_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    return _solicitud_dict(s, db, full=True)


@router.put("/solicitudes/{solicitud_id}/enviar")
def enviar_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    if s.estado != "borrador":
        raise HTTPException(status_code=400, detail=f"Solo se puede enviar una solicitud en borrador (estado actual: {s.estado})")
    if not s.items:
        raise HTTPException(status_code=400, detail="La solicitud no tiene ítems")
    # La aprobación se decide sobre cotizaciones: exige ≥1 y una ganadora marcada
    if not s.cotizaciones:
        raise HTTPException(status_code=400, detail="Agrega al menos una cotización antes de enviar a aprobación")
    if not any(c.es_ganadora for c in s.cotizaciones):
        raise HTTPException(status_code=400, detail="Marca una cotización como ganadora antes de enviar a aprobación")
    s.estado = "pendiente_aprobacion"
    db.commit()
    db.refresh(s)
    return _solicitud_dict(s, db, full=True)


@router.post("/solicitudes/{solicitud_id}/aprobar")
def aprobar_solicitud(
    solicitud_id: str,
    data: AprobarIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.aprobar"),
):
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    if s.estado != "pendiente_aprobacion":
        raise HTTPException(status_code=400, detail=f"Solo se aprueba una solicitud pendiente (estado actual: {s.estado})")
    s.estado = "aprobada"
    s.aprobado_por_id = current_user.id
    s.fecha_aprobacion = datetime.now()
    if data.observaciones:
        s.observaciones = data.observaciones
    db.commit()
    db.refresh(s)
    return _solicitud_dict(s, db, full=True)


@router.post("/solicitudes/{solicitud_id}/rechazar")
def rechazar_solicitud(
    solicitud_id: str,
    data: RechazarIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.aprobar"),
):
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    if s.estado != "pendiente_aprobacion":
        raise HTTPException(status_code=400, detail=f"Solo se rechaza una solicitud pendiente (estado actual: {s.estado})")
    if not data.motivo_rechazo or not data.motivo_rechazo.strip():
        raise HTTPException(status_code=400, detail="El motivo de rechazo es obligatorio")
    s.estado = "rechazada"
    s.motivo_rechazo = data.motivo_rechazo.strip()
    s.aprobado_por_id = current_user.id
    s.fecha_aprobacion = datetime.now()
    db.commit()
    db.refresh(s)
    return _solicitud_dict(s, db, full=True)


@router.post("/solicitudes/{solicitud_id}/cancelar")
def cancelar_solicitud(
    solicitud_id: str,
    data: CancelarIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    if s.estado not in ("borrador", "pendiente_aprobacion"):
        if s.estado in ("aprobada", "en_proceso", "recibida", "completada"):
            raise HTTPException(status_code=400, detail="No se puede cancelar una solicitud ya aprobada")
        raise HTTPException(status_code=400, detail=f"No se puede cancelar una solicitud en estado '{s.estado}'")
    if not data.motivo_cancelacion or not data.motivo_cancelacion.strip():
        raise HTTPException(status_code=400, detail="El motivo de cancelación es obligatorio")
    s.estado = "cancelada"
    s.motivo_cancelacion = data.motivo_cancelacion.strip()
    db.commit()
    db.refresh(s)
    return _solicitud_dict(s, db, full=True)


@router.post("/solicitudes/{solicitud_id}/completar")
def completar_solicitud(
    solicitud_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    """Marca la solicitud como 'completada' manualmente. Pensado para cuando los
    recursos se crearon FUERA del módulo de compras (directamente en activos/
    accesorios) y el disparador automático no se activó. Permitido desde
    'recibida', 'en_proceso' o 'aprobada'."""
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    if s.estado == "completada":
        raise HTTPException(status_code=400, detail="La solicitud ya está completada")
    if s.estado not in ("recibida", "en_proceso", "aprobada"):
        raise HTTPException(
            status_code=400,
            detail=f"Solo se puede completar una solicitud aprobada, en proceso o recibida (estado actual: {s.estado})")
    s.estado = "completada"
    db.commit()
    db.refresh(s)
    return _solicitud_dict(s, db, full=True)


# ══════════════════════════════════════════════════════════
#  COTIZACIONES  (etapa temprana: solicitud borrador → documentar cotizaciones)
# ══════════════════════════════════════════════════════════
def _get_cotizacion_o_404(db: Session, cotizacion_id: str, current_user) -> Cotizacion:
    c = db.query(Cotizacion).filter(Cotizacion.id == cotizacion_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cotización no encontrada")
    _check_empresa_acceso(db, current_user, c.solicitud.empresa_id)
    return c


@router.get("/solicitudes/{solicitud_id}/cotizaciones")
def listar_cotizaciones(
    solicitud_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    return [_cotizacion_dict(c) for c in s.cotizaciones]


@router.post("/solicitudes/{solicitud_id}/cotizaciones", status_code=status.HTTP_201_CREATED)
def crear_cotizacion(
    solicitud_id: str,
    proveedor_id: str = Form(...),
    valor_total: Optional[float] = Form(None),
    referencia: Optional[str] = Form(None),
    fecha: Optional[date] = Form(None),
    observaciones: Optional[str] = Form(None),
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    """Agrega una cotización (con adjunto) a una solicitud en borrador."""
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    if s.estado != "borrador":
        raise HTTPException(status_code=400, detail=f"Solo se pueden agregar cotizaciones en borrador (estado actual: {s.estado})")

    prov = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not prov:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    # Proveedores GLOBALES: cualquier empresa puede cotizar con cualquier proveedor.

    # Guarda el adjunto en disco (valida tipo + tamaño); la BD solo la referencia
    prefijo = s.empresa.prefijo if s.empresa else s.empresa_id
    info = guardar_adjunto(archivo, "cotizaciones", prefijo)

    c = Cotizacion(
        solicitud_id=s.id, proveedor_id=proveedor_id, referencia=referencia,
        valor_total=valor_total, fecha=fecha, observaciones=observaciones,
        es_ganadora=False,
        archivo_nombre=info["archivo_nombre"], archivo_path=info["archivo_path"],
        archivo_tipo=info["archivo_tipo"],
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _cotizacion_dict(c)


@router.post("/cotizaciones/{cotizacion_id}/ganadora")
def marcar_ganadora(
    cotizacion_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    """Marca esta cotización como ganadora; limpia cualquier ganadora previa de
    la misma solicitud (exactamente una ganadora). Solo en borrador."""
    c = _get_cotizacion_o_404(db, cotizacion_id, current_user)
    if c.solicitud.estado != "borrador":
        raise HTTPException(status_code=400, detail=f"Solo se puede cambiar la ganadora en borrador (estado actual: {c.solicitud.estado})")
    for otra in c.solicitud.cotizaciones:
        otra.es_ganadora = (otra.id == c.id)
    db.commit()
    db.refresh(c)
    return _cotizacion_dict(c)


@router.delete("/cotizaciones/{cotizacion_id}")
def eliminar_cotizacion(
    cotizacion_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    """Elimina una cotización y su adjunto del disco. Solo en borrador."""
    c = _get_cotizacion_o_404(db, cotizacion_id, current_user)
    if c.solicitud.estado != "borrador":
        raise HTTPException(status_code=400, detail=f"Solo se pueden eliminar cotizaciones en borrador (estado actual: {c.solicitud.estado})")
    ruta = c.archivo_path
    db.delete(c)
    db.commit()
    eliminar_adjunto(ruta)   # borra el archivo tras confirmar el commit
    return {"mensaje": "Cotización eliminada"}


@router.get("/cotizaciones/{cotizacion_id}/archivo")
def descargar_cotizacion(
    cotizacion_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    """Descarga/stream del adjunto, gated por permiso + acceso a la empresa.
    Nunca expone la ruta cruda del filesystem al cliente."""
    c = _get_cotizacion_o_404(db, cotizacion_id, current_user)
    if not c.archivo_path:
        raise HTTPException(status_code=404, detail="Esta cotización no tiene adjunto")
    abs_path = ruta_absoluta(c.archivo_path)
    return FileResponse(
        path=str(abs_path),
        filename=c.archivo_nombre or "cotizacion",
        media_type=c.archivo_tipo or "application/octet-stream",
    )


# ══════════════════════════════════════════════════════════
#  ORDENES DE COMPRA
# ══════════════════════════════════════════════════════════
class OrdenIn(BaseModel):
    solicitud_id: str
    # proveedor/valor opcionales: si no vienen, se heredan de la cotización ganadora
    proveedor_id: Optional[str] = None
    numero_orden_erp: Optional[str] = None   # n.º de orden del ERP/contable (opcional)
    tipo: str                              # compra, alquiler
    fecha_emision: date
    fecha_entrega_esperada: Optional[date] = None
    valor_total: Optional[float] = None
    observaciones: Optional[str] = None
    fecha_inicio_alquiler: Optional[date] = None
    fecha_fin_alquiler: Optional[date] = None
    valor_mensual_alquiler: Optional[float] = None


def _orden_dict(o: OrdenCompra, db: Optional[Session] = None, full: bool = False) -> dict:
    base = {
        "id": o.id, "solicitud_id": o.solicitud_id, "proveedor_id": o.proveedor_id,
        "empresa_id": o.empresa_id, "numero_oc": o.numero_oc,
        "numero_orden_erp": o.numero_orden_erp,
        "numero_solicitud": o.solicitud.numero_solicitud if o.solicitud else None,  # origen (trazabilidad)
        "tipo": o.tipo,
        "fecha_emision": o.fecha_emision, "fecha_entrega_esperada": o.fecha_entrega_esperada,
        "valor_total": _f(o.valor_total), "estado": o.estado, "observaciones": o.observaciones,
        "fecha_inicio_alquiler": o.fecha_inicio_alquiler, "fecha_fin_alquiler": o.fecha_fin_alquiler,
        "valor_mensual_alquiler": _f(o.valor_mensual_alquiler),
        "proveedor": o.proveedor.nombre if o.proveedor else None,
        "nombre_empresa": o.empresa.nombre_empresa if o.empresa else None,
        "created_at": o.created_at,
    }
    if full:
        base["facturas"] = [_factura_dict(f) for f in o.facturas]
        base["recepciones"] = [_recepcion_dict(r, full=True) for r in o.recepciones]
        base["contrato_alquiler"] = _contrato_dict(o.contrato_alquiler) if o.contrato_alquiler else None
    return base


@router.get("/ordenes")
def listar_ordenes(
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    query = _scope_empresa(db.query(OrdenCompra), OrdenCompra, db, current_user, empresa_id)
    if estado:
        query = query.filter(OrdenCompra.estado == estado)
    if tipo:
        query = query.filter(OrdenCompra.tipo == tipo)
    rows = query.order_by(OrdenCompra.created_at.desc()).all()
    return [_orden_dict(o) for o in rows]


@router.post("/ordenes", status_code=status.HTTP_201_CREATED)
def crear_orden(
    data: OrdenIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    s = db.query(SolicitudCompra).filter(SolicitudCompra.id == data.solicitud_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    _check_empresa_acceso(db, current_user, s.empresa_id)
    if s.estado not in ("aprobada", "en_proceso"):
        raise HTTPException(status_code=400, detail=f"La solicitud debe estar aprobada (estado actual: {s.estado})")

    # Herencia de la cotización ganadora (prefill; el form puede sobreescribir)
    ganadora = next((c for c in s.cotizaciones if c.es_ganadora), None)
    proveedor_id = data.proveedor_id or (ganadora.proveedor_id if ganadora else None)
    valor_total = data.valor_total if data.valor_total is not None else (
        _f(ganadora.valor_total) if ganadora else None)
    if not proveedor_id:
        raise HTTPException(status_code=400, detail="Falta el proveedor (no hay cotización ganadora de la cual heredarlo)")

    prov = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not prov:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    # Proveedores GLOBALES: cualquier empresa puede emitir órdenes a cualquier proveedor.

    o = OrdenCompra(
        solicitud_id=s.id, proveedor_id=proveedor_id, empresa_id=s.empresa_id,
        numero_oc=generar_numero_documento(db, s.empresa_id, "ORDEN", "OC"),  # auto, robusto
        numero_orden_erp=data.numero_orden_erp,
        tipo=data.tipo, fecha_emision=data.fecha_emision,
        fecha_entrega_esperada=data.fecha_entrega_esperada, valor_total=valor_total,
        observaciones=data.observaciones, estado="emitida",
        fecha_inicio_alquiler=data.fecha_inicio_alquiler,
        fecha_fin_alquiler=data.fecha_fin_alquiler,
        valor_mensual_alquiler=data.valor_mensual_alquiler,
    )
    db.add(o)
    s.estado = "en_proceso"
    db.commit()
    db.refresh(o)
    return _orden_dict(o, db, full=True)


@router.get("/ordenes/{orden_id}")
def obtener_orden(
    orden_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    o = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    _check_empresa_acceso(db, current_user, o.empresa_id)
    return _orden_dict(o, db, full=True)


class OrdenErpUpdate(BaseModel):
    numero_orden_erp: Optional[str] = None   # n.º de orden del ERP (opcional; None/"" lo limpia)


@router.put("/ordenes/{orden_id}")
def actualizar_orden_erp(
    orden_id: str,
    data: OrdenErpUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_solicitud"),
):
    """Actualiza ÚNICAMENTE el número de orden del ERP (referencia externa, a
    menudo conocida después). Permitido en cualquier estado de la OC — es solo
    una anotación de referencia. No toca ningún otro campo."""
    o = db.query(OrdenCompra).filter(OrdenCompra.id == orden_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    _check_empresa_acceso(db, current_user, o.empresa_id)
    valor = (data.numero_orden_erp or "").strip()
    o.numero_orden_erp = valor or None
    db.commit()
    db.refresh(o)
    return _orden_dict(o, db, full=True)


# ══════════════════════════════════════════════════════════
#  FACTURAS
# ══════════════════════════════════════════════════════════
class FacturaIn(BaseModel):
    orden_compra_id: str
    numero_factura: str
    fecha_factura: date
    fecha_vencimiento: Optional[date] = None
    subtotal: Optional[float] = None
    iva: Optional[float] = None
    valor_total: float
    observaciones: Optional[str] = None


class FacturaUpdate(BaseModel):
    estado: Optional[str] = None
    observaciones: Optional[str] = None


def _factura_dict(f: Factura) -> dict:
    hoy = date.today()
    vencida_calc = bool(f.fecha_vencimiento and f.fecha_vencimiento < hoy and f.estado not in ("pagada", "anulada"))
    return {
        "id": f.id, "orden_compra_id": f.orden_compra_id, "empresa_id": f.empresa_id,
        "proveedor_id": f.proveedor_id, "numero_factura": f.numero_factura,
        "fecha_factura": f.fecha_factura, "fecha_vencimiento": f.fecha_vencimiento,
        "subtotal": _f(f.subtotal), "iva": _f(f.iva), "valor_total": _f(f.valor_total),
        "estado": f.estado, "url_pdf": f.url_pdf, "observaciones": f.observaciones,
        "proveedor": f.proveedor.nombre if f.proveedor else None,
        "numero_oc": f.orden_compra.numero_oc if f.orden_compra else None,
        "vencida": vencida_calc,
        "created_at": f.created_at,
    }


@router.get("/facturas")
def listar_facturas(
    estado: Optional[str] = None,
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    query = _scope_empresa(db.query(Factura), Factura, db, current_user, empresa_id)
    if estado:
        query = query.filter(Factura.estado == estado)
    rows = query.order_by(Factura.fecha_factura.desc()).all()
    return [_factura_dict(f) for f in rows]


@router.post("/facturas", status_code=status.HTTP_201_CREATED)
def crear_factura(
    data: FacturaIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.gestionar_facturas"),
):
    o = db.query(OrdenCompra).filter(OrdenCompra.id == data.orden_compra_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    _check_empresa_acceso(db, current_user, o.empresa_id)
    f = Factura(
        orden_compra_id=o.id, empresa_id=o.empresa_id, proveedor_id=o.proveedor_id,
        numero_factura=data.numero_factura, fecha_factura=data.fecha_factura,
        fecha_vencimiento=data.fecha_vencimiento, subtotal=data.subtotal, iva=data.iva,
        valor_total=data.valor_total, observaciones=data.observaciones, estado="pendiente",
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return _factura_dict(f)


@router.put("/facturas/{factura_id}")
def actualizar_factura(
    factura_id: str,
    data: FacturaUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.gestionar_facturas"),
):
    f = db.query(Factura).filter(Factura.id == factura_id).first()
    if not f:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    _check_empresa_acceso(db, current_user, f.empresa_id)
    if data.estado is not None:
        if data.estado not in ("pendiente", "pagada", "vencida", "anulada"):
            raise HTTPException(status_code=400, detail="Estado de factura inválido")
        f.estado = data.estado
    if data.observaciones is not None:
        f.observaciones = data.observaciones
    db.commit()
    db.refresh(f)
    return _factura_dict(f)


# ══════════════════════════════════════════════════════════
#  RECEPCIONES
# ══════════════════════════════════════════════════════════
class RecepcionItemIn(BaseModel):
    solicitud_item_id: Optional[str] = None
    descripcion: str
    cantidad_esperada: int
    cantidad_recibida: int = 0
    estado: str = "ok"            # ok, dañado, incompleto, no_recibido
    serial: Optional[str] = None
    observacion: Optional[str] = None


class RecepcionIn(BaseModel):
    orden_compra_id: str
    fecha_recepcion: date
    items: List[RecepcionItemIn] = []
    observaciones: Optional[str] = None
    novedades: Optional[str] = None


class CrearInventarioItem(BaseModel):
    recepcion_item_id: str
    empresa_id: str
    tipo_activo: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serial: Optional[str] = None
    estado: Optional[str] = None
    tipo_accesorio: Optional[str] = None


class CrearInventarioIn(BaseModel):
    items: List[CrearInventarioItem] = []


def _recepcion_item_dict(i: RecepcionItem) -> dict:
    return {
        "id": i.id, "solicitud_item_id": i.solicitud_item_id, "descripcion": i.descripcion,
        "cantidad_esperada": i.cantidad_esperada, "cantidad_recibida": i.cantidad_recibida,
        "estado": i.estado, "serial": i.serial, "observacion": i.observacion,
        "activo_creado_id": i.activo_creado_id, "accesorio_creado_id": i.accesorio_creado_id,
        "procesado": bool(i.activo_creado_id or i.accesorio_creado_id),
    }


def _recepcion_dict(r: Recepcion, full: bool = False) -> dict:
    # Progreso de creación de inventario calculado desde los conteos reales de
    # unidades creadas (RecepcionItemCreado), no desde el estado — así es siempre
    # exacto aunque el estado no se haya actualizado. Ítems elegibles = recibidos
    # OK con cantidad > 0 (misma regla que items-para-inventario / crear-unidad).
    items_inv = [i for i in r.items if i.estado == "ok" and i.cantidad_recibida > 0]
    unidades_totales = sum(i.cantidad_recibida for i in items_inv)
    unidades_creadas = sum(min(len(i.creados), i.cantidad_recibida) for i in items_inv)
    inventario_completo = bool(items_inv) and all(
        len(i.creados) >= i.cantidad_recibida for i in items_inv)

    base = {
        "id": r.id, "orden_compra_id": r.orden_compra_id, "empresa_id": r.empresa_id,
        "recibido_por_id": r.recibido_por_id,
        "recibido_por": r.recibido_por.nombre if r.recibido_por else None,
        "fecha_recepcion": r.fecha_recepcion, "estado": r.estado,
        "observaciones": r.observaciones, "novedades": r.novedades,
        "numero_oc": r.orden_compra.numero_oc if r.orden_compra else None,
        "proveedor": r.orden_compra.proveedor.nombre if (r.orden_compra and r.orden_compra.proveedor) else None,
        "items_count": len(r.items),
        "unidades_totales": unidades_totales,        # unidades a crear (ítems OK)
        "unidades_creadas": unidades_creadas,        # unidades ya creadas
        "inventario_completo": inventario_completo,  # todas las unidades creadas
        "created_at": r.created_at,
    }
    if full:
        base["items"] = [_recepcion_item_dict(i) for i in r.items]
    return base


def _recalcular_estado_orden(o: OrdenCompra):
    """Actualiza el estado de la OC según lo recibido en todas sus recepciones."""
    items = [it for r in o.recepciones for it in r.items]
    if not items:
        return
    total_esp = sum(it.cantidad_esperada for it in items)
    total_rec = sum(it.cantidad_recibida for it in items)
    if total_rec <= 0:
        o.estado = "emitida"
    elif total_rec < total_esp:
        o.estado = "parcialmente_recibida"
    else:
        o.estado = "recibida"


@router.get("/recepciones")
def listar_recepciones(
    estado: Optional[str] = None,
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    query = _scope_empresa(db.query(Recepcion), Recepcion, db, current_user, empresa_id)
    if estado:
        query = query.filter(Recepcion.estado == estado)
    rows = query.order_by(Recepcion.fecha_recepcion.desc()).all()
    return [_recepcion_dict(r) for r in rows]


@router.post("/recepciones", status_code=status.HTTP_201_CREATED)
def crear_recepcion(
    data: RecepcionIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.recepcionar"),
):
    o = db.query(OrdenCompra).filter(OrdenCompra.id == data.orden_compra_id).first()
    if not o:
        raise HTTPException(status_code=404, detail="Orden de compra no encontrada")
    _check_empresa_acceso(db, current_user, o.empresa_id)

    r = Recepcion(
        orden_compra_id=o.id, empresa_id=o.empresa_id, recibido_por_id=current_user.id,
        fecha_recepcion=data.fecha_recepcion, observaciones=data.observaciones,
        novedades=data.novedades, estado="pendiente",
    )
    db.add(r)
    db.flush()
    for it in data.items:
        db.add(RecepcionItem(
            recepcion_id=r.id, solicitud_item_id=it.solicitud_item_id,
            descripcion=it.descripcion, cantidad_esperada=it.cantidad_esperada,
            cantidad_recibida=it.cantidad_recibida, estado=it.estado,
            serial=it.serial, observacion=it.observacion,
        ))
    db.flush()

    # Estado de la recepción según ítems
    items = data.items
    if items and all(i.cantidad_recibida >= i.cantidad_esperada for i in items) and \
            all(i.estado == "ok" for i in items):
        r.estado = "recibida_completa"
    elif any(i.estado in ("dañado", "incompleto", "no_recibido") for i in items):
        r.estado = "con_novedad"
    elif any(i.cantidad_recibida > 0 for i in items):
        r.estado = "recibida_parcial"

    db.refresh(o)
    _recalcular_estado_orden(o)
    db.commit()
    db.refresh(r)
    return _recepcion_dict(r, full=True)


@router.get("/recepciones/{recepcion_id}")
def obtener_recepcion(
    recepcion_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    r = db.query(Recepcion).filter(Recepcion.id == recepcion_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    _check_empresa_acceso(db, current_user, r.empresa_id)
    return _recepcion_dict(r, full=True)


@router.post("/recepciones/{recepcion_id}/crear-inventario", status_code=status.HTTP_201_CREATED)
def crear_inventario_desde_recepcion(
    recepcion_id: str,
    data: CrearInventarioIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_inventario"),
):
    r = db.query(Recepcion).filter(Recepcion.id == recepcion_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    _check_empresa_acceso(db, current_user, r.empresa_id)

    creados = []
    for it in data.items:
        ri = db.query(RecepcionItem).filter(
            RecepcionItem.id == it.recepcion_item_id,
            RecepcionItem.recepcion_id == recepcion_id,
        ).first()
        if not ri:
            raise HTTPException(status_code=404, detail=f"Ítem de recepción {it.recepcion_item_id} no encontrado")
        if ri.activo_creado_id or ri.accesorio_creado_id:
            continue  # ya procesado
        _check_empresa_acceso(db, current_user, it.empresa_id)

        # Determinar tipo según el item de solicitud (si existe) o por los campos enviados
        si = ri.solicitud_item
        es_accesorio = bool(it.tipo_accesorio) or (si and si.tipo_item == "accesorio" and not it.tipo_activo)

        if es_accesorio:
            placa = generar_placa_accesorio(db, it.empresa_id)
            acc = Accesorio(
                id_placa_accesorio=placa, empresa_id=it.empresa_id,
                tipo_accesorio=it.tipo_accesorio or (si.descripcion if si else ri.descripcion),
                marca=it.marca, modelo=it.modelo, serial=it.serial or ri.serial,
                estado=it.estado or "disponible",
            )
            db.add(acc)
            db.flush()
            ri.accesorio_creado_id = acc.id
            creados.append({"tipo": "accesorio", "id": acc.id, "placa": placa})
        else:
            placa = generar_placa_activo(db, it.empresa_id)
            act = Activo(
                id_placa_activo=placa, empresa_id=it.empresa_id,
                tipo_activo=it.tipo_activo or (si.descripcion if si else ri.descripcion),
                marca=it.marca, modelo=it.modelo, serial=it.serial or ri.serial,
                estado=it.estado or "disponible",
            )
            db.add(act)
            db.flush()
            ri.activo_creado_id = act.id
            creados.append({"tipo": "activo", "id": act.id, "placa": placa})

    db.flush()

    # ¿Todos los ítems de la recepción quedaron procesados?
    db.refresh(r)
    todos_procesados = all(
        bool(i.activo_creado_id or i.accesorio_creado_id)
        for i in r.items if i.estado == "ok"
    )

    o = db.query(OrdenCompra).filter(OrdenCompra.id == r.orden_compra_id).first()
    if todos_procesados and o:
        o.estado = "recibida"
        s = db.query(SolicitudCompra).filter(SolicitudCompra.id == o.solicitud_id).first()
        if s:
            # recibida = mercancía llegó; completada = todo el inventario creado
            s.estado = "completada" if _solicitud_completamente_inventariada(db, s) else "recibida"

    db.commit()
    return {"creados": creados, "todos_procesados": todos_procesados}


# ══════════════════════════════════════════════════════════
#  CREAR INVENTARIO POR UNIDAD (modal completo, respeta cantidades)
# ══════════════════════════════════════════════════════════
class CrearUnidadIn(BaseModel):
    # Acepta el payload completo de activo/accesorio (mismos campos que los
    # endpoints normales) + el tipo de recurso a crear.
    model_config = ConfigDict(extra="allow")
    tipo_recurso: str                      # "activo" | "accesorio"


def _creados_count(db: Session, recepcion_item_id: str) -> int:
    return db.query(RecepcionItemCreado).filter(
        RecepcionItemCreado.recepcion_item_id == recepcion_item_id).count()


def _numero_baja_alquiler(db: Session, empresa_id: str) -> str:
    """BAJA-{YYYY}-{NNN} por empresa+año (mismo formato que estados.solicitar_baja)."""
    anio = datetime.now().year
    n = db.query(BajaActivo).filter(
        BajaActivo.empresa_id == empresa_id,
        BajaActivo.numero_baja.like(f"BAJA-{anio}-%"),
    ).count()
    return f"BAJA-{anio}-{n + 1:03d}"


def _get_or_create_contrato_alquiler(db: Session, oc: OrdenCompra) -> ContratoAlquiler:
    """UN contrato por OC de alquiler: lo crea en la primera unidad y lo reutiliza
    para las siguientes (clave = orden_compra_id, UNIQUE). Datos desde la OC."""
    c = db.query(ContratoAlquiler).filter(
        ContratoAlquiler.orden_compra_id == oc.id).first()
    if c:
        return c
    inicio = oc.fecha_inicio_alquiler or oc.fecha_emision or date.today()
    fin = oc.fecha_fin_alquiler or (inicio + timedelta(days=365))
    c = ContratoAlquiler(
        orden_compra_id=oc.id, empresa_id=oc.empresa_id, proveedor_id=oc.proveedor_id,
        fecha_inicio=inicio, fecha_fin=fin,
        valor_mensual=(oc.valor_mensual_alquiler if oc.valor_mensual_alquiler is not None else 0),
        estado="activo",
    )
    db.add(c)
    db.flush()
    return c


def _solicitud_completamente_inventariada(db: Session, s: SolicitudCompra) -> bool:
    """True si TODOS los ítems inventariables de la solicitud tienen ya creadas
    todas sus unidades. "Inventariable" = ítem de recepción OK con
    cantidad_recibida>0, en cualquier recepción de cualquier orden de la
    solicitud. Misma regla de progreso que items-para-inventario (conteo de
    RecepcionItemCreado vs cantidad_recibida). Requiere ≥1 ítem inventariable."""
    items = [
        it
        for o in s.ordenes
        for r in o.recepciones
        for it in r.items
        if it.estado == "ok" and it.cantidad_recibida > 0
    ]
    if not items:
        return False
    return all(_creados_count(db, it.id) >= it.cantidad_recibida for it in items)


def _numero_oc_de_recepcion(r: Recepcion) -> str:
    return (r.orden_compra.numero_oc if (r.orden_compra and r.orden_compra.numero_oc)
            else (r.orden_compra_id[:8] if r.orden_compra_id else "—"))


@router.get("/recepciones/{recepcion_id}/items-para-inventario")
def items_para_inventario(
    recepcion_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_inventario"),
):
    """Ítems OK de la recepción con el progreso de creación (creados/pendientes)
    y datos sugeridos para prellenar el modal de crear activo/accesorio."""
    r = db.query(Recepcion).filter(Recepcion.id == recepcion_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    _check_empresa_acceso(db, current_user, r.empresa_id)

    o = r.orden_compra
    fac = db.query(Factura).filter(Factura.orden_compra_id == o.id).first() if o else None
    fecha_compra = (fac.fecha_factura if (fac and fac.fecha_factura)
                    else (o.fecha_emision if o else None))

    out = []
    for it in r.items:
        # Solo se crean en inventario los ítems recibidos OK con cantidad > 0
        if it.estado != "ok" or it.cantidad_recibida <= 0:
            continue
        si = it.solicitud_item
        creados = _creados_count(db, it.id)
        tipo_item = (si.tipo_item if si else None) or "activo"
        costo = float(si.valor_unitario_estimado) if (si and si.valor_unitario_estimado is not None) else None
        out.append({
            "recepcion_item_id": it.id,
            "descripcion": it.descripcion,
            "tipo_item": tipo_item,            # tipo sugerido (de la solicitud)
            "tipo_item_original": tipo_item,   # explícito: lo que se solicitó originalmente (no se muta)
            "cantidad_recibida": it.cantidad_recibida,
            "creados": creados,
            "pendientes": max(0, it.cantidad_recibida - creados),
            "completo": creados >= it.cantidad_recibida,
            "empresa_id": r.empresa_id,
            "modelo_sugerido": it.descripcion,
            "costo_unitario": costo,
            "fecha_compra": fecha_compra,
            "serial_sugerido": it.serial,
        })
    return out


@router.post("/recepciones/items/{recepcion_item_id}/crear-unidad",
             status_code=status.HTTP_201_CREATED)
def crear_unidad_inventario(
    recepcion_item_id: str,
    data: CrearUnidadIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.crear_inventario"),
):
    """Crea UNA unidad de inventario (activo o accesorio) a partir de un ítem de
    recepción, reutilizando la MISMA lógica que POST /activos|/accesorios."""
    ri = db.query(RecepcionItem).filter(RecepcionItem.id == recepcion_item_id).first()
    if not ri:
        raise HTTPException(status_code=404, detail="Ítem de recepción no encontrado")
    rec = ri.recepcion
    if not rec:
        raise HTTPException(status_code=404, detail="Recepción no encontrada")
    _check_empresa_acceso(db, current_user, rec.empresa_id)

    # Guard de cantidad: no crear más unidades de las recibidas
    ya = _creados_count(db, ri.id)
    if ya >= ri.cantidad_recibida:
        raise HTTPException(status_code=400, detail="Ya se crearon todas las unidades de este ítem")

    tipo = data.tipo_recurso
    if tipo not in ("activo", "accesorio"):
        raise HTTPException(status_code=400, detail="tipo_recurso debe ser 'activo' o 'accesorio'")

    # Construir el schema canónico a partir del payload (empresa forzada a la de la recepción)
    payload = data.model_dump()
    payload.pop("tipo_recurso", None)
    payload.pop("garantia_id", None)   # campo legado ignorado (módulo de garantías retirado)
    payload["empresa_id"] = rec.empresa_id

    if tipo == "accesorio":
        schema = AccesorioCreate(**{k: v for k, v in payload.items() if k in AccesorioCreate.model_fields})
        recurso = crear_accesorio_core(db, schema, current_user)
        ri.accesorio_creado_id = recurso.id          # backward compat (último creado)
        placa = recurso.id_placa_accesorio
    else:
        schema = ActivoCreate(**{k: v for k, v in payload.items() if k in ActivoCreate.model_fields})
        recurso = crear_activo_core(db, schema, current_user)
        ri.activo_creado_id = recurso.id             # backward compat (último creado)
        placa = recurso.id_placa_activo

    # Trazabilidad: vínculo unidad ↔ ítem de recepción
    db.add(RecepcionItemCreado(
        recepcion_item_id=ri.id, tipo_recurso=tipo, recurso_id=recurso.id, placa=placa))

    # Historial de procedencia (además del "creacion" que ya registra el core)
    numero_oc = _numero_oc_de_recepcion(rec)
    db.add(HistorialMovimiento(
        id_activo=recurso.id if tipo == "activo" else None,
        id_accesorio=recurso.id if tipo == "accesorio" else None,
        tipo_movimiento="creacion", responsable=current_user.email,
        observaciones=f"Creado desde recepción OC {numero_oc}",
    ))

    # ── Alquiler: si la OC es de alquiler, adjunta el equipo a su contrato ──
    _oc = rec.orden_compra
    if _oc and _oc.tipo == "alquiler":
        contrato = _get_or_create_contrato_alquiler(db, _oc)
        recurso.es_alquiler = True
        recurso.contrato_alquiler_id = contrato.id
        db.add(HistorialMovimiento(
            id_activo=recurso.id if tipo == "activo" else None,
            id_accesorio=recurso.id if tipo == "accesorio" else None,
            tipo_movimiento="creacion", responsable=current_user.email,
            observaciones=f"Equipo en alquiler — contrato de OC {numero_oc}",
        ))

    db.flush()
    creados = _creados_count(db, ri.id)
    completo_item = creados >= ri.cantidad_recibida

    # ¿Recepción completa? todos los ítems OK con sus unidades creadas
    db.refresh(rec)
    items_ok = [i for i in rec.items if i.estado == "ok" and i.cantidad_recibida > 0]
    recepcion_completa = bool(items_ok) and all(
        _creados_count(db, i.id) >= i.cantidad_recibida for i in items_ok)
    if recepcion_completa:
        rec.estado = "recibida_completa"
        o = db.query(OrdenCompra).filter(OrdenCompra.id == rec.orden_compra_id).first()
        if o:
            o.estado = "recibida"
            s = db.query(SolicitudCompra).filter(SolicitudCompra.id == o.solicitud_id).first()
            if s:
                # recibida = mercancía llegó; completada = todo el inventario creado
                s.estado = "completada" if _solicitud_completamente_inventariada(db, s) else "recibida"

    db.commit()
    db.refresh(recurso)
    return {
        "recurso": {"tipo": tipo, "id": recurso.id, "placa": placa},
        "creados": creados,
        "pendientes": max(0, ri.cantidad_recibida - creados),
        "completo": completo_item,
        "recepcion_completa": recepcion_completa,
    }


# ══════════════════════════════════════════════════════════
#  CONTRATOS DE ALQUILER
# ══════════════════════════════════════════════════════════
class TerminarContratoIn(BaseModel):
    fecha_devolucion_real: date
    observaciones_devolucion: Optional[str] = None


def _contrato_dict(c: ContratoAlquiler) -> dict:
    hoy = date.today()
    proximo = bool(c.fecha_fin and hoy <= c.fecha_fin <= hoy + timedelta(days=60)
                   and c.estado == "activo")
    return {
        "id": c.id, "orden_compra_id": c.orden_compra_id, "empresa_id": c.empresa_id,
        "proveedor_id": c.proveedor_id,
        "numero_oc": c.orden_compra.numero_oc if c.orden_compra else None,
        "fecha_inicio": c.fecha_inicio, "fecha_fin": c.fecha_fin,
        "valor_mensual": _f(c.valor_mensual), "valor_total_contrato": _f(c.valor_total_contrato),
        "estado": c.estado, "fecha_devolucion_real": c.fecha_devolucion_real,
        "observaciones_devolucion": c.observaciones_devolucion,
        "proveedor": c.proveedor.nombre if c.proveedor else None,
        "equipos_count": len(c.activos) + len(c.accesorios),
        "equipos": (
            [{"tipo": "activo", "id": a.id, "placa": a.id_placa_activo,
              "descripcion": " ".join(filter(None, [a.tipo_activo, a.marca, a.modelo])),
              "estado": a.estado} for a in c.activos]
            + [{"tipo": "accesorio", "id": a.id, "placa": a.id_placa_accesorio,
                "descripcion": " ".join(filter(None, [a.tipo_accesorio, a.marca, a.modelo])),
                "estado": a.estado} for a in c.accesorios]
        ),
        "proximo_a_vencer": proximo,
    }


@router.get("/contratos-alquiler")
def listar_contratos(
    estado: Optional[str] = None,
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    query = _scope_empresa(db.query(ContratoAlquiler), ContratoAlquiler, db, current_user, empresa_id)
    if estado:
        query = query.filter(ContratoAlquiler.estado == estado)
    rows = query.order_by(ContratoAlquiler.fecha_fin.asc()).all()
    return [_contrato_dict(c) for c in rows]


@router.post("/contratos-alquiler/{contrato_id}/terminar")
def terminar_contrato(
    contrato_id: str,
    data: TerminarContratoIn,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.gestionar_facturas"),
):
    c = db.query(ContratoAlquiler).filter(ContratoAlquiler.id == contrato_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    _check_empresa_acceso(db, current_user, c.empresa_id)
    if c.estado != "activo":
        raise HTTPException(status_code=400, detail=f"El contrato no está activo (estado actual: {c.estado})")

    c.fecha_devolucion_real = data.fecha_devolucion_real
    c.observaciones_devolucion = data.observaciones_devolucion
    # Si se devuelve antes del fin → terminado anticipado; si no, vencido
    c.estado = "terminado_anticipado" if data.fecha_devolucion_real < c.fecha_fin else "vencido"

    # Retirar cada equipo del contrato con una baja "devuelto_proveedor" AUTO-APROBADA
    num_oc = c.orden_compra.numero_oc if c.orden_compra else ""
    equipos = [("activo", a) for a in c.activos] + [("accesorio", a) for a in c.accesorios]
    retirados = []
    for tipo, r in equipos:
        if r.estado == "retirado":
            continue
        es_activo = tipo == "activo"
        baja = BajaActivo(
            numero_baja=_numero_baja_alquiler(db, r.empresa_id),
            tipo_recurso=tipo, recurso_id=r.id,
            placa=(r.id_placa_activo if es_activo else r.id_placa_accesorio),
            empresa_id=r.empresa_id,
            tipo_activo=(r.tipo_activo if es_activo else r.tipo_accesorio),
            marca=r.marca, modelo=r.modelo, serial=r.serial,
            fecha_compra=(r.fecha_compra if es_activo else None),
            costo_original=(float(r.costo) if (es_activo and r.costo) else None),
            motivo="devuelto_proveedor",
            justificacion=f"Devolución al proveedor por término del contrato de alquiler (OC {num_oc})",
            estado_aprobacion="aprobada",
            solicitado_por_id=current_user.id, aprobado_por_id=current_user.id,
            fecha_aprobacion=datetime.now(),
        )
        db.add(baja)
        db.flush()
        r.estado = "retirado"
        r.id_usuario = None
        db.add(HistorialMovimiento(
            id_activo=r.id if es_activo else None,
            id_accesorio=r.id if not es_activo else None,
            tipo_movimiento="baja", responsable=current_user.email,
            observaciones=f"Devuelto a proveedor — contrato de alquiler terminado ({baja.numero_baja})"))
        try:
            from services.pdf_service import generar_pdf_baja
            baja.url_pdf = generar_pdf_baja(baja, db)
        except Exception as e:
            print(f"[BAJA PDF] {e}")
        retirados.append(baja.numero_baja)

    db.commit()
    db.refresh(c)
    out = _contrato_dict(c)
    out["bajas_generadas"] = retirados
    return out


# ══════════════════════════════════════════════════════════
#  STATS
# ══════════════════════════════════════════════════════════
@router.get("/stats")
def stats_compras(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("compras.ver"),
):
    hoy = date.today()
    en_30 = hoy + timedelta(days=30)
    en_60 = hoy + timedelta(days=60)
    inicio_mes = hoy.replace(day=1)

    def scoped(model):
        return _scope_empresa(db.query(model), model, db, current_user, empresa_id)

    solicitudes_pend = scoped(SolicitudCompra).filter(
        SolicitudCompra.estado == "pendiente_aprobacion").count()

    ordenes_pend = scoped(OrdenCompra).filter(
        OrdenCompra.estado.in_(["emitida", "parcialmente_recibida"])).count()

    facturas_por_vencer = scoped(Factura).filter(
        Factura.estado == "pendiente",
        Factura.fecha_vencimiento != None,
        Factura.fecha_vencimiento >= hoy,
        Factura.fecha_vencimiento <= en_30,
    ).count()

    facturas_vencidas = scoped(Factura).filter(
        Factura.estado.in_(["pendiente", "vencida"]),
        Factura.fecha_vencimiento != None,
        Factura.fecha_vencimiento < hoy,
    ).count()

    contratos_por_vencer = scoped(ContratoAlquiler).filter(
        ContratoAlquiler.estado == "activo",
        ContratoAlquiler.fecha_fin >= hoy,
        ContratoAlquiler.fecha_fin <= en_60,
    ).count()

    facturas_mes = scoped(Factura).filter(
        Factura.estado == "pagada",
        Factura.fecha_factura >= inicio_mes,
    ).all()
    total_compras_mes = sum(_f(f.valor_total) or 0 for f in facturas_mes)

    equipos_en_alquiler = scoped(ContratoAlquiler).filter(
        ContratoAlquiler.estado == "activo").count()

    return {
        "solicitudes_pendientes_aprobacion": solicitudes_pend,
        "ordenes_pendientes_recepcion": ordenes_pend,
        "facturas_por_vencer": facturas_por_vencer,
        "facturas_vencidas": facturas_vencidas,
        "contratos_por_vencer": contratos_por_vencer,
        "total_compras_mes": total_compras_mes,
        "equipos_en_alquiler": equipos_en_alquiler,
    }
