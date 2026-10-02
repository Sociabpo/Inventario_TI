"""
Creates a test user 'auditor_sociabpo@test.com' with password 'Test1234!'
assigned to Socia BPO with the auditoria role.
"""
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
    # Find Socia BPO
    empresa = db.query(Empresa).filter(Empresa.nombre_empresa.ilike("%socia%")).first()
    if not empresa:
        print("ERROR: Socia BPO not found")
        sys.exit(1)
    print(f"Socia BPO id: {empresa.id}")

    # Find auditoria role
    rol = db.query(Rol).filter(Rol.nombre == "auditoria").first()
    if not rol:
        print("ERROR: auditoria role not found")
        sys.exit(1)
    print(f"Rol auditoria id: {rol.id}")

    # Create or get test user
    email = "auditor_sociabpo@test.com"
    user = db.query(UsuarioSistema).filter(UsuarioSistema.email == email).first()
    if not user:
        user = UsuarioSistema(
            nombre="Auditor Test",
            email=email,
            password=pwd_ctx.hash("Test1234!"),
            rol="auditoria",
            activo=True,
        )
        db.add(user)
        db.flush()
        print(f"Created user {email}")
    else:
        user.password = pwd_ctx.hash("Test1234!")
        user.activo = True
        db.flush()
        print(f"Reset password for existing user {email}")

    # Remove old role assignments for this user to start clean
    db.query(UsuarioRol).filter(UsuarioRol.usuario_sistema_id == user.id).delete()
    db.flush()

    # Assign auditoria role to Socia BPO only
    asignacion = UsuarioRol(
        usuario_sistema_id=user.id,
        rol_id=rol.id,
        empresa_id=empresa.id,
        activo=True,
    )
    db.add(asignacion)
    db.commit()
    print(f"Assigned auditoria role to Socia BPO ({empresa.id}) for user {email}")
    print("Done. Test credentials: auditor_sociabpo@test.com / Test1234!")

finally:
    db.close()
