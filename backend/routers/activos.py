from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
from database import get_db
from models.activo import Activo
from models.empresa import Empresa
from models.usuario import Usuario
from models.historial import HistorialMovimiento
from models.asignacion import Asignacion
from models.acta import Acta, ActaDetalle
from models.accesorio import Accesorio
from routers.auth import get_current_user
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids
from services.prestamo_service import loan_dict
from services.inventario_service import crear_activo_core, calcular_fecha_obsolescencia, calcular_garantia_fin, _validar_ubicacion_o_400, resolver_custodio

router = APIRouter(prefix="/api/activos", tags=["Activos"])

# Estados válidos de un recurso (activo/accesorio)
ESTADOS_RECURSO = [
    "disponible", "asignado", "mantenimiento_preventivo", "mantenimiento_correctivo",
    "en_reparacion", "en_garantia", "retirado", "reservado",
]

# ── Schemas ──────────────────────────────────────────────
class ActivoCreate(BaseModel):
    empresa_id: str
    tipo_activo: str
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serial: Optional[str] = None
    numero_parte: Optional[str] = None
    codigo_contable: Optional[str] = None
    ubicacion: Optional[str] = None
    procesador: Optional[str] = None
    memoria_ram: Optional[str] = None
    disco_1: Optional[str] = None
    disco_2: Optional[str] = None
    resolucion: Optional[str] = None
    tipo_conexion: Optional[str] = None
    tamano_pantalla: Optional[str] = None
    imei: Optional[str] = None
    numero_telefono: Optional[str] = None
    capacidad_almacenamiento: Optional[str] = None
    color: Optional[str] = None
    tipo_impresora: Optional[str] = None
    ip_dispositivo: Optional[str] = None
    tipo_camara: Optional[str] = None
    canales_dvr: Optional[int] = None
    con_microfono: Optional[bool] = None
    extension: Optional[str] = None
    linea_telefono: Optional[str] = None
    tipo_telefono: Optional[str] = None
    capacidad_ups: Optional[str] = None
    tiempo_respaldo_ups: Optional[str] = None
    fecha_compra: Optional[date] = None
    fecha_obsolescencia: Optional[date] = None
    costo: Optional[float] = None
    observaciones: Optional[str] = None
    garantia_meses: Optional[int] = None
    garantia_fin: Optional[date] = None

class ActivoUpdate(BaseModel):
    tipo_activo: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serial: Optional[str] = None
    numero_parte: Optional[str] = None
    codigo_contable: Optional[str] = None
    ubicacion: Optional[str] = None
    procesador: Optional[str] = None
    memoria_ram: Optional[str] = None
    disco_1: Optional[str] = None
    disco_2: Optional[str] = None
    resolucion: Optional[str] = None
    tipo_conexion: Optional[str] = None
    tamano_pantalla: Optional[str] = None
    imei: Optional[str] = None
    numero_telefono: Optional[str] = None
    capacidad_almacenamiento: Optional[str] = None
    color: Optional[str] = None
    tipo_impresora: Optional[str] = None
    ip_dispositivo: Optional[str] = None
    tipo_camara: Optional[str] = None
    canales_dvr: Optional[int] = None
    con_microfono: Optional[bool] = None
    extension: Optional[str] = None
    linea_telefono: Optional[str] = None
    tipo_telefono: Optional[str] = None
    capacidad_ups: Optional[str] = None
    tiempo_respaldo_ups: Optional[str] = None
    fecha_compra: Optional[date] = None
    fecha_obsolescencia: Optional[date] = None
    costo: Optional[float] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None
    id_usuario: Optional[str] = None
    garantia_meses: Optional[int] = None
    garantia_fin: Optional[date] = None

