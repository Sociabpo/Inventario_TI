"""
Módulo de RESERVAS de activos/accesorios.
Prefix: /api/reservas

Una reserva agrupa uno o varios recursos (activos + accesorios) que TI aparta para
un ingreso ("alta") hasta que el nuevo empleado llegue. Los recursos pasan a estado
"reservado" y vuelven a "disponible" si la reserva se cancela o vence.

Reglas:
  - Solo recursos en estado "disponible" pueden reservarse.
  - El estado "reservado" se gestiona EXCLUSIVAMENTE desde este módulo (nunca desde
    el modal de edición ni desde cambio de estado).
  - Aislamiento multiempresa vía get_user_empresa_ids().
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime

from database import get_db
from models.activo import Activo
from models.accesorio import Accesorio
from models.empresa import Empresa
from models.historial import HistorialMovimiento
from models.reserva import Reserva, ReservaItem
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids, user_has_empresa_access

router = APIRouter(prefix="/api/reservas", tags=["Reservas"])


# ── Schemas ───────────────────────────────────────────────
class ItemIn(BaseModel):
    tipo_recurso: str   # "activo" | "accesorio"
    recurso_id: str


class ReservaCreate(BaseModel):
    numero_alta: str
    descripcion: Optional[str] = None
    empresa_id: str
    fecha_limite: date
    items: List[ItemIn]


class ReservaUpdate(BaseModel):
    fecha_limite: Optional[date] = None
    descripcion: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────
def _model(tipo_recurso: str):
    if tipo_recurso == "activo":
        return Activo
    if tipo_recurso == "accesorio":
        return Accesorio
    return None


def _placa(r, tipo_recurso: str):
    return r.id_placa_activo if tipo_recurso == "activo" else r.id_placa_accesorio


def _historial(db, tipo_recurso, recurso_id, responsable, obs):
    db.add(HistorialMovimiento(
        id_activo=recurso_id if tipo_recurso == "activo" else None,
        id_accesorio=recurso_id if tipo_recurso == "accesorio" else None,
        tipo_movimiento="reserva",
        responsable=responsable,
        observaciones=obs,
    ))


def _verify_empresa(db, current_user, empresa_id):
    if not user_has_empresa_access(db, current_user.id, empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")


def _item_detalle(db, item: ReservaItem) -> dict:
    """Snapshot + datos vivos del recurso (marca/modelo/tipo)."""
    Model = _model(item.tipo_recurso)
    rec = db.query(Model).filter(Model.id == item.recurso_id).first() if Model else None
    tipo = (rec.tipo_activo if item.tipo_recurso == "activo" else rec.tipo_accesorio) if rec else None
    return {
        "id": item.id,
        "tipo_recurso": item.tipo_recurso,
        "recurso_id": item.recurso_id,
        "placa": item.placa,
        "estado": item.estado,
        "tipo": tipo,
        "marca": rec.marca if rec else None,
        "modelo": rec.modelo if rec else None,
        "estado_recurso": rec.estado if rec else None,
    }


def _reserva_dict(db, reserva: Reserva, with_items: bool = True) -> dict:
    items = db.query(ReservaItem).filter(ReservaItem.reserva_id == reserva.id).all()
    emp = db.query(Empresa).filter(Empresa.id == reserva.empresa_id).first()
    hoy = date.today()
    dias_restantes = (reserva.fecha_limite - hoy).days if reserva.fecha_limite else None
    out = {
        "id": reserva.id,
        "numero_alta": reserva.numero_alta,
        "descripcion": reserva.descripcion,
        "empresa_id": reserva.empresa_id,
        "nombre_empresa": emp.nombre_empresa if emp else None,
        "fecha_limite": reserva.fecha_limite,
        "estado": reserva.estado,
        "created_at": reserva.created_at,
        "fecha_cierre": reserva.fecha_cierre,
        "total_items": len(items),
        "items_reservados": sum(1 for i in items if i.estado == "reservado"),
        "dias_restantes": dias_restantes,
    }
    if with_items:
        out["items"] = [_item_detalle(db, i) for i in items]
    return out


# ── GET / (listar) ────────────────────────────────────────
@router.get("")
def listar_reservas(
    estado: Optional[str] = None,
    empresa_id: Optional[str] = None,
    q: Optional[str] = None,   # busca por nº de alta, placa o serial del recurso
    db: Session = Depends(get_db),
    current_user = require_permission("reservas.gestionar"),
):
    query = db.query(Reserva)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Reserva.empresa_id == empresa_id)
        else:
            query = query.filter(Reserva.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Reserva.empresa_id == empresa_id)
    if estado:
        query = query.filter(Reserva.estado == estado)

    # Búsqueda por nº de alta, placa (snapshot del item) o serial del recurso
    termino = (q or "").strip()
    if termino:
        like = f"%{termino}%"
        # recursos cuyo serial coincide → sus ids
        act_ids = [r[0] for r in db.query(Activo.id).filter(Activo.serial.ilike(like)).all()]
        acc_ids = [r[0] for r in db.query(Accesorio.id).filter(Accesorio.serial.ilike(like)).all()]
        serial_recurso_ids = act_ids + acc_ids
        # reservas que matchean por placa del item o por serial del recurso
        item_q = db.query(ReservaItem.reserva_id).filter(ReservaItem.placa.ilike(like))
        if serial_recurso_ids:
            item_q = db.query(ReservaItem.reserva_id).filter(
                or_(ReservaItem.placa.ilike(like),
                    ReservaItem.recurso_id.in_(serial_recurso_ids))
            )
        ids_por_item = {r[0] for r in item_q.all()}
        conds = [Reserva.numero_alta.ilike(like)]
        if ids_por_item:
            conds.append(Reserva.id.in_(ids_por_item))
        query = query.filter(or_(*conds))

    reservas = query.order_by(Reserva.created_at.desc()).all()
    return [_reserva_dict(db, r, with_items=True) for r in reservas]


# ── GET /recurso/{tipo}/{id} (reserva activa de un recurso) ──
# Debe declararse ANTES de /{reserva_id} para no colisionar.
@router.get("/recurso/{tipo_recurso}/{recurso_id}")
def reserva_de_recurso(
    tipo_recurso: str,
    recurso_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("reservas.gestionar"),
):
    item = db.query(ReservaItem).filter(
        ReservaItem.tipo_recurso == tipo_recurso,
        ReservaItem.recurso_id == recurso_id,
        ReservaItem.estado == "reservado",
    ).first()
    if not item:
        return None
    reserva = db.query(Reserva).filter(
        Reserva.id == item.reserva_id, Reserva.estado == "activa").first()
    if not reserva:
        return None
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and reserva.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta reserva")
    return {
        "reserva_id": reserva.id,
        "numero_alta": reserva.numero_alta,
        "descripcion": reserva.descripcion,
        "fecha_limite": reserva.fecha_limite,
    }


# ── GET /co-reservados/{tipo}/{id} (otros recursos de la misma reserva) ──
# Para el módulo de asignaciones: al agregar un recurso reservado, trae el resto
# de la reserva para precargarlos. Debe ir ANTES de /{reserva_id}.
@router.get("/co-reservados/{tipo_recurso}/{recurso_id}")
def co_reservados(
    tipo_recurso: str,
    recurso_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear"),
):
    vacio = {"reserva_id": None, "numero_alta": None, "items": []}
    item = db.query(ReservaItem).filter(
        ReservaItem.tipo_recurso == tipo_recurso,
        ReservaItem.recurso_id == recurso_id,
        ReservaItem.estado == "reservado",
    ).first()
    if not item:
        return vacio
    reserva = db.query(Reserva).filter(
        Reserva.id == item.reserva_id, Reserva.estado == "activa").first()
    if not reserva:
        return vacio
    # Aislamiento multiempresa
    if not user_has_empresa_access(db, current_user.id, reserva.empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    otros = db.query(ReservaItem).filter(
        ReservaItem.reserva_id == reserva.id,
        ReservaItem.estado == "reservado",
        ReservaItem.recurso_id != recurso_id,
    ).all()
    items = []
    for it in otros:
        d = _item_detalle(db, it)
        # solo los que el recurso real sigue "reservado"
        if d.get("estado_recurso") != "reservado":
            continue
        items.append({
            "tipo_recurso": it.tipo_recurso,
            "recurso_id": it.recurso_id,
            "placa": it.placa,
            "tipo": d["tipo"],
            "marca": d["marca"],
            "modelo": d["modelo"],
            "estado_recurso": d["estado_recurso"],
        })
    return {"reserva_id": reserva.id, "numero_alta": reserva.numero_alta, "items": items}


# ── GET /{id} (detalle) ───────────────────────────────────
@router.get("/{reserva_id}")
def obtener_reserva(
    reserva_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("reservas.gestionar"),
):
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    _verify_empresa(db, current_user, reserva.empresa_id)
    return _reserva_dict(db, reserva, with_items=True)


# ── PUT /{id} (editar fecha límite / descripción) ─────────
@router.put("/{reserva_id}")
def editar_reserva(
    reserva_id: str,
    data: ReservaUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("reservas.gestionar"),
):
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    _verify_empresa(db, current_user, reserva.empresa_id)
    if reserva.estado != "activa":
        raise HTTPException(status_code=400, detail=f"Solo se pueden editar reservas activas (estado: {reserva.estado})")

    if data.fecha_limite is not None:
        if data.fecha_limite <= date.today():
            raise HTTPException(status_code=400, detail="La fecha límite debe ser posterior a hoy")
        reserva.fecha_limite = data.fecha_limite
    if data.descripcion is not None:
        reserva.descripcion = data.descripcion.strip() or None

    db.commit()
    db.refresh(reserva)
    return _reserva_dict(db, reserva, with_items=True)


# ── POST / (crear) ────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def crear_reserva(
    data: ReservaCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("reservas.gestionar"),
):
    # 1. Acceso a la empresa
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    _verify_empresa(db, current_user, data.empresa_id)

    # 2. fecha_limite futura
    if not data.fecha_limite or data.fecha_limite <= date.today():
        raise HTTPException(status_code=400, detail="La fecha límite debe ser posterior a hoy")

    # 3. Al menos un item
    if not data.items:
        raise HTTPException(status_code=400, detail="Debes incluir al menos un recurso")

    # 4. Validar TODOS los items ANTES de modificar nada (todo-o-nada)
    recursos = []   # [(item, recurso)]
    vistos = set()
    for it in data.items:
        Model = _model(it.tipo_recurso)
        if not Model:
            raise HTTPException(status_code=400, detail=f"tipo_recurso inválido: {it.tipo_recurso}")
        clave = (it.tipo_recurso, it.recurso_id)
        if clave in vistos:
            raise HTTPException(status_code=400, detail="Hay recursos duplicados en la reserva")
        vistos.add(clave)
        rec = db.query(Model).filter(Model.id == it.recurso_id).first()
        if not rec:
            raise HTTPException(status_code=404, detail=f"Recurso {it.recurso_id} no encontrado")
        if rec.empresa_id != data.empresa_id:
            raise HTTPException(status_code=400,
                                detail=f"El recurso {_placa(rec, it.tipo_recurso)} no pertenece a esta empresa")
        if rec.estado != "disponible":
            raise HTTPException(status_code=400,
                                detail=f"El recurso {_placa(rec, it.tipo_recurso)} no está disponible (estado: {rec.estado})")
        recursos.append((it, rec))

    # 5. Crear la reserva
    reserva = Reserva(
        numero_alta=data.numero_alta.strip(),
        descripcion=(data.descripcion or None),
        empresa_id=data.empresa_id,
        fecha_limite=data.fecha_limite,
        estado="activa",
        creado_por_id=current_user.id,
    )
    db.add(reserva)
    db.flush()

    # 6. Crear items + reservar recursos
    for it, rec in recursos:
        placa = _placa(rec, it.tipo_recurso)
        db.add(ReservaItem(
            reserva_id=reserva.id,
            tipo_recurso=it.tipo_recurso,
            recurso_id=rec.id,
            placa=placa,
            estado="reservado",
        ))
        rec.estado = "reservado"
        _historial(db, it.tipo_recurso, rec.id, current_user.email,
                   f"Reservado para alta {reserva.numero_alta}")

    db.commit()
    db.refresh(reserva)
    return _reserva_dict(db, reserva, with_items=True)


# ── POST /{id}/cancelar ───────────────────────────────────
@router.post("/{reserva_id}/cancelar")
def cancelar_reserva(
    reserva_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("reservas.gestionar"),
):
    reserva = db.query(Reserva).filter(Reserva.id == reserva_id).first()
    if not reserva:
        raise HTTPException(status_code=404, detail="Reserva no encontrada")
    _verify_empresa(db, current_user, reserva.empresa_id)
    if reserva.estado != "activa":
        raise HTTPException(status_code=400, detail=f"La reserva ya está {reserva.estado}")

    items = db.query(ReservaItem).filter(
        ReservaItem.reserva_id == reserva.id, ReservaItem.estado == "reservado").all()
    for item in items:
        Model = _model(item.tipo_recurso)
        rec = db.query(Model).filter(Model.id == item.recurso_id).first() if Model else None
        # Solo liberar si sigue "reservado" (no tocar si ya fue asignado u otro)
        if rec and rec.estado == "reservado":
            rec.estado = "disponible"
            _historial(db, item.tipo_recurso, rec.id, current_user.email,
                       f"Reserva {reserva.numero_alta} cancelada, recurso liberado")
        item.estado = "liberado"

    reserva.estado = "cancelada"
    reserva.fecha_cierre = datetime.utcnow()
    db.commit()
    db.refresh(reserva)
    return _reserva_dict(db, reserva, with_items=True)
