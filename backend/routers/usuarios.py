from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional, List
from database import get_db
from models.usuario import Usuario
from models.empresa import Empresa
from models.activo import Activo
from models.accesorio import Accesorio
from routers.auth import get_current_user
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids, get_empresas_relacionadas

router = APIRouter(prefix="/api/usuarios", tags=["Empleados"])

# ── Schemas ──────────────────────────────────────────────
class UsuarioCreate(BaseModel):
    empresa_id: str
    documento: str
    nombre_completo: str
    cargo: Optional[str] = None
    area: Optional[str] = None
    sede: Optional[str] = None
    unidad_negocio: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None

class UsuarioUpdate(BaseModel):
    nombre_completo: Optional[str] = None
    cargo: Optional[str] = None
    area: Optional[str] = None
    sede: Optional[str] = None
    unidad_negocio: Optional[str] = None
    correo: Optional[str] = None
    telefono: Optional[str] = None
    estado: Optional[str] = None  # activo, inactivo, retirado

class UsuarioResponse(BaseModel):
    id: str
    empresa_id: str
    documento: str
    nombre_completo: str
    cargo: Optional[str]
    area: Optional[str]
    sede: Optional[str]
    unidad_negocio: Optional[str] = None
    correo: Optional[str]
    telefono: Optional[str]
    estado: str
    nombre_empresa: Optional[str] = None

    class Config:
        from_attributes = True

# ── Endpoints ────────────────────────────────────────────
@router.get("", response_model=List[UsuarioResponse])
def listar_usuarios(
    empresa_id: Optional[str] = None,
    q: Optional[str] = Query(None, description="Buscar por cédula o nombre"),
    estado: Optional[str] = "activo",
    db: Session = Depends(get_db),
    current_user = require_permission("usuarios.ver")
):
    query = db.query(Usuario)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Usuario.empresa_id == empresa_id)
        else:
            query = query.filter(Usuario.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Usuario.empresa_id == empresa_id)
    if estado:
        query = query.filter(Usuario.estado == estado)
    if q:
        query = query.filter(
            or_(
                Usuario.documento.ilike(f"%{q}%"),
                Usuario.nombre_completo.ilike(f"%{q}%")
            )
        )

    usuarios = query.order_by(Usuario.nombre_completo).all()

    # Agregar nombre de empresa a cada usuario
    result = []
    for u in usuarios:
        u_dict = {
            "id": u.id,
            "empresa_id": u.empresa_id,
            "documento": u.documento,
            "nombre_completo": u.nombre_completo,
            "cargo": u.cargo,
            "area": u.area,
            "sede": u.sede,
            "correo": u.correo,
            "telefono": u.telefono,
            "estado": u.estado,
            "nombre_empresa": u.empresa.nombre_empresa if u.empresa else None
        }
        result.append(u_dict)
    return result


@router.post("", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def crear_usuario(
    data: UsuarioCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("usuarios.crear")
):
    # Verificar que la empresa existe
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    # Verificar cédula única por empresa
    existente = db.query(Usuario).filter(
        Usuario.documento == data.documento,
        Usuario.empresa_id == data.empresa_id
    ).first()
    if existente:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Ya existe un empleado con documento {data.documento} en esta empresa"
        )

    usuario = Usuario(**data.model_dump())
    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return {
        **{c.name: getattr(usuario, c.name) for c in usuario.__table__.columns},
        "nombre_empresa": empresa.nombre_empresa
    }


