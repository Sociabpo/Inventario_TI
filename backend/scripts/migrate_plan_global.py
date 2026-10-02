r"""
Migración: los PLANES de mantenimiento pasan a ser GLOBALES (no per-empresa).

Elimina planes_mantenimiento.empresa_id (y su FK si existe). Una plantilla es
la misma para todas las empresas; lo per-empresa es la TAREA (del equipo), que
NO cambia. Todo el dato actual es de prueba — sin back-fill.

Idempotente: comprueba la columna/FK antes de alterar.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_plan_global.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLA = "planes_mantenimiento"
COL = "empresa_id"


def _col_existe(conn) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": TABLA, "c": COL}).scalar())


def _fk_nombre(conn):
    return conn.execute(text(
        "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
        "AND COLUMN_NAME = :c AND REFERENCED_TABLE_NAME IS NOT NULL"
    ), {"t": TABLA, "c": COL}).scalar()


with engine.connect() as conn:
    try:
        if not _col_existe(conn):
            print(f"[=] {TABLA}.{COL} no existe - nada que hacer (ya es global)")
        else:
            fk = _fk_nombre(conn)
            if fk:
                conn.execute(text(f"ALTER TABLE {TABLA} DROP FOREIGN KEY {fk}"))
                conn.commit()
                print(f"[+] FK {fk} eliminada")
            conn.execute(text(f"ALTER TABLE {TABLA} DROP COLUMN {COL}"))
            conn.commit()
            print(f"[+] {TABLA}.{COL} eliminada — los planes ahora son globales")
        print("\nMigracion plan-global completada.")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e}")
        sys.exit(1)
