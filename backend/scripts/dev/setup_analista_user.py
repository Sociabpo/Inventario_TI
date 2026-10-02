"""Creates analista_activos@test.com assigned to Socia BPO only."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.usuario_sistema import UsuarioSistema
from models.rol import Rol
from models.usuario_rol import UsuarioRol
from models.empresa import Empresa
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
db = SessionLocal()

try:
    empresa = db.query(Empresa).filter(Empresa.nombre_empresa.ilike("%socia%")).first()
    rol = db.query(Rol).filter(Rol.nombre == "analista_activos").first()
    assert empresa and rol, "empresa or rol not found"

    email = "analista_sociabpo@test.com"
    user = db.query(UsuarioSistema).filter(UsuarioSistema.email == email).first()
    if not user:
        user = UsuarioSistema(nombre="Analista Test", email=email,
                              password=pwd_ctx.hash("Test1234!"), rol="analista_activos", activo=True)
        db.add(user)
        db.flush()
        print(f"Created {email}")
    else:
        user.password = pwd_ctx.hash("Test1234!")
        user.activo = True
        db.flush()
        print(f"Reset password for {email}")

    db.query(UsuarioRol).filter(UsuarioRol.usuario_sistema_id == user.id).delete()
    db.add(UsuarioRol(usuario_sistema_id=user.id, rol_id=rol.id, empresa_id=empresa.id, activo=True))
    db.commit()
    print(f"Assigned analista_activos -> Socia BPO ({empresa.id})")
    print("Credentials: analista_sociabpo@test.com / Test1234!")
finally:
    db.close()
