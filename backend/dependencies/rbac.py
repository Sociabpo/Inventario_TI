from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from database import get_db
from models.usuario_sistema import UsuarioSistema
from routers.auth import get_current_user
from services.rbac_service import (
    get_all_user_permissions,
    get_all_user_roles,
    is_super_admin,
    user_has_empresa_access,
)


def require_permission(permission_code: str):
    """
    Factory: returns a Depends that requires a specific permission.
    Checks the union of permissions across ALL company assignments — not just
    current_user.empresa_id — so multi-company users work correctly.
    """
    def _dep(
        db: Session = Depends(get_db),
        current_user: UsuarioSistema = Depends(get_current_user),
    ) -> UsuarioSistema:
        if permission_code not in get_all_user_permissions(db, current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permiso requerido: '{permission_code}'",
            )
        return current_user
    return Depends(_dep)


def require_any_permission(*permission_codes: str):
    """Factory: passes if the user has AT LEAST ONE of the given permissions (any company)."""
    def _dep(
        db: Session = Depends(get_db),
        current_user: UsuarioSistema = Depends(get_current_user),
    ) -> UsuarioSistema:
        user_perms = get_all_user_permissions(db, current_user.id)
        if not any(p in user_perms for p in permission_codes):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Se requiere alguno de: {', '.join(permission_codes)}",
            )
        return current_user
    return Depends(_dep)


def require_role(*role_names: str):
    """
    Factory: requires the user to have AT LEAST ONE of the given roles.
    Checks across ALL company assignments so multi-company admins are recognized.
    """
    def _dep(
        db: Session = Depends(get_db),
        current_user: UsuarioSistema = Depends(get_current_user),
    ) -> UsuarioSistema:
        roles = get_all_user_roles(db, current_user.id)
        if not any(r in roles for r in role_names):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol requerido: {' o '.join(role_names)}",
            )
        return current_user
    return Depends(_dep)


def verify_empresa_access(
    empresa_id: str,
    db: Session = Depends(get_db),
    current_user: UsuarioSistema = Depends(get_current_user),
):
    """
    Inline dependency for endpoints with empresa_id in path or query.
    super_admin always passes; others must have an active UsuarioRol for that empresa.
    """
    if not user_has_empresa_access(db, current_user.id, empresa_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esa empresa.",
        )
