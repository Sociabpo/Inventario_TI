r"""
Migración: nuevos motivos de baja (hurto, traslado).

Agrega a la tabla `bajas_activos`:
    numero_denuncia        VARCHAR(100) NULL   (motivo "hurto")
    empresa_destino_id     VARCHAR(36)  NULL   (motivo "traslado")
    empresa_destino_nombre VARCHAR(150) NULL   (snapshot del nombre)

Idempotente: comprueba information_schema antes de cada ALTER.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_baja_motivos.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLA = "bajas_activos"
COLUMNAS = [
    ("numero_denuncia",        "VARCHAR(100) NULL"),
    ("empresa_destino_id",     "VARCHAR(36) NULL"),
    ("empresa_destino_nombre", "VARCHAR(150) NULL"),
]


def _columna_existe(conn, tabla: str, columna: str) -> bool:
    row = conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": tabla, "c": columna}).scalar()
    return bool(row)


with engine.connect() as conn:
    for col, ddl in COLUMNAS:
        try:
            if _columna_existe(conn, TABLA, col):
                print(f"[=] {TABLA}.{col} ya existe — omitido")
                continue
            conn.execute(text(f"ALTER TABLE {TABLA} ADD COLUMN {col} {ddl}"))
            conn.commit()
            print(f"[+] {TABLA}.{col} agregada")
        except Exception as e:
            print(f"[ERROR] {TABLA}.{col}: {e}")
            sys.exit(1)
    print("\nMigración de motivos de baja completada.")
