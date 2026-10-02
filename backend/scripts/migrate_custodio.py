r"""
Migración: custodio (empleado responsable de un recurso DISPONIBLE).

Agrega a `activos` y `accesorios`:
    custodio_id VARCHAR(36) NULL   (FK lógica a usuarios.id)

Custodia NO es un estado: el recurso sigue 'disponible'. Idempotente
(comprueba information_schema). Solo esquema, sin inserción de datos.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_custodio.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLAS = ["activos", "accesorios"]
COLUMNA = "custodio_id"
DDL_TIPO = "VARCHAR(36) NULL"


def _existe(conn, tabla, columna) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": tabla, "c": columna}).scalar())


with engine.connect() as conn:
    for tabla in TABLAS:
        try:
            if _existe(conn, tabla, COLUMNA):
                print(f"[=] {tabla}.{COLUMNA} ya existe - omitido")
                continue
            conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {COLUMNA} {DDL_TIPO}"))
            conn.commit()
            print(f"[+] {tabla}.{COLUMNA} agregada")
        except Exception as e:
            print(f"[ERROR] {tabla}.{COLUMNA}: {e}")
            sys.exit(1)
    print("\nMigracion de custodio completada.")
