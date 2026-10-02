from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
from database import get_db
from models.asignacion import Asignacion
from models.activo import Activo
from models.accesorio import Accesorio
from models.usuario import Usuario
from models.usuario_sistema import UsuarioSistema
from models.empresa import Empresa
from models.historial import HistorialMovimiento
from models.acta import Acta, ActaDetalle
from routers.auth import get_current_user
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids, empresas_pueden_compartir, has_permission
from services.reserva_service import cerrar_reserva_al_asignar
from services.inventario_service import resolver_custodio
from services.mantenimiento_service import (
    coverage_activa, tecnico_puede_ejecutar, activos_con_tarea_abierta,
    crear_tarea_preventiva,
)

router = APIRouter(prefix="/api/asignaciones", tags=["Asignaciones"])

# ── Schemas ──────────────────────────────────────────────
class AsignacionCreate(BaseModel):
    empresa_id: str
    # Multi-activo: el formulario envía activos_ids (lista). id_activo se
    # mantiene por compatibilidad (algunas integraciones envían uno solo).
    activos_ids: Optional[List[str]] = []
    id_activo: Optional[str] = None
    id_usuario: str
    accesorios_ids: Optional[List[str]] = []
    responsable_entrega: str
    responsable_recibe: str
    observaciones: Optional[str] = None
    es_prestamo: Optional[bool] = False
    fecha_limite_devolucion: Optional[date] = None

class DevolucionCreate(BaseModel):
    accesorios_ids: Optional[List[str]] = []
    responsable_entrega: str
    responsable_recibe: str
    observaciones: Optional[str] = None
    solo_accesorios: Optional[bool] = False  # True = devolver solo accesorios, no liberar el activo
    custodio_documento: Optional[str] = None  # opcional: custodio del recurso que queda en sede (sin acta)

class LiberarCreate(BaseModel):
    # Devolución de recursos asignados que NO tienen una Asignación (origen
    # importación/migración: estado=asignado sin acta). Libera por recurso.
    activo_id: Optional[str] = None
    accesorios_ids: Optional[List[str]] = []
    responsable_entrega: str
    responsable_recibe: str
    observaciones: Optional[str] = None
    custodio_documento: Optional[str] = None  # opcional: custodio en sede

class MantenimientoLoteCreate(BaseModel):
    # Programación OPCIONAL de mantenimiento preventivo junto con la devolución.
    # Un solo técnico + una sola fecha para todo el lote; activos_ids = los
    # equipos marcados (subconjunto de los activos que se devuelven).
    tecnico_id: str
    fecha: Optional[date] = None                # default: hoy
    activos_ids: Optional[List[str]] = []        # equipos marcados para mantenimiento

class DevolverLoteCreate(BaseModel):
    # Devolución consolidada: TODOS los recursos seleccionados en una sola
    # operación. Genera UNA acta por empresa (los recursos de empresas
    # distintas — hermanas — se separan en actas distintas). Maneja tanto
    # recursos CON Asignación activa como recursos importados SIN asignación.
    activos_ids: Optional[List[str]] = []
    accesorios_ids: Optional[List[str]] = []
    responsable_entrega: str
    responsable_recibe: str
    observaciones: Optional[str] = None
    custodio_documento: Optional[str] = None  # opcional: custodio en sede para todo el lote
    mantenimiento: Optional[MantenimientoLoteCreate] = None  # opcional: programar preventivo

class AsignacionResponse(BaseModel):
    id: str
    empresa_id: str
    id_activo: str
    id_usuario: str
    fecha_asignacion: datetime
    fecha_devolucion: Optional[datetime]
    estado: str
    asignado_por: str
    responsable_entrega: Optional[str]
    observaciones: Optional[str]
    placa_activo: Optional[str] = None
    tipo_activo: Optional[str] = None
    nombre_usuario: Optional[str] = None
    documento_usuario: Optional[str] = None
    nombre_empresa: Optional[str] = None

    class Config:
        from_attributes = True

# ── Helper ───────────────────────────────────────────────
def _normalizar_prestamo(es_prestamo: Optional[bool], fecha: Optional[date]):
    """
    Valida los parámetros de préstamo y devuelve (es_prestamo, fecha) normalizados.
    - es_prestamo=True  → fecha obligatoria y > hoy.
    - es_prestamo=False → fecha ignorada (None).
    """
    if not es_prestamo:
        return False, None
    if not fecha:
        raise HTTPException(status_code=400, detail="La fecha límite es obligatoria cuando es un préstamo")
    if fecha <= date.today():
        raise HTTPException(status_code=400, detail="La fecha límite debe ser posterior a hoy")
    return True, fecha


