from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from database import get_db
from config import settings
from services.auth_service import (
    authenticate_user, create_access_token,
    hash_password, decode_token, get_usuario_by_email
)
from models.usuario_sistema import UsuarioSistema

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ── Schemas ──────────────────────────────────────────────
class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario: dict

class CrearAdminSchema(BaseModel):
    nombre: str
    email: EmailStr
    password: str
    clave_instalacion: str  # Clave secreta para crear el primer admin

# ── Dependencia: obtener usuario actual ──────────────────
def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> UsuarioSistema:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_token(token)
    if not payload:
        raise credentials_exception

    email: str = payload.get("sub")
    if not email:
        raise credentials_exception

    user = get_usuario_by_email(db, email)
    if not user:
        raise credentials_exception

    return user

def require_admin(current_user: UsuarioSistema = Depends(get_current_user)):
    if current_user.rol not in ["admin", "superadmin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permisos para realizar esta acción"
        )
    return current_user

def require_superadmin(current_user: UsuarioSistema = Depends(get_current_user)):
    if current_user.rol != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el superadministrador puede realizar esta acción"
        )
    return current_user

# ── Endpoints ────────────────────────────────────────────
@router.post("/login", response_model=LoginResponse)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={
        "sub": user.email,
        "rol": user.rol,
        "nombre": user.nombre,
        "empresa_id": user.empresa_id
    })
    return LoginResponse(
        access_token=token,
        usuario={
            "id": user.id,
            "nombre": user.nombre,
            "email": user.email,
            "rol": user.rol,
            "empresa_id": user.empresa_id
        }
    )

@router.get("/me")
def get_me(current_user: UsuarioSistema = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "nombre": current_user.nombre,
        "email": current_user.email,
        "rol": current_user.rol,
        "empresa_id": current_user.empresa_id
    }

@router.post("/setup", status_code=status.HTTP_201_CREATED)
def crear_primer_admin(
    data: CrearAdminSchema,
    db: Session = Depends(get_db)
):
    """
    Crea el primer superadmin del sistema.
    Solo funciona si no existe ningún usuario en la BD.
    Requiere la clave de instalación del .env
    """
    # Verificar clave de instalación
    if data.clave_instalacion != settings.SECRET_KEY[:20]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clave de instalación incorrecta"
        )
    # Solo si no hay usuarios creados
    total = db.query(UsuarioSistema).count()
    if total > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya existe un administrador. Usa el panel de administración."
        )
    admin = UsuarioSistema(
        nombre=data.nombre,
        email=data.email,
        password=hash_password(data.password),
        rol="superadmin",
        activo=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return {
        "mensaje": "Superadmin creado correctamente",
        "email": admin.email,
        "rol": admin.rol
    }