class ActivoResponse(BaseModel):
    id: str
    id_placa_activo: str
    empresa_id: str
    id_usuario: Optional[str] = None
    tipo_activo: str
    marca: Optional[str]
    modelo: Optional[str]
    serial: Optional[str]
    numero_parte: Optional[str]
    codigo_contable: Optional[str] = None
    ubicacion: Optional[str] = None
    procesador: Optional[str]
    memoria_ram: Optional[str]
    disco_1: Optional[str]
    disco_2: Optional[str]
    resolucion: Optional[str] = None
    tipo_conexion: Optional[str] = None
    tamano_pantalla: Optional[str] = None
    imei: Optional[str] = None
    numero_telefono: Optional[str] = None
    capacidad_almacenamiento: Optional[str] = None
    color: Optional[str] = None
    tipo_impresora: Optional[str] = None
    ip_dispositivo: Optional[str] = None
    tipo_camara: Optional[str] = None
    canales_dvr: Optional[int] = None
    con_microfono: Optional[bool] = None
    extension: Optional[str] = None
    linea_telefono: Optional[str] = None
    tipo_telefono: Optional[str] = None
    capacidad_ups: Optional[str] = None
    tiempo_respaldo_ups: Optional[str] = None
    fecha_compra: Optional[date]
    fecha_obsolescencia: Optional[date]
    costo: Optional[float]
    estado: str
    observaciones: Optional[str]
    garantia_meses: Optional[int] = None
    garantia_fin: Optional[date] = None
    nombre_empresa: Optional[str] = None
    nombre_usuario: Optional[str] = None
    documento_usuario: Optional[str] = None
    custodio_id: Optional[str] = None
    custodio_nombre: Optional[str] = None
    custodio_documento: Optional[str] = None
    reserva_alta: Optional[str] = None
    reserva_fecha_limite: Optional[date] = None
    # Préstamo temporal (loan)
    es_prestamo: Optional[bool] = False
    fecha_limite_devolucion: Optional[date] = None
    prestamo_vencido: Optional[bool] = False
    dias_para_vencer: Optional[int] = None

    class Config:
        from_attributes = True

# ── Helper ───────────────────────────────────────────────
def activo_to_dict(activo: Activo) -> dict:
    return {
        **loan_dict(activo),
        "id":                    activo.id,
        "id_placa_activo":       activo.id_placa_activo,
        "empresa_id":            activo.empresa_id,
        "id_usuario":            activo.id_usuario,
        "tipo_activo":           activo.tipo_activo,
        "marca":                 activo.marca,
        "modelo":                activo.modelo,
        "serial":                activo.serial,
        "numero_parte":          activo.numero_parte,
        "codigo_contable":       activo.codigo_contable,
        "ubicacion":             activo.ubicacion,
        "procesador":            activo.procesador,
        "memoria_ram":           activo.memoria_ram,
        "disco_1":               activo.disco_1,
        "disco_2":               activo.disco_2,
        "resolucion":            activo.resolucion,
        "tipo_conexion":         activo.tipo_conexion,
        "tamano_pantalla":       activo.tamano_pantalla,
        "imei":                  activo.imei,
        "numero_telefono":       activo.numero_telefono,
        "capacidad_almacenamiento": activo.capacidad_almacenamiento,
        "color":                 activo.color,
        "tipo_impresora":        activo.tipo_impresora,
        "ip_dispositivo":        activo.ip_dispositivo,
        "tipo_camara":           activo.tipo_camara,
        "canales_dvr":           activo.canales_dvr,
        "con_microfono":         activo.con_microfono,
        "extension":             activo.extension,
        "linea_telefono":        activo.linea_telefono,
        "tipo_telefono":         activo.tipo_telefono,
        "capacidad_ups":         activo.capacidad_ups,
        "tiempo_respaldo_ups":   activo.tiempo_respaldo_ups,
        "fecha_compra":          activo.fecha_compra,
        "fecha_obsolescencia":   activo.fecha_obsolescencia,
        "costo":                 float(activo.costo) if activo.costo else None,
        "estado":                activo.estado,
        "observaciones":         activo.observaciones,
        "garantia_meses":        activo.garantia_meses,
        "garantia_fin":          activo.garantia_fin,
        "es_alquiler":           bool(activo.es_alquiler),
        "contrato_alquiler_id":  activo.contrato_alquiler_id,
        "nombre_empresa":        activo.empresa.nombre_empresa if activo.empresa else None,
        "nombre_usuario":        activo.usuario.nombre_completo if activo.usuario else None,
        "documento_usuario":     activo.usuario.documento if activo.usuario else None,
        "custodio_id":           activo.custodio_id,
        "custodio_nombre":       activo.custodio.nombre_completo if activo.custodio else None,
        "custodio_documento":    activo.custodio.documento if activo.custodio else None,
    }

# Adjunta info de la reserva activa (numero_alta + fecha_limite) a los recursos
# que están en estado "reservado". Consulta en lote para evitar N+1.
def _adjuntar_reservas(db: Session, dicts: list, tipo_recurso: str = "activo") -> list:
    from models.reserva import Reserva, ReservaItem
    ids = [d["id"] for d in dicts if d.get("estado") == "reservado"]
    if not ids:
        return dicts
    rows = db.query(ReservaItem, Reserva).join(
        Reserva, ReservaItem.reserva_id == Reserva.id
    ).filter(
        ReservaItem.tipo_recurso == tipo_recurso,
        ReservaItem.recurso_id.in_(ids),
        ReservaItem.estado == "reservado",
        Reserva.estado == "activa",
    ).all()
    m = {item.recurso_id: reserva for item, reserva in rows}
    for d in dicts:
        r = m.get(d["id"])
        if r:
            d["reserva_alta"] = r.numero_alta
            d["reserva_fecha_limite"] = r.fecha_limite
    return dicts