@router.get("/buscar", response_model=List[UsuarioResponse])
def buscar_por_cedula(
    cedula: str = Query(..., description="Número de cédula a buscar"),
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Búsqueda rápida por cédula — usado en el formulario de asignación"""
    query = db.query(Usuario).filter(
        Usuario.documento.ilike(f"%{cedula}%"),
        Usuario.estado == "activo"
    )
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Usuario.empresa_id == empresa_id)
        else:
            query = query.filter(Usuario.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Usuario.empresa_id == empresa_id)

    usuarios = query.limit(10).all()
    result = []
    for u in usuarios:
        result.append({
            "id": u.id,
            "empresa_id": u.empresa_id,
            "documento": u.documento,
            "nombre_completo": u.nombre_completo,
            "cargo": u.cargo,
            "area": u.area,
            "sede": u.sede,
            "correo": u.correo,
            "telefono": u.telefono,
            "estado": u.estado,
            "nombre_empresa": u.empresa.nombre_empresa if u.empresa else None
        })
    return result


@router.get("/buscar-para-asignacion")
def buscar_para_asignacion(
    documento: str = Query(..., description="Cédula/documento a buscar"),
    empresa_id: str = Query(..., description="Empresa seleccionada en el formulario de asignación"),
    db: Session = Depends(get_db),
    current_user = require_permission("asignaciones.crear"),
):
    """
    Búsqueda de empleado para el formulario de asignación, ampliada a la empresa
    seleccionada + sus empresas relacionadas (hermanas). Espeja la regla de
    asignación (un recurso de A puede asignarse a un empleado de una hermana B).

    Gating: el usuario debe tener acceso a la empresa SELECCIONADA. Las hermanas
    se incluyen en el alcance de búsqueda aunque no estén en su lista habitual de
    empresas permitidas — NO amplía la visibilidad general de datos (es un lookup
    puntual del flujo de asignación, gobernado por la relación de empresas).
    """
    # 1. Gate: acceso a la empresa seleccionada (super_admin → empresa_ids None, pasa)
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    # 2. Alcance = empresa seleccionada + sus hermanas directas (no transitivo)
    scope = {empresa_id} | get_empresas_relacionadas(db, empresa_id)

    # 3. Búsqueda del empleado activo por documento dentro del alcance
    usuarios = db.query(Usuario).filter(
        Usuario.documento.ilike(f"%{documento}%"),
        Usuario.estado == "activo",
        Usuario.empresa_id.in_(scope),
    ).limit(10).all()

    # 4. Resultado con info de empresa + bandera de empresa relacionada
    return [{
        "id": u.id,
        "empresa_id": u.empresa_id,
        "documento": u.documento,
        "nombre_completo": u.nombre_completo,
        "cargo": u.cargo,
        "area": u.area,
        "sede": u.sede,
        "correo": u.correo,
        "telefono": u.telefono,
        "estado": u.estado,
        "nombre_empresa": u.empresa.nombre_empresa if u.empresa else None,
        "es_empresa_relacionada": u.empresa_id != empresa_id,
    } for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioResponse)
def obtener_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and usuario.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este empleado")
    return {
        **{c.name: getattr(usuario, c.name) for c in usuario.__table__.columns},
        "nombre_empresa": usuario.empresa.nombre_empresa if usuario.empresa else None
    }


@router.get("/{usuario_id}/activos")
def obtener_activos_usuario(
    usuario_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Retorna todos los activos y accesorios asignados actualmente a un empleado"""
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and usuario.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este empleado")

    activos = db.query(Activo).filter(
        Activo.id_usuario == usuario_id,
        Activo.estado == "asignado"
    ).all()

    accesorios = db.query(Accesorio).filter(
        Accesorio.id_usuario == usuario_id,
        Accesorio.estado == "asignado"
    ).all()

    return {
        "usuario": {
            "id": usuario.id,
            "nombre_completo": usuario.nombre_completo,
            "documento": usuario.documento,
            "cargo": usuario.cargo,
            "sede": usuario.sede
        },
        "activos": [{
            "id": a.id,
            "id_placa_activo": a.id_placa_activo,
            "tipo_activo": a.tipo_activo,
            "marca": a.marca,
            "modelo": a.modelo,
            "serial": a.serial,
            "estado": a.estado
        } for a in activos],
        "accesorios": [{
            "id": a.id,
            "id_placa_accesorio": a.id_placa_accesorio,
            "tipo_accesorio": a.tipo_accesorio,
            "marca": a.marca,
            "modelo": a.modelo,
            "estado": a.estado
        } for a in accesorios],
        "total_activos": len(activos),
        "total_accesorios": len(accesorios)
    }


@router.put("/{usuario_id}", response_model=UsuarioResponse)
def actualizar_usuario(
    usuario_id: str,
    data: UsuarioUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("usuarios.editar")
):
    usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Empleado no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and usuario.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a este empleado")

    # Validar estado
    if data.estado and data.estado not in ["activo", "inactivo", "retirado"]:
        raise HTTPException(
            status_code=400,
            detail="Estado inválido. Use: activo, inactivo, retirado"
        )

    for campo, valor in data.model_dump(exclude_unset=True).items():
        setattr(usuario, campo, valor)

    db.commit()
    db.refresh(usuario)

    return {
        **{c.name: getattr(usuario, c.name) for c in usuario.__table__.columns},
        "nombre_empresa": usuario.empresa.nombre_empresa if usuario.empresa else None
    }