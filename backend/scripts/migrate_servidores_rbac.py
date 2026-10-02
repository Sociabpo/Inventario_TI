"""
RBAC migration: add servidores permissions and assign to existing roles.
Run from backend/: python scripts/migrate_servidores_rbac.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.permiso import Permiso
from models.rol import Rol
from models.rol_permiso import RolPermiso

db = SessionLocal()

PERMISOS = [
    ("servidores.ver",      "servidores", "ver",      "Ver listado e información de servidores"),
    ("servidores.crear",    "servidores", "crear",    "Registrar nuevos servidores"),
    ("servidores.editar",   "servidores", "editar",   "Editar información de servidores"),
    ("servidores.eliminar", "servidores", "eliminar", "Desactivar / dar de baja servidores"),
]

# Create permissions if they don't exist
perm_ids = {}
for codigo, modulo, accion, desc in PERMISOS:
    p = db.query(Permiso).filter_by(codigo=codigo).first()
    if not p:
        p = Permiso(codigo=codigo, modulo=modulo, accion=accion, descripcion=desc)
        db.add(p)
        db.flush()
        print(f"  + Permiso creado: {codigo}")
    else:
        print(f"  ~ Permiso ya existe: {codigo}")
    perm_ids[codigo] = p.id

db.commit()

# Assign permissions to roles
ROLE_PERMS = {
    "super_admin": ["servidores.ver", "servidores.crear", "servidores.editar", "servidores.eliminar"],
    "admin":       ["servidores.ver", "servidores.crear", "servidores.editar", "servidores.eliminar"],
    "auditor":     ["servidores.ver"],
    "soporte":     ["servidores.ver", "servidores.editar"],
    "consultor":   ["servidores.ver"],
    "operador":    ["servidores.ver", "servidores.crear", "servidores.editar"],
}

for rol_nombre, codigos in ROLE_PERMS.items():
    rol = db.query(Rol).filter_by(nombre=rol_nombre).first()
    if not rol:
        print(f"  ! Rol '{rol_nombre}' no encontrado — omitido")
        continue
    for codigo in codigos:
        pid = perm_ids.get(codigo)
        if not pid:
            continue
        exists = db.query(RolPermiso).filter_by(rol_id=rol.id, permiso_id=pid).first()
        if not exists:
            db.add(RolPermiso(rol_id=rol.id, permiso_id=pid))
            print(f"  + {rol_nombre} <- {codigo}")
        else:
            print(f"  ~ {rol_nombre} ya tiene: {codigo}")

db.commit()
db.close()
print("\nMigración RBAC servidores completada.")
