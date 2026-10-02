"""
Seed inicial de roles y permisos RBAC.
Idempotente: puede ejecutarse varias veces sin duplicar datos.

Uso (desde backend/):
    python scripts/seed_rbac.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso

# ── Definiciones ──────────────────────────────────────────────────────────────

ROLES = [
    ("super_admin",      "Acceso total al sistema, todas las empresas"),
    ("admin",            "Administración completa por empresa"),
    ("analista_activos", "Gestión completa de activos y asignaciones"),
    ("soporte_ti",       "Operación básica: edición y devoluciones"),
    ("auditoria",        "Solo lectura y exportación de reportes"),
    ("rrhh",             "Gestión de empleados y consulta de asignaciones"),
]

PERMISOS = [
    ("activos.ver",           "Ver listado de activos"),
    ("activos.crear",         "Crear nuevos activos"),
    ("activos.editar",        "Editar activos existentes"),
    ("activos.eliminar",      "Eliminar activos"),
    ("activos.asignar",       "Asignar activos a empleados"),
    ("activos.devolver",      "Registrar devoluciones de activos"),

    ("accesorios.ver",        "Ver listado de accesorios"),
    ("accesorios.crear",      "Crear nuevos accesorios"),
    ("accesorios.editar",     "Editar accesorios existentes"),
    ("accesorios.eliminar",   "Eliminar accesorios"),
    ("accesorios.asignar",    "Asignar accesorios a empleados"),
    ("accesorios.devolver",   "Registrar devoluciones de accesorios"),

    ("asignaciones.ver",      "Ver asignaciones"),
    ("asignaciones.crear",    "Crear asignaciones"),
    ("asignaciones.devolver", "Procesar devoluciones"),

    ("actas.ver",             "Ver actas generadas"),
    ("actas.generar",         "Generar nuevas actas PDF"),
    ("actas.descargar",       "Descargar actas PDF"),

    ("usuarios.ver",          "Ver empleados"),
    ("usuarios.crear",        "Crear empleados"),
    ("usuarios.editar",       "Editar empleados"),
    ("usuarios.eliminar",     "Eliminar empleados"),

    ("empresas.ver",          "Ver empresas"),
    ("empresas.crear",        "Crear empresas"),
    ("empresas.editar",       "Editar empresas"),
    ("empresas.eliminar",     "Eliminar empresas"),

    ("auditoria.ver",         "Ver log de auditoría"),
    ("auditoria.exportar",    "Exportar log de auditoría"),

    ("reportes.ver",          "Ver reportes"),
    ("reportes.exportar",     "Exportar reportes"),
]

ALL = {p[0] for p in PERMISOS}

ROL_PERMISOS = {
    "super_admin": ALL,
    "admin": ALL - {"empresas.eliminar", "usuarios.eliminar"},
    "analista_activos": {
        "activos.ver", "activos.crear", "activos.editar", "activos.asignar", "activos.devolver",
        "accesorios.ver", "accesorios.crear", "accesorios.editar", "accesorios.asignar", "accesorios.devolver",
        "asignaciones.ver", "asignaciones.crear", "asignaciones.devolver",
        "actas.ver", "actas.generar", "actas.descargar",
        "reportes.ver",
    },
    "soporte_ti": {
        "activos.ver", "activos.editar", "activos.devolver",
        "accesorios.ver", "accesorios.editar", "accesorios.devolver",
        "asignaciones.ver", "asignaciones.devolver",
        "actas.ver", "actas.descargar",
        "reportes.ver",
    },
    "auditoria": {
        "activos.ver", "accesorios.ver", "asignaciones.ver",
        "actas.ver", "actas.descargar",
        "auditoria.ver", "auditoria.exportar",
        "reportes.ver", "reportes.exportar",
        "usuarios.ver",
    },
    "rrhh": {
        "usuarios.ver", "usuarios.crear", "usuarios.editar",
        "activos.ver", "accesorios.ver", "asignaciones.ver",
        "actas.ver", "actas.generar", "actas.descargar",
        "reportes.ver", "reportes.exportar",
    },
}

# ── Seed ──────────────────────────────────────────────────────────────────────

def seed():
    db = SessionLocal()
    try:
        print("Iniciando seed RBAC...\n")

        # Roles
        roles_map = {}
        for nombre, desc in ROLES:
            rol = db.query(Rol).filter_by(nombre=nombre).first()
            if not rol:
                rol = Rol(nombre=nombre, descripcion=desc)
                db.add(rol)
                db.flush()
                print(f"  [+] Rol creado:    {nombre}")
            else:
                print(f"  [=] Rol existente: {nombre}")
            roles_map[nombre] = rol

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

        # Asociaciones rol ↔ permiso
        print("\nAsignando permisos a roles...")
        nuevas = 0
        for nombre_rol, codigos in ROL_PERMISOS.items():
            rol = roles_map[nombre_rol]
            for codigo in codigos:
                exists = db.query(RolPermiso).filter_by(
                    rol_id=rol.id,
                    permiso_id=permisos_map[codigo].id
                ).first()
                if not exists:
                    db.add(RolPermiso(rol_id=rol.id, permiso_id=permisos_map[codigo].id))
                    nuevas += 1

        db.commit()
        print(f"  [+] {nuevas} asociaciones nuevas creadas.")
        print("\nSeed RBAC completado exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed()
