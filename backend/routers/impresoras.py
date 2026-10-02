import re
import json
import base64
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from database import get_db
from models.impresoras import Impresora
from models.empresa import Empresa
from models.catalogo import Catalogo
from models.compra import Proveedor
from models.reporte_dano import ReporteDano
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids
from services.email_service import enviar_reporte_dano

# Límites de imágenes del reporte de daño (adjuntos en memoria, sin storage).
_REP_MAX_IMGS   = 10
_REP_MAX_BYTES  = 5 * 1024 * 1024    # por imagen
_REP_TOTAL_BYTES = 15 * 1024 * 1024  # total
_DATAURL_RE = re.compile(r"^data:image/(png|jpe?g|gif|webp);base64,(.+)$", re.IGNORECASE | re.DOTALL)
_EMAIL_RE   = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

router = APIRouter(prefix="/api/impresoras", tags=["Impresoras"])

TIPOS_VALIDOS   = {"color", "monocromatica"}
# 'reemplazada' es un valor VÁLIDO almacenado/filtrable, pero NO se fija a mano
# (solo lo pone el flujo de /reemplazar). crear/actualizar lo rechazan explícitamente.
ESTADOS_VALIDOS = {"en_servicio", "inactiva", "en_reparacion", "reemplazada"}
ESTADO_REEMPLAZADA = "reemplazada"


# ── Schemas ───────────────────────────────────────────────────────────────────

class ImpresoraCreate(BaseModel):
    empresa_id:         str
    sede_catalogo_id:   Optional[str] = None
    ciudad_catalogo_id: Optional[str] = None
    dependencia:        Optional[str] = None
    modelo:             Optional[str] = None
    tipo:               Optional[str] = None
    serial:             Optional[str] = None
    ip:                 Optional[str] = None
    estado:             Optional[str] = "en_servicio"
    correo_escaneo:     Optional[str] = None
    proveedor_id:       Optional[str] = None


class ImpresoraUpdate(BaseModel):
    sede_catalogo_id:   Optional[str] = None
    ciudad_catalogo_id: Optional[str] = None
    dependencia:        Optional[str] = None
    modelo:             Optional[str] = None
    tipo:               Optional[str] = None
    serial:             Optional[str] = None
    ip:                 Optional[str] = None
    estado:             Optional[str] = None
    correo_escaneo:     Optional[str] = None
    proveedor_id:       Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────--

def _impresora_dict(i: Impresora, cat_map: dict = None, prov_map: dict = None) -> dict:
    """Combina la impresora con nombres resueltos (sede/ciudad/proveedor).
    Los mapas se pasan pre-cargados en lote (sin N+1); si no vienen, se leen de la relación."""
    cat_map = cat_map or {}
    prov_map = prov_map or {}
    sede_nombre = cat_map.get(i.sede_catalogo_id) if i.sede_catalogo_id in cat_map else (i.sede.valor if i.sede else None)
    ciudad_nombre = cat_map.get(i.ciudad_catalogo_id) if i.ciudad_catalogo_id in cat_map else (i.ciudad.valor if i.ciudad else None)
    _pm = prov_map.get(i.proveedor_id)
    prov_nombre = _pm["nombre"] if _pm else (i.proveedor.nombre if i.proveedor else None)
    prov_correo = _pm["correo"] if _pm else (i.proveedor.correo if i.proveedor else None)
    return {
        "id":                 i.id,
        "empresa_id":         i.empresa_id,
        "empresa":            {"id": i.empresa.id, "nombre": i.empresa.nombre_empresa} if i.empresa else None,
        "sede_catalogo_id":   i.sede_catalogo_id,
        "sede":               sede_nombre,
        "ciudad_catalogo_id": i.ciudad_catalogo_id,
        "ciudad":             ciudad_nombre,
        "dependencia":        i.dependencia,
        "modelo":             i.modelo,
        "tipo":               i.tipo,
        "serial":             i.serial,
        "ip":                 i.ip,
        "estado":             i.estado,
        "correo_escaneo":     i.correo_escaneo,
        "proveedor_id":       i.proveedor_id,
        "proveedor":          prov_nombre,
        "proveedor_correo":   prov_correo,
        "activo":             i.activo,
        "created_at":         i.created_at.isoformat() if i.created_at else None,
        "reemplaza_a":        i.reemplaza_a,
        "motivo_reemplazo":   i.motivo_reemplazo,
        "reemplazado_at":     i.reemplazado_at.isoformat() if i.reemplazado_at else None,
    }


def _scope_or_403(db: Session, current_user, empresa_id: str):
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")