# ── Obsolescencia automática (años por tipo) — lógica compartida en el service ──
# Se reexporta el helper para el endpoint GET /calcular-obsolescencia y para reuso.
_calcular_fecha_obsolescencia = calcular_fecha_obsolescencia


# ── Endpoints ────────────────────────────────────────────
@router.get("", response_model=List[ActivoResponse])
def listar_activos(
    empresa_id: Optional[str] = None,
    estado: Optional[str] = None,
    tipo_activo: Optional[str] = None,
    incluir_retirados: bool = False,
    q: Optional[str] = Query(None, description="Buscar por placa, serial o modelo"),
    db: Session = Depends(get_db),
    current_user = require_permission("activos.ver")
):
    query = db.query(Activo)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Activo.empresa_id == empresa_id)
        else:
            query = query.filter(Activo.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Activo.empresa_id == empresa_id)
    if estado:
        query = query.filter(Activo.estado == estado)
    elif not incluir_retirados:
        query = query.filter(Activo.estado != "retirado")
    if tipo_activo:
        query = query.filter(Activo.tipo_activo.ilike(f"%{tipo_activo}%"))
    if q:
        query = query.filter(or_(
            Activo.id_placa_activo.ilike(f"%{q}%"),
            Activo.serial.ilike(f"%{q}%"),
            Activo.modelo.ilike(f"%{q}%"),
            Activo.marca.ilike(f"%{q}%"),
        ))
    return _adjuntar_reservas(db, [activo_to_dict(a) for a in query.order_by(Activo.id_placa_activo).all()])


@router.post("", response_model=ActivoResponse, status_code=status.HTTP_201_CREATED)
def crear_activo(
    data: ActivoCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.crear")
):
    # Reutiliza el núcleo compartido (placa, obsolescencia, historial) — el mismo
    # que usa el flujo de "crear inventario desde recepción".
    activo = crear_activo_core(db, data, current_user)
    db.commit()
    db.refresh(activo)
    return activo_to_dict(activo)


@router.get("/disponibles", response_model=List[ActivoResponse])
def listar_disponibles(
    empresa_id: str,
    tipo_activo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.ver")
):
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    query = db.query(Activo).filter(
        Activo.empresa_id == empresa_id,
        Activo.estado == "disponible"
    )
    if tipo_activo:
        query = query.filter(Activo.tipo_activo.ilike(f"%{tipo_activo}%"))
    return [activo_to_dict(a) for a in query.order_by(Activo.id_placa_activo).all()]


@router.get("/placa/{placa}", response_model=ActivoResponse)
def buscar_por_placa(
    placa: str,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.ver")
):
    activo = db.query(Activo).filter(
        Activo.id_placa_activo.ilike(placa)
    ).first()
    if not activo:
        raise HTTPException(status_code=404, detail=f"No se encontró activo con placa {placa}")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and activo.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese activo")
    return activo_to_dict(activo)


# ── Búsqueda de activos para la Hoja de Vida ──────────────
# (debe ir ANTES de "/{activo_id}" para no colisionar con esa ruta)
@router.get("/buscar-hoja-vida")
def buscar_hoja_vida(
    q: str,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.ver"),
):
    termino = (q or "").strip()
    if not termino:
        return []
    query = db.query(Activo)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        query = query.filter(Activo.empresa_id.in_(empresa_ids))

    up = termino.upper()
    exactos = query.filter(or_(
        Activo.id_placa_activo == up,
        Activo.serial == termino,
    )).all()
    parciales = query.filter(or_(
        Activo.id_placa_activo.ilike(f"%{termino}%"),
        Activo.serial.ilike(f"%{termino}%"),
        Activo.modelo.ilike(f"%{termino}%"),
        Activo.marca.ilike(f"%{termino}%"),
    )).all()

    vistos, resultado = set(), []
    for a in exactos + parciales:
        if a.id in vistos:
            continue
        vistos.add(a.id)
        resultado.append({
            "id": a.id, "id_placa_activo": a.id_placa_activo, "serial": a.serial,
            "tipo_activo": a.tipo_activo, "marca": a.marca, "modelo": a.modelo,
            "estado": a.estado,
            "nombre_usuario": a.usuario.nombre_completo if a.usuario else None,
        })
        if len(resultado) >= 10:
            break
    return resultado


