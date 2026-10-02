from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from database import get_db
from models.usuario_sistema import UsuarioSistema
from models.rol import Rol
from models.permiso import Permiso
from models.usuario_rol import UsuarioRol
from models.empresa import Empresa
from routers.auth import get_current_user
from dependencies.rbac import require_role
from services.rbac_service import (
    get_user_roles, get_all_user_permissions,
    get_all_user_roles, is_super_admin,
    get_user_empresa_ids, user_has_empresa_access,
)
from services.auth_service import hash_password

# Roles de nivel administrativo: solo un super_admin puede asignarlos o revocarlos
# (Opción B — un admin no-super delega roles funcionales pero no clona poder admin).
_ROLES_ADMIN_TIER = {"super_admin", "admin"}

router = APIRouter(prefix="/api/rbac", tags=["RBAC"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AsignarRolBody(BaseModel):
    rol_id: str
    empresa_id: Optional[str] = None

class AsignarAccesoBody(BaseModel):
    rol_id: str
    empresa_id: Optional[str] = None

class CrearUsuarioSistemaBody(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    empresa_id: Optional[str] = None

class EditarUsuarioSistemaBody(BaseModel):
    nombre: Optional[str] = None
    email: Optional[EmailStr] = None
    activo: Optional[bool] = None

class CambiarPasswordBody(BaseModel):
    nueva_password: str

class RolBody(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    permisos: List[str] = []          # códigos de permiso

class RolEditBody(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    permisos: Optional[List[str]] = None

# Roles del sistema (no se pueden renombrar ni eliminar)
ROLES_SISTEMA = {"super_admin", "admin", "analista_activos", "soporte_ti", "auditoria", "rrhh"}


def _slug_rol(nombre: str) -> str:
    import re
    s = re.sub(r"[^a-z0-9]+", "_", (nombre or "").strip().lower())
    return s.strip("_")


# ── Roles (referencia) ────────────────────────────────────────────────────────

@router.get("/roles")
def listar_roles(
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    roles = db.query(Rol).filter(Rol.activo == True).order_by(Rol.nombre).all()
    return [{
        "id": r.id,
        "nombre": r.nombre,
        "descripcion": r.descripcion,
        "permisos": sorted([p.codigo for p in r.permisos]),
        "es_sistema": r.nombre in ROLES_SISTEMA,
        "num_usuarios": db.query(UsuarioRol).filter(UsuarioRol.rol_id == r.id, UsuarioRol.activo == True).count(),
    } for r in roles]


@router.post("/roles", status_code=status.HTTP_201_CREATED)
def crear_rol(
    body: RolBody,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    nombre = _slug_rol(body.nombre)
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre del rol es obligatorio")
    if db.query(Rol).filter(Rol.nombre == nombre).first():
        raise HTTPException(status_code=400, detail=f"Ya existe un rol con el nombre '{nombre}'")
    rol = Rol(nombre=nombre, descripcion=body.descripcion, activo=True)
    if body.permisos:
        rol.permisos = db.query(Permiso).filter(Permiso.codigo.in_(body.permisos)).all()
    db.add(rol)
    db.commit()
    db.refresh(rol)
    return {
        "id": rol.id, "nombre": rol.nombre, "descripcion": rol.descripcion,
        "permisos": sorted([p.codigo for p in rol.permisos]),
    }


@router.put("/roles/{rol_id}")
def editar_rol(
    rol_id: str,
    body: RolEditBody,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if rol.nombre == "super_admin":
        raise HTTPException(status_code=400, detail="El rol super_admin no se puede modificar")

    if body.nombre is not None:
        nuevo = _slug_rol(body.nombre)
        if rol.nombre in ROLES_SISTEMA and nuevo != rol.nombre:
            raise HTTPException(status_code=400, detail="No se puede renombrar un rol del sistema")
        if nuevo and nuevo != rol.nombre:
            if db.query(Rol).filter(Rol.nombre == nuevo, Rol.id != rol.id).first():
                raise HTTPException(status_code=400, detail=f"Ya existe un rol con el nombre '{nuevo}'")
            rol.nombre = nuevo
    if body.descripcion is not None:
        rol.descripcion = body.descripcion
    if body.permisos is not None:
        rol.permisos = db.query(Permiso).filter(Permiso.codigo.in_(body.permisos)).all()

    db.commit()
    db.refresh(rol)
    return {
        "id": rol.id, "nombre": rol.nombre, "descripcion": rol.descripcion,
        "permisos": sorted([p.codigo for p in rol.permisos]),
    }


@router.delete("/roles/{rol_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_rol(
    rol_id: str,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    rol = db.query(Rol).filter(Rol.id == rol_id).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    if rol.nombre in ROLES_SISTEMA:
        raise HTTPException(status_code=400, detail="No se puede eliminar un rol del sistema")
    en_uso = db.query(UsuarioRol).filter(UsuarioRol.rol_id == rol.id, UsuarioRol.activo == True).count()
    if en_uso:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar: el rol está asignado a {en_uso} usuario(s)")
    rol.activo = False
    db.commit()


# ── Permisos (referencia) ─────────────────────────────────────────────────────

@router.get("/permisos")
def listar_permisos(
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    permisos = db.query(Permiso).order_by(Permiso.modulo, Permiso.accion).all()
    grupos: dict = {}
    for p in permisos:
        grupos.setdefault(p.modulo, []).append({
            "id": p.id,
            "codigo": p.codigo,
            "accion": p.accion,
            "descripcion": p.descripcion,
        })
    return grupos


# ── Empresas disponibles para el usuario actual ───────────────────────────────

@router.get("/empresas-disponibles")
def empresas_disponibles(
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = Depends(get_current_user),
):
    if is_super_admin(db, current_user.id):
        empresas = db.query(Empresa).filter(Empresa.activo == True).order_by(Empresa.nombre_empresa).all()
    else:
        empresa_ids = db.query(UsuarioRol.empresa_id).filter(
            UsuarioRol.usuario_sistema_id == current_user.id,
            UsuarioRol.activo == True,
            UsuarioRol.empresa_id != None,
        ).distinct().all()
        ids = [r[0] for r in empresa_ids]
        if not ids:
            return []
        empresas = db.query(Empresa).filter(
            Empresa.id.in_(ids), Empresa.activo == True,
        ).order_by(Empresa.nombre_empresa).all()
    return [{"id": e.id, "nombre_empresa": e.nombre_empresa, "prefijo": e.prefijo, "nit": e.nit, "sedes": e.sedes_list} for e in empresas]


# ── Gestión de usuarios del sistema ──────────────────────────────────────────

@router.get("/usuarios")
def listar_usuarios_sistema(
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = Depends(get_current_user),
):
    if not (is_super_admin(db, current_user.id) or
            "usuarios.ver" in get_all_user_permissions(db, current_user.id)):
        raise HTTPException(status_code=403, detail="Permiso requerido: 'usuarios.ver'")

    if is_super_admin(db, current_user.id):
        usuarios = db.query(UsuarioSistema).order_by(UsuarioSistema.nombre).all()
    else:
        empresa_ids = db.query(UsuarioRol.empresa_id).filter(
            UsuarioRol.usuario_sistema_id == current_user.id,
            UsuarioRol.activo == True,
            UsuarioRol.empresa_id != None,
        ).distinct().all()
        mis_empresas = [r[0] for r in empresa_ids]
        if not mis_empresas:
            return []
        user_ids = db.query(UsuarioRol.usuario_sistema_id).filter(
            UsuarioRol.empresa_id.in_(mis_empresas),
            UsuarioRol.activo == True,
        ).distinct().all()
        ids = [r[0] for r in user_ids]
        usuarios = db.query(UsuarioSistema).filter(
            UsuarioSistema.id.in_(ids),
        ).order_by(UsuarioSistema.nombre).all()

    result = []
    for u in usuarios:
        accesos = db.query(UsuarioRol).filter(
            UsuarioRol.usuario_sistema_id == u.id,
            UsuarioRol.activo == True,
        ).all()
        result.append({
            "id": u.id,
            "nombre": u.nombre,
            "email": u.email,
            "activo": u.activo,
            "accesos": [{
                "id": a.id,
                "rol_nombre": a.rol.nombre,
                "empresa_id": a.empresa_id,
                "empresa_nombre": a.empresa.nombre_empresa if a.empresa else None,
            } for a in accesos],
        })
    return result


@router.post("/usuarios", status_code=status.HTTP_201_CREATED)
def crear_usuario_sistema(
    body: CrearUsuarioSistemaBody,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = Depends(get_current_user),
):
    if "usuarios.crear" not in get_all_user_permissions(db, current_user.id):
        raise HTTPException(status_code=403, detail="Permiso requerido: 'usuarios.crear'")

    existente = db.query(UsuarioSistema).filter_by(email=body.email).first()
    if existente:
        raise HTTPException(status_code=400, detail="Ya existe un usuario con ese email")

    nuevo = UsuarioSistema(
        nombre=body.nombre,
        email=body.email,
        password=hash_password(body.password),
        empresa_id=body.empresa_id or None,
        rol="visualizador",
        activo=True,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"id": nuevo.id, "nombre": nuevo.nombre, "email": nuevo.email}


@router.put("/usuarios/{usuario_id}")
def editar_usuario_sistema(
    usuario_id: str,
    body: EditarUsuarioSistemaBody,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = Depends(get_current_user),
):
    if "usuarios.editar" not in get_all_user_permissions(db, current_user.id):
        raise HTTPException(status_code=403, detail="Permiso requerido: 'usuarios.editar'")

    usuario = db.query(UsuarioSistema).filter_by(id=usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Nadie (ni super_admin) puede desactivar su propia cuenta (evita auto-bloqueo).
    if usuario_id == current_user.id and body.activo is False:
        raise HTTPException(status_code=403, detail="No puedes desactivar tu propia cuenta")

    # Defensa en profundidad: un admin no-super no edita cuentas super_admin, y solo
    # edita usuarios que comparten al menos una de sus empresas (igual que el listado).
    if not is_super_admin(db, current_user.id):
        if is_super_admin(db, usuario_id):
            raise HTTPException(status_code=403, detail="No puedes editar una cuenta super_admin")
        mis_empresas = set(get_user_empresa_ids(db, current_user.id) or [])
        target_empresas = {r[0] for r in db.query(UsuarioRol.empresa_id).filter(
            UsuarioRol.usuario_sistema_id == usuario_id,
            UsuarioRol.activo == True,
            UsuarioRol.empresa_id != None,
        ).distinct().all()}
        if not (mis_empresas & target_empresas):
            raise HTTPException(status_code=403, detail="No tienes acceso a este usuario")

    if body.nombre is not None:
        usuario.nombre = body.nombre
    if body.email is not None:
        conflicto = db.query(UsuarioSistema).filter(
            UsuarioSistema.email == body.email,
            UsuarioSistema.id != usuario_id,
        ).first()
        if conflicto:
            raise HTTPException(status_code=400, detail="Ese email ya está en uso")
        usuario.email = body.email
    if body.activo is not None:
        usuario.activo = body.activo

    db.commit()
    db.refresh(usuario)
    return {"id": usuario.id, "nombre": usuario.nombre, "email": usuario.email, "activo": usuario.activo}


@router.post("/usuarios/{usuario_id}/cambiar-password", status_code=status.HTTP_200_OK)
def cambiar_password(
    usuario_id: str,
    body: CambiarPasswordBody,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = Depends(get_current_user),
):
    if not is_super_admin(db, current_user.id):
        raise HTTPException(status_code=403, detail="Solo un super_admin puede cambiar contraseñas")

    usuario = db.query(UsuarioSistema).filter_by(id=usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if not body.nueva_password or len(body.nueva_password) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")

    usuario.password = hash_password(body.nueva_password)
    db.commit()
    return {"mensaje": "Contraseña actualizada correctamente"}


# ── Gestión de accesos (rol + empresa) ───────────────────────────────────────

@router.get("/usuarios/{usuario_id}/accesos")
def listar_accesos(
    usuario_id: str,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    usuario = db.query(UsuarioSistema).filter_by(id=usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    registros = db.query(UsuarioRol).filter(
        UsuarioRol.usuario_sistema_id == usuario_id,
        UsuarioRol.activo == True,
    ).all()
    return [{
        "id":           r.id,
        "rol_id":       r.rol_id,
        "rol_nombre":   r.rol.nombre,
        "empresa_id":   r.empresa_id,
        "empresa_nombre": r.empresa.nombre_empresa if r.empresa else None,
    } for r in registros]


@router.post("/usuarios/{usuario_id}/accesos", status_code=status.HTTP_201_CREATED)
def agregar_acceso(
    usuario_id: str,
    body: AsignarAccesoBody,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    usuario = db.query(UsuarioSistema).filter_by(id=usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    rol = db.query(Rol).filter_by(id=body.rol_id, activo=True).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    if rol.nombre == "super_admin" and not is_super_admin(db, current_user.id):
        raise HTTPException(status_code=403, detail="Solo un super_admin puede asignar el rol super_admin")

    if rol.nombre == "super_admin" and body.empresa_id is not None:
        raise HTTPException(status_code=400, detail="El rol super_admin debe asignarse sin empresa (acceso global)")

    if rol.nombre != "super_admin" and not body.empresa_id:
        raise HTTPException(status_code=400, detail="Debes seleccionar una empresa para este rol")

    if not is_super_admin(db, current_user.id) and body.empresa_id:
        mis_empresas = {r[0] for r in db.query(UsuarioRol.empresa_id).filter(
            UsuarioRol.usuario_sistema_id == current_user.id,
            UsuarioRol.activo == True,
            UsuarioRol.empresa_id != None,
        ).all()}
        if body.empresa_id not in mis_empresas:
            raise HTTPException(status_code=403, detail="No puedes asignar acceso a esa empresa")

    existente = db.query(UsuarioRol).filter_by(
        usuario_sistema_id=usuario_id,
        rol_id=body.rol_id,
        empresa_id=body.empresa_id,
        activo=True,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="El usuario ya tiene este rol para esa empresa")

    nuevo = UsuarioRol(
        usuario_sistema_id=usuario_id,
        rol_id=body.rol_id,
        empresa_id=body.empresa_id,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"mensaje": f"Acceso '{rol.nombre}' asignado correctamente", "id": nuevo.id}


@router.delete("/usuarios/{usuario_id}/accesos/{acceso_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_acceso(
    usuario_id: str,
    acceso_id: str,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    registro = db.query(UsuarioRol).filter_by(
        id=acceso_id,
        usuario_sistema_id=usuario_id,
        activo=True,
    ).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Acceso no encontrado")

    if (current_user.id == usuario_id and
            registro.rol.nombre == "super_admin"):
        raise HTTPException(status_code=403, detail="No puedes eliminar tu propio acceso super_admin")

    registro.activo = False
    db.commit()


# ── Gestión de roles (endpoints heredados de Phase 3) ────────────────────────

@router.get("/usuarios/{usuario_sistema_id}/roles")
def roles_de_usuario(
    usuario_sistema_id: str,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    usuario = db.query(UsuarioSistema).filter_by(id=usuario_sistema_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario del sistema no encontrado")

    registros = db.query(UsuarioRol).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
    ).all()
    return [{
        "id":             r.id,
        "rol_id":         r.rol_id,
        "rol_nombre":     r.rol.nombre,
        "empresa_id":     r.empresa_id,
        "empresa_nombre": r.empresa.nombre_empresa if r.empresa else None,
        "created_at":     r.created_at,
    } for r in registros]


@router.post("/usuarios/{usuario_sistema_id}/roles", status_code=status.HTTP_201_CREATED)
def asignar_rol(
    usuario_sistema_id: str,
    body: AsignarRolBody,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    usuario = db.query(UsuarioSistema).filter_by(id=usuario_sistema_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario del sistema no encontrado")

    rol = db.query(Rol).filter_by(id=body.rol_id, activo=True).first()
    if not rol:
        raise HTTPException(status_code=404, detail="Rol no encontrado")

    # Defensa en profundidad: un admin no-super solo delega roles funcionales,
    # dentro de sus empresas, y nunca a su propia cuenta. super_admin: sin restricción.
    if not is_super_admin(db, current_user.id):
        if usuario_sistema_id == current_user.id:
            raise HTTPException(status_code=403, detail="No puedes asignar roles a tu propia cuenta")
        if rol.nombre in _ROLES_ADMIN_TIER:
            raise HTTPException(status_code=403, detail=f"Solo un super_admin puede asignar el rol '{rol.nombre}'")
        if body.empresa_id is None:
            raise HTTPException(status_code=403, detail="Un administrador no puede asignar roles globales (a todas las empresas)")
        if not user_has_empresa_access(db, current_user.id, body.empresa_id):
            raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    existente = db.query(UsuarioRol).filter_by(
        usuario_sistema_id=usuario_sistema_id,
        rol_id=body.rol_id,
        empresa_id=body.empresa_id,
        activo=True,
    ).first()
    if existente:
        raise HTTPException(status_code=400, detail="El usuario ya tiene este rol para esa empresa")

    nuevo = UsuarioRol(
        usuario_sistema_id=usuario_sistema_id,
        rol_id=body.rol_id,
        empresa_id=body.empresa_id,
    )
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    return {"mensaje": f"Rol '{rol.nombre}' asignado correctamente", "id": nuevo.id}


@router.delete("/usuarios/{usuario_sistema_id}/roles/{usuario_rol_id}", status_code=status.HTTP_204_NO_CONTENT)
def revocar_rol(
    usuario_sistema_id: str,
    usuario_rol_id: str,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = require_role("super_admin", "admin"),
):
    registro = db.query(UsuarioRol).filter_by(
        id=usuario_rol_id,
        usuario_sistema_id=usuario_sistema_id,
        activo=True,
    ).first()
    if not registro:
        raise HTTPException(status_code=404, detail="Asignación de rol no encontrada")

    # Simétrico con Opción B: un admin no-super no revoca roles de nivel admin (a nadie),
    # ni toca cuentas super_admin, ni asignaciones globales, ni su propia cuenta.
    if not is_super_admin(db, current_user.id):
        if usuario_sistema_id == current_user.id:
            raise HTTPException(status_code=403, detail="No puedes revocar roles de tu propia cuenta")
        if registro.rol.nombre in _ROLES_ADMIN_TIER or is_super_admin(db, usuario_sistema_id):
            raise HTTPException(status_code=403, detail="Solo un super_admin puede revocar roles de nivel admin o de una cuenta super_admin")
        if registro.empresa_id is None:
            raise HTTPException(status_code=403, detail="Un administrador no puede revocar roles globales")
        if not user_has_empresa_access(db, current_user.id, registro.empresa_id):
            raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    registro.activo = False
    db.commit()


# ── Consulta propia (usada por el frontend) ───────────────────────────────────

@router.get("/me/permisos")
def mis_permisos(
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = Depends(get_current_user),
):
    permisos  = get_all_user_permissions(db, current_user.id)
    roles     = get_user_roles(db, current_user.id, current_user.empresa_id)
    super_adm = is_super_admin(db, current_user.id)
    return {
        "roles":          roles,
        # roles_todas: todos los roles del usuario en TODAS las empresas (no
        # depende del empresa_id legado). Para mostrar el rol real en la UI.
        "roles_todas":    get_all_user_roles(db, current_user.id),
        "permisos":       sorted(permisos),
        "empresa_id":     current_user.empresa_id,
        "is_super_admin": super_adm,
    }