def _get_impresora_scoped(db: Session, current_user, impresora_id: str) -> Impresora:
    i = db.query(Impresora).filter(Impresora.id == impresora_id).first()
    if not i:
        raise HTTPException(status_code=404, detail="Impresora no encontrada")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and i.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa impresora")
    return i


def _validar_sede(db: Session, sede_catalogo_id: Optional[str], empresa_id: str):
    if not sede_catalogo_id:
        return
    sede = db.query(Catalogo).filter(
        Catalogo.id == sede_catalogo_id, Catalogo.categoria == "sede").first()
    if not sede:
        raise HTTPException(status_code=400, detail="La sede indicada no existe")
    if sede.empresa_id != empresa_id:
        raise HTTPException(status_code=400, detail="La sede no pertenece a esa empresa")


def _validar_ciudad(db: Session, ciudad_catalogo_id: Optional[str]):
    if not ciudad_catalogo_id:
        return
    ciudad = db.query(Catalogo).filter(
        Catalogo.id == ciudad_catalogo_id, Catalogo.categoria == "ciudad").first()
    if not ciudad:
        raise HTTPException(status_code=400, detail="La ciudad indicada no existe")


def _validar_proveedor(db: Session, proveedor_id: Optional[str]):
    if not proveedor_id:
        return
    prov = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not prov:
        raise HTTPException(status_code=400, detail="El proveedor indicado no existe")
    if "impresoras" not in prov.modulos_list:
        raise HTTPException(status_code=400, detail="El proveedor no aplica al módulo de impresoras")


def _validar_tipo_estado(tipo: Optional[str], estado: Optional[str]):
    if tipo and tipo not in TIPOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Tipo inválido. Use: {', '.join(sorted(TIPOS_VALIDOS))}")
    # 'reemplazada' NO se fija a mano — solo la pone el flujo de reemplazo.
    if estado == ESTADO_REEMPLAZADA:
        raise HTTPException(status_code=400, detail="El estado 'reemplazada' solo se asigna al reemplazar una impresora, no manualmente")
    manuales = ESTADOS_VALIDOS - {ESTADO_REEMPLAZADA}
    if estado and estado not in manuales:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Use: {', '.join(sorted(manuales))}")


def _validar_serial_unico(db: Session, empresa_id: str, serial: Optional[str], exclude_id: str = None):
    """Serial único entre impresoras ACTIVAS de la misma empresa (chequeo app-level,
    no constraint de BD — así el reemplazo-con-historial de fase 2 no colisiona)."""
    if not serial or not serial.strip():
        return
    q = db.query(Impresora).filter(
        Impresora.empresa_id == empresa_id,
        Impresora.serial == serial.strip(),
        Impresora.activo == True,
        Impresora.estado != ESTADO_REEMPLAZADA,   # una reemplazada libera su serial
    )
    if exclude_id:
        q = q.filter(Impresora.id != exclude_id)
    if q.first():
        raise HTTPException(status_code=409, detail=f"Ya existe una impresora activa con serial «{serial.strip()}» en esta empresa")


def _resolver_mapas(db: Session, impresoras: list) -> tuple:
    """Carga en lote los nombres de sede/ciudad (catalogos) y proveedor (sin N+1)."""
    cat_ids = {i.sede_catalogo_id for i in impresoras if i.sede_catalogo_id} | \
              {i.ciudad_catalogo_id for i in impresoras if i.ciudad_catalogo_id}
    prov_ids = {i.proveedor_id for i in impresoras if i.proveedor_id}
    cat_map = {c.id: c.valor for c in db.query(Catalogo.id, Catalogo.valor)
               .filter(Catalogo.id.in_(cat_ids)).all()} if cat_ids else {}
    prov_map = {p.id: {"nombre": p.nombre, "correo": p.correo}
                for p in db.query(Proveedor.id, Proveedor.nombre, Proveedor.correo)
                .filter(Proveedor.id.in_(prov_ids)).all()} if prov_ids else {}
    return cat_map, prov_map


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def listar_impresoras(
    empresa_id: Optional[str] = None,
    estado:     Optional[str] = None,
    q:          Optional[str] = Query(None, description="Buscar por serial o modelo"),
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.ver"),
):
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    query = db.query(Impresora).filter(Impresora.activo == True)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Impresora.empresa_id == empresa_id)
        else:
            query = query.filter(Impresora.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Impresora.empresa_id == empresa_id)

    if estado:
        query = query.filter(Impresora.estado == estado)   # incl. ?estado=reemplazada para verlas
    else:
        query = query.filter(Impresora.estado != ESTADO_REEMPLAZADA)   # activas: reemplazada fuera del listado
    if q:
        query = query.filter(or_(
            Impresora.serial.ilike(f"%{q}%"),
            Impresora.modelo.ilike(f"%{q}%"),
        ))

    impresoras = query.order_by(Impresora.modelo).all()
    cat_map, prov_map = _resolver_mapas(db, impresoras)
    return [_impresora_dict(i, cat_map, prov_map) for i in impresoras]


