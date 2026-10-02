"""
Router del módulo Mantenimiento Preventivo — Fase 1: CRUD de PLANES (plantillas).
Prefix: /api/mantenimiento

Coexiste con el mantenimiento reactivo (estados.py) — no lo toca.
Fase 1 = solo planes. Tareas/ejecución/calendario/acta/alertas = fases posteriores.

Aislamiento multiempresa (get_user_empresa_ids) — mismo patrón que reservas/compras.
Regla clave: dentro de una empresa, un tipo_activo no puede estar en dos planes
ACTIVOS a la vez (para que la recomendación futura sea inequívoca).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from pathlib import Path
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_, func
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime, timedelta
import calendar

from database import get_db
from models.catalogo import Catalogo
from models.empresa import Empresa
from models.activo import Activo
from models.usuario import Usuario
from models.usuario_sistema import UsuarioSistema
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso
from models.historial import HistorialMovimiento
from models.mantenimiento import (
    PlanMantenimiento, PlanTipoActivo, PlanChecklistItem,
    TareaMantenimiento, TareaChecklistItem,
)
from dependencies.rbac import require_permission, require_any_permission
from services.rbac_service import get_user_empresa_ids, is_super_admin, has_permission
from services.mantenimiento_service import (
    coverage_activa, activos_con_tarea_abierta, tecnico_puede_ejecutar,
    crear_tarea_preventiva, ESTADOS_TAREA_ABIERTA,
)

router = APIRouter(prefix="/api/mantenimiento", tags=["Mantenimiento Preventivo"])

_SECCIONES = {"diagnostico", "hardware", "software"}
_TIPOS_ITEM = {"check", "dato"}


# ── Schemas ───────────────────────────────────────────────
class ChecklistItemIn(BaseModel):
    seccion: str
    tipo_item: str
    texto: str
    orden: Optional[int] = 0


class PlanIn(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    periodicidad_meses: Optional[int] = 12
    codigo_formato: Optional[str] = "FTIN09"
    version_formato: Optional[str] = "1.1"
    fecha_emision_formato: Optional[date] = None
    clasificacion: Optional[str] = "Interno"
    proceso: Optional[str] = "Servicio"
    tipos: List[str] = []
    checklist: List[ChecklistItemIn] = []


class PlanUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    periodicidad_meses: Optional[int] = None
    codigo_formato: Optional[str] = None
    version_formato: Optional[str] = None
    fecha_emision_formato: Optional[date] = None
    clasificacion: Optional[str] = None
    proceso: Optional[str] = None
    tipos: Optional[List[str]] = None
    checklist: Optional[List[ChecklistItemIn]] = None


# ── Helpers ───────────────────────────────────────────────
def _tipos_validos_catalogo(db: Session) -> set:
    """Valores activos del catálogo global 'tipo_activo'."""
    rows = db.query(Catalogo).filter(
        Catalogo.categoria == "tipo_activo", Catalogo.activo == True).all()
    return {r.valor for r in rows}


def _validar_tipos(db: Session, tipos: List[str]):
    tipos = [t.strip() for t in (tipos or []) if t and t.strip()]
    if not tipos:
        raise HTTPException(status_code=400, detail="El plan debe cubrir al menos un tipo de activo")
    dedup = list(dict.fromkeys(tipos))
    validos = _tipos_validos_catalogo(db)
    for t in dedup:
        if t not in validos:
            raise HTTPException(status_code=400, detail=f"El tipo de activo '{t}' no existe en el catálogo")
    return dedup


def _validar_unicidad_tipos(db: Session, tipos: List[str], exclude_plan_id: Optional[str] = None):
    """GLOBAL: ningún tipo puede estar en dos planes ACTIVOS a la vez."""
    q = db.query(PlanTipoActivo).join(
        PlanMantenimiento, PlanTipoActivo.plan_id == PlanMantenimiento.id).filter(
        PlanMantenimiento.activo == True,
        PlanTipoActivo.tipo_activo.in_(tipos),
    )
    if exclude_plan_id:
        q = q.filter(PlanMantenimiento.id != exclude_plan_id)
    conf = q.first()
    if conf:
        raise HTTPException(
            status_code=400,
            detail=f"El tipo '{conf.tipo_activo}' ya está cubierto por un plan activo")


def _validar_checklist(items: List[ChecklistItemIn]):
    for it in (items or []):
        if it.seccion not in _SECCIONES:
            raise HTTPException(status_code=400, detail=f"Sección inválida: {it.seccion}")
        if it.tipo_item not in _TIPOS_ITEM:
            raise HTTPException(status_code=400, detail=f"Tipo de ítem inválido: {it.tipo_item}")
        if not it.texto or not it.texto.strip():
            raise HTTPException(status_code=400, detail="Cada ítem del checklist requiere texto")


def _plan_dict(p: PlanMantenimiento, full: bool = False) -> dict:
    base = {
        "id": p.id, "nombre": p.nombre,
        "descripcion": p.descripcion, "periodicidad_meses": p.periodicidad_meses,
        "activo": bool(p.activo),
        "codigo_formato": p.codigo_formato, "version_formato": p.version_formato,
        "fecha_emision_formato": p.fecha_emision_formato,
        "clasificacion": p.clasificacion, "proceso": p.proceso,
        "tipos": [t.tipo_activo for t in p.tipos],
        "checklist_count": len(p.checklist_items),
        "created_at": p.created_at,
    }
    if full:
        base["checklist"] = [{
            "id": i.id, "seccion": i.seccion, "tipo_item": i.tipo_item,
            "texto": i.texto, "orden": i.orden,
        } for i in sorted(p.checklist_items, key=lambda x: (x.seccion, x.orden))]
    return base


# ── Endpoints ─────────────────────────────────────────────
@router.get("/planes")
def listar_planes(
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    # Planes GLOBALES: cualquiera con mantenimiento.planes ve todos.
    query = db.query(PlanMantenimiento)
    if activo is not None:
        query = query.filter(PlanMantenimiento.activo == activo)
    rows = query.order_by(PlanMantenimiento.created_at.desc()).all()
    return [_plan_dict(p) for p in rows]


@router.get("/planes/{plan_id}")
def obtener_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    p = db.query(PlanMantenimiento).filter(PlanMantenimiento.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    return _plan_dict(p, full=True)


@router.post("/planes", status_code=status.HTTP_201_CREATED)
def crear_plan(
    data: PlanIn,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    if not data.nombre or not data.nombre.strip():
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")

    tipos = _validar_tipos(db, data.tipos)
    _validar_checklist(data.checklist)
    _validar_unicidad_tipos(db, tipos)   # plan nuevo = activo (unicidad global)

    p = PlanMantenimiento(
        nombre=data.nombre.strip(),
        descripcion=data.descripcion,
        periodicidad_meses=data.periodicidad_meses if data.periodicidad_meses else 12,
        activo=True,
        codigo_formato=data.codigo_formato or "FTIN09",
        version_formato=data.version_formato or "1.1",
        fecha_emision_formato=data.fecha_emision_formato,
        clasificacion=data.clasificacion or "Interno",
        proceso=data.proceso or "Servicio",
        created_by=current_user.id,
    )
    db.add(p)
    db.flush()
    for t in tipos:
        db.add(PlanTipoActivo(plan_id=p.id, tipo_activo=t))
    for it in data.checklist:
        db.add(PlanChecklistItem(
            plan_id=p.id, seccion=it.seccion, tipo_item=it.tipo_item,
            texto=it.texto.strip(), orden=it.orden or 0))
    db.commit()
    db.refresh(p)
    return _plan_dict(p, full=True)


@router.put("/planes/{plan_id}")
def editar_plan(
    plan_id: str,
    data: PlanUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    p = db.query(PlanMantenimiento).filter(PlanMantenimiento.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Plan no encontrado")

    if data.nombre is not None:
        if not data.nombre.strip():
            raise HTTPException(status_code=400, detail="El nombre no puede quedar vacío")
        p.nombre = data.nombre.strip()
    if data.descripcion is not None:
        p.descripcion = data.descripcion
    if data.periodicidad_meses is not None:
        p.periodicidad_meses = data.periodicidad_meses
    if data.codigo_formato is not None:
        p.codigo_formato = data.codigo_formato
    if data.version_formato is not None:
        p.version_formato = data.version_formato
    if data.fecha_emision_formato is not None:
        p.fecha_emision_formato = data.fecha_emision_formato
    if data.clasificacion is not None:
        p.clasificacion = data.clasificacion
    if data.proceso is not None:
        p.proceso = data.proceso

    # Reemplazo de tipos (con validación de unicidad si el plan está activo)
    if data.tipos is not None:
        tipos = _validar_tipos(db, data.tipos)
        if p.activo:
            _validar_unicidad_tipos(db, tipos, exclude_plan_id=p.id)
        for t in list(p.tipos):
            db.delete(t)
        db.flush()
        for t in tipos:
            db.add(PlanTipoActivo(plan_id=p.id, tipo_activo=t))

    # Reemplazo del checklist (editar el plan NO afecta tareas históricas: las
    # tareas copian estos ítems como snapshot al crearse — fases posteriores)
    if data.checklist is not None:
        _validar_checklist(data.checklist)
        for it in list(p.checklist_items):
            db.delete(it)
        db.flush()
        for it in data.checklist:
            db.add(PlanChecklistItem(
                plan_id=p.id, seccion=it.seccion, tipo_item=it.tipo_item,
                texto=it.texto.strip(), orden=it.orden or 0))

    db.commit()
    db.refresh(p)
    return _plan_dict(p, full=True)


@router.post("/planes/{plan_id}/desactivar")
def desactivar_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    p = db.query(PlanMantenimiento).filter(PlanMantenimiento.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    p.activo = False   # soft-deactivate (puede estar referenciado por tareas futuras)
    db.commit()
    db.refresh(p)
    return _plan_dict(p, full=True)


@router.post("/planes/{plan_id}/activar")
def activar_plan(
    plan_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    p = db.query(PlanMantenimiento).filter(PlanMantenimiento.id == plan_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Plan no encontrado")
    # Al reactivar, re-validar que sus tipos no choquen con otro plan activo (global)
    tipos = [t.tipo_activo for t in p.tipos]
    if tipos:
        _validar_unicidad_tipos(db, tipos, exclude_plan_id=p.id)
    p.activo = True
    db.commit()
    db.refresh(p)
    return _plan_dict(p, full=True)


# ══════════════════════════════════════════════════════════
#  FASE 2 — RECOMENDACIÓN + PLANIFICACIÓN
# ══════════════════════════════════════════════════════════
_ESTADOS_ELEGIBLES = ("asignado", "disponible")      # candidatos a mantenimiento preventivo
_ESTADOS_TAREA_ABIERTA = ESTADOS_TAREA_ABIERTA       # (compartido con el servicio)
# UI: L M X J V (S D) → Python weekday() Lun=0 … Dom=6
_DIAS_VALIDOS = {0, 1, 2, 3, 4, 5, 6}


def _empresa_scope(db: Session, current_user, empresa_id: Optional[str]):
    """Devuelve (empresa_ids_permitidos | None, filtro_empresa_id). None = todas (super_admin)."""
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    return empresa_ids


def _meses_entre(desde: date, hasta: date) -> int:
    """Meses completos entre dos fechas (para 'Hace N meses')."""
    m = (hasta.year - desde.year) * 12 + (hasta.month - desde.month)
    if hasta.day < desde.day:
        m -= 1
    return max(0, m)


# Cobertura y elegibilidad viven ahora en services.mantenimiento_service (compartidas
# con la devolución). Se conservan los nombres privados como alias por compatibilidad.
_coverage_activa = coverage_activa


def _ultimo_preventivo_map(db: Session, activo_ids: List[str]) -> dict:
    """activo_id → fecha (date) del último mantenimiento preventivo COMPLETADO."""
    if not activo_ids:
        return {}
    rows = db.query(TareaMantenimiento.activo_id, TareaMantenimiento.fecha_fin_ejec).filter(
        TareaMantenimiento.activo_id.in_(activo_ids),
        TareaMantenimiento.estado == "completada",
        TareaMantenimiento.fecha_fin_ejec != None,
    ).all()
    ult = {}
    for aid, fin in rows:
        f = fin.date() if isinstance(fin, datetime) else fin
        if aid not in ult or (f and f > ult[aid]):
            ult[aid] = f
    return ult


_activos_con_tarea_abierta = activos_con_tarea_abierta


@router.get("/recomendados")
def listar_recomendados(
    empresa_id: Optional[str] = None,
    tipo_activo: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    """Equipos DUE para mantenimiento preventivo (las 4 reglas)."""
    empresa_ids = _empresa_scope(db, current_user, empresa_id)
    cobertura = _coverage_activa(db)      # global: tipo_activo → plan
    if not cobertura:
        return []
    tipos_cubiertos = set(cobertura.keys())

    q = db.query(Activo).filter(
        Activo.estado.in_(_ESTADOS_ELEGIBLES),
        Activo.tipo_activo.in_(tipos_cubiertos),
    )
    if empresa_id:
        q = q.filter(Activo.empresa_id == empresa_id)
    elif empresa_ids is not None:
        q = q.filter(Activo.empresa_id.in_(empresa_ids))
    if tipo_activo:
        q = q.filter(Activo.tipo_activo == tipo_activo)
    candidatos = q.all()

    ids = [a.id for a in candidatos]
    con_tarea = _activos_con_tarea_abierta(db, ids)
    ultimos = _ultimo_preventivo_map(db, ids)
    hoy = date.today()

    out = []
    for a in candidatos:
        plan = cobertura.get(a.tipo_activo)
        if not plan:
            continue                          # su tipo no tiene plan activo (global)
        if a.id in con_tarea:
            continue                          # ya tiene tarea abierta
        ult = ultimos.get(a.id)
        meses = _meses_entre(ult, hoy) if ult else None
        if ult is not None and meses < (plan.periodicidad_meses or 12):
            continue                          # aún dentro de la ventana de periodicidad
        out.append({
            "activo_id": a.id, "placa": a.id_placa_activo, "tipo_activo": a.tipo_activo,
            "marca": a.marca, "modelo": a.modelo, "empresa_id": a.empresa_id,
            "nombre_empresa": a.empresa.nombre_empresa if a.empresa else None,
            "estado": a.estado,
            "tenedor": (a.usuario.nombre_completo if (a.estado == "asignado" and a.usuario) else None),
            "ultimo_mantenimiento": ("Nunca" if ult is None else f"Hace {meses} mes(es)"),
            "meses_desde": meses,
            "plan_id": plan.id, "plan_nombre": plan.nombre,
            "periodicidad_meses": plan.periodicidad_meses,
        })
    out.sort(key=lambda r: (r["nombre_empresa"] or "", r["tipo_activo"] or "", r["placa"] or ""))
    return out


@router.get("/tecnicos")
def listar_tecnicos(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    """Usuarios elegibles como técnico: tienen mantenimiento.ejecutar (por rol) +
    super_admins. Empresa-scoped por la asignación de rol."""
    empresa_ids = _empresa_scope(db, current_user, empresa_id)

    # Usuarios cuyo rol activo concede mantenimiento.ejecutar
    q = db.query(UsuarioSistema).join(
        UsuarioRol, UsuarioRol.usuario_sistema_id == UsuarioSistema.id).join(
        Rol, Rol.id == UsuarioRol.rol_id).join(
        RolPermiso, RolPermiso.rol_id == Rol.id).join(
        Permiso, Permiso.id == RolPermiso.permiso_id).filter(
        Permiso.codigo == "mantenimiento.ejecutar",
        UsuarioRol.activo == True, Rol.activo == True, UsuarioSistema.activo == True,
    )
    if empresa_id:
        q = q.filter(UsuarioRol.empresa_id == empresa_id)
    elif empresa_ids is not None:
        q = q.filter(or_(UsuarioRol.empresa_id.in_(empresa_ids), UsuarioRol.empresa_id.is_(None)))
    tecnicos = {u.id: u for u in q.all()}

    # super_admins (tienen todos los permisos aunque no vía un rol-permiso explícito)
    for u in db.query(UsuarioSistema).filter(UsuarioSistema.activo == True).all():
        if u.id not in tecnicos and is_super_admin(db, u.id):
            tecnicos[u.id] = u

    return sorted(
        [{"id": u.id, "nombre": u.nombre, "email": u.email} for u in tecnicos.values()],
        key=lambda x: x["nombre"] or "")


@router.get("/tecnicos-con-tareas")
def listar_tecnicos_con_tareas(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    """Técnicos DISTINTOS que tienen al menos una tarea asignada (para el filtro de
    'tareas programadas'). Derivado de datos reales — no incluye técnicos sin tareas.
    Empresa-scoped igual que la lista de tareas. Single join, sin N+1."""
    empresa_ids = _empresa_scope(db, current_user, empresa_id)
    q = db.query(UsuarioSistema.id, UsuarioSistema.nombre).join(
        TareaMantenimiento, TareaMantenimiento.tecnico_id == UsuarioSistema.id)
    if empresa_id:
        q = q.filter(TareaMantenimiento.empresa_id == empresa_id)
    elif empresa_ids is not None:
        q = q.filter(TareaMantenimiento.empresa_id.in_(empresa_ids))
    rows = q.distinct().all()
    return sorted(
        [{"id": uid, "nombre": nombre} for uid, nombre in rows],
        key=lambda x: (x["nombre"] or "").lower())


@router.get("/tipos-cubiertos")
def listar_tipos_cubiertos(
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    """Lista de tipo_activo que tienen un plan de mantenimiento ACTIVO (global).
    La usa la devolución para decidir a qué equipos ofrecerles el checkbox de
    'programar mantenimiento' (los tipos sin plan no tienen checklist que aplicar)."""
    return sorted(coverage_activa(db).keys())


class RangoIn(BaseModel):
    tipo: str                       # "mes" | "semana" | "custom"
    desde: Optional[date] = None
    hasta: Optional[date] = None


class CrearTareasIn(BaseModel):
    activos_ids: List[str]
    tecnico_id: str
    rango: RangoIn
    dias_referencia: List[int]      # weekday() ints (Lun=0 … Dom=6)


def _resolver_rango(r: RangoIn):
    hoy = date.today()
    if r.tipo == "mes":
        desde = hoy.replace(day=1)
        # primer día del mes siguiente - 1
        nm = desde.replace(year=desde.year + 1, month=1) if desde.month == 12 else desde.replace(month=desde.month + 1)
        hasta = nm - timedelta(days=1)
    elif r.tipo == "semana":
        desde = hoy - timedelta(days=hoy.weekday())   # lunes
        hasta = desde + timedelta(days=6)             # domingo
    elif r.tipo == "custom":
        if not r.desde or not r.hasta:
            raise HTTPException(status_code=400, detail="El rango personalizado requiere desde y hasta")
        desde, hasta = r.desde, r.hasta
    else:
        raise HTTPException(status_code=400, detail="Tipo de rango inválido (mes | semana | custom)")
    if hasta < desde:
        raise HTTPException(status_code=400, detail="La fecha 'hasta' no puede ser anterior a 'desde'")
    return desde, hasta


def _fechas_candidatas(desde: date, hasta: date, dias_ref: List[int]) -> List[date]:
    dias = {d for d in dias_ref if d in _DIAS_VALIDOS}
    if not dias:
        raise HTTPException(status_code=400, detail="Debes marcar al menos un día de referencia válido")
    fechas, d = [], desde
    while d <= hasta:
        if d.weekday() in dias:
            fechas.append(d)
        d += timedelta(days=1)
    return fechas


_tecnico_puede_ejecutar = tecnico_puede_ejecutar


@router.post("/tareas", status_code=status.HTTP_201_CREATED)
def crear_tareas(
    data: CrearTareasIn,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    """Crea tareas de mantenimiento preventivo para los equipos seleccionados,
    distribuyendo fecha_programada por los días de referencia dentro del rango
    (rotación con wrap-módulo). Re-valida cada equipo (skip-with-reasons)."""
    if not data.activos_ids:
        raise HTTPException(status_code=400, detail="Selecciona al menos un equipo")
    tecnico = db.query(UsuarioSistema).filter(UsuarioSistema.id == data.tecnico_id).first()
    if not tecnico:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    if not _tecnico_puede_ejecutar(db, data.tecnico_id):
        raise HTTPException(status_code=400, detail="El técnico no tiene permiso para ejecutar mantenimientos")

    desde, hasta = _resolver_rango(data.rango)
    candidatas = _fechas_candidatas(desde, hasta, data.dias_referencia)
    if not candidatas:
        raise HTTPException(status_code=400, detail="Ningún día de referencia cae dentro del rango elegido")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    cobertura = _coverage_activa(db)      # global: tipo_activo → plan
    con_tarea = _activos_con_tarea_abierta(db, data.activos_ids)

    creadas, omitidos = [], []
    idx = 0
    for aid in data.activos_ids:
        a = db.query(Activo).filter(Activo.id == aid).first()
        if not a:
            omitidos.append({"activo_id": aid, "placa": None, "motivo": "El equipo no existe"})
            continue
        if empresa_ids is not None and a.empresa_id not in empresa_ids:
            omitidos.append({"activo_id": aid, "placa": a.id_placa_activo, "motivo": "Sin acceso a la empresa del equipo"})
            continue
        if a.estado not in _ESTADOS_ELEGIBLES:
            omitidos.append({"activo_id": aid, "placa": a.id_placa_activo, "motivo": f"Ya no está disponible (estado: {a.estado})"})
            continue
        if a.id in con_tarea:
            omitidos.append({"activo_id": aid, "placa": a.id_placa_activo, "motivo": "Ya tiene una tarea abierta"})
            continue
        plan = cobertura.get(a.tipo_activo)
        if not plan:
            omitidos.append({"activo_id": aid, "placa": a.id_placa_activo, "motivo": "Su tipo ya no tiene un plan activo"})
            continue

        fecha = candidatas[idx % len(candidatas)]   # rotación con wrap-módulo (siempre dentro del rango)
        idx += 1
        # Crear + snapshot vía helper compartido (idéntico a ad-hoc y devolución)
        tarea = crear_tarea_preventiva(db, a, plan, data.tecnico_id, fecha, current_user.id,
                                       origen="planificacion")
        con_tarea.add(a.id)   # evita duplicar si el mismo id viene repetido
        creadas.append({
            "tarea_id": tarea.id, "activo_id": a.id, "placa": a.id_placa_activo,
            "fecha_programada": fecha, "plan_nombre": plan.nombre,
        })

    db.commit()
    return {
        "creadas": creadas, "total_creadas": len(creadas),
        "omitidos": omitidos, "total_omitidos": len(omitidos),
        "rango": {"desde": desde, "hasta": hasta},
        "fechas_candidatas": candidatas,
    }


def _tarea_dict(t: TareaMantenimiento, db: Session, *,
                activos_map: Optional[dict] = None,
                tecnicos_map: Optional[dict] = None,
                planes_map: Optional[dict] = None,
                checklist_counts: Optional[dict] = None) -> dict:
    """Serializa una tarea. Los *_map opcionales permiten servir listas sin N+1
    (se resuelven por lote antes de llamar); si no se pasan, cae al lookup por fila
    (llamadas de un solo ítem: reprogramar/reasignar/cancelar/mis-tareas)."""
    if activos_map is not None:
        a = activos_map.get(t.activo_id)
    else:
        a = db.query(Activo).filter(Activo.id == t.activo_id).first()
    if not t.tecnico_id:
        tec = None
    elif tecnicos_map is not None:
        tec = tecnicos_map.get(t.tecnico_id)
    else:
        tec = db.query(UsuarioSistema).filter(UsuarioSistema.id == t.tecnico_id).first()
    if planes_map is not None:
        plan = planes_map.get(t.plan_id)
        plan_nombre = plan.nombre if plan else None
    else:
        plan_nombre = t.plan.nombre if t.plan else None
    if checklist_counts is not None:
        ccount = checklist_counts.get(t.id, 0)
    else:
        ccount = len(t.checklist_items)
    return {
        "id": t.id, "activo_id": t.activo_id,
        "placa": a.id_placa_activo if a else None,
        "tipo_activo": a.tipo_activo if a else None,
        "marca": a.marca if a else None, "modelo": a.modelo if a else None,
        "empresa_id": t.empresa_id,
        "nombre_empresa": a.empresa.nombre_empresa if (a and a.empresa) else None,
        "tecnico_id": t.tecnico_id, "tecnico": tec.nombre if tec else None,
        "plan_id": t.plan_id, "plan_nombre": plan_nombre,
        "estado": t.estado, "fecha_programada": t.fecha_programada,
        "checklist_count": ccount,
        "created_at": t.created_at,
    }


@router.get("/tareas")
def listar_tareas(
    estado: Optional[str] = None,
    tecnico_id: Optional[str] = None,
    empresa_id: Optional[str] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    fecha_filtro: Optional[str] = None,   # atajo: hoy | semana | mes | vencidas
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    empresa_ids = _empresa_scope(db, current_user, empresa_id)
    q = db.query(TareaMantenimiento)
    if empresa_id:
        q = q.filter(TareaMantenimiento.empresa_id == empresa_id)
    elif empresa_ids is not None:
        q = q.filter(TareaMantenimiento.empresa_id.in_(empresa_ids))
    if estado:
        q = q.filter(TareaMantenimiento.estado == estado)
    if tecnico_id:
        q = q.filter(TareaMantenimiento.tecnico_id == tecnico_id)

    # ── Fecha: atajo server-side (date.today(), consistente con el resto) ──
    # o rango personalizado (desde/hasta). "vencidas" = MISMA def. que el panel de
    # pendientes: abierta (ESTADOS_TAREA_ABIERTA) + fecha_programada pasada.
    hoy = date.today()
    if fecha_filtro == "hoy":
        q = q.filter(TareaMantenimiento.fecha_programada == hoy)
    elif fecha_filtro == "semana":
        ini = hoy - timedelta(days=hoy.weekday())      # lunes
        fin = ini + timedelta(days=6)                  # domingo
        q = q.filter(TareaMantenimiento.fecha_programada >= ini,
                     TareaMantenimiento.fecha_programada <= fin)
    elif fecha_filtro == "mes":
        ini, fin = _mes_rango(hoy)
        q = q.filter(TareaMantenimiento.fecha_programada >= ini,
                     TareaMantenimiento.fecha_programada <= fin)
    elif fecha_filtro == "vencidas":
        q = q.filter(TareaMantenimiento.estado.in_(_ESTADOS_TAREA_ABIERTA),
                     TareaMantenimiento.fecha_programada != None,
                     TareaMantenimiento.fecha_programada < hoy)
    if desde:
        q = q.filter(TareaMantenimiento.fecha_programada >= desde)
    if hasta:
        q = q.filter(TareaMantenimiento.fecha_programada <= hasta)

    # MySQL no soporta "NULLS LAST": empujamos los nulos al final con un flag ordenable
    rows = q.order_by((TareaMantenimiento.fecha_programada == None),
                      TareaMantenimiento.fecha_programada.asc(),
                      TareaMantenimiento.created_at.desc()).all()
    if not rows:
        return []

    # ── Enriquecimiento por LOTE (sin N+1) ──
    activo_ids  = {t.activo_id for t in rows if t.activo_id}
    tecnico_ids = {t.tecnico_id for t in rows if t.tecnico_id}
    plan_ids    = {t.plan_id for t in rows if t.plan_id}
    tarea_ids   = [t.id for t in rows]
    activos_map = {a.id: a for a in db.query(Activo).options(
        joinedload(Activo.empresa)).filter(Activo.id.in_(activo_ids)).all()} if activo_ids else {}
    tecnicos_map = {u.id: u for u in db.query(UsuarioSistema).filter(
        UsuarioSistema.id.in_(tecnico_ids)).all()} if tecnico_ids else {}
    planes_map = {p.id: p for p in db.query(PlanMantenimiento).filter(
        PlanMantenimiento.id.in_(plan_ids)).all()} if plan_ids else {}
    checklist_counts = dict(db.query(
        TareaChecklistItem.tarea_id, func.count(TareaChecklistItem.id)).filter(
        TareaChecklistItem.tarea_id.in_(tarea_ids)).group_by(
        TareaChecklistItem.tarea_id).all())

    return [_tarea_dict(t, db, activos_map=activos_map, tecnicos_map=tecnicos_map,
                        planes_map=planes_map, checklist_counts=checklist_counts)
            for t in rows]


# ══════════════════════════════════════════════════════════
#  FASE 3 — EJECUCIÓN (técnico)
# ══════════════════════════════════════════════════════════
_ESTADOS_INICIABLES = ("asignado", "disponible")


def _get_tarea_propia(db: Session, tarea_id: str, current_user, permitir_planner: bool = False):
    """Devuelve la tarea si el usuario es su técnico (o un planner si se permite)."""
    t = db.query(TareaMantenimiento).filter(TareaMantenimiento.id == tarea_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    es_tecnico = (t.tecnico_id == current_user.id)
    if not es_tecnico and not permitir_planner:
        raise HTTPException(status_code=403, detail="Esta tarea no está asignada a ti")
    return t


def _tarea_detalle_dict(t: TareaMantenimiento, db: Session) -> dict:
    a = db.query(Activo).filter(Activo.id == t.activo_id).first()
    empresa = a.empresa if a else None
    tec = db.query(UsuarioSistema).filter(UsuarioSistema.id == t.tecnico_id).first() if t.tecnico_id else None
    items = sorted(t.checklist_items, key=lambda x: (x.seccion, x.orden))
    return {
        "id": t.id, "estado": t.estado, "fecha_programada": t.fecha_programada,
        "fecha_inicio_ejec": t.fecha_inicio_ejec, "fecha_fin_ejec": t.fecha_fin_ejec,
        "observaciones": t.observaciones, "url_acta_pdf": t.url_acta_pdf,
        "tecnico_id": t.tecnico_id, "tecnico": tec.nombre if tec else None,
        "plan_id": t.plan_id, "plan_nombre": t.plan.nombre if t.plan else None,
        "activo": {
            "id": a.id if a else None,
            "placa": a.id_placa_activo if a else None,
            "tipo_activo": a.tipo_activo if a else None,
            "marca": a.marca if a else None, "modelo": a.modelo if a else None,
            "serial": a.serial if a else None,
            "estado": a.estado if a else None,
            "empresa_id": a.empresa_id if a else None,
            "nombre_empresa": empresa.nombre_empresa if empresa else None,
        } if a else None,
        "checklist": [{
            "id": i.id, "seccion": i.seccion, "tipo_item": i.tipo_item,
            "texto": i.texto, "orden": i.orden,
            "realizado": i.realizado, "valor_dato": i.valor_dato,
        } for i in items],
    }


def _hist(db, activo_id, responsable, obs):
    db.add(HistorialMovimiento(
        id_activo=activo_id, tipo_movimiento="mantenimiento",
        responsable=responsable, observaciones=obs))


def _mes_rango(hoy: date):
    desde = hoy.replace(day=1)
    fin = desde.replace(year=desde.year + 1, month=1) if desde.month == 12 else desde.replace(month=desde.month + 1)
    return desde, fin - timedelta(days=1)


@router.get("/mis-tareas")
def mis_tareas(
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.ejecutar"),
):
    hoy = date.today()
    mes_desde, mes_hasta = _mes_rango(hoy)

    # ── Tarjetas: tareas activas (pendiente + en_ejecucion) del técnico ──
    rows = db.query(TareaMantenimiento).filter(
        TareaMantenimiento.tecnico_id == current_user.id,
        TareaMantenimiento.estado.in_(("pendiente", "en_ejecucion")),
    ).order_by(
        (TareaMantenimiento.fecha_programada == None),
        TareaMantenimiento.fecha_programada.asc(),
    ).all()

    # Enriquecimiento en lote (sin N+1): activos + holder + último preventivo
    activo_ids = [t.activo_id for t in rows]
    activos = {a.id: a for a in db.query(Activo).filter(Activo.id.in_(activo_ids)).all()} if activo_ids else {}
    ultimos = _ultimo_preventivo_map(db, activo_ids)   # activo_id → fecha (reusa Fase 2)
    # holders (usuarios) en lote para los activos asignados
    holder_ids = [a.id_usuario for a in activos.values() if a.estado == "asignado" and a.id_usuario]
    holders = {u.id: u.nombre_completo for u in
               db.query(Usuario).filter(Usuario.id.in_(holder_ids)).all()} if holder_ids else {}

    tareas = []
    for t in rows:
        a = activos.get(t.activo_id)
        base = _tarea_dict(t, db)
        ult = ultimos.get(t.activo_id)
        meses = _meses_entre(ult, hoy) if ult else None
        base.update({
            "nombre_empresa": a.empresa.nombre_empresa if (a and a.empresa) else None,
            "activo_estado": a.estado if a else None,
            "tenedor": (holders.get(a.id_usuario) if (a and a.estado == "asignado") else None),
            "ultimo_mantenimiento": ("Nunca" if ult is None else f"Hace {meses} mes(es)"),
            "meses_desde": meses,
        })
        tareas.append(base)

    # ── Resumen del mes (por fecha_programada) + vencidos (cualquier mes) ──
    def _cnt(*estados, en_mes=True):
        q = db.query(TareaMantenimiento).filter(
            TareaMantenimiento.tecnico_id == current_user.id,
            TareaMantenimiento.estado.in_(estados))
        if en_mes:
            q = q.filter(TareaMantenimiento.fecha_programada >= mes_desde,
                         TareaMantenimiento.fecha_programada <= mes_hasta)
        return q.count()

    completadas = _cnt("completada")
    pendientes_mes = _cnt("pendiente", "en_ejecucion")
    total_mes = completadas + pendientes_mes
    pct = round(completadas / total_mes * 100) if total_mes else 0
    vencidos = db.query(TareaMantenimiento).filter(
        TareaMantenimiento.tecnico_id == current_user.id,
        TareaMantenimiento.estado == "pendiente",
        TareaMantenimiento.fecha_programada != None,
        TareaMantenimiento.fecha_programada < hoy,
    ).count()

    return {
        "resumen": {
            "mes": {"completadas": completadas, "pendientes": pendientes_mes,
                    "total": total_mes, "pct": pct},
            "vencidos": vencidos,
        },
        "tareas": tareas,
    }


@router.get("/tareas/{tarea_id}")
def obtener_tarea(
    tarea_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.ejecutar"),
):
    # técnico propio o planner (mantenimiento.planes lo maneja el frontend; aquí
    # permitimos al técnico dueño ver su tarea)
    t = _get_tarea_propia(db, tarea_id, current_user, permitir_planner=True)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and t.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta tarea")
    return _tarea_detalle_dict(t, db)


@router.post("/tareas/{tarea_id}/iniciar")
def iniciar_tarea(
    tarea_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.ejecutar"),
):
    t = _get_tarea_propia(db, tarea_id, current_user)
    if t.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"Solo se puede iniciar una tarea pendiente (estado: {t.estado})")
    a = db.query(Activo).filter(Activo.id == t.activo_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    if a.estado not in _ESTADOS_INICIABLES:
        raise HTTPException(
            status_code=400,
            detail=f"El equipo está en '{a.estado}' y no puede entrar a mantenimiento preventivo ahora")

    # Guardar estado previo EN LA TAREA + flip (ubicación/id_usuario intactos)
    t.estado_activo_previo = a.estado
    t.usuario_previo = a.id_usuario
    a.estado = "mantenimiento_preventivo"
    t.estado = "en_ejecucion"
    t.fecha_inicio_ejec = datetime.now()
    _hist(db, a.id, current_user.nombre if hasattr(current_user, "nombre") else current_user.email,
          f"Inicio mantenimiento preventivo — plan {t.plan.nombre if t.plan else ''}")
    db.commit()
    db.refresh(t)
    return _tarea_detalle_dict(t, db)


# ── AD-HOC (mantenimiento sin programar) ──────────────────
@router.get("/adhoc/equipos")
def adhoc_equipos_elegibles(
    q: Optional[str] = None,
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.ejecutar"),
):
    """Equipos elegibles para mantenimiento ad-hoc: tipo cubierto por un plan
    activo + estado asignado/disponible + acceso a la empresa. SIN los filtros
    de 'sin tarea abierta' ni '12 meses' (el técnico puede re-hacerlo)."""
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    cobertura = _coverage_activa(db)
    if not cobertura:
        return []
    query = db.query(Activo).filter(
        Activo.estado.in_(_ESTADOS_ELEGIBLES),
        Activo.tipo_activo.in_(list(cobertura.keys())),
    )
    if empresa_id:
        query = query.filter(Activo.empresa_id == empresa_id)
    elif empresa_ids is not None:
        query = query.filter(Activo.empresa_id.in_(empresa_ids))
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Activo.id_placa_activo.ilike(like), Activo.serial.ilike(like),
            Activo.marca.ilike(like), Activo.modelo.ilike(like)))
    activos = query.order_by(Activo.id_placa_activo.asc()).limit(50).all()
    holder_ids = [a.id_usuario for a in activos if a.estado == "asignado" and a.id_usuario]
    holders = {u.id: u.nombre_completo for u in
               db.query(Usuario).filter(Usuario.id.in_(holder_ids)).all()} if holder_ids else {}
    out = []
    for a in activos:
        plan = cobertura.get(a.tipo_activo)
        out.append({
            "activo_id": a.id, "placa": a.id_placa_activo, "tipo_activo": a.tipo_activo,
            "marca": a.marca, "modelo": a.modelo, "estado": a.estado,
            "nombre_empresa": a.empresa.nombre_empresa if a.empresa else None,
            "tenedor": (holders.get(a.id_usuario) if a.estado == "asignado" else None),
            "plan_nombre": plan.nombre if plan else None,
        })
    return out


class AdhocIn(BaseModel):
    activo_id: str


@router.post("/tareas/adhoc", status_code=status.HTTP_201_CREATED)
def crear_tarea_adhoc(
    data: AdhocIn,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.ejecutar"),
):
    """Crea una tarea de mantenimiento sobre la marcha (asignada al técnico que
    actúa), copia el snapshot del plan y la INICIA de inmediato. Devuelve la
    tarea en ejecución para abrir la pantalla de ejecución."""
    a = db.query(Activo).filter(Activo.id == data.activo_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and a.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a la empresa del equipo")
    if a.estado not in _ESTADOS_ELEGIBLES:
        raise HTTPException(status_code=400, detail=f"El equipo está en '{a.estado}' y no es elegible para mantenimiento ahora")
    cobertura = _coverage_activa(db)
    plan = cobertura.get(a.tipo_activo)
    if not plan:
        raise HTTPException(status_code=400, detail=f"Ningún plan activo cubre el tipo '{a.tipo_activo}' — no hay checklist que aplicar")

    # Crear + snapshot vía helper compartido (idéntico a planificación y devolución)
    t = crear_tarea_preventiva(db, a, plan, current_user.id, date.today(), current_user.id,
                               origen="adhoc")

    # Iniciar de inmediato (mismo mecanismo que iniciar_tarea)
    t.estado_activo_previo = a.estado
    t.usuario_previo = a.id_usuario
    a.estado = "mantenimiento_preventivo"
    t.estado = "en_ejecucion"
    t.fecha_inicio_ejec = datetime.now()
    _hist(db, a.id, current_user.nombre if hasattr(current_user, "nombre") else current_user.email,
          f"Mantenimiento preventivo sin programar (ad-hoc) — plan {plan.nombre}")
    db.commit()
    db.refresh(t)
    return _tarea_detalle_dict(t, db)


class ReprogramarIn(BaseModel):
    fecha_programada: date


@router.post("/tareas/{tarea_id}/reprogramar")
def reprogramar_tarea(
    tarea_id: str,
    data: ReprogramarIn,
    db: Session = Depends(get_db),
    current_user = require_any_permission("mantenimiento.ejecutar", "mantenimiento.planes"),
):
    """Cambia la fecha programada de una tarea PENDIENTE. Puede hacerlo:
      - el técnico asignado (su propia tarea), o
      - un planner con mantenimiento.planes EN LA EMPRESA de la tarea.
    Se permite cualquier fecha (conocen su disponibilidad)."""
    t = db.query(TareaMantenimiento).filter(TareaMantenimiento.id == tarea_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    es_tecnico = (t.tecnico_id == current_user.id)
    es_planner = has_permission(db, current_user.id, t.empresa_id, "mantenimiento.planes")
    if not es_tecnico and not es_planner:
        raise HTTPException(status_code=403, detail="No puedes reprogramar esta tarea")
    if t.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"Solo se puede reprogramar una tarea pendiente (estado: {t.estado})")
    anterior = t.fecha_programada
    t.fecha_programada = data.fecha_programada
    _hist(db, t.activo_id, current_user.nombre if hasattr(current_user, "nombre") else current_user.email,
          f"Mantenimiento preventivo reprogramado: {anterior or '—'} → {data.fecha_programada}")
    db.commit()
    db.refresh(t)
    return _tarea_dict(t, db)


class ReasignarIn(BaseModel):
    tecnico_id: str


@router.post("/tareas/{tarea_id}/reasignar")
def reasignar_tarea(
    tarea_id: str,
    data: ReasignarIn,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    """El planner reasigna una tarea PENDIENTE a otro técnico. Empresa-scoped."""
    t = db.query(TareaMantenimiento).filter(TareaMantenimiento.id == tarea_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    if not has_permission(db, current_user.id, t.empresa_id, "mantenimiento.planes"):
        raise HTTPException(status_code=403, detail="No tienes acceso a la empresa de esta tarea")
    if t.estado != "pendiente":
        raise HTTPException(status_code=400, detail=f"Solo se puede reasignar una tarea pendiente (estado: {t.estado})")
    if not data.tecnico_id:
        raise HTTPException(status_code=400, detail="Debes indicar el técnico")
    nuevo = db.query(UsuarioSistema).filter(UsuarioSistema.id == data.tecnico_id).first()
    if not nuevo:
        raise HTTPException(status_code=404, detail="Técnico no encontrado")
    if not _tecnico_puede_ejecutar(db, data.tecnico_id):
        raise HTTPException(status_code=400, detail="El técnico no tiene permiso para ejecutar mantenimientos")

    ant = db.query(UsuarioSistema).filter(UsuarioSistema.id == t.tecnico_id).first() if t.tecnico_id else None
    t.tecnico_id = data.tecnico_id
    _hist(db, t.activo_id, current_user.nombre if hasattr(current_user, "nombre") else current_user.email,
          f"Mantenimiento preventivo reasignado: {ant.nombre if ant else '—'} → {nuevo.nombre}")
    db.commit()
    db.refresh(t)
    return _tarea_dict(t, db)


class ChecklistResultIn(BaseModel):
    id: str
    realizado: Optional[bool] = None      # Sí=true / No=false / N/A=null (ítems check)
    valor_dato: Optional[str] = None      # ítems dato


class GuardarChecklistIn(BaseModel):
    items: List[ChecklistResultIn] = []
    observaciones: Optional[str] = None


def _aplicar_checklist(t: TareaMantenimiento, data: GuardarChecklistIn, db: Session):
    by_id = {i.id: i for i in t.checklist_items}
    for r in data.items:
        it = by_id.get(r.id)
        if not it:
            continue                       # ignora ids ajenos (defensa)
        if it.tipo_item == "check":
            it.realizado = r.realizado
        else:
            it.valor_dato = r.valor_dato
    if data.observaciones is not None:
        t.observaciones = data.observaciones


@router.put("/tareas/{tarea_id}/checklist")
def guardar_checklist(
    tarea_id: str,
    data: GuardarChecklistIn,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.ejecutar"),
):
    t = _get_tarea_propia(db, tarea_id, current_user)
    if t.estado != "en_ejecucion":
        raise HTTPException(status_code=400, detail="La tarea debe estar en ejecución para guardar el checklist")
    _aplicar_checklist(t, data, db)
    db.commit()
    db.refresh(t)
    return _tarea_detalle_dict(t, db)


@router.post("/tareas/{tarea_id}/completar")
def completar_tarea(
    tarea_id: str,
    data: GuardarChecklistIn,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.ejecutar"),
):
    t = _get_tarea_propia(db, tarea_id, current_user)
    if t.estado != "en_ejecucion":
        raise HTTPException(status_code=400, detail="Solo se completa una tarea en ejecución")
    a = db.query(Activo).filter(Activo.id == t.activo_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Equipo no encontrado")

    # Guardar checklist final + observaciones
    _aplicar_checklist(t, data, db)

    # Restaurar estado EXACTO previo (asignado→mismo empleado / disponible→disponible)
    a.estado = t.estado_activo_previo or "disponible"
    a.id_usuario = t.usuario_previo        # None si venía de disponible
    t.estado = "completada"
    t.fecha_fin_ejec = datetime.now()
    db.flush()

    # Acta PDF (corporativo, sin OTP)
    try:
        from services.pdf_service import generar_pdf_mantenimiento
        tec = db.query(UsuarioSistema).filter(UsuarioSistema.id == t.tecnico_id).first()
        t.url_acta_pdf = generar_pdf_mantenimiento(
            t, a, a.empresa, t.plan, (tec.nombre if tec else None), list(t.checklist_items))
    except Exception as e:
        print(f"[MANT ACTA] {e}")

    total = len(t.checklist_items)
    hechos = sum(1 for i in t.checklist_items if (i.tipo_item == "check" and i.realizado is not None) or (i.tipo_item == "dato" and i.valor_dato))
    _hist(db, a.id, current_user.nombre if hasattr(current_user, "nombre") else current_user.email,
          f"Mantenimiento preventivo realizado — plan {t.plan.nombre if t.plan else ''} — {hechos}/{total} ítems"
          + (f" — acta {Path(t.url_acta_pdf).name}" if t.url_acta_pdf else ""))

    # ── Auto-cancelar tareas HUÉRFANAS del mismo equipo ──────────────────────
    # El equipo acaba de recibir mantenimiento; cualquier OTRA tarea abierta para
    # él queda sin sentido. Es state-neutral: NO toca a.estado (T ya hizo el
    # round-trip; los huérfanos son 'pendiente' por el guard de iniciar).
    fecha_txt = t.fecha_fin_ejec.strftime("%Y-%m-%d") if t.fecha_fin_ejec else ""
    acta_txt = Path(t.url_acta_pdf).name if t.url_acta_pdf else "sin acta"
    huerfanas = db.query(TareaMantenimiento).filter(
        TareaMantenimiento.activo_id == a.id,
        TareaMantenimiento.id != t.id,
        TareaMantenimiento.estado.in_(("pendiente", "en_ejecucion")),
    ).all()
    for h in huerfanas:
        h.estado = "cancelada"
        h.motivo_cancelacion = f"Cancelada automáticamente: el equipo recibió mantenimiento el {fecha_txt} (acta {acta_txt})"
    if huerfanas:
        _hist(db, a.id, current_user.nombre if hasattr(current_user, "nombre") else current_user.email,
              f"{len(huerfanas)} tarea(s) de mantenimiento canceladas automáticamente (equipo ya mantenido)")

    db.commit()
    db.refresh(t)
    out = _tarea_detalle_dict(t, db)
    out["orphans_cancelados"] = len(huerfanas)
    return out


class CancelarTareaIn(BaseModel):
    motivo: Optional[str] = None


@router.post("/tareas/{tarea_id}/cancelar")
def cancelar_tarea(
    tarea_id: str,
    data: CancelarTareaIn,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    """Cancela una tarea (planner). Si estaba en ejecución, restaura el estado del equipo."""
    t = db.query(TareaMantenimiento).filter(TareaMantenimiento.id == tarea_id).first()
    if not t:
        raise HTTPException(status_code=404, detail="Tarea no encontrada")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and t.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta tarea")
    if t.estado in ("completada", "cancelada"):
        raise HTTPException(status_code=400, detail=f"La tarea ya está {t.estado}")
    if t.estado == "en_ejecucion":
        a = db.query(Activo).filter(Activo.id == t.activo_id).first()
        if a and a.estado == "mantenimiento_preventivo":
            a.estado = t.estado_activo_previo or "disponible"
            a.id_usuario = t.usuario_previo
            _hist(db, a.id, current_user.nombre if hasattr(current_user, "nombre") else current_user.email,
                  "Mantenimiento preventivo cancelado — estado del equipo restaurado")
    t.estado = "cancelada"
    t.motivo_cancelacion = (data.motivo or "").strip() or None
    db.commit()
    db.refresh(t)
    return _tarea_dict(t, db)


@router.get("/tareas/{tarea_id}/acta")
def descargar_acta_mantenimiento(
    tarea_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.ejecutar"),
):
    t = _get_tarea_propia(db, tarea_id, current_user, permitir_planner=True)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and t.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta tarea")
    if not t.url_acta_pdf:
        raise HTTPException(status_code=404, detail="Esta tarea aún no tiene acta generada")
    ruta = Path(__file__).parent.parent / t.url_acta_pdf
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="El PDF del acta no se encontró en el servidor")
    a = db.query(Activo).filter(Activo.id == t.activo_id).first()
    nombre = f"acta_mantenimiento_{a.id_placa_activo if a else t.id[:8]}.pdf"
    return FileResponse(path=str(ruta), media_type="application/pdf", filename=nombre)


# ══════════════════════════════════════════════════════════
#  TABLEROS — analítica gerencial (solo lectura, gate mantenimiento.planes)
# ══════════════════════════════════════════════════════════
_PARQUE_EXCLUIR = ("retirado",)          # estados fuera de la flota "viva"


def _add_months(d: date, n: int) -> date:
    """Suma n meses a una fecha, ajustando el día al último válido del mes destino."""
    m = d.month - 1 + n
    y = d.year + m // 12
    m = m % 12 + 1
    dia = min(d.day, calendar.monthrange(y, m)[1])
    return date(y, m, dia)


def _fleet_query(db: Session, current_user, empresa_id):
    """Flota VIVA (sin retirados) dentro del alcance del usuario + filtro opcional."""
    empresa_ids = _empresa_scope(db, current_user, empresa_id)
    q = db.query(Activo).filter(Activo.estado.notin_(_PARQUE_EXCLUIR))
    if empresa_id:
        q = q.filter(Activo.empresa_id == empresa_id)
    elif empresa_ids is not None:
        q = q.filter(Activo.empresa_id.in_(empresa_ids))
    return q.all()


def _clasificar_equipos(db: Session, activos, cobertura, hoy):
    """Para los activos CON plan: última fecha preventiva, meses, próximo vencimiento
    y clasificación semáforo. 'vencido' = nunca o próximo < hoy; 'por_vencer' = vence
    en ≤60 días; 'al_dia' = vence en >60 días. Batch (un solo _ultimo_preventivo_map)."""
    con_plan = [a for a in activos if a.tipo_activo in cobertura]
    ult_map = _ultimo_preventivo_map(db, [a.id for a in con_plan])
    out = []
    for a in con_plan:
        plan = cobertura[a.tipo_activo]
        per = plan.periodicidad_meses or 12
        ult = ult_map.get(a.id)
        if ult is None:
            out.append({"a": a, "ult": None, "meses": None, "next_due": None, "cls": "vencido"})
            continue
        meses = _meses_entre(ult, hoy)
        nd = _add_months(ult, per)
        if nd < hoy:
            cls = "vencido"
        elif (nd - hoy).days <= 60:
            cls = "por_vencer"
        else:
            cls = "al_dia"
        out.append({"a": a, "ult": ult, "meses": meses, "next_due": nd, "cls": cls})
    return out


def _nombres_tecnicos(db: Session, ids) -> dict:
    ids = [i for i in set(ids) if i]
    if not ids:
        return {}
    rows = db.query(UsuarioSistema.id, UsuarioSistema.nombre, UsuarioSistema.email).filter(
        UsuarioSistema.id.in_(ids)).all()
    return {r[0]: (r[1] or r[2] or "—") for r in rows}


@router.get("/tableros/coordinacion")
def tablero_coordinacion(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    hoy = date.today()
    cobertura = coverage_activa(db)
    activos = _fleet_query(db, current_user, empresa_id)
    analisis = _clasificar_equipos(db, activos, cobertura, hoy)
    total = len(analisis)

    al_dia = sum(1 for x in analisis if x["cls"] == "al_dia")
    por_vencer = sum(1 for x in analisis if x["cls"] == "por_vencer")
    vencidos = sum(1 for x in analisis if x["cls"] == "vencido")
    # Cobertura (definición): último preventivo < periodicidad ⇒ no vencido
    no_vencidos = al_dia + por_vencer
    cobertura_pct = round(100 * no_vencidos / total) if total else 0

    # Próxima ola — buckets exclusivos por días hasta el próximo vencimiento
    d30 = d60 = d90 = 0
    for x in analisis:
        if x["next_due"] is None:
            continue
        dd = (x["next_due"] - hoy).days
        if 0 <= dd <= 30:
            d30 += 1
        elif 31 <= dd <= 60:
            d60 += 1
        elif 61 <= dd <= 90:
            d90 += 1

    # Cobertura por empresa
    por_emp = {}
    for x in analisis:
        e = x["a"].empresa_id
        d = por_emp.setdefault(e, {"no_venc": 0, "tot": 0})
        d["tot"] += 1
        if x["cls"] != "vencido":
            d["no_venc"] += 1
    nombres_emp = {e.id: e.nombre_empresa for e in db.query(Empresa).filter(
        Empresa.id.in_(list(por_emp.keys()))).all()} if por_emp else {}
    por_empresa = sorted(
        [{"empresa": nombres_emp.get(e, "—"),
          "pct": round(100 * v["no_venc"] / v["tot"]) if v["tot"] else 0,
          "equipos": v["tot"]}
         for e, v in por_emp.items()],
        key=lambda r: r["pct"], reverse=True)

    # Tendencia de cobertura — 12 meses (single-scan + bucketing en memoria)
    tendencia = _tendencia_cobertura(db, activos, cobertura, hoy)

    return {
        "cobertura_pct": cobertura_pct,
        "al_dia": al_dia, "por_vencer": por_vencer, "vencidos": vencidos,
        "total_con_plan": total,
        "tendencia": tendencia,
        "por_empresa": por_empresa,
        "proxima_ola": {"d30": d30, "d60": d60, "d90": d90},
    }


def _tendencia_cobertura(db: Session, activos, cobertura, hoy):
    """% al día de la flota-con-plan ACTUAL a cada fin de mes de los últimos 12 meses.
    Un solo escaneo de preventivos completados; luego bucketing en memoria. El
    denominador (flota-con-plan de hoy) y la periodicidad se mantienen constantes
    (no versionamos historia de planes): responde "de la flota mantenible de hoy,
    qué parte tenía un preventivo válido a cada fin de mes"."""
    con_plan = [a for a in activos if a.tipo_activo in cobertura]
    total = len(con_plan)
    # Fines de mes de los últimos 12 meses (incluye el mes en curso)
    primero_mes = date(hoy.year, hoy.month, 1)
    meses_fin = []
    for k in range(11, -1, -1):
        fm = _add_months(primero_mes, -k)
        ultimo_dia = calendar.monthrange(fm.year, fm.month)[1]
        meses_fin.append(date(fm.year, fm.month, ultimo_dia))
    if not total:
        return [{"mes": f"{d.year}-{d.month:02d}", "pct": 0} for d in meses_fin]

    ids = [a.id for a in con_plan]
    per_by_activo = {a.id: (cobertura[a.tipo_activo].periodicidad_meses or 12) for a in con_plan}
    # Historial de preventivos completados (una sola consulta)
    fins_by_activo = {}
    rows = db.query(TareaMantenimiento.activo_id, TareaMantenimiento.fecha_fin_ejec).filter(
        TareaMantenimiento.activo_id.in_(ids),
        TareaMantenimiento.estado == "completada",
        TareaMantenimiento.fecha_fin_ejec != None,
    ).all() if ids else []
    for aid, fin in rows:
        f = fin.date() if isinstance(fin, datetime) else fin
        fins_by_activo.setdefault(aid, []).append(f)
    for aid in fins_by_activo:
        fins_by_activo[aid].sort()

    out = []
    for D in meses_fin:
        cubiertos = 0
        for aid in ids:
            per = per_by_activo[aid]
            # último preventivo completado <= D
            ultimo = None
            for f in fins_by_activo.get(aid, []):
                if f <= D:
                    ultimo = f
                else:
                    break
            if ultimo is not None and _meses_entre(ultimo, D) < per:
                cubiertos += 1
        out.append({"mes": f"{D.year}-{D.month:02d}", "pct": round(100 * cubiertos / total)})
    return out


