r"""
Migración: campos de BAJA en servidores.

Añade a `servidores` (idempotente, information_schema-guarded ADD COLUMN):
  - motivo_baja    TEXT NULL
  - fecha_baja     DATETIME NULL
  - dado_baja_por  VARCHAR(36) NULL

La baja = activo=0 (el registro se conserva; NO hard-delete) + estado 'Dado de baja'.
Solo esquema.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_servidores_baja.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

COLUMNAS = [
    ("motivo_baja",   "ALTER TABLE servidores ADD COLUMN motivo_baja TEXT NULL"),
    ("fecha_baja",    "ALTER TABLE servidores ADD COLUMN fecha_baja DATETIME NULL"),
    ("dado_baja_por", "ALTER TABLE servidores ADD COLUMN dado_baja_por VARCHAR(36) NULL"),
]


def _tiene_columna(conn, col):
    return conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = 'servidores' AND column_name = :c"
    ), {"c": col}).scalar()


def migrate():
    with engine.begin() as conn:
        for col, ddl in COLUMNAS:
            if _tiene_columna(conn, col):
                print(f"  [=] Columna ya existe: {col}")
            else:
                conn.execute(text(ddl))
                print(f"  [+] Columna agregada:  {col}")
    print("\nMigracion servidores-baja completada.")


if __name__ == "__main__":
    migrate()