# ── Preview de obsolescencia (para el formulario) ─────────
# Debe ir ANTES de "/{activo_id}" para no colisionar con esa ruta.
@router.get("/calcular-obsolescencia")
def calcular_obsolescencia(
    tipo_activo: str,
    fecha_compra: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.ver"),
):
    anios, fecha = _calcular_fecha_obsolescencia(db, tipo_activo, fecha_compra)
    return {"anios": anios, "fecha_obsolescencia": fecha}


# ── Preview de garantía (para el formulario) ──────────────
# Cálculo puro de fecha (base + meses); sin DB ni catálogo. Usado por activos Y
# accesorios. Debe ir ANTES de "/{activo_id}" para no colisionar con esa ruta.
@router.get("/calcular-garantia")
def calcular_garantia(
    meses: int,
    fecha_compra: Optional[date] = None,
    current_user = Depends(get_current_user),
):
    if meses < 0:
        raise HTTPException(status_code=400, detail="meses no puede ser negativo")
    return {"meses": meses, "garantia_fin": calcular_garantia_fin(meses, fecha_compra)}


@router.get("/{activo_id}", response_model=ActivoResponse)
def obtener_activo(
    activo_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.ver")
):
    activo = db.query(Activo).filter(Activo.id == activo_id).first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and activo.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este activo")
    return activo_to_dict(activo)


# ── Hoja de Vida del Activo (solo lectura) ────────────────
def _meses_entre(desde, hasta) -> int:
    if not desde:
        return 0
    d = desde.date() if hasattr(desde, "date") else desde
    h = hasta.date() if hasattr(hasta, "date") else hasta
    return max(0, (h.year - d.year) * 12 + (h.month - d.month))


def _dur_label(ini, fin, ahora):
    if not ini:
        return "—"
    fin2 = fin or ahora
    dias = max(0, (fin2 - ini).days)
    return f"{dias} días" if dias < 60 else f"{dias // 30} meses"


_TL_COLOR = {
    "creacion": "#A78BFF", "asignacion": "#06BFFF", "devolucion": "#00E5A0",
    "mantenimiento": "#FFB020", "upgrade": "#06BFFF", "cambio_estado": "#8b949e",
    "incidente": "#FF4D6D", "baja": "#FF4D6D",
}
_TL_ICON = {
    "creacion": "package", "asignacion": "user-plus", "devolucion": "rotate",
    "mantenimiento": "tool", "upgrade": "settings", "cambio_estado": "settings",
    "incidente": "alert-triangle", "baja": "trash",
}
_AVATAR_COLORS = ["#06BFFF", "#00E5A0", "#FFB020", "#A78BFF", "#FF6B6B", "#54A0FF"]

# Vida útil estimada por tipo de activo (años)
VIDA_UTIL_ESTIMADA = {
    "PC": 5, "Portatil": 5, "AIO": 5,
    "Monitor": 7, "Televisor": 7, "Video Beam": 6,
    "Celular": 3, "Tablet": 4, "Ipad": 4,
    "Impresora": 5, "Escaner": 6,
    "Camara": 6, "DVR": 6,
    "Diadema": 3, "Telefono": 7,
    "UPS": 4,
}
DEFAULT_VIDA_UTIL = 5


def _calcular_vida_util(activo, ahora: datetime) -> dict:
    inicio = activo.fecha_compra or (activo.created_at.date() if activo.created_at else ahora.date())
    if hasattr(inicio, "date"):
        inicio = inicio.date()
    hoy = ahora.date()
    anios = None
    if activo.fecha_obsolescencia:
        fin = activo.fecha_obsolescencia
        origen = "fecha_obsolescencia"
    else:
        anios = VIDA_UTIL_ESTIMADA.get(activo.tipo_activo, DEFAULT_VIDA_UTIL)
        fin = inicio + timedelta(days=anios * 365)
        origen = "estimada"
    total_dias = max(1, (fin - inicio).days)
    transcurrido_dias = (hoy - inicio).days
    porcentaje = max(0, min(100, round(transcurrido_dias / total_dias * 100)))
    dias_restantes = (fin - hoy).days
    if porcentaje >= 100:
        estado_vida, color = "Vida útil cumplida", "#FF4D6D"
    elif porcentaje >= 85:
        estado_vida, color = "Próximo a reemplazo", "#FFB020"
    elif porcentaje >= 60:
        estado_vida, color = "Madurez", "#06BFFF"
    else:
        estado_vida, color = "Óptimo", "#00E5A0"
    out = {
        "fecha_inicio": inicio, "fecha_fin": fin, "origen": origen,
        "total_dias": total_dias, "transcurrido_dias": transcurrido_dias,
        "porcentaje": porcentaje, "dias_restantes": dias_restantes,
        "estado_vida": estado_vida, "color": color,
    }
    if anios is not None:
        out["años_estimados"] = anios
    return out


