import re
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from database import get_db
from models.redes import CuartoTecnico, Rack, DispositivoRed
from models.empresa import Empresa
from models.catalogo import Catalogo
from models.activo import Activo
from models.historial import HistorialMovimiento
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids

router = APIRouter(prefix="/api/redes", tags=["Redes"])

# ── Tipos de red (ÚNICO lugar) ──────────────────────────────────────────────────
# Un activo es "de red" (montable en Redes) si su tipo_activo está marcado es_red=1
# en el catálogo (categoria='tipo_activo'). Administrable desde Catálogos (reemplaza
# el antiguo match por palabra clave). Se ignora el flag `activo` del catálogo:
# mountability (es_red) y disponibilidad-para-nuevos-activos (activo) son ortogonales.
def _tipos_red_set(db: Session) -> set:
    rows = db.query(Catalogo.valor).filter(
        Catalogo.categoria == "tipo_activo", Catalogo.es_red == True).all()
    return {r[0] for r in rows}

def es_tipo_red(db: Session, tipo_activo: Optional[str]) -> bool:
    return bool(tipo_activo) and tipo_activo in _tipos_red_set(db)


# ── Color por tipo (para el PDF) ────────────────────────────────────────────────
# Réplica FIEL de REDES_TIPO_ESTILO en frontend/js/redes.js (mismo orden y colores).
# El color es cosmético; si cambias uno aquí, cámbialo también allá.
_TIPO_COLOR = [
    (re.compile(r"switch", re.I),                 "#185FA5"),
    (re.compile(r"firewall|fortigate", re.I),     "#993C1D"),
    (re.compile(r"router", re.I),                 "#6C4AB6"),
    (re.compile(r"patch", re.I),                  "#0E7C7B"),
    (re.compile(r"ont", re.I),                    "#0E7C7B"),
    (re.compile(r"ups", re.I),                    "#5F5E5A"),
    (re.compile(r"access\s*point|\bap\b", re.I),  "#185FA5"),
    (re.compile(r"servidor|server", re.I),        "#633806"),
]
_TIPO_COLOR_FALLBACK = "#5F5E5A"

def _tipo_color(tipo: Optional[str]) -> str:
    t = tipo or ""
    for rx, color in _TIPO_COLOR:
        if rx.search(t):
            return color
    return _TIPO_COLOR_FALLBACK


def _rack_layout(rack: dict, devices: list) -> list:
    """Construye las filas del rack de arriba (capacidad_u) hacia abajo (1), FULL
    (sin colapsar). Cada fila es un dispositivo (con su span en U) o una U libre.
    Réplica server-side de _rackBodyHTML(collapse=false) de redes.js."""
    cap = rack.get("capacidad_u") or 0
    by_top, occupied = {}, set()
    for d in devices:
        if d.get("posicion_u") is None:
            continue
        size = d.get("tamano_u") or 1
        top = d["posicion_u"] + size - 1
        by_top[top] = d
        for k in range(d["posicion_u"], top + 1):
            occupied.add(k)

    rows, u = [], cap
    while u >= 1:
        if u in by_top:
            d = by_top[u]
            size = d.get("tamano_u") or 1
            marca_modelo = " ".join(x for x in [d.get("marca"), d.get("modelo")] if x)
            rows.append({
                "kind": "dev", "span": size,
                "u_ini": d["posicion_u"], "u_fin": d["posicion_u"] + size - 1,
                "color": _tipo_color(d.get("tipo_activo")),
                "consecutivo": d.get("consecutivo") or "—",
                "tipo": d.get("tipo_activo") or "",
                "modelo": marca_modelo,
                "ip": d.get("ip_gestion"),
                "puertos": d.get("num_puertos"),
            })
            u -= size
        elif u in occupied:
            u -= 1   # defensivo (no debería ocurrir sin solapes)
        else:
            rows.append({"kind": "free", "u": u})
            u -= 1
    return rows


# ── Schemas ───────────────────────────────────────────────────────────────────

class CuartoCreate(BaseModel):
    empresa_id:        str
    sede_catalogo_id:  str
    identificador:     str
    nombre:            Optional[str] = None
    descripcion:       Optional[str] = None
    ubicacion_detalle: Optional[str] = None


class CuartoUpdate(BaseModel):
    sede_catalogo_id:  Optional[str] = None
    identificador:     Optional[str] = None
    nombre:            Optional[str] = None
    descripcion:       Optional[str] = None
    ubicacion_detalle: Optional[str] = None


