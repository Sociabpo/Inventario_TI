from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional, List
from datetime import date
from database import get_db
from models.accesorio import Accesorio
from models.activo import Activo
from models.empresa import Empresa
from models.usuario import Usuario
from models.historial import HistorialMovimiento
from models.acta import Acta, ActaDetalle
from routers.auth import get_current_user
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids, empresas_pueden_compartir
from services.reserva_service import cerrar_reserva_al_asignar
from services.prestamo_service import loan_dict
from services.inventario_service import crear_accesorio_core, _validar_ubicacion_o_400, resolver_custodio
from services.pdf_service import generar_pdf_acta, generar_pdf_acta_accesorios

router = APIRouter(prefix="/api/accesorios", tags=["Accesorios"])

# ── Schemas ──────────────────────────────────────────────
class AccesorioCreate(BaseModel):
    empresa_id: str
    tipo_accesorio: str  # Mouse, Teclado, Diadema, Guaya, Hub, Bolso, Cargador
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serial: Optional[str] = None
    ubicacion: Optional[str] = None
    observaciones: Optional[str] = None
    garantia_meses: Optional[int] = None
    garantia_fin: Optional[date] = None

class AccesorioUpdate(BaseModel):
    tipo_accesorio: Optional[str] = None
    marca: Optional[str] = None
    modelo: Optional[str] = None
    serial: Optional[str] = None
    estado: Optional[str] = None
    ubicacion: Optional[str] = None
    observaciones: Optional[str] = None
    id_usuario: Optional[str] = None
    garantia_meses: Optional[int] = None
    garantia_fin: Optional[date] = None

class AccesorioResponse(BaseModel):
    id: str
    id_placa_accesorio: str
    empresa_id: str
    tipo_accesorio: str
    marca: Optional[str]
    modelo: Optional[str]
    serial: Optional[str]
    estado: str
    ubicacion: Optional[str] = None
    observaciones: Optional[str]
    garantia_meses: Optional[int] = None
    garantia_fin: Optional[date] = None
    nombre_empresa: Optional[str] = None
    id_usuario: Optional[str] = None
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
def accesorio_to_dict(acc: Accesorio) -> dict:
    return {
        **loan_dict(acc),
        "id": acc.id,
        "id_placa_accesorio": acc.id_placa_accesorio,
        "empresa_id": acc.empresa_id,
        "tipo_accesorio": acc.tipo_accesorio,
        "marca": acc.marca,
        "modelo": acc.modelo,
        "serial": acc.serial,
        "estado": acc.estado,
        "ubicacion": acc.ubicacion,
        "observaciones": acc.observaciones,
        "garantia_meses": acc.garantia_meses,
        "garantia_fin": acc.garantia_fin,
        "es_alquiler": bool(acc.es_alquiler),
        "contrato_alquiler_id": acc.contrato_alquiler_id,
        "nombre_empresa": acc.empresa.nombre_empresa if acc.empresa else None,
        "id_usuario": acc.id_usuario,
        "nombre_usuario": acc.usuario.nombre_completo if acc.usuario else None,
        "documento_usuario": acc.usuario.documento if acc.usuario else None,
        "custodio_id": acc.custodio_id,
        "custodio_nombre": acc.custodio.nombre_completo if acc.custodio else None,
        "custodio_documento": acc.custodio.documento if acc.custodio else None,
    }

