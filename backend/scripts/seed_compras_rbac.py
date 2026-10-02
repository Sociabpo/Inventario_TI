"""
Seed de permisos RBAC del módulo Compras.
Additivo e idempotente: reutiliza los roles existentes (creados por seed_rbac.py),
solo inserta los 6 permisos del módulo y sus asociaciones rol↔permiso.

Uso (desde backend/):
    python scripts/seed_compras_rbac.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso

# ── Permisos del módulo ───────────────────────────────────────────────────────
PERMISOS = [
    ("compras.ver",                "Ver módulo de compras"),
    ("compras.crear_solicitud",    "Crear solicitudes y órdenes de compra"),
    ("compras.aprobar",            "Aprobar o rechazar solicitudes de compra"),
    ("compras.recepcionar",        "Registrar recepciones de mercancía"),
    ("compras.crear_inventario",   "Crear activos/accesorios desde recepciones"),
    ("compras.gestionar_facturas", "Gestionar facturas, proveedores y contratos"),
]

ALL = {p[0] for p in PERMISOS}

# ── Asignación a roles ────────────────────────────────────────────────────────
ROL_PERMISOS = {
    "super_admin": ALL,
    "admin":       ALL,
    "analista_activos": {
        "compras.ver", "compras.crear_solicitud", "compras.recepcionar",
        "compras.crear_inventario",
    },
    "soporte_ti": {
        "compras.ver", "compras.recepcionar",
    },
    "auditoria": {"compras.ver"},
    "rrhh":      {"compras.ver"},
}


def seed():
    db = SessionLocal()
    try:
        print("Iniciando seed RBAC de Compras...\n")

        # Permisos
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

        # Roles (deben existir ya; si falta alguno, se avisa y se omite)
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
        print("\nSeed RBAC de Compras completado exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
