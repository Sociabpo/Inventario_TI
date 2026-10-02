r"""
Migración: sede + área en la solicitud de compra (trazabilidad para reportes).

Agrega a `solicitudes_compra`:
    sede VARCHAR(150) NULL
    area VARCHAR(150) NULL

Nullable en BD (filas antiguas no se rompen); la API/UI las exige en
creación/edición. Idempotente (comprueba information_schema). Solo esquema.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_solicitud_sede_area.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLA = "solicitudes_compra"
COLUMNAS = [("sede", "VARCHAR(150) NULL"), ("area", "VARCHAR(150) NULL")]


def _existe(conn, tabla, columna) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": tabla, "c": columna}).scalar())


with engine.connect() as conn:
    for columna, tipo in COLUMNAS:
        try:
            if _existe(conn, TABLA, columna):
                print(f"[=] {TABLA}.{columna} ya existe - omitido")
                continue
            conn.execute(text(f"ALTER TABLE {TABLA} ADD COLUMN {columna} {tipo}"))
            conn.commit()
            print(f"[+] {TABLA}.{columna} agregada")
        except Exception as e:
            print(f"[ERROR] {TABLA}.{columna}: {e}")
            sys.exit(1)
    print("\nMigracion de sede/area en solicitudes completada.")