def asignacion_to_dict(a: Asignacion) -> dict:
    return {
        "id": a.id,
        "empresa_id": a.empresa_id,
        "id_activo": a.id_activo,
        "id_usuario": a.id_usuario,
        "fecha_asignacion": a.fecha_asignacion,
        "fecha_devolucion": a.fecha_devolucion,
        "estado": a.estado,
        "asignado_por": a.asignado_por,
        "responsable_entrega": a.recibido_por,
        "observaciones": a.observaciones,
        "placa_activo": a.activo.id_placa_activo if a.activo else None,
        "tipo_activo": a.activo.tipo_activo if a.activo else None,
        "nombre_usuario": a.usuario.nombre_completo if a.usuario else None,
        "documento_usuario": a.usuario.documento if a.usuario else None,
        "nombre_empresa": a.empresa.nombre_empresa if a.empresa else None,
    }

# ── Endpoints ────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def crear_asignacion(
    data: AsignacionCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear")
):
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and data.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    # Préstamo temporal (opcional): la fecha límite se aplica a todos los recursos nuevos
    es_prestamo, fecha_limite = _normalizar_prestamo(data.es_prestamo, data.fecha_limite_devolucion)

    # Normalizar lista de activos (multi-activo + compat. con id_activo único), sin duplicados
    activos_ids = list(data.activos_ids or [])
    if data.id_activo and data.id_activo not in activos_ids:
        activos_ids.append(data.id_activo)
    activos_ids = list(dict.fromkeys(activos_ids))  # dedup preservando orden

    if not activos_ids:
        raise HTTPException(status_code=400, detail="Debes seleccionar al menos un activo")

    usuario = db.query(Usuario).filter(Usuario.id == data.id_usuario).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    if usuario.estado != "activo":
        raise HTTPException(status_code=400, detail="El empleado no está activo")
    # El empleado debe pertenecer a la empresa del recurso O a una empresa
    # relacionada (hermana). Relación directa, no transitiva. NO afecta la
    # visibilidad de datos: solo amplía a QUIÉN se puede asignar el recurso.
    if not empresas_pueden_compartir(db, data.empresa_id, usuario.empresa_id):
        raise HTTPException(status_code=400, detail="El empleado no pertenece a la empresa del recurso ni a una empresa relacionada")

    # ── VALIDAR TODO antes de mutar (all-or-nothing) ──
    # Validar todos los activos nuevos
    activos_nuevos = []
    for act_id in activos_ids:
        activo = db.query(Activo).filter(Activo.id == act_id).first()
        if not activo:
            raise HTTPException(status_code=404, detail=f"Activo {act_id} no encontrado")
        if activo.estado not in ("disponible", "reservado"):
            raise HTTPException(status_code=400, detail=f"El activo {activo.id_placa_activo} no está disponible — estado actual: {activo.estado}")
        if activo.empresa_id != data.empresa_id:
            raise HTTPException(status_code=400, detail=f"El activo {activo.id_placa_activo} no pertenece a esta empresa")
        activos_nuevos.append(activo)

    # Validar accesorios nuevos a asignar
    accesorios_nuevos = []
    for acc_id in data.accesorios_ids:
        acc = db.query(Accesorio).filter(Accesorio.id == acc_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail=f"Accesorio {acc_id} no encontrado")
        if acc.estado not in ("disponible", "reservado"):
            raise HTTPException(status_code=400, detail=f"El accesorio {acc.id_placa_accesorio} no está disponible — estado actual: {acc.estado}")
        if acc.empresa_id != data.empresa_id:
            raise HTTPException(status_code=400, detail=f"El accesorio {acc.id_placa_accesorio} no pertenece a esta empresa")
        accesorios_nuevos.append(acc)

    # ── MUTAR (todo validado) ──
    # Una fila de Asignación por cada activo
    asignaciones_creadas = []
    for activo in activos_nuevos:
        asignacion = Asignacion(
            empresa_id=data.empresa_id,
            id_activo=activo.id,
            id_usuario=data.id_usuario,
            asignado_por=current_user.email,
            recibido_por=data.responsable_recibe,
            observaciones=data.observaciones,
            estado="activa"
        )
        db.add(asignacion)
        asignaciones_creadas.append(asignacion)

        # Cierra su reserva si estaba reservado, libera custodia y marca asignado
        cerrar_reserva_al_asignar(db, "activo", activo.id)
        activo.estado = "asignado"
        activo.id_usuario = data.id_usuario
        activo.es_prestamo = es_prestamo
        activo.fecha_limite_devolucion = fecha_limite
        activo.alerta_vencimiento_enviada = False
        if activo.custodio_id:
            db.add(HistorialMovimiento(
                id_activo=activo.id, tipo_movimiento="custodio", responsable=current_user.email,
                observaciones="Custodio retirado automáticamente (recurso asignado)"))
            activo.custodio_id = None

    # Actualizar accesorios nuevos (cierra su reserva si estaban reservados)
    for acc in accesorios_nuevos:
        cerrar_reserva_al_asignar(db, "accesorio", acc.id)
        acc.estado = "asignado"
        acc.id_usuario = data.id_usuario
        acc.es_prestamo = es_prestamo
        acc.fecha_limite_devolucion = fecha_limite
        acc.alerta_vencimiento_enviada = False
        if acc.custodio_id:
            db.add(HistorialMovimiento(
                id_accesorio=acc.id, tipo_movimiento="custodio", responsable=current_user.email,
                observaciones="Custodio retirado automáticamente (recurso asignado)"))
            acc.custodio_id = None

    db.flush()

    # ── Construir UNA acta con TODO lo que el empleado tendrá asignado (snapshot) ──
    ids_nuevos_activos = [a.id for a in activos_nuevos]
    # Activos ya asignados antes de esta operación (excluye los nuevos que ya se actualizaron)
    activos_previos = db.query(Activo).filter(
        Activo.id_usuario == data.id_usuario,
        Activo.estado == "asignado",
        ~Activo.id.in_(ids_nuevos_activos)
    ).all()

    # Accesorios ya asignados antes de esta operación
    ids_nuevos_acc = [a.id for a in accesorios_nuevos]
    accesorios_previos = db.query(Accesorio).filter(
        Accesorio.id_usuario == data.id_usuario,
        Accesorio.estado == "asignado",
        ~Accesorio.id.in_(ids_nuevos_acc) if ids_nuevos_acc else True
    ).all()

    # El acta lleva como activo principal el primer activo nuevo de esta operación
    activo_principal = activos_nuevos[0]
    acta = Acta(
        empresa_id=data.empresa_id,
        id_activo=activo_principal.id,
        id_usuario=data.id_usuario,
        tipo="entrega",
        responsable_entrega=data.responsable_entrega,
        responsable_recibe=data.responsable_recibe,
        observaciones=data.observaciones
    )
    db.add(acta)
    db.flush()

    # Detalle + historial: activos nuevos
    for activo in activos_nuevos:
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="activo", id_activo=activo.id))
        db.add(HistorialMovimiento(
            id_activo=activo.id, id_usuario=data.id_usuario, id_acta=acta.id,
            tipo_movimiento="asignacion", responsable=current_user.email,
            observaciones=f"Activo {activo.id_placa_activo} asignado a {usuario.nombre_completo} ({usuario.documento})"
        ))

    # Detalle: activos previamente asignados (snapshot)
    for a in activos_previos:
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="activo", id_activo=a.id))

    # Detalle + historial: accesorios nuevos
    for acc in accesorios_nuevos:
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="accesorio", id_accesorio=acc.id))
        db.add(HistorialMovimiento(
            id_accesorio=acc.id, id_usuario=data.id_usuario, id_acta=acta.id,
            tipo_movimiento="asignacion", responsable=current_user.email,
            observaciones=f"Accesorio {acc.id_placa_accesorio} asignado a {usuario.nombre_completo}"
        ))

    # Detalle: accesorios previamente asignados (snapshot)
    for acc in accesorios_previos:
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="accesorio", id_accesorio=acc.id))

    db.commit()
    for asg in asignaciones_creadas:
        db.refresh(asg)

    total_activos     = len(activos_nuevos) + len(activos_previos)
    total_accesorios  = len(accesorios_nuevos) + len(accesorios_previos)

    return {
        "mensaje": "Asignación creada correctamente",
        "asignacion_id": asignaciones_creadas[0].id,           # compat. (primera)
        "asignacion_ids": [a.id for a in asignaciones_creadas],
        "acta_id": acta.id,
        "placa_activo": activo_principal.id_placa_activo,
        "empleado": usuario.nombre_completo,
        "activos_asignados": len(activos_nuevos),
        "accesorios_asignados": len(accesorios_nuevos),
        "total_activos_en_acta": total_activos,
        "total_accesorios_en_acta": total_accesorios,
        "pdf_generado": False
    }