# Adjunta info de la reserva activa (numero_alta + fecha_limite) a los accesorios
# en estado "reservado". Consulta en lote para evitar N+1.
def _adjuntar_reservas(db: Session, dicts: list) -> list:
    from models.reserva import Reserva, ReservaItem
    ids = [d["id"] for d in dicts if d.get("estado") == "reservado"]
    if not ids:
        return dicts
    rows = db.query(ReservaItem, Reserva).join(
        Reserva, ReservaItem.reserva_id == Reserva.id
    ).filter(
        ReservaItem.tipo_recurso == "accesorio",
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


class AsignarLoteCreate(BaseModel):
    empresa_id: str
    id_usuario: str
    accesorios_ids: List[str]
    responsable_entrega: str
    responsable_recibe: str
    observaciones: Optional[str] = None
    es_prestamo: Optional[bool] = False
    fecha_limite_devolucion: Optional[date] = None


# ── Endpoints ────────────────────────────────────────────
@router.post("/asignar-lote", status_code=status.HTTP_201_CREATED)
def asignar_accesorios_lote(
    data: AsignarLoteCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("accesorios.asignar")
):
    """
    Asigna uno o varios accesorios a un empleado, crea el acta de entrega
    y genera el PDF. Pensado para asignaciones sin activo principal.
    """
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and data.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

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

    # Préstamo temporal (opcional): la fecha límite se aplica a cada accesorio
    es_prestamo = bool(data.es_prestamo)
    fecha_limite = None
    if es_prestamo:
        if not data.fecha_limite_devolucion:
            raise HTTPException(status_code=400, detail="La fecha límite es obligatoria cuando es un préstamo")
        if data.fecha_limite_devolucion <= date.today():
            raise HTTPException(status_code=400, detail="La fecha límite debe ser posterior a hoy")
        fecha_limite = data.fecha_limite_devolucion

    # Validar y cargar accesorios
    accesorios = []
    for acc_id in data.accesorios_ids:
        acc = db.query(Accesorio).filter(Accesorio.id == acc_id).first()
        if not acc:
            raise HTTPException(status_code=404, detail=f"Accesorio {acc_id} no encontrado")
        if acc.estado not in ("disponible", "reservado"):
            raise HTTPException(status_code=400, detail=f"El accesorio {acc.id_placa_accesorio} no está disponible — estado actual: {acc.estado}")
        if acc.empresa_id != data.empresa_id:
            raise HTTPException(status_code=400, detail=f"El accesorio {acc.id_placa_accesorio} no pertenece a esta empresa")
        accesorios.append(acc)

    # Asignar cada accesorio nuevo (cierra su reserva si estaba reservado)
    for acc in accesorios:
        cerrar_reserva_al_asignar(db, "accesorio", acc.id)
        acc.estado     = "asignado"
        acc.id_usuario = data.id_usuario
        acc.es_prestamo = es_prestamo
        acc.fecha_limite_devolucion = fecha_limite
        acc.alerta_vencimiento_enviada = False
        # La asignación para uso elimina la custodia
        if acc.custodio_id:
            db.add(HistorialMovimiento(
                id_accesorio=acc.id, tipo_movimiento="custodio", responsable=current_user.email,
                observaciones="Custodio retirado automáticamente (recurso asignado)"))
            acc.custodio_id = None

    db.flush()

    # ── Construir acta con TODO lo que el empleado tendrá asignado ──
    ids_nuevos = [a.id for a in accesorios]

    activos_asignados = db.query(Activo).filter(
        Activo.id_usuario == data.id_usuario,
        Activo.estado == "asignado"
    ).all()

    accesorios_previos = db.query(Accesorio).filter(
        Accesorio.id_usuario == data.id_usuario,
        Accesorio.estado == "asignado",
        ~Accesorio.id.in_(ids_nuevos)
    ).all()

    acta = Acta(
        empresa_id=data.empresa_id,
        id_activo=activos_asignados[0].id if activos_asignados else None,
        id_usuario=data.id_usuario,
        tipo="entrega",
        responsable_entrega=data.responsable_entrega,
        responsable_recibe=data.responsable_recibe,
        observaciones=data.observaciones
    )
    db.add(acta)
    db.flush()

    # Detalle: activos ya asignados
    for a in activos_asignados:
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="activo", id_activo=a.id))

    # Detalle: accesorios nuevos
    for acc in accesorios:
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="accesorio", id_accesorio=acc.id))
        db.add(HistorialMovimiento(
            id_accesorio=acc.id,
            id_usuario=data.id_usuario,
            id_acta=acta.id,
            tipo_movimiento="asignacion",
            responsable=current_user.email,
            observaciones=f"Accesorio {acc.id_placa_accesorio} asignado a {usuario.nombre_completo} ({usuario.documento})"
        ))

    # Detalle: accesorios previos
    for acc in accesorios_previos:
        db.add(ActaDetalle(acta_id=acta.id, tipo_item="accesorio", id_accesorio=acc.id))

    db.commit()

    # Generar PDF acumulativo leyendo todos los ActaDetalle guardados
    try:
        detalles = db.query(ActaDetalle).filter(ActaDetalle.acta_id == acta.id).all()

        activos_pdf = []
        for d in detalles:
            if d.tipo_item == "activo" and d.id_activo:
                a = db.query(Activo).filter(Activo.id == d.id_activo).first()
                if a:
                    activos_pdf.append(a)

        accesorios_pdf = []
        for d in detalles:
            if d.tipo_item == "accesorio" and d.id_accesorio:
                acc_obj = db.query(Accesorio).filter(Accesorio.id == d.id_accesorio).first()
                if acc_obj:
                    accesorios_pdf.append(acc_obj)

        if activos_pdf:
            activo_principal = activos_pdf[0]
            ruta_pdf, hash_pdf = generar_pdf_acta(
                acta=acta,
                activo=activo_principal,
                activos_extra=activos_pdf[1:],
                usuario=usuario,
                empresa=empresa,
                accesorios=accesorios_pdf
            )
        else:
            ruta_pdf, hash_pdf = generar_pdf_acta_accesorios(
                acta=acta,
                usuario=usuario,
                empresa=empresa,
                accesorios=accesorios_pdf
            )

        acta.url_pdf  = ruta_pdf
        acta.hash_pdf = hash_pdf
        db.commit()
    except Exception as e:
        ruta_pdf = None
        hash_pdf = None

    return {
        "mensaje": f"{len(accesorios)} accesorio(s) asignado(s) correctamente",
        "acta_id": acta.id,
        "empleado": usuario.nombre_completo,
        "accesorios_asignados": len(accesorios),
        "url_pdf": ruta_pdf,
        "pdf_generado": ruta_pdf is not None
    }