@router.get("/{activo_id}/hoja-de-vida")
def get_hoja_de_vida(
    activo_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.ver"),
):
    activo = db.query(Activo).filter(Activo.id == activo_id).first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and activo.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese activo")

    ahora = datetime.now()
    fecha_base = activo.fecha_compra or activo.created_at or ahora
    edad_meses = _meses_entre(fecha_base, ahora)

    asigs = db.query(Asignacion).filter(Asignacion.id_activo == activo_id)\
        .order_by(Asignacion.fecha_asignacion.asc()).all()
    historial = db.query(HistorialMovimiento).filter(HistorialMovimiento.id_activo == activo_id)\
        .order_by(HistorialMovimiento.fecha_movimiento.asc()).all()

    # días totales en uso (suma de periodos asignado)
    dias_en_uso = 0
    for a in asigs:
        if a.fecha_asignacion:
            fin = a.fecha_devolucion or ahora
            dias_en_uso += max(0, (fin - a.fecha_asignacion).days)

    cant_mant = sum(1 for h in historial if h.tipo_movimiento == "mantenimiento")
    cant_inc  = sum(1 for h in historial if h.tipo_movimiento == "incidente")

    score = 100
    score -= min(cant_mant * 5, 20)
    score -= min(cant_inc * 10, 30)
    if edad_meses > 36: score -= 10
    if edad_meses > 48: score -= 10
    score = max(0, score)

    label_salud = "Excelente" if score > 90 else "Bueno" if score > 70 else "Regular" if score > 50 else "Crítico"

    costo = float(activo.costo) if activo.costo else 0.0
    costo_mant = 0.0
    inversion_total = costo + costo_mant

    # ── usuario actual ──
    usuario_actual = None
    if activo.id_usuario:
        u = db.query(Usuario).filter(Usuario.id == activo.id_usuario).first()
        if u:
            emp = db.query(Empresa).filter(Empresa.id == u.empresa_id).first()
            usuario_actual = {
                "id": u.id, "nombre_completo": u.nombre_completo, "cargo": u.cargo,
                "area": u.area, "sede": u.sede, "correo": u.correo, "empresa_id": u.empresa_id,
                "nombre_empresa": emp.nombre_empresa if emp else None,
            }

    # ── accesorios del usuario actual ──
    accesorios_asignados = []
    if activo.id_usuario:
        accs = db.query(Accesorio).filter(
            Accesorio.id_usuario == activo.id_usuario,
            Accesorio.empresa_id == activo.empresa_id,
            Accesorio.estado == "asignado",
        ).all()
        accesorios_asignados = [{
            "id": ac.id, "id_placa_accesorio": ac.id_placa_accesorio,
            "tipo_accesorio": ac.tipo_accesorio, "marca": ac.marca, "modelo": ac.modelo,
        } for ac in accs]

    # ── línea de tiempo ──
    asig_actual = next((a for a in asigs if a.estado == "activa"), None)
    eventos = []
    eventos.append({
        "fecha": activo.created_at or fecha_base, "tipo": "creacion",
        "titulo": "Ingreso al inventario",
        "descripcion": f"Registrado como {activo.id_placa_activo}" + (f" · {activo.marca or ''} {activo.modelo or ''}".rstrip() if (activo.marca or activo.modelo) else ""),
        "icono": _TL_ICON["creacion"], "color": _TL_COLOR["creacion"],
        "duracion_dias": None, "es_actual": False,
    })
    for a in asigs:
        u = a.usuario
        nombre = u.nombre_completo if u else "—"
        fin = a.fecha_devolucion or ahora
        dur = max(0, (fin - a.fecha_asignacion).days) if a.fecha_asignacion else None
        partes = []
        if u and u.area: partes.append(u.area)
        if u and u.sede: partes.append(u.sede)
        eventos.append({
            "fecha": a.fecha_asignacion, "tipo": "asignacion",
            "titulo": f"Asignado a {nombre}",
            "descripcion": " · ".join(partes) or "Asignación registrada",
            "icono": _TL_ICON["asignacion"], "color": _TL_COLOR["asignacion"],
            "duracion_dias": dur, "es_actual": bool(asig_actual and a.id == asig_actual.id),
        })
        if a.estado == "devuelta" and a.fecha_devolucion:
            eventos.append({
                "fecha": a.fecha_devolucion, "tipo": "devolucion",
                "titulo": "Devuelto al inventario",
                "descripcion": f"Recibido por {a.recibido_por}" if a.recibido_por else "Devolución registrada",
                "icono": _TL_ICON["devolucion"], "color": _TL_COLOR["devolucion"],
                "duracion_dias": None, "es_actual": False,
            })
    for h in historial:
        obs = (h.observaciones or "")
        tm = h.tipo_movimiento
        tipo_ev = None
        if tm == "mantenimiento":
            tipo_ev = "mantenimiento"
        elif tm == "incidente":
            tipo_ev = "incidente"
        elif tm == "asignacion" and any(k in obs.lower() for k in ("upgrade", "ram", "ssd", "disco")):
            tipo_ev = "upgrade"
        elif tm == "baja":
            tipo_ev = "baja"
        # los cambio_estado se toman de CambioEstado (más detalle), no del historial
        if not tipo_ev:
            continue
        eventos.append({
            "fecha": h.fecha_movimiento, "tipo": tipo_ev,
            "titulo": {"mantenimiento": "Mantenimiento", "incidente": "Incidente",
                       "upgrade": "Mejora / Upgrade", "baja": "Baja / Retiro"}[tipo_ev],
            "descripcion": obs or (h.responsable or "—"),
            "icono": _TL_ICON[tipo_ev], "color": _TL_COLOR[tipo_ev],
            "duracion_dias": None, "es_actual": False,
        })

    # ── cambios de estado (CambioEstado) en la línea de tiempo ──
    _MANT_ESTADOS = {"mantenimiento_preventivo", "mantenimiento_correctivo", "en_reparacion", "en_garantia"}
    try:
        from models.cambio_estado import CambioEstado
        cambios = db.query(CambioEstado).filter(
            CambioEstado.tipo_recurso == "activo", CambioEstado.recurso_id == activo_id).all()
        for ce in cambios:
            es_mant = ce.estado_nuevo in _MANT_ESTADOS
            tipo_ev = "mantenimiento" if es_mant else "cambio_estado"
            partes = []
            if ce.tipo_mantenimiento: partes.append(f"Mant. {ce.tipo_mantenimiento}")
            if ce.cubierto_garantia: partes.append(f"garantía {ce.cubre_garantia or ''}".strip())
            if ce.ubicacion: partes.append(ce.ubicacion)
            if ce.descripcion: partes.append(ce.descripcion)
            if ce.resultado_mant: partes.append(f"resultado: {ce.resultado_mant}")
            desc = " · ".join(partes) or f"{ce.estado_anterior} → {ce.estado_nuevo}"
            eventos.append({
                "fecha": ce.fecha, "tipo": tipo_ev,
                "titulo": "Mantenimiento" if es_mant else "Cambio de estado",
                "descripcion": desc,
                "icono": _TL_ICON[tipo_ev], "color": _TL_COLOR[tipo_ev],
                "duracion_dias": None, "es_actual": False,
            })
    except Exception:
        pass

    eventos.sort(key=lambda e: e["fecha"] or ahora)

    # ── historial de responsables (asignaciones + huecos en inventario) ──
    responsables = []
    cursor = activo.created_at or fecha_base
    pal = 0
    def _ini(nombre):
        nombre = (nombre or "").strip()
        return (nombre[:2].upper() if nombre else "??")
    for a in asigs:
        if a.fecha_asignacion and cursor and (a.fecha_asignacion - cursor).days >= 1:
            responsables.append({
                "tipo": "inventario", "iniciales": "CT", "nombre": "Disponible en CT",
                "rol": "Inventario TI", "fecha_inicio": cursor, "fecha_fin": a.fecha_asignacion,
                "duracion_label": _dur_label(cursor, a.fecha_asignacion, ahora),
                "es_actual": False, "color_avatar": "#8b949e",
            })
        u = a.usuario
        responsables.append({
            "tipo": "usuario", "iniciales": _ini(u.nombre_completo if u else "?"),
            "nombre": u.nombre_completo if u else "—", "rol": (u.cargo if u and u.cargo else "—"),
            "fecha_inicio": a.fecha_asignacion, "fecha_fin": a.fecha_devolucion,
            "duracion_label": _dur_label(a.fecha_asignacion, a.fecha_devolucion, ahora),
            "es_actual": a.fecha_devolucion is None and a.estado == "activa",
            "color_avatar": _AVATAR_COLORS[pal % len(_AVATAR_COLORS)],
        })
        pal += 1
        cursor = a.fecha_devolucion  # None si sigue activa
    if cursor is not None:
        responsables.append({
            "tipo": "inventario", "iniciales": "CT", "nombre": "Disponible en CT",
            "rol": "Inventario TI", "fecha_inicio": cursor, "fecha_fin": None,
            "duracion_label": _dur_label(cursor, None, ahora),
            "es_actual": True, "color_avatar": "#8b949e",
        })

    # ── actas (por id_activo o por ActaDetalle) ──
    acta_ids = {row[0] for row in db.query(Acta.id).filter(Acta.id_activo == activo_id).all()}
    acta_ids |= {row[0] for row in db.query(ActaDetalle.acta_id).filter(ActaDetalle.id_activo == activo_id).all()}
    actas_objs = db.query(Acta).filter(Acta.id.in_(acta_ids)).order_by(Acta.fecha_entrega.desc()).all() if acta_ids else []

    def _num_acta(url):
        if not url: return None
        return url.split("/")[-1].replace(".pdf", "")

    actas_out = [{
        "id": ac.id, "tipo": ac.tipo, "fecha_entrega": ac.fecha_entrega,
        "firmada": ac.firmada, "fecha_firma": ac.fecha_firma, "url_pdf": ac.url_pdf,
        "numero": _num_acta(ac.url_pdf),
        "responsable_entrega": ac.responsable_entrega, "responsable_recibe": ac.responsable_recibe,
        "usuario_nombre": ac.usuario.nombre_completo if ac.usuario else None,
    } for ac in actas_objs]

    # ── asignaciones (historial completo) ──
    asigs_out = []
    for a in sorted(asigs, key=lambda x: x.fecha_asignacion or ahora, reverse=True):
        u = a.usuario
        emp = db.query(Empresa).filter(Empresa.id == a.empresa_id).first()
        dur = max(0, ((a.fecha_devolucion or ahora) - a.fecha_asignacion).days) if a.fecha_asignacion else None
        actas_asig = [x for x in actas_out if x["usuario_nombre"] == (u.nombre_completo if u else None)]
        asigs_out.append({
            "id": a.id, "fecha_asignacion": a.fecha_asignacion, "fecha_devolucion": a.fecha_devolucion,
            "estado": a.estado, "duracion_dias": dur,
            "usuario": {
                "nombre_completo": u.nombre_completo if u else "—",
                "documento": u.documento if u else None, "cargo": u.cargo if u else None,
                "empresa": emp.nombre_empresa if emp else None,
            },
            "actas": actas_asig,
        })

    # ── mantenimientos / upgrades ──
    mantenimientos = [{
        "id": h.id, "created_at": h.fecha_movimiento, "tipo_cambio": h.tipo_movimiento,
        "observaciones": h.observaciones, "responsable": h.responsable,
    } for h in sorted(
        [h for h in historial if h.tipo_movimiento in ("mantenimiento", "upgrade")],
        key=lambda x: x.fecha_movimiento or ahora, reverse=True)]

    # ── mantenimientos preventivos (módulo mantenimiento, tareas completadas) ──
    mant_preventivos = []
    try:
        from models.mantenimiento import TareaMantenimiento
        from models.usuario_sistema import UsuarioSistema as _US
        tareas = db.query(TareaMantenimiento).filter(
            TareaMantenimiento.activo_id == activo_id,
            TareaMantenimiento.estado == "completada",
        ).order_by(TareaMantenimiento.fecha_fin_ejec.desc()).all()
        for t in tareas:
            tec = db.query(_US).filter(_US.id == t.tecnico_id).first() if t.tecnico_id else None
            its = t.checklist_items
            total = len(its)
            hechos = sum(1 for i in its if (i.tipo_item == "check" and i.realizado is not None)
                         or (i.tipo_item == "dato" and i.valor_dato))
            mant_preventivos.append({
                "id": t.id,
                "fecha": t.fecha_fin_ejec,
                "plan": t.plan.nombre if t.plan else None,
                "tecnico": tec.nombre if tec else None,
                "resumen": f"{hechos}/{total} ítems",
                "observaciones": t.observaciones,
                "tiene_acta": bool(t.url_acta_pdf),
            })
    except Exception:
        mant_preventivos = []

    # ── auditoría (todos los movimientos) ──
    auditoria = [{
        "id": h.id, "fecha": h.fecha_movimiento, "tipo_movimiento": h.tipo_movimiento,
        "responsable": h.responsable, "observaciones": h.observaciones,
    } for h in sorted(historial, key=lambda x: x.fecha_movimiento or ahora, reverse=True)]

    base = activo_to_dict(activo)
    base.update({"edad_meses": edad_meses, "dias_en_uso": dias_en_uso, "score_salud": score})

    vida_util = _calcular_vida_util(activo, ahora)

    return {
        "activo": base,
        "vida_util": vida_util,
        "usuario_actual": usuario_actual,
        "accesorios_asignados": accesorios_asignados,
        "stats": {
            "total_asignaciones": len(asigs),
            "total_mantenimientos": cant_mant,
            "total_incidentes": cant_inc,
            "costo_mantenimientos": costo_mant,
            "inversion_total": inversion_total,
            "edad_meses": edad_meses,
            "score_salud": score,
            "label_salud": label_salud,
        },
        "linea_de_tiempo": eventos,
        "historial_responsables": responsables,
        "asignaciones": asigs_out,
        "mantenimientos": mantenimientos,
        "mantenimientos_preventivos": mant_preventivos,
        "actas": actas_out,
        "auditoria": auditoria,
    }


