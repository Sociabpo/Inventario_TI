from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
import json
from sqlalchemy import or_
from database import get_db
from models.empresa import Empresa
from models.empresa_relacion import EmpresaRelacion
from routers.auth import get_current_user
from dependencies.rbac import require_permission, require_role
from services.rbac_service import get_empresas_relacionadas, user_has_empresa_access
from services import empresa_logo_service

router = APIRouter(prefix="/api/empresas", tags=["Empresas"])

# ── Schemas ──────────────────────────────────────────────
# NOTA: create/edit se reciben como multipart/form-data (Form + File) porque
# incluyen la carga del logo, igual que el endpoint de cotizaciones (compras.py).
class EmpresaResponse(BaseModel):
    id: str
    nit: str
    nombre_empresa: str
    prefijo: str
    direccion: Optional[str]
    ciudad: Optional[str]
    telefono: Optional[str]
    correo: Optional[str]
    sedes: List[str] = []
    activo: bool
    tiene_logo: bool = False        # False → la UI muestra el aviso "falta logo"
    relacionadas: List[dict] = []   # [{empresa_id, nombre_empresa}] empresas hermanas

    class Config:
        from_attributes = True


# ── Helpers ──────────────────────────────────────────────
def _opt(v: Optional[str]) -> Optional[str]:
    """Cadena recortada o None si queda vacía (para campos opcionales de un form)."""
    v = (v or "").strip()
    return v or None


def _parse_sedes(raw: Optional[str]) -> List[str]:
    """Parsea el campo `sedes` del form (un JSON array de strings)."""
    if not raw:
        return []
    try:
        v = json.loads(raw)
        return [str(s) for s in v] if isinstance(v, list) else []
    except (ValueError, TypeError):
        return []


def _limpiar_sedes(sedes: Optional[List[str]]) -> List[str]:
    """Normaliza la lista: recorta espacios, descarta vacíos y duplicados (case-insensitive), conserva orden."""
    if not sedes:
        return []
    vistas, limpias = set(), []
    for s in sedes:
        nombre = (s or "").strip()
        if not nombre:
            continue
        clave = nombre.lower()
        if clave in vistas:
            continue
        vistas.add(clave)
        limpias.append(nombre)
    return limpias

def _relaciones_de(db: Session, empresa_id: str) -> List[dict]:
    """Lista [{empresa_id, nombre_empresa}] de las empresas relacionadas (bidireccional)."""
    rows = db.query(EmpresaRelacion).filter(
        or_(EmpresaRelacion.empresa_a_id == empresa_id,
            EmpresaRelacion.empresa_b_id == empresa_id),
    ).all()
    otros_ids = [
        (r.empresa_b_id if r.empresa_a_id == empresa_id else r.empresa_a_id)
        for r in rows
    ]
    if not otros_ids:
        return []
    empresas = db.query(Empresa).filter(Empresa.id.in_(otros_ids)).all()
    return [{"empresa_id": e.id, "nombre_empresa": e.nombre_empresa}
            for e in sorted(empresas, key=lambda x: x.nombre_empresa or "")]


def empresa_to_dict(e: Empresa, db: Optional[Session] = None) -> dict:
    return {
        "id": e.id,
        "nit": e.nit,
        "nombre_empresa": e.nombre_empresa,
        "prefijo": e.prefijo,
        "direccion": e.direccion,
        "ciudad": e.ciudad,
        "telefono": e.telefono,
        "correo": e.correo,
        "sedes": e.sedes_list,
        "activo": e.activo,
        "tiene_logo": empresa_logo_service.tiene_logo(e.prefijo),
        "relacionadas": _relaciones_de(db, e.id) if db is not None else [],
    }

# ── Endpoints ────────────────────────────────────────────
@router.get("", response_model=List[EmpresaResponse])
def listar_empresas(
    solo_activas: bool = True,
    db: Session = Depends(get_db),
    current_user = require_permission("empresas.ver")
):
    query = db.query(Empresa)
    if solo_activas:
        query = query.filter(Empresa.activo == True)
    return [empresa_to_dict(e, db) for e in query.order_by(Empresa.nombre_empresa).all()]


@router.post("", response_model=EmpresaResponse, status_code=status.HTTP_201_CREATED)
def crear_empresa(
    nit: str = Form(...),
    nombre_empresa: str = Form(...),
    prefijo: str = Form(...),
    direccion: Optional[str] = Form(None),
    ciudad: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    correo: Optional[str] = Form(None),
    sedes: Optional[str] = Form(None),          # JSON array de strings
    logo: UploadFile = File(...),               # OBLIGATORIO al crear
    db: Session = Depends(get_db),
    current_user = require_permission("empresas.crear")
):
    nit = (nit or "").strip()
    prefijo = (prefijo or "").strip().upper()
    nombre_empresa = (nombre_empresa or "").strip()
    if not nit or not prefijo or not nombre_empresa:
        raise HTTPException(status_code=400, detail="NIT, prefijo y razón social son obligatorios")

    # Validar el logo ANTES de tocar la BD (falla 400 si no es imagen/tamaño/vacío)
    png_bytes = empresa_logo_service.validar_y_convertir(logo)

    # Verificar NIT único
    existente = db.query(Empresa).filter(Empresa.nit == nit).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe una empresa con el NIT {nit}"
        )
    empresa = Empresa(
        nit=nit,
        nombre_empresa=nombre_empresa,
        prefijo=prefijo,
        direccion=_opt(direccion),
        ciudad=_opt(ciudad),
        telefono=_opt(telefono),
        correo=_opt(correo),
        sedes=json.dumps(_limpiar_sedes(_parse_sedes(sedes))),
    )
    db.add(empresa)
    db.commit()
    db.refresh(empresa)
    # Guardar el logo DONDE LAS ACTAS LO LEEN (templates/img/logo_{prefijo}.png)
    empresa_logo_service.escribir_logo(prefijo, png_bytes)
    return empresa_to_dict(empresa, db)


