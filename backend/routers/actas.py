from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import date
from pathlib import Path
from database import get_db
from models.acta import Acta, ActaDetalle
from models.activo import Activo
from models.accesorio import Accesorio
from models.usuario import Usuario
from models.empresa import Empresa
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids, user_has_empresa_access
from services.pdf_service import generar_pdf_acta, generar_pdf_acta_accesorios

router = APIRouter(prefix="/api/actas", tags=["Actas PDF"])

BASE_DIR = Path(__file__).parent.parent


@router.post("/{acta_id}/generar-pdf")
def generar_pdf(
    acta_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("actas.generar")
):
    """Genera el PDF de un acta y guarda la URL en la BD"""

    acta    = db.query(Acta).filter(Acta.id == acta_id).first()
    if not acta:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and acta.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta acta")
    if acta.firmada:
        raise HTTPException(status_code=400, detail="Acta firmada — no se puede regenerar el PDF de un acta ya firmada")

    usuario = db.query(Usuario).filter(Usuario.id == acta.id_usuario).first()
    empresa = db.query(Empresa).filter(Empresa.id == acta.empresa_id).first()

    # TI responsible: responsable_entrega is always the TI admin (both entrega and devolucion)
    nombre_ti = acta.responsable_entrega
    usuario_ti = db.query(Usuario).filter(Usuario.nombre_completo == nombre_ti).first() if nombre_ti else None
    if not usuario_ti:
        usuario_ti = current_user

    # Leer TODOS los ítems del detalle del acta
    detalles = db.query(ActaDetalle).filter(ActaDetalle.acta_id == acta_id).all()

    activos_acta = []
    for d in detalles:
        if d.tipo_item == "activo" and d.id_activo:
            a = db.query(Activo).filter(Activo.id == d.id_activo).first()
            if a:
                activos_acta.append(a)

    accesorios_acta = []
    for d in detalles:
        if d.tipo_item == "accesorio" and d.id_accesorio:
            acc = db.query(Accesorio).filter(Accesorio.id == d.id_accesorio).first()
            if acc:
                accesorios_acta.append(acc)

    # Activo principal: el referenciado en acta.id_activo, o el primero del detalle
    activo_principal = None
    if acta.id_activo:
        activo_principal = db.query(Activo).filter(Activo.id == acta.id_activo).first()
    if not activo_principal and activos_acta:
        activo_principal = activos_acta[0]

    # Elegir función de generación según contenido
    try:
        if activo_principal:
            ruta_pdf, hash_pdf = generar_pdf_acta(
                acta=acta,
                activo=activo_principal,
                activos_extra=[a for a in activos_acta if a.id != activo_principal.id],
                usuario=usuario,
                empresa=empresa,
                accesorios=accesorios_acta,
                usuario_ti=usuario_ti,
            )
        else:
            ruta_pdf, hash_pdf = generar_pdf_acta_accesorios(
                acta=acta,
                usuario=usuario,
                empresa=empresa,
                accesorios=accesorios_acta,
                usuario_ti=usuario_ti,
            )
    except Exception as e:
        import traceback
        raise HTTPException(
            status_code=500,
            detail=f"Error generando PDF: {str(e)} | {traceback.format_exc()}"
        )

    acta.url_pdf  = ruta_pdf
    acta.hash_pdf = hash_pdf
    db.commit()

    return {
        "mensaje": "PDF generado correctamente",
        "acta_id": acta_id,
        "url_pdf": ruta_pdf,
        "hash_pdf": hash_pdf
    }


@router.get("/{acta_id}/descargar")
def descargar_pdf(
    acta_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("actas.descargar")
):
    """Descarga el PDF de un acta"""
    acta = db.query(Acta).filter(Acta.id == acta_id).first()
    if not acta:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and acta.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esta acta")
    if not acta.url_pdf:
        raise HTTPException(
            status_code=404,
            detail="El PDF aún no ha sido generado. Use POST /actas/{id}/generar-pdf primero."
        )

    ruta_completa = BASE_DIR / acta.url_pdf
    if not ruta_completa.exists():
        raise HTTPException(status_code=404, detail="Archivo PDF no encontrado en el servidor")

    return FileResponse(
        path=str(ruta_completa),
        media_type="application/pdf",
        filename=f"acta_{acta_id[:8]}.pdf"
    )


@router.get("")
def listar_actas(
    empresa_id: Optional[str] = None,
    tipo: Optional[str] = None,
    usuario_id: Optional[str] = None,
    limit: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("actas.ver")
):
    query = db.query(Acta)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Acta.empresa_id == empresa_id)
        else:
            query = query.filter(Acta.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Acta.empresa_id == empresa_id)
    if tipo:
        query = query.filter(Acta.tipo == tipo)
    if usuario_id:
        query = query.filter(Acta.id_usuario == usuario_id)

    query = query.order_by(Acta.fecha_entrega.desc())
    if limit:
        query = query.limit(limit)

    actas = query.all()

    return [{
        "id": a.id,
        "tipo": a.tipo,
        "fecha": a.fecha_entrega,
        "placa_activo": a.activo.id_placa_activo if a.activo else None,
        "empleado": a.usuario.nombre_completo if a.usuario else None,
        "documento": a.usuario.documento if a.usuario else None,
        "empresa": a.empresa.nombre_empresa if a.empresa else None,
        "responsable_entrega": a.responsable_entrega,
        "tiene_pdf": a.url_pdf is not None,
        "firmada": a.firmada,
        "fecha_firma": a.fecha_firma,
        "responsable_recibe": a.responsable_recibe,
        "fecha_inicio_vigencia": a.fecha_inicio_vigencia,
        "es_anticipada": a.es_anticipada,
        "recordatorios_enviados": a.recordatorios_enviados,
    } for a in actas]


# ── Configurar vigencia / fecha de ingreso (actas anticipadas) ──
class ConfigurarVigenciaBody(BaseModel):
    fecha_inicio_vigencia: Optional[date] = None
    es_anticipada: Optional[bool] = False


@router.post("/{acta_id}/configurar-vigencia")
def configurar_vigencia(
    acta_id: str,
    data: ConfigurarVigenciaBody,
    db: Session = Depends(get_db),
    current_user = require_permission("actas.generar"),
):
    acta = db.query(Acta).filter(Acta.id == acta_id).first()
    if not acta:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    if not user_has_empresa_access(db, current_user.id, acta.empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa acta")
    if acta.firmada:
        raise HTTPException(status_code=400, detail="No se puede modificar un acta ya firmada")
    if data.es_anticipada and not data.fecha_inicio_vigencia:
        raise HTTPException(status_code=400, detail="Indica la fecha de ingreso del empleado para un acta anticipada")

    acta.es_anticipada = bool(data.es_anticipada)
    acta.fecha_inicio_vigencia = data.fecha_inicio_vigencia if data.es_anticipada else None
    db.commit()
    db.refresh(acta)
    return {
        "id": acta.id,
        "es_anticipada": acta.es_anticipada,
        "fecha_inicio_vigencia": acta.fecha_inicio_vigencia,
        "firmada": acta.firmada,
    }