r"""
Migración: préstamos temporales (loan deadline) sobre activos y accesorios.

Agrega a las tablas `activos` y `accesorios`:
    fecha_limite_devolucion    DATE NULL
    es_prestamo                BOOLEAN NOT NULL DEFAULT FALSE
    alerta_vencimiento_enviada BOOLEAN NOT NULL DEFAULT FALSE

Idempotente: comprueba information_schema antes de cada ALTER (MySQL no soporta
ADD COLUMN IF NOT EXISTS de forma portable).

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_prestamos.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

COLUMNAS = [
    ("fecha_limite_devolucion",    "DATE NULL"),
    ("es_prestamo",                "BOOLEAN NOT NULL DEFAULT FALSE"),
    ("alerta_vencimiento_enviada", "BOOLEAN NOT NULL DEFAULT FALSE"),
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
                    print(f"[=] {tabla}.{col} ya existe — omitido")
                    continue
                conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} {ddl}"))
                conn.commit()
                print(f"[+] {tabla}.{col} agregada")
            except Exception as e:
                print(f"[ERROR] {tabla}.{col}: {e}")
                sys.exit(1)
    print("\nMigración de préstamos completada.")
