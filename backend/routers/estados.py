"""
Módulo de cambio de estado de activos/accesorios + bajas.
Prefix: /api/estados

Reconciliación con el modelo de 7 estados existente:
  El selector de alto nivel (disponible/mantenimiento/retirado) se mapea al estado
  canónico real (en_garantia, en_reparacion, mantenimiento_preventivo/correctivo).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

from database import get_db
from models.activo import Activo
from models.accesorio import Accesorio
from models.usuario import Usuario
from models.empresa import Empresa
from models.historial import HistorialMovimiento
from models.cambio_estado import CambioEstado
from models.baja_activo import BajaActivo
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids, user_has_empresa_access
from services.inventario_service import _validar_ubicacion_o_400

router = APIRouter(prefix="/api/estados", tags=["Cambio de estado"])

# Estados de mantenimiento REACTIVO (los que gestiona este módulo). El
# preventivo NO está aquí: se gestiona íntegramente en el módulo de Mantenimiento
# (con checklist + acta + reloj de 12 meses), que fija/restaura el estado por su
# cuenta. Excluirlo evita que el "finalizar mantenimiento" reactivo toque un
# equipo cuyo preventivo es propiedad del módulo.
ESTADOS_MANT = {"mantenimiento_correctivo", "en_reparacion", "en_garantia"}


# ── Helpers ───────────────────────────────────────────────
def _get_recurso(db, tipo_recurso, recurso_id):
    Model = Activo if tipo_recurso == "activo" else Accesorio if tipo_recurso == "accesorio" else None
    if not Model:
        raise HTTPException(status_code=400, detail="tipo_recurso inválido")
    r = db.query(Model).filter(Model.id == recurso_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Recurso no encontrado")
    return r


def _placa(r, tipo):
    return r.id_placa_activo if tipo == "activo" else r.id_placa_accesorio


def _verify(db, current_user, empresa_id):
    if not user_has_empresa_access(db, current_user.id, empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")


def _derivar_estado_mant(tipo_mant, cubierto_garantia, reparacion_externa):
    """Deriva el estado de mantenimiento a partir de SEÑALES EXPLÍCITAS, no del
    texto de la ubicación. La ubicación es solo la ubicación física (catálogo).
      - cubierto_garantia        → en_garantia
      - reparacion_externa (proveedor|fabricante) → en_reparacion
      - en otro caso             → mantenimiento_correctivo | mantenimiento_preventivo
    """
    if cubierto_garantia:
        return "en_garantia"
    if reparacion_externa in ("proveedor", "fabricante"):
        return "en_reparacion"
    return "mantenimiento_correctivo" if tipo_mant == "correctivo" else "mantenimiento_preventivo"


def _historial(db, tipo, recurso_id, responsable, obs, tipo_movimiento="cambio_estado"):
    db.add(HistorialMovimiento(
        id_activo=recurso_id if tipo == "activo" else None,
        id_accesorio=recurso_id if tipo == "accesorio" else None,
        tipo_movimiento=tipo_movimiento,
        responsable=responsable,
        observaciones=obs,
    ))


# ── POST /cambiar ─────────────────────────────────────────
class CambiarIn(BaseModel):
    tipo_recurso: str
    recurso_id: str
    estado_nuevo: str                       # disponible | mantenimiento | retirado
    ubicacion: Optional[str] = None
    tipo_mantenimiento: Optional[str] = None
    reparacion_externa: Optional[str] = None  # None/"" | "proveedor" | "fabricante" → en_reparacion
    cubierto_garantia: Optional[bool] = False
    cubre_garantia: Optional[str] = None
    tiempo_estimado_dias: Optional[int] = None
    responsable_mant: Optional[str] = None
    descripcion: Optional[str] = None


@router.post("/cambiar")
def cambiar_estado(data: CambiarIn, db: Session = Depends(get_db),
                   current_user = require_permission("estados.cambiar")):
    r = _get_recurso(db, data.tipo_recurso, data.recurso_id)
    _verify(db, current_user, r.empresa_id)
    estado_anterior = r.estado
    id_usuario_original = r.id_usuario   # antes de cualquier modificación

    if r.estado == "retirado":
        raise HTTPException(status_code=400, detail="Un recurso retirado no puede cambiar de estado")
    if r.estado == "reservado":
        raise HTTPException(status_code=400, detail="El recurso está reservado. Cancela la reserva primero.")
    if data.tipo_recurso == "accesorio" and data.reparacion_externa in ("proveedor", "fabricante"):
        raise HTTPException(status_code=400, detail="Los accesorios no se envían a reparación externa")
    if data.estado_nuevo == "retirado":
        raise HTTPException(status_code=400, detail="Para retirar usa la solicitud de baja (/estados/solicitar-baja)")
    if data.estado_nuevo not in ("disponible", "mantenimiento"):
        raise HTTPException(status_code=400, detail="estado_nuevo debe ser 'disponible' o 'mantenimiento'")

    # Ubicación contra el catálogo de la empresa del recurso (si se proporcionó)
    ubicacion_canonica = _validar_ubicacion_o_400(db, r.empresa_id, data.ubicacion)

    if data.estado_nuevo == "disponible":
        canonico = "disponible"
    else:
        canonico = _derivar_estado_mant(data.tipo_mantenimiento, data.cubierto_garantia, data.reparacion_externa)
        # El preventivo NO se puede fijar manualmente: va por el módulo de Mantenimiento.
        if canonico == "mantenimiento_preventivo":
            raise HTTPException(
                status_code=400,
                detail="El mantenimiento preventivo se gestiona desde el módulo de Mantenimiento")

    # El cambio de estado NUNCA retira el equipo del usuario ni genera actas: toda
    # devolución/retiro debe pasar por el flujo completo de devolución (con su acta y
    # firma). Si el recurso estaba asignado y entra a mantenimiento, conserva su
    # usuario y se guarda 'usuario_previo' para restaurar "asignado" al finalizar.
    genero_acta, acta_id = False, None

    # Aplicar estado + ubicación (canónica del catálogo)
    r.estado = canonico
    if ubicacion_canonica:
        r.ubicacion = ubicacion_canonica

    usuario_previo = id_usuario_original if estado_anterior == "asignado" else None

    ce = CambioEstado(
        tipo_recurso=data.tipo_recurso, recurso_id=r.id, placa=_placa(r, data.tipo_recurso),
        empresa_id=r.empresa_id, estado_anterior=estado_anterior, estado_nuevo=canonico,
        ubicacion=ubicacion_canonica, tipo_mantenimiento=data.tipo_mantenimiento,
        cubierto_garantia=bool(data.cubierto_garantia), cubre_garantia=data.cubre_garantia,
        tiempo_estimado_dias=data.tiempo_estimado_dias,
        responsable_mant=data.responsable_mant, descripcion=data.descripcion,
        genero_acta=genero_acta, acta_id=acta_id, usuario_previo=usuario_previo,
        realizado_por_id=current_user.id,
    )
    db.add(ce)
    _historial(db, data.tipo_recurso, r.id, current_user.nombre,
               f"Estado: {estado_anterior} → {canonico}" + (f" · {ubicacion_canonica}" if ubicacion_canonica else ""))
    db.commit()
    db.refresh(r)
    return {
        "ok": True, "estado": r.estado, "ubicacion": r.ubicacion,
        "genero_acta": genero_acta, "acta_id": acta_id, "cambio_id": ce.id,
    }


# ── POST /finalizar-mantenimiento ─────────────────────────
class FinalizarIn(BaseModel):
    tipo_recurso: str
    recurso_id: str
    resultado: str                  # exitoso | sin_solucion | requiere_baja
    costo_real: Optional[float] = None
    destino: str = "disponible"     # disponible | retirar
    ubicacion: Optional[str] = None


def _ce_mantenimiento_abierto(db, r):
    """Devuelve el CambioEstado que metió al recurso en mantenimiento (el más reciente)."""
    return db.query(CambioEstado).filter(
        CambioEstado.recurso_id == r.id).order_by(CambioEstado.fecha.desc()).first()


def _finalizacion_ce(db, r, current_user, estado_anterior, estado_nuevo, ubicacion, resultado, costo_real):
    """Registra un CambioEstado que marca la SALIDA de mantenimiento (para la línea de tiempo)."""
    db.add(CambioEstado(
        tipo_recurso=("activo" if hasattr(r, "id_placa_activo") else "accesorio"),
        recurso_id=r.id, placa=_placa(r, "activo" if hasattr(r, "id_placa_activo") else "accesorio"),
        empresa_id=r.empresa_id, estado_anterior=estado_anterior, estado_nuevo=estado_nuevo,
        ubicacion=ubicacion, resultado_mant=resultado, costo_real=costo_real,
        descripcion=f"Mantenimiento finalizado ({resultado})", realizado_por_id=current_user.id,
    ))


@router.post("/finalizar-mantenimiento")
def finalizar_mantenimiento(data: FinalizarIn, db: Session = Depends(get_db),
                            current_user = require_permission("estados.cambiar")):
    r = _get_recurso(db, data.tipo_recurso, data.recurso_id)
    _verify(db, current_user, r.empresa_id)
    if r.estado not in ESTADOS_MANT:
        raise HTTPException(status_code=400, detail="El recurso no está en mantenimiento")
    estado_mant = r.estado

    # Registro de mantenimiento abierto → determina si el equipo fue devuelto o no
    ce = _ce_mantenimiento_abierto(db, r)
    fue_devuelto = ce.genero_acta if ce is not None else (r.id_usuario is None)
    usuario_a_restaurar = r.id_usuario or (ce.usuario_previo if ce else None)

    # Anotamos el resultado/costo en el registro de entrada de mantenimiento
    if ce:
        ce.resultado_mant = data.resultado
        if data.costo_real is not None:
            ce.costo_real = data.costo_real

    # ── CASO A: el equipo NO fue devuelto (sigue con su usuario) ──────────────
    if not fue_devuelto and usuario_a_restaurar:
        if data.resultado == "requiere_baja":
            raise HTTPException(
                status_code=400,
                detail="El equipo requiere baja pero sigue asignado a un usuario. "
                       "Primero genera la devolución del usuario y luego solicita la baja."
            )
        usuario = db.query(Usuario).filter(Usuario.id == usuario_a_restaurar).first()
        r.id_usuario = usuario_a_restaurar     # garantiza el vínculo (defensa en profundidad)
        r.estado = "asignado"
        # ubicación no aplica: el equipo está con el usuario
        _finalizacion_ce(db, r, current_user, estado_mant, "asignado", None, data.resultado, data.costo_real)
        nombre = usuario.nombre_completo if usuario else "el usuario"
        _historial(db, data.tipo_recurso, r.id, current_user.nombre,
                   f"Mantenimiento finalizado ({data.resultado}): {estado_mant} → asignado · devuelto a {nombre}")
        db.commit()
        db.refresh(r)
        return {"ok": True, "estado": r.estado, "volvio_a_asignado": True,
                "usuario_id": usuario_a_restaurar,
                "usuario_nombre": (usuario.nombre_completo if usuario else None)}

    # ── CASO B: el equipo SÍ fue devuelto (sin dueño) ─────────────────────────
    if data.destino == "retirar" or data.resultado == "requiere_baja":
        db.commit()
        return {"ok": True, "volvio_a_asignado": False, "instruccion": "solicitar_baja",
                "mensaje": "Registra la solicitud de baja en /estados/solicitar-baja"}

    if not data.ubicacion or not str(data.ubicacion).strip():
        raise HTTPException(status_code=400, detail="La ubicación es obligatoria al volver a disponible")
    # Ubicación contra el catálogo de la empresa del recurso
    ubic_canonica = _validar_ubicacion_o_400(db, r.empresa_id, data.ubicacion)
    r.estado = "disponible"
    r.ubicacion = ubic_canonica
    _finalizacion_ce(db, r, current_user, estado_mant, "disponible", ubic_canonica, data.resultado, data.costo_real)
    _historial(db, data.tipo_recurso, r.id, current_user.nombre,
               f"Mantenimiento finalizado ({data.resultado}): {estado_mant} → disponible")
    db.commit()
    db.refresh(r)
    return {"ok": True, "estado": r.estado, "ubicacion": r.ubicacion, "volvio_a_asignado": False}


@router.get("/mantenimiento-activo/{tipo_recurso}/{recurso_id}")
def info_mantenimiento(tipo_recurso: str, recurso_id: str, db: Session = Depends(get_db),
                       current_user = require_permission("estados.cambiar")):
    """Informa si el recurso está en mantenimiento y si fue devuelto (genero_acta)."""
    r = _get_recurso(db, tipo_recurso, recurso_id)
    _verify(db, current_user, r.empresa_id)
    en_mant = r.estado in ESTADOS_MANT
    ce = _ce_mantenimiento_abierto(db, r) if en_mant else None
    genero_acta = bool(ce.genero_acta) if ce else (r.id_usuario is None)
    usuario_previo = r.id_usuario or (ce.usuario_previo if ce else None)
    nombre = None
    if usuario_previo:
        u = db.query(Usuario).filter(Usuario.id == usuario_previo).first()
        nombre = u.nombre_completo if u else None
    return {
        "en_mantenimiento": en_mant, "estado": r.estado, "genero_acta": genero_acta,
        "usuario_previo": (usuario_previo if not genero_acta else None),
        "usuario_previo_nombre": (nombre if not genero_acta else None),
    }


# ── POST /solicitar-baja ──────────────────────────────────
MOTIVOS_BAJA_VALIDOS = ["donado", "vendido", "destruido", "retiro_operacion", "hurto", "traslado", "devuelto_proveedor"]


class SolicitarBajaIn(BaseModel):
    tipo_recurso: str
    recurso_id: str
    motivo: str                     # donado | vendido | destruido | retiro_operacion | hurto | traslado
    justificacion: str
    estado_fisico: Optional[str] = None
    valor_venta: Optional[float] = None
    comprador: Optional[str] = None
    entidad_receptora: Optional[str] = None
    metodo_destruccion: Optional[str] = None
    numero_denuncia: Optional[str] = None       # motivo "hurto"
    empresa_destino_id: Optional[str] = None     # motivo "traslado"


def _numero_baja(db, empresa_id):
    anio = datetime.now().year
    n = db.query(BajaActivo).filter(
        BajaActivo.empresa_id == empresa_id,
        BajaActivo.numero_baja.like(f"BAJA-{anio}-%"),
    ).count()
    return f"BAJA-{anio}-{n + 1:03d}"


@router.post("/solicitar-baja", status_code=status.HTTP_201_CREATED)
def solicitar_baja(data: SolicitarBajaIn, db: Session = Depends(get_db),
                   current_user = require_permission("estados.cambiar")):
    r = _get_recurso(db, data.tipo_recurso, data.recurso_id)
    _verify(db, current_user, r.empresa_id)
    if r.estado == "asignado":
        raise HTTPException(status_code=400, detail="Debes registrar la devolución del equipo antes de darlo de baja")
    if not data.justificacion or not data.justificacion.strip():
        raise HTTPException(status_code=400, detail="La justificación es obligatoria")
    if data.motivo not in MOTIVOS_BAJA_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Motivo de baja inválido: {data.motivo}")
    # "devuelto_proveedor" SOLO aplica a equipos en alquiler (marca es_alquiler);
    # un equipo propio no puede "devolverse al proveedor".
    if data.motivo == "devuelto_proveedor" and not getattr(r, "es_alquiler", False):
        raise HTTPException(status_code=400, detail="'Devuelto a proveedor' solo aplica a equipos en alquiler")
    if data.motivo != "devuelto_proveedor" and getattr(r, "es_alquiler", False):
        raise HTTPException(status_code=400, detail="Un equipo en alquiler solo puede darse de baja como 'Devuelto a proveedor'")

    # ── Validación específica por motivo ──────────────────────
    # hurto: el número de denuncia es recomendado (se captura si viene, no es obligatorio).
    empresa_destino_id = None
    empresa_destino_nombre = None
    if data.motivo == "traslado":
        # "traslado" da de baja el activo SOLO en la empresa actual. La creación del
        # activo en la empresa destino es una acción MANUAL aparte (el usuario crea un
        # nuevo activo en la empresa 2 con su propia placa). Aquí NO se auto-crea nada
        # en la empresa destino: únicamente se retira aquí y se registra a dónde fue.
        if not data.empresa_destino_id:
            raise HTTPException(status_code=400, detail="Debes indicar la empresa destino del traslado")
        destino = db.query(Empresa).filter(Empresa.id == data.empresa_destino_id).first()
        if not destino:
            raise HTTPException(status_code=400, detail="La empresa destino no existe")
        if destino.id == r.empresa_id:
            raise HTTPException(status_code=400, detail="La empresa destino debe ser diferente a la empresa actual")
        empresa_destino_id = destino.id
        empresa_destino_nombre = destino.nombre_empresa

    es_activo = data.tipo_recurso == "activo"
    baja = BajaActivo(
        numero_baja=_numero_baja(db, r.empresa_id),
        tipo_recurso=data.tipo_recurso, recurso_id=r.id, placa=_placa(r, data.tipo_recurso),
        empresa_id=r.empresa_id,
        tipo_activo=r.tipo_activo if es_activo else r.tipo_accesorio,
        marca=r.marca, modelo=r.modelo, serial=r.serial,
        fecha_compra=r.fecha_compra if es_activo else None,
        costo_original=(float(r.costo) if (es_activo and r.costo) else None),
        motivo=data.motivo, justificacion=data.justificacion.strip(), estado_fisico=data.estado_fisico,
        valor_venta=data.valor_venta, comprador=data.comprador,
        entidad_receptora=data.entidad_receptora, metodo_destruccion=data.metodo_destruccion,
        numero_denuncia=(data.numero_denuncia or None) if data.motivo == "hurto" else None,
        empresa_destino_id=empresa_destino_id, empresa_destino_nombre=empresa_destino_nombre,
        estado_aprobacion="pendiente", solicitado_por_id=current_user.id,
    )
    db.add(baja)
    db.commit()
    db.refresh(baja)
    return {"id": baja.id, "numero_baja": baja.numero_baja, "estado_aprobacion": baja.estado_aprobacion}


# ── GET /bajas ────────────────────────────────────────────
def _baja_dict(b, db):
    sol = db.query(Usuario).filter(Usuario.id == b.solicitado_por_id).first()
    from models.usuario_sistema import UsuarioSistema
    solu = db.query(UsuarioSistema).filter(UsuarioSistema.id == b.solicitado_por_id).first()
    emp = db.query(Empresa).filter(Empresa.id == b.empresa_id).first()
    return {
        "id": b.id, "numero_baja": b.numero_baja, "tipo_recurso": b.tipo_recurso,
        "placa": b.placa, "tipo_activo": b.tipo_activo, "marca": b.marca, "modelo": b.modelo,
        "motivo": b.motivo, "justificacion": b.justificacion, "estado_fisico": b.estado_fisico,
        "valor_venta": float(b.valor_venta) if b.valor_venta else None, "comprador": b.comprador,
        "entidad_receptora": b.entidad_receptora, "metodo_destruccion": b.metodo_destruccion,
        "numero_denuncia": b.numero_denuncia, "empresa_destino_nombre": b.empresa_destino_nombre,
        "estado_aprobacion": b.estado_aprobacion, "fecha_solicitud": b.fecha_solicitud,
        "fecha_aprobacion": b.fecha_aprobacion, "observaciones_aprobador": b.observaciones_aprobador,
        "url_pdf": b.url_pdf, "nombre_empresa": emp.nombre_empresa if emp else None,
        "solicitado_por": (solu.nombre if solu else None),
    }


@router.get("/bajas")
def listar_bajas(estado: Optional[str] = None, empresa_id: Optional[str] = None,
                 db: Session = Depends(get_db), current_user = require_permission("estados.cambiar")):
    query = db.query(BajaActivo)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(BajaActivo.empresa_id == empresa_id)
        else:
            query = query.filter(BajaActivo.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(BajaActivo.empresa_id == empresa_id)
    if estado:
        query = query.filter(BajaActivo.estado_aprobacion == estado)
    return [_baja_dict(b, db) for b in query.order_by(BajaActivo.fecha_solicitud.desc()).all()]


@router.get("/bajas/{baja_id}/pdf")
def descargar_pdf_baja(baja_id: str, db: Session = Depends(get_db),
                       current_user = require_permission("estados.cambiar")):
    """Descarga el PDF del acta de baja vía FileResponse (las rutas de storage no
    están montadas como estáticas)."""
    from fastapi.responses import FileResponse
    from pathlib import Path
    b = db.query(BajaActivo).filter(BajaActivo.id == baja_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Baja no encontrada")
    _verify(db, current_user, b.empresa_id)
    if not b.url_pdf:
        raise HTTPException(status_code=404, detail="El PDF aún no ha sido generado")
    ruta = Path(__file__).parent.parent / b.url_pdf
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en el servidor")
    return FileResponse(path=str(ruta), media_type="application/pdf",
                        filename=f"{b.numero_baja}.pdf")


class AprobarBajaIn(BaseModel):
    observaciones_aprobador: Optional[str] = None


@router.post("/bajas/{baja_id}/aprobar")
def aprobar_baja(baja_id: str, data: AprobarBajaIn, db: Session = Depends(get_db),
                 current_user = require_permission("estados.aprobar_baja")):
    b = db.query(BajaActivo).filter(BajaActivo.id == baja_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Baja no encontrada")
    _verify(db, current_user, b.empresa_id)
    if b.estado_aprobacion != "pendiente":
        raise HTTPException(status_code=400, detail=f"La baja ya está {b.estado_aprobacion}")

    b.estado_aprobacion = "aprobada"
    b.aprobado_por_id = current_user.id
    b.fecha_aprobacion = datetime.now()
    if data.observaciones_aprobador:
        b.observaciones_aprobador = data.observaciones_aprobador

    r = _get_recurso(db, b.tipo_recurso, b.recurso_id)
    r.estado = "retirado"
    r.id_usuario = None
    _historial(db, b.tipo_recurso, r.id, current_user.nombre,
               f"Baja {b.numero_baja} aprobada — motivo: {b.motivo}",
               tipo_movimiento="baja")
    db.flush()

    try:
        from services.pdf_service import generar_pdf_baja
        b.url_pdf = generar_pdf_baja(b, db)
    except Exception as e:
        print(f"[BAJA PDF] {e}")
    db.commit()
    db.refresh(b)
    return _baja_dict(b, db)


class RechazarBajaIn(BaseModel):
    observaciones_aprobador: str


@router.post("/bajas/{baja_id}/rechazar")
def rechazar_baja(baja_id: str, data: RechazarBajaIn, db: Session = Depends(get_db),
                  current_user = require_permission("estados.aprobar_baja")):
    b = db.query(BajaActivo).filter(BajaActivo.id == baja_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Baja no encontrada")
    _verify(db, current_user, b.empresa_id)
    if b.estado_aprobacion != "pendiente":
        raise HTTPException(status_code=400, detail=f"La baja ya está {b.estado_aprobacion}")
    if not data.observaciones_aprobador or not data.observaciones_aprobador.strip():
        raise HTTPException(status_code=400, detail="Indica el motivo del rechazo")
    b.estado_aprobacion = "rechazada"
    b.aprobado_por_id = current_user.id
    b.fecha_aprobacion = datetime.now()
    b.observaciones_aprobador = data.observaciones_aprobador.strip()
    db.commit()
    return {"ok": True, "estado_aprobacion": "rechazada"}


# ── GET /historial/{tipo}/{id} ────────────────────────────
@router.get("/historial/{tipo_recurso}/{recurso_id}")
def historial_estados(tipo_recurso: str, recurso_id: str, db: Session = Depends(get_db),
                      current_user = require_permission("activos.ver")):
    rows = db.query(CambioEstado).filter(
        CambioEstado.tipo_recurso == tipo_recurso,
        CambioEstado.recurso_id == recurso_id,
    ).order_by(CambioEstado.fecha.desc()).all()
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if rows and empresa_ids is not None and rows[0].empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este recurso")
    return [{
        "id": ce.id, "fecha": ce.fecha, "estado_anterior": ce.estado_anterior,
        "estado_nuevo": ce.estado_nuevo, "ubicacion": ce.ubicacion,
        "tipo_mantenimiento": ce.tipo_mantenimiento, "cubierto_garantia": ce.cubierto_garantia,
        "cubre_garantia": ce.cubre_garantia, "descripcion": ce.descripcion,
        "resultado_mant": ce.resultado_mant, "costo_real": float(ce.costo_real) if ce.costo_real else None,
        "genero_acta": ce.genero_acta, "acta_id": ce.acta_id,
    } for ce in rows]