@router.get("/tableros/planificacion")
def tablero_planificacion(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    hoy = date.today()
    empresa_ids = _empresa_scope(db, current_user, empresa_id)

    def _scope(q):
        if empresa_id:
            return q.filter(TareaMantenimiento.empresa_id == empresa_id)
        if empresa_ids is not None:
            return q.filter(TareaMantenimiento.empresa_id.in_(empresa_ids))
        return q

    tareas = _scope(db.query(
        TareaMantenimiento.id, TareaMantenimiento.tecnico_id, TareaMantenimiento.estado,
        TareaMantenimiento.origen, TareaMantenimiento.fecha_programada,
        TareaMantenimiento.fecha_fin_ejec)).all()

    nombres = _nombres_tecnicos(db, [t.tecnico_id for t in tareas])
    def _nombre(tid):
        return nombres.get(tid, "Sin asignar") if tid else "Sin asignar"

    carga, vencidas, completados = {}, {}, {}
    pipeline = {"pendiente": 0, "en_ejecucion": 0, "completada": 0, "cancelada": 0}
    origen = {"planificacion": 0, "devolucion": 0, "adhoc": 0}
    for t in tareas:
        pipeline[t.estado] = pipeline.get(t.estado, 0) + 1
        origen[t.origen or "planificacion"] = origen.get(t.origen or "planificacion", 0) + 1
        if t.estado == "pendiente":
            carga[t.tecnico_id] = carga.get(t.tecnico_id, 0) + 1
            if t.fecha_programada and t.fecha_programada < hoy:
                vencidas[t.tecnico_id] = vencidas.get(t.tecnico_id, 0) + 1
        if t.estado == "completada" and t.fecha_fin_ejec:
            f = t.fecha_fin_ejec.date() if isinstance(t.fecha_fin_ejec, datetime) else t.fecha_fin_ejec
            if f.year == hoy.year and f.month == hoy.month:
                completados[t.tecnico_id] = completados.get(t.tecnico_id, 0) + 1

    def _rank(d):
        return sorted([{"tecnico": _nombre(k), "n": v} for k, v in d.items()],
                      key=lambda r: r["n"], reverse=True)

    return {
        "carga": _rank(carga),
        "vencidas": _rank(vencidas),
        "pipeline": pipeline,
        "completados_mes": _rank(completados),
        "origen": origen,
    }


@router.get("/tableros/parque")
def tablero_parque(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("mantenimiento.planes"),
):
    hoy = date.today()
    cobertura = coverage_activa(db)
    activos = _fleet_query(db, current_user, empresa_id)
    analisis = _clasificar_equipos(db, activos, cobertura, hoy)

    # Cobertura de planes (sobre la flota viva)
    con_plan = sum(1 for a in activos if a.tipo_activo in cobertura)
    sin_plan = len(activos) - con_plan

    # Por tipo (semáforo apilado)
    por_tipo = {}
    for x in analisis:
        tipo = x["a"].tipo_activo or "—"
        d = por_tipo.setdefault(tipo, {"al_dia": 0, "por_vencer": 0, "vencido": 0})
        d[x["cls"]] += 1
    por_tipo_out = sorted(
        [{"tipo": t, **v} for t, v in por_tipo.items()],
        key=lambda r: (r["al_dia"] + r["por_vencer"] + r["vencido"]), reverse=True)

    # Antigüedad (meses desde el último preventivo)
    buckets = [("0-3", 0), ("3-6", 0), ("6-9", 0), ("9-12", 0), ("+12/nunca", 0)]
    bmap = {k: 0 for k, _ in buckets}
    for x in analisis:
        m = x["meses"]
        if m is None:
            bmap["+12/nunca"] += 1
        elif m < 3:
            bmap["0-3"] += 1
        elif m < 6:
            bmap["3-6"] += 1
        elif m < 9:
            bmap["6-9"] += 1
        elif m < 12:
            bmap["9-12"] += 1
        else:
            bmap["+12/nunca"] += 1
    antiguedad = [{"bucket": k, "n": bmap[k]} for k, _ in buckets]

    # Top 10 más atrasados (nunca primero, luego más meses)
    orden = sorted(analisis, key=lambda x: (0 if x["meses"] is None else 1,
                                            -(x["meses"] if x["meses"] is not None else 0)))
    top = [{"placa": x["a"].id_placa_activo, "tipo": x["a"].tipo_activo, "meses": x["meses"]}
           for x in orden[:10]]

    # Por empresa (equipos-con-plan, vencidos, cobertura %)
    por_emp = {}
    for x in analisis:
        e = x["a"].empresa_id
        d = por_emp.setdefault(e, {"equipos": 0, "vencidos": 0})
        d["equipos"] += 1
        if x["cls"] == "vencido":
            d["vencidos"] += 1
    nombres_emp = {e.id: e.nombre_empresa for e in db.query(Empresa).filter(
        Empresa.id.in_(list(por_emp.keys()))).all()} if por_emp else {}
    por_empresa = sorted(
        [{"empresa": nombres_emp.get(e, "—"), "equipos": v["equipos"], "vencidos": v["vencidos"],
          "cobertura_pct": round(100 * (v["equipos"] - v["vencidos"]) / v["equipos"]) if v["equipos"] else 0}
         for e, v in por_emp.items()],
        key=lambda r: r["equipos"], reverse=True)

    return {
        "por_tipo": por_tipo_out,
        "cobertura_planes": {"con_plan": con_plan, "sin_plan": sin_plan},
        "antiguedad": antiguedad,
        "top_atrasados": top,
        "por_empresa": por_empresa,
    }
