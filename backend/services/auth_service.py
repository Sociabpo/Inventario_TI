from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.usuario_sistema import UsuarioSistema
from config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(hours=settings.ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def get_usuario_by_email(db: Session, email: str) -> Optional[UsuarioSistema]:
    return db.query(UsuarioSistema).filter(
        UsuarioSistema.email == email,
        UsuarioSistema.activo == True
    ).first()

def authenticate_user(db: Session, email: str, password: str) -> Optional[UsuarioSistema]:
    user = get_usuario_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.password):
        return None
    return user

def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None