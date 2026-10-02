"""
Asigna el rol super_admin al usuario administrador existente.
Uso (desde backend/):
    python scripts/assign_super_admin.py [email]

Si no se pasa email, usa admin@inventario.com por defecto.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.usuario_sistema import UsuarioSistema
from models.rol import Rol
from models.usuario_rol import UsuarioRol


def assign_super_admin(email: str):
    db = SessionLocal()
    try:
        usuario = db.query(UsuarioSistema).filter_by(email=email).first()
        if not usuario:
            print(f"[ERROR] No se encontró usuario con email: {email}")
            return

        rol = db.query(Rol).filter_by(nombre="super_admin", activo=True).first()
        if not rol:
            print("[ERROR] El rol 'super_admin' no existe. Ejecuta seed_rbac.py primero.")
            return

        existente = db.query(UsuarioRol).filter_by(
            usuario_sistema_id=usuario.id,
            rol_id=rol.id,
            activo=True,
        ).first()
        if existente:
            print(f"[=] '{usuario.nombre}' ({email}) ya tiene el rol super_admin asignado.")
            return

        nuevo = UsuarioRol(
            usuario_sistema_id=usuario.id,
            rol_id=rol.id,
            empresa_id=None,  # null = acceso global a todas las empresas
        )
        db.add(nuevo)
        db.commit()
        print(f"[+] Rol 'super_admin' asignado correctamente a:")
        print(f"    Nombre : {usuario.nombre}")
        print(f"    Email  : {usuario.email}")
        print(f"    Empresa: global (todas las empresas)")

    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    email = sys.argv[1] if len(sys.argv) > 1 else "admin@inventario.com"
    assign_super_admin(email)
