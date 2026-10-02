"""
Seed de permisos RBAC del módulo Mantenimiento Preventivo.
Aditivo e idempotente: reutiliza los roles existentes (seed_rbac.py), inserta los
2 permisos del módulo y sus asociaciones rol↔permiso.

  - mantenimiento.planes    → gestionar planes (plantillas) + planificar/asignar (fases posteriores)
  - mantenimiento.ejecutar  → ejecutar mantenimientos (rol técnico)

Grants:
  super_admin, admin, analista_activos → ambos
  soporte_ti (rol técnico)             → solo ejecutar

Uso (desde backend/):
    python scripts/seed_mantenimiento_rbac.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso

PERMISOS = [
    ("mantenimiento.planes",   "Gestionar planes de mantenimiento preventivo"),
    ("mantenimiento.ejecutar", "Ejecutar mantenimientos preventivos"),
]

ROL_PERMISOS = {
    "super_admin":       {"mantenimiento.planes", "mantenimiento.ejecutar"},
    "admin":             {"mantenimiento.planes", "mantenimiento.ejecutar"},
    "analista_activos":  {"mantenimiento.planes", "mantenimiento.ejecutar"},
    "soporte_ti":        {"mantenimiento.ejecutar"},
}


def seed():
    db = SessionLocal()
    try:
        print("Iniciando seed RBAC de Mantenimiento...\n")
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
                    nuevas += 1

        db.commit()
        print(f"  [+] {nuevas} asociaciones nuevas creadas.")
        print("\nSeed RBAC de Mantenimiento completado.")
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
