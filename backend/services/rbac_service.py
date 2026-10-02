from typing import Optional, List, Set
from sqlalchemy.orm import Session
from sqlalchemy import or_

# Permisos del rol "admin" — espejo exacto del seed para el fallback pre-RBAC
_ADMIN_LEGACY_PERMS: Set[str] = {
    "activos.ver", "activos.crear", "activos.editar", "activos.eliminar",
    "activos.asignar", "activos.devolver",
    "accesorios.ver", "accesorios.crear", "accesorios.editar", "accesorios.eliminar",
    "accesorios.asignar", "accesorios.devolver",
    "asignaciones.ver", "asignaciones.crear", "asignaciones.devolver",
    "actas.ver", "actas.generar", "actas.descargar",
    "usuarios.ver", "usuarios.crear", "usuarios.editar",
    "empresas.ver", "empresas.crear", "empresas.editar",
    "auditoria.ver", "auditoria.exportar",
    "reportes.ver", "reportes.exportar",
}


def is_super_admin(db: Session, usuario_sistema_id: str) -> bool:
    """True si el usuario tiene el rol super_admin (RBAC) o 'superadmin' (legado)."""
    from models.usuario_rol import UsuarioRol
    from models.rol import Rol
    from models.usuario_sistema import UsuarioSistema

    tiene_rbac = db.query(UsuarioRol).join(Rol).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
        Rol.nombre == "super_admin",
        Rol.activo == True,
    ).first()
    if tiene_rbac:
        return True

    user = db.query(UsuarioSistema).filter_by(id=usuario_sistema_id).first()
    return user is not None and user.rol in ("superadmin", "super_admin")


def get_user_roles(db: Session, usuario_sistema_id: str, empresa_id: Optional[str]) -> List[str]:
    """Nombres de roles del usuario para una empresa (incluye roles globales empresa_id=None)."""
    from models.usuario_rol import UsuarioRol
    from models.rol import Rol

    rows = db.query(Rol.nombre).join(
        UsuarioRol, UsuarioRol.rol_id == Rol.id
    ).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
        Rol.activo == True,
        or_(UsuarioRol.empresa_id == empresa_id, UsuarioRol.empresa_id == None),
    ).all()
    return [r[0] for r in rows]


def get_user_permissions(db: Session, usuario_sistema_id: str, empresa_id: Optional[str]) -> Set[str]:
    """Conjunto de códigos de permiso del usuario para una empresa dada."""
    from models.usuario_rol import UsuarioRol
    from models.rol import Rol
    from models.permiso import Permiso
    from models.rol_permiso import RolPermiso
    from models.usuario_sistema import UsuarioSistema

    if is_super_admin(db, usuario_sistema_id):
        return {p[0] for p in db.query(Permiso.codigo).all()}

    # Sin registros RBAC → fallback al campo rol legado
    tiene_roles = db.query(UsuarioRol).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
    ).first()
    if not tiene_roles:
        user = db.query(UsuarioSistema).filter_by(id=usuario_sistema_id).first()
        legacy_rol = user.rol if user else ""
        if legacy_rol in ("superadmin", "super_admin"):
            return {p[0] for p in db.query(Permiso.codigo).all()}
        if legacy_rol == "admin":
            return _ADMIN_LEGACY_PERMS.copy()
        return set()

    rows = db.query(Permiso.codigo).join(
        RolPermiso, RolPermiso.permiso_id == Permiso.id
    ).join(
        Rol, Rol.id == RolPermiso.rol_id
    ).join(
        UsuarioRol, UsuarioRol.rol_id == Rol.id
    ).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
        Rol.activo == True,
        or_(UsuarioRol.empresa_id == empresa_id, UsuarioRol.empresa_id == None),
    ).distinct().all()
    return {r[0] for r in rows}


def has_permission(db: Session, usuario_sistema_id: str, empresa_id: Optional[str], permission_code: str) -> bool:
    return permission_code in get_user_permissions(db, usuario_sistema_id, empresa_id)


def get_user_empresa_ids(db: Session, usuario_sistema_id: str):
    """
    Returns the list of empresa_ids the user has active UsuarioRol records for.
    Returns None for super_admin (caller must apply no empresa filter — sees all).
    Returns [] if the user has no company assignments (sees nothing).
    """
    from models.usuario_rol import UsuarioRol

    if is_super_admin(db, usuario_sistema_id):
        return None

    rows = db.query(UsuarioRol.empresa_id).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
        UsuarioRol.empresa_id != None,
    ).distinct().all()
    return [r[0] for r in rows]


