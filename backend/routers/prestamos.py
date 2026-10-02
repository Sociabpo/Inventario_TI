"""
Préstamos temporales (loans) sobre activos y accesorios.

El préstamo NO es un estado: el recurso sigue "asignado". Aquí se establece /
modifica / elimina la fecha límite de devolución sobre el recurso, y se exponen
las estadísticas para el dashboard. La info de préstamo se serializa en los
listados de /api/activos y /api/accesorios (ver loan_dict en prestamo_service).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from datetime import date, timedelta
from database import get_db
from models.activo import Activo
from models.accesorio import Accesorio
from models.historial import HistorialMovimiento
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids
from services.prestamo_service import loan_dict

router = APIRouter(prefix="/api/prestamos", tags=["Préstamos"])

_MODELOS = {"activo": Activo, "accesorio": Accesorio}


class FechaLimiteBody(BaseModel):
    fecha_limite_devolucion: date


def _placa(tipo: str, recurso) -> str:
    return recurso.id_placa_activo if tipo == "activo" else recurso.id_placa_accesorio


def _historial(db, tipo, recurso_id, responsable, obs):
    db.add(HistorialMovimiento(
        id_activo=recurso_id if tipo == "activo" else None,
        id_accesorio=recurso_id if tipo == "accesorio" else None,
        tipo_movimiento="prestamo",
        responsable=responsable,
        observaciones=obs,
    ))


def _cargar_recurso(db: Session, tipo: str, recurso_id: str, current_user):
    modelo = _MODELOS.get(tipo)
    if not modelo:
        raise HTTPException(status_code=400, detail="Tipo de recurso inválido (use 'activo' o 'accesorio')")
    recurso = db.query(modelo).filter(modelo.id == recurso_id).first()
    if not recurso:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and recurso.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese recurso")
    return recurso


@router.post("/{tipo}/{recurso_id}/fecha-limite")
def establecer_fecha_limite(
    tipo: str,
    recurso_id: str,
    data: FechaLimiteBody,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear"),
):
    """Establece o modifica la fecha límite del préstamo (también sirve para 'Extender')."""
    recurso = _cargar_recurso(db, tipo, recurso_id, current_user)
    if recurso.estado != "asignado":
        raise HTTPException(status_code=400, detail="El recurso debe estar asignado para definir un préstamo")
    if data.fecha_limite_devolucion <= date.today():
        raise HTTPException(status_code=400, detail="La fecha límite debe ser posterior a hoy")

    recurso.fecha_limite_devolucion    = data.fecha_limite_devolucion
    recurso.es_prestamo                = True
    recurso.alerta_vencimiento_enviada = False   # reset → puede volver a alertar si vence
    _historial(db, tipo, recurso.id, current_user.email,
               f"Fecha límite de préstamo establecida: {data.fecha_limite_devolucion} — {_placa(tipo, recurso)}")
    db.commit()
    db.refresh(recurso)
    return {
        "mensaje": "Fecha límite de préstamo establecida",
        "id": recurso.id,
        "estado": recurso.estado,
        **loan_dict(recurso),
    }


@router.post("/{tipo}/{recurso_id}/convertir-indefinido")
def convertir_indefinido(
    tipo: str,
    recurso_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear"),
):
    """Quita la fecha límite → asignación indefinida (comportamiento original)."""
    recurso = _cargar_recurso(db, tipo, recurso_id, current_user)
    if recurso.estado != "asignado":
        raise HTTPException(status_code=400, detail="El recurso debe estar asignado")

    recurso.fecha_limite_devolucion    = None
    recurso.es_prestamo                = False
    recurso.alerta_vencimiento_enviada = False
    _historial(db, tipo, recurso.id, current_user.email,
               f"Préstamo convertido a asignación indefinida — {_placa(tipo, recurso)}")
    db.commit()
    db.refresh(recurso)
    return {
        "mensaje": "Préstamo convertido a asignación indefinida",
        "id": recurso.id,
        "estado": recurso.estado,
        **loan_dict(recurso),
    }


@router.get("/stats")
def prestamos_stats(
    empresa_id: str = None,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.ver"),
):
    """Conteos para los chips del dashboard. Respeta el aislamiento por empresa."""
    hoy = date.today()
    limite_proximo = hoy + timedelta(days=3)
    empresa_ids = get_user_empresa_ids(db, current_user.id)

    def _aplicar_empresa(query, modelo):
        if empresa_ids is not None:
            if empresa_id:
                if empresa_id not in empresa_ids:
                    raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
                return query.filter(modelo.empresa_id == empresa_id)
            return query.filter(modelo.empresa_id.in_(empresa_ids))
        if empresa_id:
            return query.filter(modelo.empresa_id == empresa_id)
        return query

    activos = vencidos = por_vencer = 0
    for modelo in (Activo, Accesorio):
        base = _aplicar_empresa(
            db.query(modelo).filter(modelo.estado == "asignado", modelo.es_prestamo == True),
            modelo,
        )
        activos    += base.count()
        vencidos   += base.filter(modelo.fecha_limite_devolucion < hoy).count()
        por_vencer += base.filter(
            and_(modelo.fecha_limite_devolucion >= hoy,
                 modelo.fecha_limite_devolucion <= limite_proximo)
        ).count()

    return {
        "prestamos_activos":   activos,
        "prestamos_vencidos":  vencidos,
        "prestamos_por_vencer": por_vencer,
    }
