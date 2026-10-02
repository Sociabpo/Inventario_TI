r"""
Migración: nuevos estados de activos/accesorios + columna ubicacion.

Mapeo de estados antiguos -> nuevos:
  disponible_ct / disponible_sede / disponible        -> disponible
  mantenimiento                                        -> mantenimiento_preventivo
  baja / dado_de_baja / devuelto_proveedor / para_venta / vendido -> retirado
  asignado                                             -> (sin cambio)

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_estados.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

ADD_COLS = [
    ("activos.ubicacion",     "ALTER TABLE activos ADD COLUMN ubicacion VARCHAR(150) NULL"),
    ("accesorios.ubicacion",  "ALTER TABLE accesorios ADD COLUMN ubicacion VARCHAR(150) NULL"),
]

MAPEOS = [
    "UPDATE {t} SET estado='disponible' WHERE estado IN ('disponible_ct','disponible_sede')",
    "UPDATE {t} SET estado='mantenimiento_preventivo' WHERE estado='mantenimiento'",
    "UPDATE {t} SET estado='retirado' WHERE estado IN ('baja','dado_de_baja','devuelto_proveedor','para_venta','vendido')",
]

with engine.connect() as conn:
    for nombre, ddl in ADD_COLS:
        try:
            conn.execute(text(ddl)); conn.commit()
            print(f"[+] Columna agregada: {nombre}")
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ("duplicate column", "already exists", "1060")):
                print(f"[=] Ya existe: {nombre}")
            else:
                print(f"[ERROR] {nombre}: {e}"); sys.exit(1)

    total = 0
    for tabla in ("activos", "accesorios"):
        for tmpl in MAPEOS:
            r = conn.execute(text(tmpl.format(t=tabla)))
            total += r.rowcount or 0
    # Ubicación por defecto para items no asignados sin ubicación
    for tabla in ("activos", "accesorios"):
        conn.execute(text(
            f"UPDATE {tabla} SET ubicacion='Bodega CT' "
            f"WHERE estado <> 'asignado' AND (ubicacion IS NULL OR ubicacion='')"
        ))
    conn.commit()
    print(f"[+] Estados migrados: {total} fila(s) actualizadas.")
    print("\nMigración de estados completada.")
