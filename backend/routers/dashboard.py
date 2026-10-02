"""
Dashboard consolidado.
Prefix: /api/dashboard

GET /api/dashboard/resumen — KPIs, alertas y listas accionables (reservados,
fuera de servicio, préstamos con fecha límite). Respeta el aislamiento por
empresa y, si se pasa empresa_id, lo filtra a esa empresa (como el resto del
dashboard). No reemplaza los endpoints existentes; los nuevos paneles lo usan.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Optional
from datetime import date, datetime, timedelta

from database import get_db
from models.activo import Activo
from models.accesorio import Accesorio
from models.usuario import Usuario
from models.reserva import Reserva, ReservaItem
from models.acta import Acta
from models.cambio_estado import CambioEstado
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

ESTADOS_FUERA_SERVICIO = [
    "mantenimiento", "mantenimiento_preventivo", "mantenimiento_correctivo",
    "en_reparacion", "en_garantia",
]


@router.get("/resumen")
def dashboard_resumen(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("activos.ver"),
):
    hoy = date.today()
    en_3_dias = hoy + timedelta(days=3)
    empresa_ids = get_user_empresa_ids(db, current_user.id)

    # ── filtro de empresa reutilizable ──
    if empresa_ids is not None and empresa_id and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    def scope(query, model):
        if empresa_ids is not None:
            if empresa_id:
                return query.filter(model.empresa_id == empresa_id)
            return query.filter(model.empresa_id.in_(empresa_ids))
        if empresa_id:
            return query.filter(model.empresa_id == empresa_id)
        return query

    def placa(r, tipo):
        return r.id_placa_activo if tipo == "activo" else r.id_placa_accesorio

    def tipo_de(r, tipo):
        return r.tipo_activo if tipo == "activo" else r.tipo_accesorio

    # ── KPIs ──────────────────────────────────────────────
    act_no_retirado = scope(db.query(Activo).filter(Activo.estado != "retirado"), Activo)
    activos_all = act_no_retirado.all()
    total_activos = len(activos_all)
    asignados   = sum(1 for a in activos_all if a.estado == "asignado")
    disponibles = sum(1 for a in activos_all if a.estado == "disponible")
    mantenimiento = sum(1 for a in activos_all if a.estado in ESTADOS_FUERA_SERVICIO)
    empleados = scope(db.query(Usuario).filter(Usuario.estado == "activo"), Usuario).count()

    # ── Alertas ───────────────────────────────────────────
    def _loan_count(extra):
        total = 0
        for model in (Activo, Accesorio):
            q = scope(db.query(model).filter(
                model.estado == "asignado", model.es_prestamo == True,
                model.fecha_limite_devolucion.isnot(None)), model)
            total += extra(q, model).count()
        return total

    prestamos_vencidos = _loan_count(lambda q, m: q.filter(m.fecha_limite_devolucion < hoy))
    prestamos_por_vencer = _loan_count(lambda q, m: q.filter(
        and_(m.fecha_limite_devolucion >= hoy, m.fecha_limite_devolucion <= en_3_dias)))
    reservas_activas = scope(db.query(Reserva).filter(Reserva.estado == "activa"), Reserva).count()
    actas_sin_firmar = scope(db.query(Acta).filter(
        Acta.tipo == "entrega", Acta.firmada == False,
        Acta.fecha_entrega < datetime.now() - timedelta(days=2)), Acta).count()

    # ── Reservados (max 5) ────────────────────────────────
    reservados = []
    for tipo, model in (("activo", Activo), ("accesorio", Accesorio)):
        for r in scope(db.query(model).filter(model.estado == "reservado"), model).all():
            item = db.query(ReservaItem).filter(
                ReservaItem.tipo_recurso == tipo, ReservaItem.recurso_id == r.id,
                ReservaItem.estado == "reservado").first()
            reserva = db.query(Reserva).filter(
                Reserva.id == item.reserva_id, Reserva.estado == "activa").first() if item else None
            fl = reserva.fecha_limite if reserva else None
            reservados.append({
                "tipo_recurso": tipo, "recurso_id": r.id, "placa": placa(r, tipo),
                "tipo": tipo_de(r, tipo), "marca": r.marca, "modelo": r.modelo,
                "numero_alta": reserva.numero_alta if reserva else None,
                "fecha_limite": fl,
                "dias_para_vencer": (fl - hoy).days if fl else None,
            })
    reservados.sort(key=lambda x: (x["fecha_limite"] is None, x["fecha_limite"] or hoy))
    reservados_total = len(reservados)

    # ── Fuera de servicio (max 5) + desglose ──────────────
    fuera = []
    desglose = {"mantenimiento": 0, "en_reparacion": 0, "en_garantia": 0}
    for tipo, model in (("activo", Activo), ("accesorio", Accesorio)):
        for r in scope(db.query(model).filter(model.estado.in_(ESTADOS_FUERA_SERVICIO)), model).all():
            if r.estado == "en_reparacion":
                desglose["en_reparacion"] += 1
            elif r.estado == "en_garantia":
                desglose["en_garantia"] += 1
            else:
                desglose["mantenimiento"] += 1
            fuera.append({
                "tipo_recurso": tipo, "recurso_id": r.id, "placa": placa(r, tipo),
                "tipo": tipo_de(r, tipo), "marca": r.marca, "modelo": r.modelo,
                "estado": r.estado, "ubicacion": r.ubicacion, "descripcion": None,
            })
    fuera.sort(key=lambda x: (x["estado"], x["placa"] or ""))
    fuera_total = len(fuera)
    fuera_top = fuera[:5]
    # descripción/ubicación del último CambioEstado para los 5 mostrados
    for f in fuera_top:
        ce = db.query(CambioEstado).filter(
            CambioEstado.tipo_recurso == f["tipo_recurso"],
            CambioEstado.recurso_id == f["recurso_id"],
        ).order_by(CambioEstado.fecha.desc()).first()
        if ce:
            f["descripcion"] = ce.descripcion
            if ce.ubicacion:
                f["ubicacion"] = ce.ubicacion

    # ── Préstamos con fecha límite (max 5, por urgencia) ──
    prestamos = []
    for tipo, model in (("activo", Activo), ("accesorio", Accesorio)):
        rows = scope(db.query(model).filter(
            model.estado == "asignado", model.es_prestamo == True,
            model.fecha_limite_devolucion.isnot(None)), model).all()
        for r in rows:
            dias = (r.fecha_limite_devolucion - hoy).days
            emp = db.query(Usuario).filter(Usuario.id == r.id_usuario).first() if r.id_usuario else None
            prestamos.append({
                "tipo_recurso": tipo, "recurso_id": r.id, "placa": placa(r, tipo),
                "tipo": tipo_de(r, tipo),
                "empleado_nombre": emp.nombre_completo if emp else None,
                "fecha_limite_devolucion": r.fecha_limite_devolucion,
                "dias_para_vencer": dias, "vencido": dias < 0,
            })
    prestamos.sort(key=lambda x: x["dias_para_vencer"])   # más vencido (negativo) primero
    prestamos_total = len(prestamos)

    return {
        "kpis": {
            "total_activos": total_activos, "asignados": asignados,
            "disponibles": disponibles, "mantenimiento": mantenimiento,
            "empleados": empleados,
        },
        "alertas": {
            "prestamos_vencidos": prestamos_vencidos,
            "prestamos_por_vencer": prestamos_por_vencer,
            "reservas_activas": reservas_activas,
            "actas_sin_firmar": actas_sin_firmar,
        },
        "reservados": reservados[:5],
        "reservados_total": reservados_total,
        "fuera_servicio": fuera_top,
        "fuera_servicio_total": fuera_total,
        "fuera_servicio_desglose": desglose,
        "prestamos": prestamos[:5],
        "prestamos_total": prestamos_total,
    }