@router.get("/activas", response_model=List[AsignacionResponse])
def listar_activas(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.ver")
):
    query = db.query(Asignacion).filter(Asignacion.estado == "activa")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Asignacion.empresa_id == empresa_id)
        else:
            query = query.filter(Asignacion.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Asignacion.empresa_id == empresa_id)
    return [asignacion_to_dict(a) for a in query.order_by(Asignacion.fecha_asignacion.desc()).all()]


@router.get("/usuario/{usuario_id}/items-asignados")
def items_asignados_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.ver")
):
    """
    Retorna todos los activos Y accesorios asignados a un usuario.
    Usado en el modal de devolución.
    """
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and usuario.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese empleado")

    activos = db.query(Activo).filter(
        Activo.id_usuario == usuario_id,
        Activo.estado == "asignado"
    ).all()

    accesorios = db.query(Accesorio).filter(
        Accesorio.id_usuario == usuario_id,
        Accesorio.estado == "asignado"
    ).all()

    # Recursos bajo CUSTODIA de este empleado (disponibles, responsabilidad — no uso)
    cust_activos = db.query(Activo).filter(
        Activo.custodio_id == usuario_id, Activo.estado == "disponible").all()
    cust_accesorios = db.query(Accesorio).filter(
        Accesorio.custodio_id == usuario_id, Accesorio.estado == "disponible").all()

    return {
        "usuario": {
            "id": usuario.id,
            "nombre_completo": usuario.nombre_completo,
            "documento": usuario.documento,
            "cargo": usuario.cargo,
            "sede": usuario.sede,
            "empresa_id": usuario.empresa_id
        },
        "activos": [{
            "id": a.id,
            "id_placa_activo": a.id_placa_activo,
            "tipo_activo": a.tipo_activo,
            "marca": a.marca,
            "modelo": a.modelo,
            "serial": a.serial,
            "procesador": a.procesador,
            "memoria_ram": a.memoria_ram,
            "disco_1": a.disco_1,
            "estado": a.estado
        } for a in activos],
        "accesorios": [{
            "id": a.id,
            "id_placa_accesorio": a.id_placa_accesorio,
            "tipo_accesorio": a.tipo_accesorio,
            "marca": a.marca,
            "modelo": a.modelo,
            "serial": a.serial,
            "estado": a.estado
        } for a in accesorios],
        "en_custodia": [{
            "id": a.id, "tipo_recurso": "activo", "placa": a.id_placa_activo,
            "tipo": a.tipo_activo, "marca": a.marca, "modelo": a.modelo,
            "ubicacion": a.ubicacion, "estado": a.estado,
        } for a in cust_activos] + [{
            "id": a.id, "tipo_recurso": "accesorio", "placa": a.id_placa_accesorio,
            "tipo": a.tipo_accesorio, "marca": a.marca, "modelo": a.modelo,
            "ubicacion": a.ubicacion, "estado": a.estado,
        } for a in cust_accesorios],
    }