@router.get("/{impresora_id}")
def obtener_impresora(
    impresora_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.ver"),
):
    i = _get_impresora_scoped(db, current_user, impresora_id)
    cat_map, prov_map = _resolver_mapas(db, [i])
    return _impresora_dict(i, cat_map, prov_map)


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_impresora(
    data: ImpresoraCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.gestionar"),
):
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    _scope_or_403(db, current_user, data.empresa_id)

    _validar_tipo_estado(data.tipo, data.estado)
    _validar_sede(db, data.sede_catalogo_id, data.empresa_id)
    _validar_ciudad(db, data.ciudad_catalogo_id)
    _validar_proveedor(db, data.proveedor_id)
    _validar_serial_unico(db, data.empresa_id, data.serial)

    i = Impresora(
        empresa_id=data.empresa_id,
        sede_catalogo_id=data.sede_catalogo_id or None,
        ciudad_catalogo_id=data.ciudad_catalogo_id or None,
        dependencia=(data.dependencia or None),
        modelo=(data.modelo or None),
        tipo=(data.tipo or None),
        serial=(data.serial.strip() if data.serial else None),
        ip=(data.ip or None),
        estado=(data.estado or "en_servicio"),
        correo_escaneo=(data.correo_escaneo or None),
        proveedor_id=data.proveedor_id or None,
        created_by=current_user.id,
    )
    db.add(i)
    db.commit()
    db.refresh(i)
    cat_map, prov_map = _resolver_mapas(db, [i])
    return _impresora_dict(i, cat_map, prov_map)


@router.put("/{impresora_id}")
def actualizar_impresora(
    impresora_id: str,
    data: ImpresoraUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.gestionar"),
):
    i = _get_impresora_scoped(db, current_user, impresora_id)
    _validar_tipo_estado(data.tipo, data.estado)
    if data.sede_catalogo_id is not None:
        _validar_sede(db, data.sede_catalogo_id or None, i.empresa_id)
    if data.ciudad_catalogo_id is not None:
        _validar_ciudad(db, data.ciudad_catalogo_id or None)
    if data.proveedor_id is not None:
        _validar_proveedor(db, data.proveedor_id or None)
    if data.serial is not None:
        _validar_serial_unico(db, i.empresa_id, data.serial, exclude_id=i.id)

    campos = data.model_dump(exclude_unset=True)
    for campo, valor in campos.items():
        if campo == "serial":
            i.serial = valor.strip() if valor else None
        elif campo == "estado":
            if valor:                 # estado es NOT NULL; ignora vacío
                i.estado = valor
        elif campo in ("sede_catalogo_id", "ciudad_catalogo_id", "proveedor_id"):
            setattr(i, campo, valor or None)
        else:
            setattr(i, campo, valor if valor != "" else None)

    db.commit()
    db.refresh(i)
    cat_map, prov_map = _resolver_mapas(db, [i])
    return _impresora_dict(i, cat_map, prov_map)


@router.delete("/{impresora_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_impresora(
    impresora_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.gestionar"),
):
    i = _get_impresora_scoped(db, current_user, impresora_id)
    i.activo = False
    db.commit()


# ── Fase 2: reemplazo-con-historial ──────────────────────────────────────────--

class ReemplazoCreate(BaseModel):
    """Datos de la NUEVA impresora (prellenados desde la vieja en el cliente) + motivo.
    La empresa se hereda de la vieja (mismo punto físico); no se envía aquí."""
    sede_catalogo_id:   Optional[str] = None
    ciudad_catalogo_id: Optional[str] = None
    dependencia:        Optional[str] = None
    modelo:             Optional[str] = None
    tipo:               Optional[str] = None
    serial:             Optional[str] = None
    ip:                 Optional[str] = None
    correo_escaneo:     Optional[str] = None
    proveedor_id:       Optional[str] = None
    motivo:             str


