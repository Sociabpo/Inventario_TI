"""
Seed de permisos RBAC del módulo Redes.
Aditivo e idempotente: reutiliza los roles existentes (seed_rbac.py), inserta los
2 permisos del módulo y sus asociaciones rol↔permiso.

  - redes.ver       → ver cuartos técnicos, racks y (fase 2) dispositivos
  - redes.gestionar → crear / editar / eliminar cuartos técnicos y racks

Grants:
  super_admin, admin, soporte_ti           → ambos (ver + gestionar)
  analista_activos, auditoria (solo lectura) → solo ver

Uso (desde backend/):
    python scripts/seed_redes_rbac.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso

PERMISOS = [
    ("redes.ver",       "Ver cuartos técnicos, racks y dispositivos de red"),
    ("redes.gestionar", "Crear, editar y eliminar cuartos técnicos y racks"),
]

ROL_PERMISOS = {
    "super_admin":      {"redes.ver", "redes.gestionar"},
    "admin":            {"redes.ver", "redes.gestionar"},
    "soporte_ti":       {"redes.ver", "redes.gestionar"},
    "analista_activos": {"redes.ver"},
    "auditoria":        {"redes.ver"},
}


def seed():
    db = SessionLocal()
    try:
        print("Iniciando seed RBAC de Redes...\n")
        permisos_map = {}
        for codigo, desc in PERMISOS:
            modulo, accion = codigo.split(".", 1)
            p = db.query(Permiso).filter_by(codigo=codigo).first()
            if not p:
                p = Permiso(codigo=codigo, descripcion=desc, modulo=modulo, accion=accion)
                db.add(p)
                db.flush()
                print(f"  [+] Permiso creado:    {codigo}")
            else:
                print(f"  [=] Permiso existente: {codigo}")
            permisos_map[codigo] = p

        print("\nAsignando permisos a roles...")
        nuevas = 0
        for nombre_rol, codigos in ROL_PERMISOS.items():
            rol = db.query(Rol).filter_by(nombre=nombre_rol).first()
            if not rol:
                print(f"  [!] Rol no encontrado (omitido): {nombre_rol} — corre seed_rbac.py primero")
                continue
            for codigo in codigos:
                exists = db.query(RolPermiso).filter_by(
                    rol_id=rol.id, permiso_id=permisos_map[codigo].id
                ).first()
                if not exists:
                    db.add(RolPermiso(rol_id=rol.id, permiso_id=permisos_map[codigo].id))
                    print(f"  [+] {nombre_rol} <- {codigo}")
                    nuevas += 1
                else:
                    print(f"  [=] {nombre_rol} ya tiene: {codigo}")

        db.commit()
        print(f"\n  [+] {nuevas} asociaciones nuevas creadas.")
        print("Seed RBAC de Redes completado.")
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