@router.get("/historial/activo/{activo_id}")
def historial_activo(
    activo_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.ver")
):
    activo = db.query(Activo).filter(Activo.id == activo_id).first()
    if not activo:
        raise HTTPException(status_code=404, detail="Activo no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and activo.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este activo")

    movimientos = db.query(HistorialMovimiento).filter(
        HistorialMovimiento.id_activo == activo_id
    ).order_by(HistorialMovimiento.fecha_movimiento.desc()).all()

    return {
        "activo": {
            "id": activo.id,
            "placa": activo.id_placa_activo,
            "tipo": activo.tipo_activo,
            "marca": activo.marca,
            "modelo": activo.modelo,
            "estado_actual": activo.estado
        },
        "movimientos": [{
            "id": m.id,
            "tipo": m.tipo_movimiento,
            "fecha": m.fecha_movimiento,
            "responsable": m.responsable,
            "observaciones": m.observaciones
        } for m in movimientos]
    }


@router.get("/historial/accesorio/{accesorio_id}")
def historial_accesorio(
    accesorio_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.ver")
):
    acc = db.query(Accesorio).filter(Accesorio.id == accesorio_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and acc.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este accesorio")

    movimientos = db.query(HistorialMovimiento).filter(
        HistorialMovimiento.id_accesorio == accesorio_id
    ).order_by(HistorialMovimiento.fecha_movimiento.desc()).all()

    return {
        "accesorio": {
            "id": acc.id,
            "placa": acc.id_placa_accesorio,
            "tipo": acc.tipo_accesorio,
            "marca": acc.marca,
            "modelo": acc.modelo,
            "estado_actual": acc.estado
        },
        "movimientos": [{
            "id": m.id,
            "tipo": m.tipo_movimiento,
            "fecha": m.fecha_movimiento,
            "responsable": m.responsable,
            "observaciones": m.observaciones
        } for m in movimientos]
    }


@router.get("/historial/usuario/{usuario_id}")
def historial_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.ver")
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and usuario.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este empleado")

    actas = db.query(Acta).filter(
        Acta.id_usuario == usuario_id
    ).order_by(Acta.fecha_entrega.desc()).all()

    def _item_desc(d):
        if d.activo:
            return {
                "tipo_item": "activo",
                "placa": d.activo.id_placa_activo,
                "descripcion": f"{d.activo.tipo_activo} {d.activo.marca or ''} {d.activo.modelo or ''}".strip()
            }
        if d.accesorio:
            return {
                "tipo_item": "accesorio",
                "placa": d.accesorio.id_placa_accesorio,
                "descripcion": f"{d.accesorio.tipo_accesorio} {d.accesorio.marca or ''} {d.accesorio.modelo or ''}".strip()
            }
        return None

    return {
        "usuario": {
            "id": usuario.id,
            "nombre": usuario.nombre_completo,
            "documento": usuario.documento,
            "cargo": usuario.cargo,
            "empresa": usuario.empresa.nombre_empresa if usuario.empresa else None
        },
        "actas": [{
            "id": a.id,
            "tipo": a.tipo,
            "fecha": a.fecha_entrega,
            "responsable_entrega": a.responsable_entrega,
            "responsable_recibe": a.responsable_recibe,
            "observaciones": a.observaciones,
            "items": [i for i in (_item_desc(d) for d in a.detalle) if i]
        } for a in actas]
    }


@router.get("/{asignacion_id}")
def obtener_asignacion(
    asignacion_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.ver")
):
    asignacion = db.query(Asignacion).filter(Asignacion.id == asignacion_id).first()
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación no encontrada")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and asignacion.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta asignación")

    accesorios = db.query(Accesorio).filter(
        Accesorio.id_usuario == asignacion.id_usuario,
        Accesorio.estado == "asignado"
    ).all()

    return {
        **asignacion_to_dict(asignacion),
        "accesorios": [{
            "id": a.id,
            "placa": a.id_placa_accesorio,
            "tipo": a.tipo_accesorio,
            "marca": a.marca,
            "modelo": a.modelo
        } for a in accesorios]
    }