@router.get("", response_model=List[AccesorioResponse])
def listar_accesorios(
    empresa_id: Optional[str] = None,
    estado: Optional[str] = None,
    tipo_accesorio: Optional[str] = None,
    incluir_retirados: bool = False,
    q: Optional[str] = Query(None, description="Buscar por placa, serial o tipo"),
    db: Session = Depends(get_db),
    current_user = require_permission("accesorios.ver")
):
    query = db.query(Accesorio)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Accesorio.empresa_id == empresa_id)
        else:
            query = query.filter(Accesorio.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Accesorio.empresa_id == empresa_id)
    if estado:
        query = query.filter(Accesorio.estado == estado)
    elif not incluir_retirados:
        query = query.filter(Accesorio.estado != "retirado")
    if tipo_accesorio:
        query = query.filter(Accesorio.tipo_accesorio.ilike(f"%{tipo_accesorio}%"))
    if q:
        query = query.filter(or_(
            Accesorio.id_placa_accesorio.ilike(f"%{q}%"),
            Accesorio.serial.ilike(f"%{q}%"),
            Accesorio.tipo_accesorio.ilike(f"%{q}%"),
        ))
    return _adjuntar_reservas(db, [accesorio_to_dict(a) for a in query.order_by(Accesorio.id_placa_accesorio).all()])


@router.post("", response_model=AccesorioResponse, status_code=status.HTTP_201_CREATED)
def crear_accesorio(
    data: AccesorioCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("accesorios.crear")
):
    # Reutiliza el núcleo compartido (placa, historial) — el mismo que usa el
    # flujo de "crear inventario desde recepción".
    accesorio = crear_accesorio_core(db, data, current_user)
    db.commit()
    db.refresh(accesorio)
    return accesorio_to_dict(accesorio)


@router.get("/disponibles", response_model=List[AccesorioResponse])
def listar_disponibles(
    empresa_id: str,
    tipo_accesorio: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("accesorios.ver")
):
    """Accesorios disponibles para asignar"""
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    query = db.query(Accesorio).filter(
        Accesorio.empresa_id == empresa_id,
        Accesorio.estado == "disponible"
    )
    if tipo_accesorio:
        query = query.filter(Accesorio.tipo_accesorio.ilike(f"%{tipo_accesorio}%"))
    return [accesorio_to_dict(a) for a in query.order_by(Accesorio.id_placa_accesorio).all()]


