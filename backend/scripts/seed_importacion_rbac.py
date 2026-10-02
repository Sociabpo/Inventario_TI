"""
Seed aditivo del permiso del módulo de Importación masiva.
Idempotente. Uso (desde backend/):
    venv\\Scripts\\python.exe scripts/seed_importacion_rbac.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso

PERMISOS = [
    ("importacion.ejecutar", "Importar activos masivamente desde Excel"),
]
ROL_PERMISOS = {
    "super_admin": {"importacion.ejecutar"},
    "admin":       {"importacion.ejecutar"},
}


def seed():
    db = SessionLocal()
    try:
        pmap = {}
        for codigo, desc in PERMISOS:
            modulo, accion = codigo.split(".", 1)
            p = db.query(Permiso).filter_by(codigo=codigo).first()
            if not p:
                p = Permiso(codigo=codigo, descripcion=desc, modulo=modulo, accion=accion)
                db.add(p); db.flush()
                print(f"  [+] Permiso creado: {codigo}")
            else:
                print(f"  [=] Permiso existente: {codigo}")
            pmap[codigo] = p
        nuevas = 0
        for nombre_rol, codigos in ROL_PERMISOS.items():
            rol = db.query(Rol).filter_by(nombre=nombre_rol).first()
            if not rol:
                print(f"  [!] Rol no encontrado (omitido): {nombre_rol}")
                continue
            for codigo in codigos:
                if not db.query(RolPermiso).filter_by(rol_id=rol.id, permiso_id=pmap[codigo].id).first():
                    db.add(RolPermiso(rol_id=rol.id, permiso_id=pmap[codigo].id)); nuevas += 1
        db.commit()
        print(f"  [+] {nuevas} asociaciones nuevas.")
        print("Seed de permisos de importacion completado.")
    except Exception as e:
        db.rollback(); print(f"[ERROR] {e}"); raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