@router.post("/{asignacion_id}/devolver", status_code=status.HTTP_200_OK)
def registrar_devolucion(
    asignacion_id: str,
    data: DevolucionCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.devolver")
):
    asignacion = db.query(Asignacion).filter(
        Asignacion.id == asignacion_id,
        Asignacion.estado == "activa"
    ).first()
    if not asignacion:
        raise HTTPException(status_code=404, detail="Asignación activa no encontrada")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and asignacion.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta asignación")

    activo  = db.query(Activo).filter(Activo.id == asignacion.id_activo).first()
    usuario = db.query(Usuario).filter(Usuario.id == asignacion.id_usuario).first()

    asignacion.estado = "devuelta" if not data.solo_accesorios else asignacion.estado
    if not data.solo_accesorios:
        asignacion.fecha_devolucion = datetime.utcnow()

    if not data.solo_accesorios:
        activo.estado     = "disponible"
        activo.id_usuario = None
        activo.ubicacion  = "Bodega CT"
        activo.es_prestamo = False
        activo.fecha_limite_devolucion = None
        activo.alerta_vencimiento_enviada = False

    acta = Acta(
        empresa_id=asignacion.empresa_id,
        id_activo=activo.id if not data.solo_accesorios else None,
        id_usuario=asignacion.id_usuario,
        tipo="devolucion",
        responsable_entrega=data.responsable_entrega,
        responsable_recibe=data.responsable_recibe,
        observaciones=data.observaciones
    )
    db.add(acta)
    db.flush()

    if not data.solo_accesorios:
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="activo", id_activo=activo.id))

    accesorios_devueltos = []
    for acc_id in data.accesorios_ids:
        acc = db.query(Accesorio).filter(Accesorio.id == acc_id).first()
        if acc and acc.id_usuario == asignacion.id_usuario:
            acc.estado    = "disponible"
            acc.id_usuario = None
            acc.ubicacion = "Bodega CT"
            acc.es_prestamo = False
            acc.fecha_limite_devolucion = None
            acc.alerta_vencimiento_enviada = False
            accesorios_devueltos.append(acc)
            db.add(ActaDetalle(acta_id=acta.id, tipo_item="accesorio", id_accesorio=acc.id))
            db.add(HistorialMovimiento(
                id_accesorio=acc.id, id_usuario=asignacion.id_usuario, id_acta=acta.id,
                tipo_movimiento="devolucion", responsable=current_user.email,
                observaciones=f"Accesorio {acc.id_placa_accesorio} devuelto"
            ))

    if not data.solo_accesorios:
        db.add(HistorialMovimiento(
            id_activo=activo.id, id_usuario=asignacion.id_usuario, id_acta=acta.id,
            tipo_movimiento="devolucion", responsable=current_user.email,
            observaciones=f"Activo {activo.id_placa_activo} devuelto por {usuario.nombre_completo} ({usuario.documento})"
        ))

    # ── Custodio OPCIONAL del recurso que queda en sede (sin acta, separado de la devolución) ──
    if data.custodio_documento and str(data.custodio_documento).strip():
        emp = resolver_custodio(db, asignacion.empresa_id, data.custodio_documento)
        recursos_custodia = ([activo] if not data.solo_accesorios else []) + accesorios_devueltos
        for r in recursos_custodia:
            r.custodio_id = emp.id
            db.add(HistorialMovimiento(
                id_activo=(r.id if hasattr(r, "id_placa_activo") else None),
                id_accesorio=(r.id if hasattr(r, "id_placa_accesorio") else None),
                tipo_movimiento="custodio", responsable=current_user.email,
                observaciones=f"Custodio asignado en devolución: {emp.nombre_completo} ({emp.documento})"))

    db.commit()

    return {
        "mensaje": "Devolución registrada correctamente",
        "acta_id": acta.id,
        "placa_activo": activo.id_placa_activo,
        "empleado": usuario.nombre_completo,
        "accesorios_devueltos": len(accesorios_devueltos),
        "pdf_generado": False
    }