@router.post("/{impresora_id}/reemplazar", status_code=status.HTTP_201_CREATED)
def reemplazar_impresora(
    impresora_id: str,
    data: ReemplazoCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.gestionar"),
):
    """Reemplaza una impresora: crea la NUEVA (estado en_servicio, reemplaza_a=vieja),
    marca la VIEJA como 'reemplazada' (terminal) con motivo/fecha/autor, y las enlaza."""
    vieja = _get_impresora_scoped(db, current_user, impresora_id)
    if vieja.estado == ESTADO_REEMPLAZADA:
        raise HTTPException(status_code=400, detail="Esta impresora ya fue reemplazada; no se puede reemplazar de nuevo")
    if not vieja.activo:
        raise HTTPException(status_code=400, detail="Esta impresora está inactiva (dada de baja); no se puede reemplazar")

    motivo = (data.motivo or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="El motivo del reemplazo es obligatorio")

    _validar_tipo_estado(data.tipo, None)   # estado se fuerza a en_servicio; no se valida aquí
    _validar_sede(db, data.sede_catalogo_id or None, vieja.empresa_id)
    _validar_ciudad(db, data.ciudad_catalogo_id or None)
    _validar_proveedor(db, data.proveedor_id or None)
    # La vieja aún es activa en este instante → exclúyela del chequeo (se retira en esta tx),
    # así el serial se puede reutilizar y no choca consigo misma.
    _validar_serial_unico(db, vieja.empresa_id, data.serial, exclude_id=vieja.id)

    nueva = Impresora(
        empresa_id=vieja.empresa_id,
        sede_catalogo_id=data.sede_catalogo_id or None,
        ciudad_catalogo_id=data.ciudad_catalogo_id or None,
        dependencia=(data.dependencia or None),
        modelo=(data.modelo or None),
        tipo=(data.tipo or None),
        serial=(data.serial.strip() if data.serial else None),
        ip=(data.ip or None),
        estado="en_servicio",
        correo_escaneo=(data.correo_escaneo or None),
        proveedor_id=data.proveedor_id or None,
        reemplaza_a=vieja.id,
        created_by=current_user.id,
    )
    db.add(nueva)

    vieja.estado = ESTADO_REEMPLAZADA
    vieja.motivo_reemplazo = motivo
    vieja.reemplazado_at = datetime.utcnow()
    vieja.reemplazado_by = current_user.id

    db.commit()
    db.refresh(nueva)
    cat_map, prov_map = _resolver_mapas(db, [nueva])
    return _impresora_dict(nueva, cat_map, prov_map)


@router.get("/{impresora_id}/historial")
def historial_impresora(
    impresora_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.ver"),
):
    """Cadena de reemplazo: esta impresora ← la que reemplazó ← … (walk backward por
    reemplaza_a). Todos los nodos comparten empresa (heredada al reemplazar), así que
    el scope del nodo inicial cubre la cadena. Guard de ciclos + tope de profundidad."""
    actual = _get_impresora_scoped(db, current_user, impresora_id)
    cadena, visited, node, depth = [], set(), actual, 0
    while node and node.id not in visited and depth < 100:
        visited.add(node.id)
        cadena.append({
            "id":               node.id,
            "modelo":           node.modelo,
            "serial":           node.serial,
            "tipo":             node.tipo,
            "estado":           node.estado,
            "created_at":       node.created_at.isoformat() if node.created_at else None,
            "reemplazado_at":   node.reemplazado_at.isoformat() if node.reemplazado_at else None,
            "motivo_reemplazo": node.motivo_reemplazo,
            "es_actual":        node.id == actual.id,
        })
        if not node.reemplaza_a:
            break
        node = db.query(Impresora).filter(Impresora.id == node.reemplaza_a).first()
        depth += 1
    return {"impresora_id": actual.id, "cadena": cadena}


# ── Fase 3: reporte de daño al proveedor (correo con adjuntos en memoria) ─────--

class ReporteDanoIn(BaseModel):
    descripcion_dano: Optional[str] = None
    asunto:           str
    cuerpo:           str                       # HTML del preview editable
    destinatarios:    List[str] = []
    imagenes:         List[str] = []            # data URLs base64 (no se almacenan)


def _reporte_dict(r: ReporteDano) -> dict:
    return {
        "id":                 r.id,
        "impresora_id":       r.impresora_id,
        "descripcion_dano":   r.descripcion_dano,
        "asunto":             r.asunto,
        "cuerpo":             r.cuerpo,
        "destinatarios":      r.destinatarios_list,
        "cc":                 r.cc_list,
        "num_imagenes":       r.num_imagenes,
        "generado_por_email": r.generado_por_email,
        "created_at":         r.created_at.isoformat() if r.created_at else None,
    }