@router.get("/{empresa_id}", response_model=EmpresaResponse)
def obtener_empresa(
    empresa_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if not user_has_empresa_access(db, current_user.id, empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    return empresa_to_dict(empresa, db)


# ── Relaciones entre empresas ("hermanas") ───────────────
class RelacionesUpdate(BaseModel):
    relacionadas: List[str] = []   # conjunto completo deseado de empresa_ids relacionadas


def _orden_canonico(id1: str, id2: str):
    """Par ordenado (menor, mayor) por string, para una sola fila por relación."""
    return (id1, id2) if id1 < id2 else (id2, id1)


@router.get("/{empresa_id}/relaciones")
def listar_relaciones(
    empresa_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("empresas.ver"),
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    if not user_has_empresa_access(db, current_user.id, empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    return _relaciones_de(db, empresa_id)


@router.put("/{empresa_id}/relaciones")
def actualizar_relaciones(
    empresa_id: str,
    data: RelacionesUpdate,
    db: Session = Depends(get_db),
    current_user = require_role("super_admin"),
):
    """Reconcilia el conjunto COMPLETO de empresas relacionadas (declarativo):
    agrega las nuevas y elimina las que ya no estén. Las filas son canónicas y
    bidireccionales, así que ambos lados quedan actualizados automáticamente."""
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Validar el conjunto deseado: existen, no es ella misma, sin duplicados
    deseadas = set(data.relacionadas or [])
    if empresa_id in deseadas:
        raise HTTPException(status_code=400, detail="Una empresa no puede relacionarse consigo misma")
    if deseadas:
        existentes = {e.id for e in db.query(Empresa.id).filter(Empresa.id.in_(deseadas)).all()}
        faltan = deseadas - existentes
        if faltan:
            raise HTTPException(status_code=400, detail="Una o más empresas indicadas no existen")

    actuales = get_empresas_relacionadas(db, empresa_id)

    # Quitar las que ya no se desean
    a_quitar = actuales - deseadas
    for otro in a_quitar:
        a_id, b_id = _orden_canonico(empresa_id, otro)
        db.query(EmpresaRelacion).filter(
            EmpresaRelacion.empresa_a_id == a_id,
            EmpresaRelacion.empresa_b_id == b_id,
        ).delete(synchronize_session=False)

    # Agregar las nuevas (fila canónica única)
    a_agregar = deseadas - actuales
    for otro in a_agregar:
        a_id, b_id = _orden_canonico(empresa_id, otro)
        ya = db.query(EmpresaRelacion).filter(
            EmpresaRelacion.empresa_a_id == a_id,
            EmpresaRelacion.empresa_b_id == b_id,
        ).first()
        if not ya:
            db.add(EmpresaRelacion(empresa_a_id=a_id, empresa_b_id=b_id))

    db.commit()
    return _relaciones_de(db, empresa_id)


@router.put("/{empresa_id}", response_model=EmpresaResponse)
def actualizar_empresa(
    empresa_id: str,
    nombre_empresa: Optional[str] = Form(None),
    prefijo: Optional[str] = Form(None),
    direccion: Optional[str] = Form(None),
    ciudad: Optional[str] = Form(None),
    telefono: Optional[str] = Form(None),
    correo: Optional[str] = Form(None),
    sedes: Optional[str] = Form(None),          # JSON array de strings
    activo: Optional[bool] = Form(None),
    logo: Optional[UploadFile] = File(None),    # OPCIONAL al editar
    db: Session = Depends(get_db),
    current_user = require_role("super_admin")
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    prefijo_viejo = empresa.prefijo

    # Validar el logo (si viene) ANTES de aplicar cambios; edición NO lo exige
    png_bytes = None
    if logo is not None and logo.filename:
        png_bytes = empresa_logo_service.validar_y_convertir(logo)

    # Aplicar cambios de campos. Obligatorios: solo si llegan con valor (no vaciar).
    if nombre_empresa:            empresa.nombre_empresa = nombre_empresa.strip()
    if prefijo:                   empresa.prefijo = prefijo.strip().upper()
    if direccion is not None:     empresa.direccion = _opt(direccion)
    if ciudad is not None:        empresa.ciudad = _opt(ciudad)
    if telefono is not None:      empresa.telefono = _opt(telefono)
    if correo is not None:        empresa.correo = _opt(correo)
    if sedes is not None:         empresa.sedes = json.dumps(_limpiar_sedes(_parse_sedes(sedes)))
    if activo is not None:        empresa.activo = activo

    prefijo_nuevo = empresa.prefijo

    # Si cambió el prefijo, mover el logo existente para que las actas lo sigan encontrando
    if prefijo_nuevo != prefijo_viejo:
        empresa_logo_service.renombrar_logo(prefijo_viejo, prefijo_nuevo)

    # Si subieron un logo nuevo, sobrescribir (bajo el prefijo actual)
    if png_bytes is not None:
        empresa_logo_service.escribir_logo(prefijo_nuevo, png_bytes)

    db.commit()
    db.refresh(empresa)
    return empresa_to_dict(empresa, db)


@router.delete("/{empresa_id}", status_code=status.HTTP_204_NO_CONTENT)
def desactivar_empresa(
    empresa_id: str,
    db: Session = Depends(get_db),
    current_user = require_role("super_admin")
):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    # Soft delete — no borramos, desactivamos
    empresa.activo = False
    db.commit()