@router.post("/liberar", status_code=status.HTTP_200_OK)
def liberar_recurso_asignado(
    data: LiberarCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.devolver")
):
    """Devuelve recursos asignados que NO tienen una Asignación (origen
    importación/migración). Libera el recurso (→ disponible), genera el acta de
    devolución y, opcionalmente, fija un custodio en sede. Mismo resultado que
    /devolver, pero sin requerir una Asignación previa."""
    activo = None
    if data.activo_id:
        activo = db.query(Activo).filter(Activo.id == data.activo_id).first()
        if not activo:
            raise HTTPException(status_code=404, detail="Activo no encontrado")
        if activo.estado != "asignado":
            raise HTTPException(status_code=400, detail=f"El activo {activo.id_placa_activo} no está asignado (estado: {activo.estado})")

    accesorios = []
    for acc_id in (data.accesorios_ids or []):
        acc = db.query(Accesorio).filter(Accesorio.id == acc_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail=f"Accesorio {acc_id} no encontrado")
        if acc.estado != "asignado":
            raise HTTPException(status_code=400, detail=f"El accesorio {acc.id_placa_accesorio} no está asignado (estado: {acc.estado})")
        accesorios.append(acc)

    if not activo and not accesorios:
        raise HTTPException(status_code=400, detail="No hay recursos para liberar")

    # Empresa (para el acta) + acceso del usuario
    empresa_id = activo.empresa_id if activo else accesorios[0].empresa_id
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    # Usuario al que estaba asignado (para atribuir el acta/historial)
    id_usuario_prev = (activo.id_usuario if activo else None) or (accesorios[0].id_usuario if accesorios else None)

    acta = Acta(
        empresa_id=empresa_id,
        id_activo=activo.id if activo else None,
        id_usuario=id_usuario_prev,
        tipo="devolucion",
        responsable_entrega=data.responsable_entrega,
        responsable_recibe=data.responsable_recibe,
        observaciones=data.observaciones,
    )
    db.add(acta)
    db.flush()

    recursos_liberados = []
    if activo:
        activo.estado = "disponible"
        activo.id_usuario = None
        activo.ubicacion = "Bodega CT"
        activo.es_prestamo = False
        activo.fecha_limite_devolucion = None
        activo.alerta_vencimiento_enviada = False
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="activo", id_activo=activo.id))
        db.add(HistorialMovimiento(
            id_activo=activo.id, id_usuario=id_usuario_prev, id_acta=acta.id,
            tipo_movimiento="devolucion", responsable=current_user.email,
            observaciones=f"Activo {activo.id_placa_activo} liberado (devolución sin asignación previa)"))
        recursos_liberados.append(activo)

    for acc in accesorios:
        acc.estado = "disponible"
        acc.id_usuario = None
        acc.ubicacion = "Bodega CT"
        acc.es_prestamo = False
        acc.fecha_limite_devolucion = None
        acc.alerta_vencimiento_enviada = False
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="accesorio", id_accesorio=acc.id))
        db.add(HistorialMovimiento(
            id_accesorio=acc.id, id_usuario=id_usuario_prev, id_acta=acta.id,
            tipo_movimiento="devolucion", responsable=current_user.email,
            observaciones=f"Accesorio {acc.id_placa_accesorio} liberado (devolución sin asignación previa)"))
        recursos_liberados.append(acc)

    # Custodio OPCIONAL del recurso que queda en sede (sin acta adicional)
    if data.custodio_documento and str(data.custodio_documento).strip():
        emp = resolver_custodio(db, empresa_id, data.custodio_documento)
        for r in recursos_liberados:
            r.custodio_id = emp.id
            db.add(HistorialMovimiento(
                id_activo=(r.id if hasattr(r, "id_placa_activo") else None),
                id_accesorio=(r.id if hasattr(r, "id_placa_accesorio") else None),
                tipo_movimiento="custodio", responsable=current_user.email,
                observaciones=f"Custodio asignado en devolución: {emp.nombre_completo} ({emp.documento})"))

    db.commit()
    return {
        "mensaje": "Recurso(s) liberado(s) correctamente",
        "acta_id": acta.id,
        "placa_activo": activo.id_placa_activo if activo else None,
        "accesorios_devueltos": len(accesorios),
        "pdf_generado": False,
    }