def _sanitizar_emails(lst: list) -> tuple:
    """(válidos_sin_duplicados, inválidos) — para responder 400 claro, no 500 de EmailStr."""
    validos, invalidos, seen = [], [], set()
    for e in (lst or []):
        e = (e or "").strip()
        if not e:
            continue
        if _EMAIL_RE.match(e):
            if e.lower() not in seen:
                seen.add(e.lower())
                validos.append(e)
        else:
            invalidos.append(e)
    return validos, invalidos


def _decodificar_imagenes(urls: list) -> list:
    """Data URLs → [{filename, bytes, subtype}] en memoria. Aplica topes; lanza 400."""
    urls = urls or []
    if len(urls) > _REP_MAX_IMGS:
        raise HTTPException(status_code=400, detail=f"Máximo {_REP_MAX_IMGS} imágenes por reporte")
    out, total = [], 0
    for idx, u in enumerate(urls, 1):
        m = _DATAURL_RE.match(u or "")
        if not m:
            raise HTTPException(status_code=400, detail=f"La imagen {idx} no es una imagen pegada válida")
        sub = m.group(1).lower()
        sub = "jpeg" if sub in ("jpg", "jpeg") else sub
        try:
            raw = base64.b64decode(m.group(2), validate=True)
        except Exception:
            raise HTTPException(status_code=400, detail=f"La imagen {idx} no se pudo decodificar")
        if len(raw) > _REP_MAX_BYTES:
            raise HTTPException(status_code=400, detail=f"La imagen {idx} supera el máximo de {_REP_MAX_BYTES // (1024*1024)} MB")
        total += len(raw)
        ext = "jpg" if sub == "jpeg" else sub
        out.append({"filename": f"dano_{idx}.{ext}", "bytes": raw, "subtype": sub})
    if total > _REP_TOTAL_BYTES:
        raise HTTPException(status_code=400, detail=f"El total de imágenes supera {_REP_TOTAL_BYTES // (1024*1024)} MB")
    return out


@router.post("/{impresora_id}/reporte-dano", status_code=status.HTTP_201_CREATED)
def reportar_dano(
    impresora_id: str,
    data: ReporteDanoIn,
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.gestionar"),
):
    """Envía el reporte de daño por correo (adjuntos en memoria, CC al usuario) y —
    SOLO si el envío fue exitoso— guarda el registro de trazabilidad."""
    imp = _get_impresora_scoped(db, current_user, impresora_id)   # scope + 404

    asunto = (data.asunto or "").strip()
    if not asunto:
        raise HTTPException(status_code=400, detail="El asunto es obligatorio")

    destinatarios, invalidos = _sanitizar_emails(data.destinatarios)
    if invalidos:
        raise HTTPException(status_code=400, detail=f"Correos inválidos: {', '.join(invalidos)}")
    if not destinatarios:
        raise HTTPException(status_code=400, detail="Indica al menos un destinatario válido")

    imagenes = _decodificar_imagenes(data.imagenes)   # aplica topes (400 si excede)

    cc_email = current_user.email
    cc = [cc_email] if cc_email and _EMAIL_RE.match(cc_email) else []

    enviado = asyncio.run(enviar_reporte_dano(
        destinatarios=destinatarios, cc=cc,
        asunto=asunto, cuerpo_html=(data.cuerpo or ""), imagenes=imagenes,
    ))
    if not enviado:
        raise HTTPException(status_code=502,
                            detail="No se pudo enviar el correo. Revisa la configuración de correo del sistema.")

    # Persistir SOLO tras el envío exitoso (el historial refleja reportes realmente enviados).
    rep = ReporteDano(
        impresora_id=imp.id,
        empresa_id=imp.empresa_id,
        descripcion_dano=(data.descripcion_dano or None),
        asunto=asunto,
        cuerpo=(data.cuerpo or None),
        destinatarios=json.dumps(destinatarios),
        cc=json.dumps(cc),
        num_imagenes=len(imagenes),
        generado_por=current_user.id,
        generado_por_email=cc_email,
    )
    db.add(rep)
    db.commit()
    db.refresh(rep)
    return _reporte_dict(rep)


@router.get("/{impresora_id}/reportes-dano")
def listar_reportes_dano(
    impresora_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("impresoras.ver"),
):
    imp = _get_impresora_scoped(db, current_user, impresora_id)
    reps = (db.query(ReporteDano)
            .filter(ReporteDano.impresora_id == imp.id)
            .order_by(ReporteDano.created_at.desc())
            .all())
    return {"impresora_id": imp.id, "total": len(reps), "reportes": [_reporte_dict(r) for r in reps]}
