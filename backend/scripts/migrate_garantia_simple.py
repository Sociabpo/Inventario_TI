r"""
Migración: garantía simple por recurso (activos y accesorios).

Agrega a `activos` y `accesorios`:
    garantia_meses INTEGER NULL    (duración en meses)
    garantia_fin   DATE NULL       (fin de garantía, auto-calculado / editable)

Idempotente: comprueba information_schema antes de cada ALTER (solo esquema, sin
inserción de datos).

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_garantia_simple.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

COLUMNAS = [
    ("garantia_meses", "INTEGER NULL"),
    ("garantia_fin",   "DATE NULL"),
]
TABLAS = ["activos", "accesorios"]


def _columna_existe(conn, tabla: str, columna: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": tabla, "c": columna}).scalar()
    return bool(row)


with engine.connect() as conn:
    for tabla in TABLAS:
        for col, ddl in COLUMNAS:
            try:
                if _columna_existe(conn, tabla, col):
                    print(f"[=] {tabla}.{col} ya existe - omitido")
                    continue
                conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} {ddl}"))
                conn.commit()
                print(f"[+] {tabla}.{col} agregada")
            except Exception as e:
                print(f"[ERROR] {tabla}.{col}: {e}")
                sys.exit(1)
    print("\nMigracion de garantia simple completada.")