def get_all_user_roles(db: Session, usuario_sistema_id: str) -> List[str]:
    """All role names across ALL company assignments."""
    from models.usuario_rol import UsuarioRol
    from models.rol import Rol
    from models.usuario_sistema import UsuarioSistema

    if is_super_admin(db, usuario_sistema_id):
        return ["super_admin"]

    rows = db.query(Rol.nombre).join(
        UsuarioRol, UsuarioRol.rol_id == Rol.id
    ).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
        Rol.activo == True,
    ).distinct().all()

    if rows:
        return [r[0] for r in rows]

    # Legacy fallback
    user = db.query(UsuarioSistema).filter_by(id=usuario_sistema_id).first()
    return [user.rol] if user and user.rol else []


def user_has_empresa_access(db: Session, usuario_sistema_id: str, empresa_id: str) -> bool:
    """True if the user has at least one active role assignment for this empresa (or is super_admin)."""
    from models.usuario_rol import UsuarioRol

    if is_super_admin(db, usuario_sistema_id):
        return True
    return db.query(UsuarioRol).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.empresa_id == empresa_id,
        UsuarioRol.activo == True,
    ).first() is not None


def get_all_user_permissions(db: Session, usuario_sistema_id: str) -> Set[str]:
    """Union of permissions across ALL company assignments — used by /me/permisos only."""
    from models.usuario_rol import UsuarioRol
    from models.rol import Rol
    from models.permiso import Permiso
    from models.rol_permiso import RolPermiso
    from models.usuario_sistema import UsuarioSistema

    if is_super_admin(db, usuario_sistema_id):
        return {p[0] for p in db.query(Permiso.codigo).all()}

    tiene_roles = db.query(UsuarioRol).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
    ).first()
    if not tiene_roles:
        user = db.query(UsuarioSistema).filter_by(id=usuario_sistema_id).first()
        legacy_rol = user.rol if user else ""
        if legacy_rol in ("superadmin", "super_admin"):
            return {p[0] for p in db.query(Permiso.codigo).all()}
        if legacy_rol == "admin":
            return _ADMIN_LEGACY_PERMS.copy()
        return set()

    rows = db.query(Permiso.codigo).join(
        RolPermiso, RolPermiso.permiso_id == Permiso.id
    ).join(
        Rol, Rol.id == RolPermiso.rol_id
    ).join(
        UsuarioRol, UsuarioRol.rol_id == Rol.id
    ).filter(
        UsuarioRol.usuario_sistema_id == usuario_sistema_id,
        UsuarioRol.activo == True,
        Rol.activo == True,
    ).distinct().all()
    return {r[0] for r in rows}


# ── Relaciones entre empresas ("hermanas") ───────────────────────────────────
def get_empresas_relacionadas(db: Session, empresa_id: str) -> Set[str]:
    """Conjunto de empresa_ids DIRECTAMENTE relacionados con empresa_id.
    Bidireccional (revisa ambas columnas) y NO transitivo (solo relaciones
    directas existentes como fila)."""
    from models.empresa_relacion import EmpresaRelacion

    rows = db.query(EmpresaRelacion).filter(
        or_(EmpresaRelacion.empresa_a_id == empresa_id,
            EmpresaRelacion.empresa_b_id == empresa_id),
    ).all()
    relacionadas: Set[str] = set()
    for r in rows:
        otro = r.empresa_b_id if r.empresa_a_id == empresa_id else r.empresa_a_id
        relacionadas.add(otro)
    return relacionadas


def empresas_pueden_compartir(db: Session, empresa_recurso_id: str, empresa_empleado_id: str) -> bool:
    """True si es la misma empresa o si están DIRECTAMENTE relacionadas (hermanas)."""
    if empresa_recurso_id == empresa_empleado_id:
        return True
    return empresa_empleado_id in get_empresas_relacionadas(db, empresa_recurso_id)


def get_user_empresa_id(current_user, empresa_id_param: Optional[str], db=None) -> Optional[str]:
    """
    super_admin can access any empresa.
    Other users can access any empresa they have an active UsuarioRol for.
    If db is not provided falls back to comparing against UsuarioSistema.empresa_id.
    """
    from fastapi import HTTPException, status
    if is_super_admin(db, current_user.id) if db else current_user.rol in ("superadmin", "super_admin"):
        return empresa_id_param
    if empresa_id_param:
        if db:
            if not user_has_empresa_access(db, current_user.id, empresa_id_param):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes acceso a esa empresa.",
                )
        elif empresa_id_param != current_user.empresa_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes acceso a esa empresa.",
            )
    return empresa_id_param