@router.get("/placa/{placa}", response_model=AccesorioResponse)
def buscar_accesorio_por_placa(
    placa: str,
    db: Session = Depends(get_db),
    current_user = require_permission("accesorios.ver")
):
    acc = db.query(Accesorio).filter(
        Accesorio.id_placa_accesorio == placa.upper()
    ).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and acc.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este accesorio")
    return accesorio_to_dict(acc)


@router.get("/{accesorio_id}", response_model=AccesorioResponse)
def obtener_accesorio(
    accesorio_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("accesorios.ver")
):
    acc = db.query(Accesorio).filter(Accesorio.id == accesorio_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and acc.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este accesorio")
    return accesorio_to_dict(acc)


# ── Custodio (empleado responsable mientras el accesorio está disponible) ─────
class CustodioIn(BaseModel):
    custodio_documento: str


@router.post("/{accesorio_id}/custodio")
def set_custodio_accesorio(
    accesorio_id: str,
    data: CustodioIn,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear")
):
    acc = db.query(Accesorio).filter(Accesorio.id == accesorio_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and acc.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese accesorio")
    if acc.estado != "disponible":
        raise HTTPException(status_code=400, detail="Solo se puede asignar custodio a un recurso disponible")
    emp = resolver_custodio(db, acc.empresa_id, data.custodio_documento)
    acc.custodio_id = emp.id
    db.add(HistorialMovimiento(
        id_accesorio=acc.id, tipo_movimiento="custodio", responsable=current_user.email,
        observaciones=f"Custodio asignado: {emp.nombre_completo} ({emp.documento})"))
    db.commit()
    db.refresh(acc)
    return accesorio_to_dict(acc)


@router.delete("/{accesorio_id}/custodio")
def remove_custodio_accesorio(
    accesorio_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear")
):
    acc = db.query(Accesorio).filter(Accesorio.id == accesorio_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and acc.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese accesorio")
    if acc.custodio_id:
        db.add(HistorialMovimiento(
            id_accesorio=acc.id, tipo_movimiento="custodio", responsable=current_user.email,
            observaciones="Custodio retirado"))
    acc.custodio_id = None
    db.commit()
    db.refresh(acc)
    return accesorio_to_dict(acc)


@router.put("/{accesorio_id}", response_model=AccesorioResponse)
def actualizar_accesorio(
    accesorio_id: str,
    data: AccesorioUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("accesorios.editar")
):
    acc = db.query(Accesorio).filter(Accesorio.id == accesorio_id).first()
    if not acc:
        raise HTTPException(status_code=404, detail="Accesorio no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and acc.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este accesorio")

    # Un accesorio retirado (dado de baja) es de SOLO LECTURA: se puede consultar
    # pero no modificar. Cualquier cambio sobre él se rechaza.
    if acc.estado == "retirado":
        raise HTTPException(
            status_code=409,
            detail="El accesorio está retirado y no puede modificarse. Solo puede consultarse.",
        )

    # El estado NO se modifica desde este endpoint. Los cambios de estado se realizan
    # EXCLUSIVAMENTE a través de /api/estados/* y de los flujos de asignación/devolución.
    # Aquí se ignora cualquier 'estado' recibido (defensa en profundidad).
    update_data = data.model_dump(exclude_unset=True)
    update_data.pop("estado", None)

    # Ubicación obligatoria cuando el accesorio no está asignado (sigue siendo editable)
    if acc.estado != "asignado" and "ubicacion" in update_data:
        ubic_final = update_data["ubicacion"]
        if not ubic_final or not str(ubic_final).strip():
            raise HTTPException(status_code=400, detail="La ubicación es obligatoria cuando el estado no es 'Asignado'")
    # Validar/canonicalizar la ubicación contra el catálogo de la empresa
    if "ubicacion" in update_data and update_data["ubicacion"]:
        update_data["ubicacion"] = _validar_ubicacion_o_400(db, acc.empresa_id, update_data["ubicacion"])

    for campo, valor in update_data.items():
        setattr(acc, campo, valor)

    db.commit()
    db.refresh(acc)
    return accesorio_to_dict(acc)