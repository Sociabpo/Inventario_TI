"""
Panel "Mis Pendientes" — agregador de pendientes por permiso + empresa.

GET /api/pendientes/mis-pendientes — devuelve, para el usuario actual y su alcance
de empresa, SOLO los bloques que su rol/permiso puede gestionar, cada uno con conteo
y (según el tipo) una lista corta de ítems o un desglose. Es un tablero de
navegación: muestra y enlaza; no actúa sobre los pendientes.

Reutiliza el MISMO patrón de scoping por empresa que dashboard.py (get_user_empresa_ids
+ un closure scope()) y los MISMOS filtros de estado que el resto de módulos; no
llama ni duplica el endpoint /dashboard/resumen (sus helpers son inline, no importables).
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import date, timedelta

from database import get_db
from routers.auth import get_current_user
from services.rbac_service import get_all_user_permissions, get_user_empresa_ids

from models.compra import SolicitudCompra, OrdenCompra, Proveedor
from models.baja_activo import BajaActivo
from models.acta import Acta
from models.reserva import Reserva
from models.activo import Activo
from models.accesorio import Accesorio
from models.usuario import Usuario
from models.mantenimiento import TareaMantenimiento
from services.mantenimiento_service import ESTADOS_TAREA_ABIERTA  # ("pendiente","en_ejecucion") — misma def. que /mis-tareas

router = APIRouter(prefix="/api/pendientes", tags=["Pendientes"])

_DETALLE_CAP = 5


@router.get("/mis-pendientes")
def mis_pendientes(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    hoy = date.today()
    en_3_dias = hoy + timedelta(days=3)
    en_7_dias = hoy + timedelta(days=7)

    perms = get_all_user_permissions(db, current_user.id)
    empresa_ids = get_user_empresa_ids(db, current_user.id)

    def puede(codigo: str) -> bool:
        return codigo in perms

    # Mismo scoping por empresa que dashboard.py (None = super_admin → todas).
    def scope(query, model):
        if empresa_ids is not None:
            if empresa_id and empresa_id in empresa_ids:
                return query.filter(model.empresa_id == empresa_id)
            if empresa_id:
                # empresa fuera de alcance → nada
                return query.filter(model.empresa_id == "__none__")
            return query.filter(model.empresa_id.in_(empresa_ids))
        if empresa_id:
            return query.filter(model.empresa_id == empresa_id)
        return query

    bloques = []

    # ── Compras: solicitudes por aprobar ──
    if puede("compras.aprobar"):
        q = scope(db.query(SolicitudCompra).filter(
            SolicitudCompra.estado == "pendiente_aprobacion"), SolicitudCompra)
        total = q.count()
        if total:
            items = q.order_by(SolicitudCompra.created_at.asc()).limit(_DETALLE_CAP).all()
            bloques.append({
                "key": "compras_aprobar", "label": "Solicitudes por aprobar",
                "icon": "ti-file-check", "tipo": "detalle", "count": total,
                "modulo": "compras", "permiso": "compras.aprobar",
                "items": [{"titulo": s.numero_solicitud or s.id[:8],
                           "detalle": s.titulo or ""} for s in items],
            })

    # ── Compras: solicitudes en borrador (cargar/seleccionar cotización) ──
    if puede("compras.crear_solicitud"):
        q = scope(db.query(SolicitudCompra).filter(
            SolicitudCompra.estado == "borrador"), SolicitudCompra)
        total = q.count()
        if total:
            items = q.order_by(SolicitudCompra.created_at.asc()).limit(_DETALLE_CAP).all()
            bloques.append({
                "key": "compras_cotizar", "label": "Solicitudes en borrador (cotizar)",
                "icon": "ti-file-dollar", "tipo": "detalle", "count": total,
                "modulo": "compras", "permiso": "compras.crear_solicitud",
                "items": [{"titulo": s.numero_solicitud or s.id[:8],
                           "detalle": s.titulo or ""} for s in items],
            })

    # ── Compras: órdenes por recibir ──
    if puede("compras.recepcionar"):
        q = scope(db.query(OrdenCompra).filter(
            OrdenCompra.estado.in_(["emitida", "parcialmente_recibida"])), OrdenCompra)
        total = q.count()
        if total:
            ords = q.order_by(OrdenCompra.fecha_emision.asc()).limit(_DETALLE_CAP).all()
            prov_ids = {o.proveedor_id for o in ords if o.proveedor_id}
            prov_map = {p.id: p.nombre for p in db.query(Proveedor.id, Proveedor.nombre)
                        .filter(Proveedor.id.in_(prov_ids)).all()} if prov_ids else {}
            bloques.append({
                "key": "compras_recibir", "label": "Órdenes por recibir",
                "icon": "ti-truck-delivery", "tipo": "detalle", "count": total,
                "modulo": "compras", "permiso": "compras.recepcionar",
                "items": [{"titulo": o.numero_oc or o.id[:8],
                           "detalle": prov_map.get(o.proveedor_id, "")} for o in ords],
            })

    # ── Bajas por aprobar ──
    if puede("estados.aprobar_baja"):
        q = scope(db.query(BajaActivo).filter(
            BajaActivo.estado_aprobacion == "pendiente"), BajaActivo)
        total = q.count()
        if total:
            bajas = q.order_by(BajaActivo.fecha_solicitud.asc()).limit(_DETALLE_CAP).all() \
                if hasattr(BajaActivo, "fecha_solicitud") else q.limit(_DETALLE_CAP).all()
            bloques.append({
                "key": "bajas_aprobar", "label": "Bajas por aprobar",
                "icon": "ti-trash-x", "tipo": "detalle", "count": total,
                "modulo": "bajas", "permiso": "estados.aprobar_baja",
                "items": [{"titulo": b.numero_baja or (b.placa or b.id[:8]),
                           "detalle": f"{b.placa or ''} · {b.motivo or ''}".strip(" ·")} for b in bajas],
            })

    # ── Actas pendientes de firma ──
    if puede("actas.ver"):
        q = scope(db.query(Acta).filter(
            Acta.tipo == "entrega", Acta.firmada == False), Acta)
        total = q.count()
        if total:
            actas = q.order_by(Acta.fecha_entrega.asc()).limit(_DETALLE_CAP).all()
            uids = {a.id_usuario for a in actas if a.id_usuario}
            nombres = {u.id: u.nombre_completo for u in db.query(Usuario.id, Usuario.nombre_completo)
                       .filter(Usuario.id.in_(uids)).all()} if uids else {}
            bloques.append({
                "key": "actas_firma", "label": "Actas pendientes de firma",
                "icon": "ti-signature", "tipo": "detalle", "count": total,
                "modulo": "actas", "permiso": "actas.ver",
                "items": [{"titulo": nombres.get(a.id_usuario, a.responsable_recibe or "—"),
                           "detalle": f"Acta de {a.tipo}"} for a in actas],
            })

    # ── Reservas activas / vencidas ──
    if puede("reservas.gestionar"):
        q = scope(db.query(Reserva).filter(Reserva.estado == "activa"), Reserva)
        total = q.count()
        if total:
            resv = q.order_by(Reserva.fecha_limite.asc()).limit(_DETALLE_CAP).all()
            bloques.append({
                "key": "reservas", "label": "Reservas por gestionar",
                "icon": "ti-bookmark", "tipo": "detalle", "count": total,
                "modulo": "reservas", "permiso": "reservas.gestionar",
                "items": [{"titulo": r.numero_alta or r.id[:8],
                           "detalle": ("Vencida" if (r.fecha_limite and r.fecha_limite < hoy)
                                       else (f"Vence {r.fecha_limite.isoformat()}" if r.fecha_limite else "")),
                           "urgente": bool(r.fecha_limite and r.fecha_limite < hoy)} for r in resv],
            })

    # ── Préstamos por vencer / vencidos (Activo + Accesorio) ──
    if puede("asignaciones.devolver"):
        prestamos, total = [], 0
        for tipo, model in (("activo", Activo), ("accesorio", Accesorio)):
            q = scope(db.query(model).filter(
                model.estado == "asignado", model.es_prestamo == True,
                model.fecha_limite_devolucion.isnot(None),
                model.fecha_limite_devolucion <= en_3_dias), model)
            total += q.count()
            for r in q.order_by(model.fecha_limite_devolucion.asc()).limit(_DETALLE_CAP).all():
                emp = db.query(Usuario.nombre_completo).filter(Usuario.id == r.id_usuario).first() if r.id_usuario else None
                placa = r.id_placa_activo if tipo == "activo" else r.id_placa_accesorio
                fl = r.fecha_limite_devolucion
                prestamos.append({
                    "titulo": placa or r.id[:8],
                    "detalle": (emp[0] if emp else "") + (f" · vence {fl.isoformat()}" if fl else ""),
                    "urgente": bool(fl and fl < hoy), "_fl": fl,
                })
        if total:
            prestamos.sort(key=lambda x: x["_fl"] or hoy)
            for p in prestamos:
                p.pop("_fl", None)
            bloques.append({
                "key": "prestamos", "label": "Préstamos por vencer / vencidos",
                "icon": "ti-clock-exclamation", "tipo": "detalle", "count": total,
                "modulo": "asignaciones", "permiso": "asignaciones.devolver",
                "items": prestamos[:_DETALLE_CAP],
            })

    # ── Mantenimiento (AGRUPADO): vencidos / esta semana / próximos ──
    # CASO ESPECIAL: el mantenimiento es el único pendiente asignado a un TÉCNICO
    # específico (elegido en la PLANIFICACIÓN → TareaMantenimiento.tecnico_id, FK a
    # usuarios_sistema). Se muestra EXACTAMENTE lo que el técnico ve al entrar
    # (/mantenimiento/mis-tareas): tecnico_id == current_user.id + estado en
    # ESTADOS_TAREA_ABIERTA. Se reutiliza esa MISMA definición (constante compartida),
    # no una propia. Los demás bloques siguen por rol.
    if puede("mantenimiento.ejecutar"):
        base = scope(db.query(TareaMantenimiento).filter(
            TareaMantenimiento.estado.in_(ESTADOS_TAREA_ABIERTA),
            TareaMantenimiento.tecnico_id == current_user.id), TareaMantenimiento)
        total = base.count()
        if total:
            vencidos = base.filter(TareaMantenimiento.fecha_programada.isnot(None),
                                   TareaMantenimiento.fecha_programada < hoy).count()
            semana = base.filter(TareaMantenimiento.fecha_programada.isnot(None),
                                 and_(TareaMantenimiento.fecha_programada >= hoy,
                                      TareaMantenimiento.fecha_programada <= en_7_dias)).count()
            proximos = total - vencidos - semana   # > 7 días o sin fecha
            bloques.append({
                "key": "mantenimiento", "label": "Mantenimientos pendientes",
                "icon": "ti-tool", "tipo": "agrupado", "count": total,
                "modulo": "mantenimiento", "permiso": "mantenimiento.ejecutar",
                "desglose": {"vencidos": vencidos, "semana": semana, "proximos": proximos},
            })

    return {
        "total": sum(b["count"] for b in bloques),
        "bloques": bloques,
    }