class RackCreate(BaseModel):
    nombre:      str
    capacidad_u: Optional[int] = 42
    descripcion: Optional[str] = None
    orden:       Optional[int] = None


class RackUpdate(BaseModel):
    nombre:      Optional[str] = None
    capacidad_u: Optional[int] = None
    descripcion: Optional[str] = None
    orden:       Optional[int] = None


class DispositivoCreate(BaseModel):
    """MONTAR un activo existente en un cuarto (en rack o fuera de rack)."""
    activo_id:         str                     # el activo a montar (debe estar disponible)
    cuarto_tecnico_id: str
    rack_id:           Optional[str] = None    # null = fuera de rack
    posicion_u:        Optional[int] = None    # requerida si rack_id
    tamano_u:          Optional[int] = 1
    ubicacion_fisica:  Optional[str] = None
    ip_gestion:        Optional[str] = None
    num_puertos:       Optional[int] = None
    conexion:          Optional[str] = None
    datos_adicionales: Optional[str] = None


class DispositivoUpdate(BaseModel):
    """Editar SOLO datos de montaje/red. NO cambia el estado del activo."""
    # rack_id se envía siempre en un move: str = a un rack, None = fuera de rack.
    # Usamos un sentinel para distinguir "no tocar" de "poner en null".
    rack_id:           Optional[str] = "__keep__"
    posicion_u:        Optional[int] = None
    tamano_u:          Optional[int] = None
    ubicacion_fisica:  Optional[str] = None
    ip_gestion:        Optional[str] = None
    num_puertos:       Optional[int] = None
    conexion:          Optional[str] = None
    datos_adicionales: Optional[str] = None


# ── Helpers ─────────────────────────────────────────────────────────────────--

def _rack_dict(r: Rack, usadas_u: int = 0, num_dispositivos: int = 0) -> dict:
    return {
        "id":          r.id,
        "nombre":      r.nombre,
        "capacidad_u": r.capacidad_u,
        "descripcion": r.descripcion,
        "orden":       r.orden,
        "activo":      r.activo,
        "usadas_u":    usadas_u,
        "libres_u":    max(0, (r.capacidad_u or 0) - usadas_u),
        "num_dispositivos": num_dispositivos,
    }


def _dispositivo_dict(d: DispositivoRed, activo: Optional[Activo] = None) -> dict:
    """Combina los datos de MONTAJE (d) con los del ACTIVO (solo lectura).
    `activo` se pasa desde un mapa pre-cargado para evitar N+1; si no viene, se lee
    de la relación d.equipo."""
    a = activo if activo is not None else d.equipo
    return {
        "id":                d.id,
        "cuarto_tecnico_id": d.cuarto_tecnico_id,
        "rack_id":           d.rack_id,
        "en_rack":           d.rack_id is not None,
        "posicion_u":        d.posicion_u,
        "tamano_u":          d.tamano_u,
        "ubicacion_fisica":  d.ubicacion_fisica,
        "ip_gestion":        d.ip_gestion,
        "num_puertos":       d.num_puertos,
        "conexion":          d.conexion,
        "datos_adicionales": d.datos_adicionales,
        "activo":            d.activo,
        "created_at":        d.created_at.isoformat() if d.created_at else None,
        # ── datos del activo (solo lectura) ──
        "activo_id":         d.activo_id,
        "consecutivo":       a.id_placa_activo if a else None,
        "nombre":            a.id_placa_activo if a else None,   # etiqueta principal = consecutivo
        "tipo_activo":       a.tipo_activo if a else None,
        "marca":             a.marca if a else None,
        "modelo":            a.modelo if a else None,
        "serial":            a.serial if a else None,
        "estado_activo":     a.estado if a else None,
    }


def _cuarto_dict(c: CuartoTecnico, rack_count: int = 0, device_count: int = 0) -> dict:
    return {
        "id":                c.id,
        "empresa_id":        c.empresa_id,
        "empresa":           {"id": c.empresa.id, "nombre": c.empresa.nombre_empresa} if c.empresa else None,
        "sede_catalogo_id":  c.sede_catalogo_id,
        "sede":              {"id": c.sede.id, "nombre": c.sede.valor} if c.sede else None,
        "identificador":     c.identificador,
        "nombre":            c.nombre,
        "descripcion":       c.descripcion,
        "ubicacion_detalle": c.ubicacion_detalle,
        "activo":            c.activo,
        "created_at":        c.created_at.isoformat() if c.created_at else None,
        "num_racks":         rack_count,
        "num_dispositivos":  device_count,
    }


def _scope_or_403(db: Session, current_user, empresa_id: str):
    """Valida que la empresa esté dentro del alcance del usuario (None = super_admin)."""
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")


