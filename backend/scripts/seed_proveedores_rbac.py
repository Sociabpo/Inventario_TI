"""
Seed de permisos RBAC del catálogo COMPARTIDO de proveedores.
Aditivo e idempotente: reutiliza los roles existentes (seed_rbac.py).

  - proveedores.ver       → ver el catálogo compartido de proveedores
  - proveedores.gestionar → crear / editar proveedores en el catálogo compartido

Neutral respecto a módulos (no depende de compras): lo consumen compras e impresoras.

Grants (espejando cómo compras concede sus permisos):
  gestionar → super_admin, admin, soporte_ti
              (compras.gestionar_facturas hoy es super_admin/admin; sumamos soporte_ti
               por decisión del catálogo compartido)
  ver       → esos tres + analista_activos + auditoria (lectores de compras/impresoras)

Uso (desde backend/):
    python scripts/seed_proveedores_rbac.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso

PERMISOS = [
    ("proveedores.ver",       "Ver el catálogo compartido de proveedores"),
    ("proveedores.gestionar", "Crear y editar proveedores del catálogo compartido"),
]

ROL_PERMISOS = {
    "super_admin":      {"proveedores.ver", "proveedores.gestionar"},
    "admin":            {"proveedores.ver", "proveedores.gestionar"},
    "soporte_ti":       {"proveedores.ver", "proveedores.gestionar"},
    "analista_activos": {"proveedores.ver"},
    "auditoria":        {"proveedores.ver"},
}


def seed():
    db = SessionLocal()
    try:
        print("Iniciando seed RBAC de Proveedores (catálogo compartido)...\n")
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
        print("Seed RBAC de Proveedores completado.")
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