# ── Custodio (empleado responsable mientras el activo está disponible) ────────
class CustodioIn(BaseModel):
    custodio_documento: str


@router.post("/{activo_id}/custodio")
def set_custodio_activo(
    activo_id: str,
    data: CustodioIn,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear")
):
    activo = db.query(Activo).filter(Activo.id == activo_id).first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and activo.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese activo")
    if activo.estado != "disponible":
        raise HTTPException(status_code=400, detail="Solo se puede asignar custodio a un recurso disponible")
    emp = resolver_custodio(db, activo.empresa_id, data.custodio_documento)
    activo.custodio_id = emp.id
    db.add(HistorialMovimiento(
        id_activo=activo.id, tipo_movimiento="custodio", responsable=current_user.email,
        observaciones=f"Custodio asignado: {emp.nombre_completo} ({emp.documento})"))
    db.commit()
    db.refresh(activo)
    return activo_to_dict(activo)


@router.delete("/{activo_id}/custodio")
def remove_custodio_activo(
    activo_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear")
):
    activo = db.query(Activo).filter(Activo.id == activo_id).first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and activo.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese activo")
    if activo.custodio_id:
        db.add(HistorialMovimiento(
            id_activo=activo.id, tipo_movimiento="custodio", responsable=current_user.email,
            observaciones="Custodio retirado"))
    activo.custodio_id = None
    db.commit()
    db.refresh(activo)
    return activo_to_dict(activo)