@router.post("/devolver-lote", status_code=status.HTTP_200_OK)
def devolver_lote(
    data: DevolverLoteCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.devolver")
):
    """Devolución consolidada de varios recursos en una sola operación.

    - Genera UNA acta de devolución por empresa (recursos de empresas distintas
      — hermanas — se reparten en actas distintas).
    - Maneja recursos CON Asignación activa (cierra la asignación) y recursos
      importados SIN asignación (los libera) de forma indistinta.
    - Aplica un custodio opcional a TODO el lote liberado.
    - Toda la operación es transaccional: o se crean todas las actas con sus
      recursos liberados, o no se crea nada (rollback total).

    El PDF de cada acta se genera aparte vía POST /actas/{id}/generar-pdf.
    """
    activos_ids = data.activos_ids or []
    accesorios_ids = data.accesorios_ids or []
    if not activos_ids and not accesorios_ids:
        raise HTTPException(status_code=400, detail="No hay recursos para devolver")

    # ── Cargar y validar todos los recursos (estado y existencia) ──
    activos = []
    for aid in activos_ids:
        a = db.query(Activo).filter(Activo.id == aid).first()
        if not a:
            raise HTTPException(status_code=404, detail=f"Activo {aid} no encontrado")
        if a.estado != "asignado":
            raise HTTPException(status_code=400, detail=f"El activo {a.id_placa_activo} no está asignado (estado: {a.estado})")
        activos.append(a)

    accesorios = []
    for acc_id in accesorios_ids:
        acc = db.query(Accesorio).filter(Accesorio.id == acc_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail=f"Accesorio {acc_id} no encontrado")
        if acc.estado != "asignado":
            raise HTTPException(status_code=400, detail=f"El accesorio {acc.id_placa_accesorio} no está asignado (estado: {acc.estado})")
        accesorios.append(acc)

    # ── Validar acceso del usuario a todas las empresas implicadas ──
    empresa_ids_usuario = get_user_empresa_ids(db, current_user.id)
    empresas_lote = {r.empresa_id for r in (activos + accesorios)}
    if empresa_ids_usuario is not None:
        sin_acceso = empresas_lote - set(empresa_ids_usuario)
        if sin_acceso:
            raise HTTPException(status_code=403, detail="No tienes acceso a una o más empresas del lote")

    # ── Validar el técnico del mantenimiento ANTES de tocar nada (evita huérfanos) ──
    # Solo valida si se pidió programar mantenimiento para ≥1 equipo.
    mant = data.mantenimiento
    mant_activos_pedidos = set(mant.activos_ids or []) if mant else set()
    if mant and mant_activos_pedidos:
        tecnico = db.query(UsuarioSistema).filter(UsuarioSistema.id == mant.tecnico_id).first()
        if not tecnico:
            raise HTTPException(status_code=404, detail="Técnico de mantenimiento no encontrado")
        if not tecnico_puede_ejecutar(db, mant.tecnico_id):
            raise HTTPException(status_code=400, detail="El técnico no tiene permiso para ejecutar mantenimientos")

    # ── Agrupar por empresa ──
    grupos = {}  # empresa_id -> {"activos": [...], "accesorios": [...]}
    for a in activos:
        grupos.setdefault(a.empresa_id, {"activos": [], "accesorios": []})["activos"].append(a)
    for acc in accesorios:
        grupos.setdefault(acc.empresa_id, {"activos": [], "accesorios": []})["accesorios"].append(acc)

    # ── Procesar cada grupo dentro de UNA sola transacción (atómica) ──
    actas_creadas = []
    try:
        for empresa_id, grupo in grupos.items():
            grp_activos = grupo["activos"]
            grp_accesorios = grupo["accesorios"]

            # Usuario al que estaban asignados (para atribuir el acta/historial)
            id_usuario_prev = next((a.id_usuario for a in grp_activos if a.id_usuario), None) \
                or next((acc.id_usuario for acc in grp_accesorios if acc.id_usuario), None)

            acta = Acta(
                empresa_id=empresa_id,
                id_activo=grp_activos[0].id if grp_activos else None,
                id_usuario=id_usuario_prev,
                tipo="devolucion",
                responsable_entrega=data.responsable_entrega,
                responsable_recibe=data.responsable_recibe,
                observaciones=data.observaciones,
            )
            db.add(acta)
            db.flush()

            recursos_liberados = []

            for activo in grp_activos:
                usuario_prev = activo.id_usuario
                # Cerrar Asignación activa si existe (recursos con asignación);
                # si no existe (importados), solo se libera el recurso.
                asignacion = db.query(Asignacion).filter(
                    Asignacion.id_activo == activo.id,
                    Asignacion.estado == "activa"
                ).first()
                if asignacion:
                    asignacion.estado = "devuelta"
                    asignacion.fecha_devolucion = datetime.utcnow()

                activo.estado = "disponible"
                activo.id_usuario = None
                activo.ubicacion = "Bodega CT"
                activo.es_prestamo = False
                activo.fecha_limite_devolucion = None
                activo.alerta_vencimiento_enviada = False
                db.add(ActaDetalle(acta_id=acta.id, tipo_item="activo", id_activo=activo.id))
                db.add(HistorialMovimiento(
                    id_activo=activo.id, id_usuario=usuario_prev, id_acta=acta.id,
                    tipo_movimiento="devolucion", responsable=current_user.email,
                    observaciones=f"Activo {activo.id_placa_activo} devuelto (devolución consolidada)"))
                recursos_liberados.append(activo)

            for acc in grp_accesorios:
                usuario_prev = acc.id_usuario
                acc.estado = "disponible"
                acc.id_usuario = None
                acc.ubicacion = "Bodega CT"
                acc.es_prestamo = False
                acc.fecha_limite_devolucion = None
                acc.alerta_vencimiento_enviada = False
                db.add(ActaDetalle(acta_id=acta.id, tipo_item="accesorio", id_accesorio=acc.id))
                db.add(HistorialMovimiento(
                    id_accesorio=acc.id, id_usuario=usuario_prev, id_acta=acta.id,
                    tipo_movimiento="devolucion", responsable=current_user.email,
                    observaciones=f"Accesorio {acc.id_placa_accesorio} devuelto (devolución consolidada)"))
                recursos_liberados.append(acc)

            # Custodio OPCIONAL para todo el grupo liberado (en sede, sin acta extra)
            if data.custodio_documento and str(data.custodio_documento).strip():
                emp = resolver_custodio(db, empresa_id, data.custodio_documento)
                for r in recursos_liberados:
                    r.custodio_id = emp.id
                    db.add(HistorialMovimiento(
                        id_activo=(r.id if hasattr(r, "id_placa_activo") else None),
                        id_accesorio=(r.id if hasattr(r, "id_placa_accesorio") else None),
                        tipo_movimiento="custodio", responsable=current_user.email,
                        observaciones=f"Custodio asignado en devolución: {emp.nombre_completo} ({emp.documento})"))

            actas_creadas.append({
                "acta_id": acta.id,
                "empresa_id": empresa_id,
                "total_activos": len(grp_activos),
                "total_accesorios": len(grp_accesorios),
                "total_items": len(grp_activos) + len(grp_accesorios),
            })

        # ── Programar mantenimiento preventivo (opcional) para los equipos marcados ──
        # Se crea DESPUÉS de procesar la devolución, dentro de la MISMA transacción y
        # justo antes del commit: si la devolución falla, el rollback también descarta
        # estas tareas (sin huérfanos). Skip-with-reason para los no elegibles; nunca
        # hace fallar la devolución.
        mant_creadas, mant_omitidos = [], []
        if mant and mant_activos_pedidos:
            fecha_mant = mant.fecha or date.today()
            cobertura = coverage_activa(db)
            activos_por_id = {a.id: a for a in activos}          # solo los realmente devueltos
            con_tarea = activos_con_tarea_abierta(db, list(mant_activos_pedidos))
            for aid in mant.activos_ids:
                a = activos_por_id.get(aid)
                if not a:
                    mant_omitidos.append({"activo_id": aid, "placa": None,
                        "motivo": "No forma parte de esta devolución"})
                    continue
                if not has_permission(db, current_user.id, a.empresa_id, "mantenimiento.planes"):
                    mant_omitidos.append({"activo_id": aid, "placa": a.id_placa_activo,
                        "motivo": "Sin permiso para programar mantenimiento en su empresa"})
                    continue
                plan = cobertura.get(a.tipo_activo)
                if not plan:
                    mant_omitidos.append({"activo_id": aid, "placa": a.id_placa_activo,
                        "motivo": "Su tipo no tiene un plan de mantenimiento activo"})
                    continue
                if a.id in con_tarea:
                    mant_omitidos.append({"activo_id": aid, "placa": a.id_placa_activo,
                        "motivo": "Ya tiene una tarea de mantenimiento abierta"})
                    continue
                t = crear_tarea_preventiva(db, a, plan, mant.tecnico_id, fecha_mant, current_user.id,
                                           origen="devolucion")
                con_tarea.add(a.id)                              # evita duplicar si viene repetido
                mant_creadas.append({"tarea_id": t.id, "activo_id": a.id,
                    "placa": a.id_placa_activo, "fecha_programada": fecha_mant,
                    "plan_nombre": plan.nombre})

        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error en la devolución consolidada: {str(e)}")

    return {
        "mensaje": "Devolución consolidada registrada correctamente",
        "actas": actas_creadas,
        "total_actas": len(actas_creadas),
        "pdf_generado": False,
        "mantenimiento": {
            "creadas": mant_creadas,
            "total_creadas": len(mant_creadas),
            "omitidos": mant_omitidos,
            "total_omitidos": len(mant_omitidos),
        },
    }