def _get_cuarto_scoped(db: Session, current_user, cuarto_id: str) -> CuartoTecnico:
    c = db.query(CuartoTecnico).filter(CuartoTecnico.id == cuarto_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Cuarto técnico no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and c.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese cuarto técnico")
    return c


def _validar_sede(db: Session, sede_catalogo_id: str, empresa_id: str):
    """La sede debe ser un catálogo categoria='sede' que pertenezca a la empresa."""
    sede = db.query(Catalogo).filter(
        Catalogo.id == sede_catalogo_id,
        Catalogo.categoria == "sede",
    ).first()
    if not sede:
        raise HTTPException(status_code=400, detail="La sede indicada no existe")
    if sede.empresa_id != empresa_id:
        raise HTTPException(status_code=400, detail="La sede no pertenece a esa empresa")


def _rack_counts(db: Session, cuarto_ids: list) -> dict:
    """Conteo de racks activos por cuarto (batch, sin N+1)."""
    if not cuarto_ids:
        return {}
    rows = (
        db.query(Rack.cuarto_tecnico_id, func.count(Rack.id))
        .filter(Rack.cuarto_tecnico_id.in_(cuarto_ids), Rack.activo == True)
        .group_by(Rack.cuarto_tecnico_id)
        .all()
    )
    return {cid: n for cid, n in rows}


def _device_counts_by_cuarto(db: Session, cuarto_ids: list) -> dict:
    """Conteo de dispositivos activos por cuarto (batch, sin N+1)."""
    if not cuarto_ids:
        return {}
    rows = (
        db.query(DispositivoRed.cuarto_tecnico_id, func.count(DispositivoRed.id))
        .filter(DispositivoRed.cuarto_tecnico_id.in_(cuarto_ids), DispositivoRed.activo == True)
        .group_by(DispositivoRed.cuarto_tecnico_id)
        .all()
    )
    return {cid: n for cid, n in rows}


def _rack_usage(db: Session, rack_ids: list) -> dict:
    """Por rack: {rack_id: {"num": nº dispositivos, "usadas_u": suma de tamano_u}} (batch)."""
    if not rack_ids:
        return {}
    rows = (
        db.query(
            DispositivoRed.rack_id,
            func.count(DispositivoRed.id),
            func.coalesce(func.sum(DispositivoRed.tamano_u), 0),
        )
        .filter(DispositivoRed.rack_id.in_(rack_ids), DispositivoRed.activo == True)
        .group_by(DispositivoRed.rack_id)
        .all()
    )
    return {rid: {"num": int(num), "usadas_u": int(u)} for rid, num, u in rows}


def _get_dispositivo_scoped(db: Session, current_user, disp_id: str) -> DispositivoRed:
    d = db.query(DispositivoRed).filter(DispositivoRed.id == disp_id).first()
    if not d:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")
    # El alcance se hereda del cuarto → empresa.
    _get_cuarto_scoped(db, current_user, d.cuarto_tecnico_id)
    return d


def _validar_ubicacion_dispositivo(db, cuarto: CuartoTecnico, rack_id, posicion_u,
                                   tamano_u, exclude_id=None) -> dict:
    """Valida ubicación de un dispositivo. Devuelve los valores normalizados a persistir:
    {"rack_id","posicion_u","tamano_u"}.

    - rack_id nulo  → fuera de rack: posicion_u/tamano_u se anulan.
    - rack_id dado  → el rack debe pertenecer al mismo cuarto y estar activo;
      posicion_u requerida ≥1; tamano_u ≥1; debe caber en capacidad_u; sin solape
      con otro dispositivo activo del rack.
    """
    if not rack_id:
        return {"rack_id": None, "posicion_u": None, "tamano_u": None}

    rack = db.query(Rack).filter(Rack.id == rack_id, Rack.activo == True).first()
    if not rack:
        raise HTTPException(status_code=400, detail="El rack indicado no existe")
    if rack.cuarto_tecnico_id != cuarto.id:
        raise HTTPException(status_code=400, detail="El rack no pertenece a ese cuarto técnico")

    if posicion_u is None:
        raise HTTPException(status_code=400, detail="La posición (U) es obligatoria para un dispositivo en rack")
    size = tamano_u if tamano_u is not None else 1
    if posicion_u < 1:
        raise HTTPException(status_code=400, detail="La posición (U) debe ser ≥ 1")
    if size < 1:
        raise HTTPException(status_code=400, detail="El tamaño (U) debe ser ≥ 1")
    tope = posicion_u + size - 1
    if tope > rack.capacidad_u:
        raise HTTPException(
            status_code=400,
            detail=f"No cabe en el rack: ocuparía U{posicion_u}–U{tope} y el rack tiene {rack.capacidad_u}U",
        )

    # Sin solape con otros dispositivos activos del mismo rack.
    otros = db.query(DispositivoRed).filter(
        DispositivoRed.rack_id == rack_id,
        DispositivoRed.activo == True,
    )
    if exclude_id:
        otros = otros.filter(DispositivoRed.id != exclude_id)
    for o in otros.all():
        if o.posicion_u is None:
            continue
        o_size = o.tamano_u or 1
        o_ini, o_fin = o.posicion_u, o.posicion_u + o_size - 1
        if posicion_u <= o_fin and o_ini <= tope:
            placa = o.equipo.id_placa_activo if o.equipo else "otro dispositivo"
            raise HTTPException(
                status_code=400,
                detail=f"Se solapa con «{placa}» (ocupa U{o_ini}–U{o_fin})",
            )
    return {"rack_id": rack_id, "posicion_u": posicion_u, "tamano_u": size}


# ── Cuartos técnicos ────────────────────────────────────────────────────────--

@router.get("/cuartos")
def listar_cuartos(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.ver"),
):
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    query = db.query(CuartoTecnico).filter(CuartoTecnico.activo == True)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(CuartoTecnico.empresa_id == empresa_id)
        else:
            query = query.filter(CuartoTecnico.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(CuartoTecnico.empresa_id == empresa_id)

    cuartos = query.order_by(CuartoTecnico.identificador).all()
    ids = [c.id for c in cuartos]
    rack_counts = _rack_counts(db, ids)
    dev_counts  = _device_counts_by_cuarto(db, ids)
    return [_cuarto_dict(c, rack_count=rack_counts.get(c.id, 0),
                         device_count=dev_counts.get(c.id, 0)) for c in cuartos]


@router.get("/cuartos/{cuarto_id}")
def obtener_cuarto(
    cuarto_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.ver"),
):
    c = _get_cuarto_scoped(db, current_user, cuarto_id)
    racks = (
        db.query(Rack)
        .filter(Rack.cuarto_tecnico_id == c.id, Rack.activo == True)
        .order_by(Rack.orden.asc(), Rack.nombre.asc())
        .all()
    )
    usage = _rack_usage(db, [r.id for r in racks])
    dev_count = _device_counts_by_cuarto(db, [c.id]).get(c.id, 0)
    result = _cuarto_dict(c, rack_count=len(racks), device_count=dev_count)
    result["racks"] = [
        _rack_dict(r, usadas_u=usage.get(r.id, {}).get("usadas_u", 0),
                   num_dispositivos=usage.get(r.id, {}).get("num", 0))
        for r in racks
    ]
    return result


@router.post("/cuartos", status_code=status.HTTP_201_CREATED)
def crear_cuarto(
    data: CuartoCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    _scope_or_403(db, current_user, data.empresa_id)

    identificador = (data.identificador or "").strip()
    if not identificador:
        raise HTTPException(status_code=400, detail="El identificador es obligatorio")

    _validar_sede(db, data.sede_catalogo_id, data.empresa_id)

    cuarto = CuartoTecnico(
        empresa_id=data.empresa_id,
        sede_catalogo_id=data.sede_catalogo_id,
        identificador=identificador,
        nombre=(data.nombre or None),
        descripcion=(data.descripcion or None),
        ubicacion_detalle=(data.ubicacion_detalle or None),
        created_by=current_user.id,
    )
    db.add(cuarto)
    db.commit()
    db.refresh(cuarto)
    return _cuarto_dict(cuarto, rack_count=0)


@router.put("/cuartos/{cuarto_id}")
def actualizar_cuarto(
    cuarto_id: str,
    data: CuartoUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    c = _get_cuarto_scoped(db, current_user, cuarto_id)

    if data.sede_catalogo_id is not None:
        _validar_sede(db, data.sede_catalogo_id, c.empresa_id)
        c.sede_catalogo_id = data.sede_catalogo_id
    if data.identificador is not None:
        ident = data.identificador.strip()
        if not ident:
            raise HTTPException(status_code=400, detail="El identificador no puede estar vacío")
        c.identificador = ident
    if data.nombre is not None:            c.nombre = data.nombre or None
    if data.descripcion is not None:       c.descripcion = data.descripcion or None
    if data.ubicacion_detalle is not None: c.ubicacion_detalle = data.ubicacion_detalle or None

    db.commit()
    db.refresh(c)
    rc = _rack_counts(db, [c.id]).get(c.id, 0)
    dc = _device_counts_by_cuarto(db, [c.id]).get(c.id, 0)
    return _cuarto_dict(c, rack_count=rc, device_count=dc)


@router.delete("/cuartos/{cuarto_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_cuarto(
    cuarto_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    c = _get_cuarto_scoped(db, current_user, cuarto_id)
    # Regla segura: no permitir eliminar un cuarto que aún tiene racks activos.
    racks_activos = db.query(Rack).filter(
        Rack.cuarto_tecnico_id == c.id, Rack.activo == True
    ).count()
    if racks_activos:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar: el cuarto técnico tiene {racks_activos} rack(s). "
                   f"Elimina primero los racks.",
        )
    c.activo = False
    db.commit()


# ── Racks ──────────────────────────────────────────────────────────────────--

@router.get("/cuartos/{cuarto_id}/racks")
def listar_racks(
    cuarto_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.ver"),
):
    c = _get_cuarto_scoped(db, current_user, cuarto_id)
    racks = (
        db.query(Rack)
        .filter(Rack.cuarto_tecnico_id == c.id, Rack.activo == True)
        .order_by(Rack.orden.asc(), Rack.nombre.asc())
        .all()
    )
    usage = _rack_usage(db, [r.id for r in racks])
    return [
        _rack_dict(r, usadas_u=usage.get(r.id, {}).get("usadas_u", 0),
                   num_dispositivos=usage.get(r.id, {}).get("num", 0))
        for r in racks
    ]


@router.post("/cuartos/{cuarto_id}/racks", status_code=status.HTTP_201_CREATED)
def crear_rack(
    cuarto_id: str,
    data: RackCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    c = _get_cuarto_scoped(db, current_user, cuarto_id)

    nombre = (data.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del rack es obligatorio")

    capacidad = data.capacidad_u if data.capacidad_u is not None else 42
    if capacidad <= 0:
        raise HTTPException(status_code=400, detail="La capacidad (U) debe ser mayor que 0")

    rack = Rack(
        cuarto_tecnico_id=c.id,
        nombre=nombre,
        capacidad_u=capacidad,
        descripcion=(data.descripcion or None),
        orden=(data.orden if data.orden is not None else 0),
        created_by=current_user.id,
    )
    db.add(rack)
    db.commit()
    db.refresh(rack)
    return _rack_dict(rack)


def _get_rack_scoped(db: Session, current_user, rack_id: str) -> Rack:
    r = db.query(Rack).filter(Rack.id == rack_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Rack no encontrado")
    # El alcance del rack se hereda del cuarto → empresa.
    _get_cuarto_scoped(db, current_user, r.cuarto_tecnico_id)
    return r


@router.put("/racks/{rack_id}")
def actualizar_rack(
    rack_id: str,
    data: RackUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    r = _get_rack_scoped(db, current_user, rack_id)

    if data.nombre is not None:
        nombre = data.nombre.strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="El nombre del rack no puede estar vacío")
        r.nombre = nombre
    if data.capacidad_u is not None:
        if data.capacidad_u <= 0:
            raise HTTPException(status_code=400, detail="La capacidad (U) debe ser mayor que 0")
        r.capacidad_u = data.capacidad_u
    if data.descripcion is not None: r.descripcion = data.descripcion or None
    if data.orden is not None:       r.orden = data.orden

    # Al reducir capacidad, avisar si algún dispositivo montado quedaría fuera de rango.
    if data.capacidad_u is not None:
        disp = db.query(DispositivoRed).filter(
            DispositivoRed.rack_id == r.id, DispositivoRed.activo == True,
            DispositivoRed.posicion_u.isnot(None),
        ).all()
        for d in disp:
            tope = d.posicion_u + (d.tamano_u or 1) - 1
            if tope > r.capacidad_u:
                placa = d.equipo.id_placa_activo if d.equipo else "un dispositivo"
                raise HTTPException(
                    status_code=400,
                    detail=f"No se puede reducir a {r.capacidad_u}U: «{placa}» ocupa hasta U{tope}",
                )

    db.commit()
    db.refresh(r)
    u = _rack_usage(db, [r.id]).get(r.id, {})
    return _rack_dict(r, usadas_u=u.get("usadas_u", 0), num_dispositivos=u.get("num", 0))


@router.delete("/racks/{rack_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_rack(
    rack_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    r = _get_rack_scoped(db, current_user, rack_id)
    disp = db.query(DispositivoRed).filter(
        DispositivoRed.rack_id == r.id, DispositivoRed.activo == True
    ).count()
    if disp:
        raise HTTPException(
            status_code=409,
            detail=f"No se puede eliminar: el rack tiene {disp} dispositivo(s). "
                   f"Muévelos o elimínalos primero.",
        )
    r.activo = False
    db.commit()


# ── Dispositivos de red (montajes de activos) ────────────────────────────────--

def _activos_map(db: Session, disp_list) -> dict:
    """Carga en LOTE los activos de una lista de montajes → {activo_id: Activo} (sin N+1)."""
    ids = list({d.activo_id for d in disp_list})
    if not ids:
        return {}
    return {a.id: a for a in db.query(Activo).filter(Activo.id.in_(ids)).all()}


def _historial_activo(db: Session, activo_id: str, responsable: str, tipo_movimiento: str, obs: str):
    """Registra un movimiento en la hoja de vida del activo (mismo mecanismo que
    asignaciones/estados: una fila en historial_movimientos). NO crea Asignacion/Acta."""
    db.add(HistorialMovimiento(
        id_activo=activo_id,
        tipo_movimiento=tipo_movimiento,
        responsable=responsable,
        observaciones=obs,
    ))


def _mount_desc(db: Session, cuarto: CuartoTecnico, rack_id) -> str:
    """Texto legible del punto de montaje para el historial: 'Rack A · CT-001' o
    'Fuera de rack · CT-001'."""
    if rack_id:
        rk = db.query(Rack).filter(Rack.id == rack_id).first()
        lugar = rk.nombre if rk else "rack"
    else:
        lugar = "Fuera de rack"
    return f"{lugar} · {cuarto.identificador}"


@router.get("/activos-montables")
def activos_montables(
    cuarto_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.ver"),
):
    """Activos que se pueden montar en este cuarto: disponibles, de tipo de red y no
    montados ya en otro sitio. Reutiliza el patrón de /activos/disponibles."""
    c = _get_cuarto_scoped(db, current_user, cuarto_id)
    disponibles = (
        db.query(Activo)
        .filter(Activo.empresa_id == c.empresa_id, Activo.estado == "disponible")
        .order_by(Activo.id_placa_activo)
        .all()
    )
    montados = {row[0] for row in db.query(DispositivoRed.activo_id)
                .filter(DispositivoRed.activo == True).all()}
    tipos_red = _tipos_red_set(db)   # una sola consulta al catálogo
    out = []
    for a in disponibles:
        if a.id in montados or a.tipo_activo not in tipos_red:
            continue
        out.append({
            "id":              a.id,
            "id_placa_activo": a.id_placa_activo,
            "tipo_activo":     a.tipo_activo,
            "marca":           a.marca,
            "modelo":          a.modelo,
            "serial":          a.serial,
        })
    return out


@router.get("/cuartos/{cuarto_id}/dispositivos")
def listar_dispositivos_cuarto(
    cuarto_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.ver"),
):
    c = _get_cuarto_scoped(db, current_user, cuarto_id)
    disp = (
        db.query(DispositivoRed)
        .filter(DispositivoRed.cuarto_tecnico_id == c.id, DispositivoRed.activo == True)
        .all()
    )
    amap = _activos_map(db, disp)
    en_rack = [_dispositivo_dict(d, amap.get(d.activo_id)) for d in disp if d.rack_id]
    fuera   = [_dispositivo_dict(d, amap.get(d.activo_id)) for d in disp if not d.rack_id]
    en_rack.sort(key=lambda x: (x["rack_id"], x["posicion_u"] or 0))
    fuera.sort(key=lambda x: (x["consecutivo"] or "").lower())
    return {"en_rack": en_rack, "fuera_de_rack": fuera, "total": len(disp)}


@router.get("/racks/{rack_id}/dispositivos")
def listar_dispositivos_rack(
    rack_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.ver"),
):
    r = _get_rack_scoped(db, current_user, rack_id)
    disp = (
        db.query(DispositivoRed)
        .filter(DispositivoRed.rack_id == r.id, DispositivoRed.activo == True)
        .order_by(DispositivoRed.posicion_u.asc())
        .all()
    )
    amap = _activos_map(db, disp)
    return [_dispositivo_dict(d, amap.get(d.activo_id)) for d in disp]


@router.post("/dispositivos", status_code=status.HTTP_201_CREATED)
def montar_dispositivo(
    data: DispositivoCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    """MONTA un activo existente. Valida disponibilidad/tipo/duplicado, fija estado
    del activo a 'asignado' y registra el movimiento en su hoja de vida."""
    c = _get_cuarto_scoped(db, current_user, data.cuarto_tecnico_id)

    activo = db.query(Activo).filter(Activo.id == data.activo_id).first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    if activo.empresa_id != c.empresa_id:
        raise HTTPException(status_code=400, detail="El activo no pertenece a la empresa del cuarto técnico")
    if not es_tipo_red(db, activo.tipo_activo):
        raise HTTPException(status_code=400,
                            detail=f"El activo (tipo «{activo.tipo_activo}») no es un dispositivo de red")
    if activo.estado != "disponible":
        raise HTTPException(status_code=400,
                            detail=f"Solo se pueden montar activos disponibles. «{activo.id_placa_activo}» está: {activo.estado}")
    ya_montado = db.query(DispositivoRed).filter(
        DispositivoRed.activo_id == activo.id, DispositivoRed.activo == True).first()
    if ya_montado:
        raise HTTPException(status_code=409, detail="Ese activo ya está montado en un cuarto/rack")

    ubic = _validar_ubicacion_dispositivo(db, c, data.rack_id, data.posicion_u, data.tamano_u)

    d = DispositivoRed(
        activo_id=activo.id,
        cuarto_tecnico_id=c.id,
        rack_id=ubic["rack_id"],
        posicion_u=ubic["posicion_u"],
        tamano_u=ubic["tamano_u"],
        ubicacion_fisica=(data.ubicacion_fisica or None),
        ip_gestion=(data.ip_gestion or None),
        num_puertos=data.num_puertos,
        conexion=(data.conexion or None),
        datos_adicionales=(data.datos_adicionales or None),
        created_by=current_user.id,
    )
    db.add(d)
    # Estado del activo → asignado (mismo mecanismo que asignaciones: estado + historial;
    # SIN acta, SIN responsable, SIN Asignacion).
    activo.estado = "asignado"
    _historial_activo(db, activo.id, current_user.nombre, "asignacion",
                      f"Montado en {_mount_desc(db, c, ubic['rack_id'])}")
    db.commit()
    db.refresh(d)
    return _dispositivo_dict(d, activo)


@router.put("/dispositivos/{disp_id}")
def actualizar_dispositivo(
    disp_id: str,
    data: DispositivoUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    """Edita SOLO datos de montaje/red (mover rack↔fuera, reposicionar, ip/puertos/
    conexion/datos). NO cambia el estado del activo (sigue 'asignado' mientras montado)."""
    d = _get_dispositivo_scoped(db, current_user, disp_id)
    cuarto = db.query(CuartoTecnico).filter(CuartoTecnico.id == d.cuarto_tecnico_id).first()

    # rack_id trae el sentinel "__keep__" cuando no se quiere tocar la ubicación.
    mover = data.rack_id != "__keep__"
    if mover:
        nuevo_tam = data.tamano_u if data.tamano_u is not None else (d.tamano_u or 1)
        ubic = _validar_ubicacion_dispositivo(db, cuarto, data.rack_id, data.posicion_u,
                                              nuevo_tam, exclude_id=d.id)
        d.rack_id    = ubic["rack_id"]
        d.posicion_u = ubic["posicion_u"]
        d.tamano_u   = ubic["tamano_u"]
    elif (data.posicion_u is not None or data.tamano_u is not None) and d.rack_id:
        nueva_pos = data.posicion_u if data.posicion_u is not None else d.posicion_u
        nuevo_tam = data.tamano_u if data.tamano_u is not None else (d.tamano_u or 1)
        ubic = _validar_ubicacion_dispositivo(db, cuarto, d.rack_id, nueva_pos,
                                              nuevo_tam, exclude_id=d.id)
        d.posicion_u = ubic["posicion_u"]
        d.tamano_u   = ubic["tamano_u"]

    if data.ubicacion_fisica is not None: d.ubicacion_fisica = data.ubicacion_fisica or None
    if data.ip_gestion is not None:        d.ip_gestion = data.ip_gestion or None
    if data.num_puertos is not None:       d.num_puertos = data.num_puertos
    if data.conexion is not None:          d.conexion = data.conexion or None
    if data.datos_adicionales is not None: d.datos_adicionales = data.datos_adicionales or None

    db.commit()
    db.refresh(d)
    return _dispositivo_dict(d, d.equipo)


@router.delete("/dispositivos/{disp_id}")
def desmontar_dispositivo(
    disp_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.gestionar"),
):
    """DESMONTA el activo: elimina (soft) el montaje y devuelve el activo a
    'disponible' — SOLO si sigue en el 'asignado' que fijó el montaje. Si su estado
    cambió por otro flujo, NO lo sobreescribe: avisa."""
    d = _get_dispositivo_scoped(db, current_user, disp_id)
    activo = d.equipo
    cuarto = db.query(CuartoTecnico).filter(CuartoTecnico.id == d.cuarto_tecnico_id).first()
    desc = _mount_desc(db, cuarto, d.rack_id) if cuarto else "cuarto técnico"

    d.activo = False  # soft-delete del montaje

    warning = None
    if activo and activo.estado == "asignado":
        activo.estado = "disponible"
        _historial_activo(db, activo.id, current_user.nombre, "devolucion",
                          f"Desmontado de {desc}")
    elif activo:
        warning = (f"El montaje se retiró, pero el activo «{activo.id_placa_activo}» no estaba "
                   f"'asignado' (está: {activo.estado}); su estado no se modificó.")
        _historial_activo(db, activo.id, current_user.nombre, "cambio_estado",
                          f"Desmontado de {desc} (estado no modificado: {activo.estado})")
    db.commit()
    return {"ok": True, "warning": warning,
            "estado_activo": activo.estado if activo else None}


# ── Export PDF del cuarto técnico (solo lectura, en memoria) ─────────────────--

@router.get("/cuartos/{cuarto_id}/export-pdf")
def exportar_cuarto_pdf(
    cuarto_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("redes.ver"),
):
    """Genera (en memoria, sin persistir) un PDF con el cuarto técnico: todos sus
    racks dibujados FULL lado a lado + los dispositivos fuera de rack. Documento de
    consulta del estado ACTUAL — no cambia nada."""
    c = _get_cuarto_scoped(db, current_user, cuarto_id)   # 404 + scope 403

    racks = (
        db.query(Rack)
        .filter(Rack.cuarto_tecnico_id == c.id, Rack.activo == True)
        .order_by(Rack.orden.asc(), Rack.nombre.asc())
        .all()
    )
    disp = (
        db.query(DispositivoRed)
        .filter(DispositivoRed.cuarto_tecnico_id == c.id, DispositivoRed.activo == True)
        .all()
    )
    amap = _activos_map(db, disp)                 # batch, sin N+1
    usage = _rack_usage(db, [r.id for r in racks])

    # Dispositivos por rack + fuera de rack, ya con datos del activo
    por_rack, fuera = {}, []
    for d in disp:
        dd = _dispositivo_dict(d, amap.get(d.activo_id))
        if dd["rack_id"]:
            por_rack.setdefault(dd["rack_id"], []).append(dd)
        else:
            fuera.append(dd)

    racks_ctx = []
    for r in racks:
        rd = _rack_dict(r, usadas_u=usage.get(r.id, {}).get("usadas_u", 0),
                        num_dispositivos=usage.get(r.id, {}).get("num", 0))
        racks_ctx.append({
            "nombre": r.nombre,
            "capacidad_u": r.capacidad_u,
            "usadas_u": rd["usadas_u"],
            "libres_u": rd["libres_u"],
            "rows": _rack_layout({"capacidad_u": r.capacidad_u}, por_rack.get(r.id, [])),
        })

    fuera_ctx = [{
        "consecutivo": d["consecutivo"] or "—",
        "tipo": d["tipo_activo"] or "",
        "modelo": " ".join(x for x in [d.get("marca"), d.get("modelo")] if x),
        "ubicacion_fisica": d.get("ubicacion_fisica"),
        "ip": d.get("ip_gestion"),
        "puertos": d.get("num_puertos"),
        "conexion": d.get("conexion"),
        "color": _tipo_color(d["tipo_activo"]),
    } for d in sorted(fuera, key=lambda x: (x["consecutivo"] or "").lower())]

    empresa = c.empresa
    ctx = {
        "empresa_nombre": empresa.nombre_empresa if empresa else "—",
        "empresa_prefijo": empresa.prefijo if empresa else None,
        "sede": c.sede.valor if c.sede else "—",
        "identificador": c.identificador,
        "nombre": c.nombre,
        "ubicacion_detalle": c.ubicacion_detalle,
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "racks": racks_ctx,
        "fuera": fuera_ctx,
        "num_dispositivos": len(disp),
    }

    from services.pdf_service import generar_pdf_cuarto_red
    pdf_bytes = generar_pdf_cuarto_red(ctx)
    # nombre de archivo seguro
    safe = re.sub(r"[^A-Za-z0-9_\-]+", "_", (c.identificador or "cuarto")).strip("_") or "cuarto"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="cuarto_{safe}.pdf"'},
    )