@router.put("/{activo_id}", response_model=ActivoResponse)
def actualizar_activo(
    activo_id: str,
    data: ActivoUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.editar")
):
    activo = db.query(Activo).filter(Activo.id == activo_id).first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and activo.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este activo")

    # Un activo retirado (dado de baja) es de SOLO LECTURA: se puede consultar pero
    # no modificar. Cualquier cambio sobre él se rechaza.
    if activo.estado == "retirado":
        raise HTTPException(
            status_code=409,
            detail="El activo está retirado y no puede modificarse. Solo puede consultarse.",
        )

    # El estado NO se modifica desde este endpoint. Los cambios de estado se realizan
    # EXCLUSIVAMENTE a través de /api/estados/* (cambio de estado, baja) y de los flujos
    # de asignación/devolución, que escriben sobre el modelo directamente. Aquí se ignora
    # cualquier 'estado' recibido (defensa en profundidad) para no saltarse esa lógica.
    update_fields = data.model_dump(exclude_unset=True)
    update_fields.pop("estado", None)

    # Ubicación obligatoria cuando el activo no está asignado (sigue siendo editable libremente)
    if activo.estado != "asignado" and "ubicacion" in update_fields:
        ubic_final = update_fields["ubicacion"]
        if not ubic_final or not str(ubic_final).strip():
            raise HTTPException(status_code=400, detail="La ubicación es obligatoria cuando el estado no es 'Asignado'")
    # Validar/canonicalizar la ubicación contra el catálogo de la empresa
    if "ubicacion" in update_fields and update_fields["ubicacion"]:
        update_fields["ubicacion"] = _validar_ubicacion_o_400(db, activo.empresa_id, update_fields["ubicacion"])

    for campo, valor in update_fields.items():
        setattr(activo, campo, valor)

    db.commit()
    db.refresh(activo)
    return activo_to_dict(activo)
