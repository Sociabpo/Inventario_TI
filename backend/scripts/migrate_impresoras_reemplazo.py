r"""
Migración: Impresoras Fase 2 — reemplazo-con-historial.

Añade a `impresoras` (idempotente, information_schema-guarded ADD COLUMN):
  - reemplaza_a      VARCHAR(36) NULL  → self-FK a impresoras.id (la NUEVA apunta a la vieja)
  - motivo_reemplazo VARCHAR(300) NULL → por qué se reemplazó (en la VIEJA)
  - reemplazado_at   DATETIME NULL     → cuándo (en la VIEJA)
  - reemplazado_by   VARCHAR(36) NULL  → quién (en la VIEJA)
+ índice en reemplaza_a + FK self-referencial. Solo esquema.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_impresoras_reemplazo.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

COLUMNAS = [
    ("reemplaza_a",      "ALTER TABLE impresoras ADD COLUMN reemplaza_a VARCHAR(36) NULL"),
    ("motivo_reemplazo", "ALTER TABLE impresoras ADD COLUMN motivo_reemplazo VARCHAR(300) NULL"),
    ("reemplazado_at",   "ALTER TABLE impresoras ADD COLUMN reemplazado_at DATETIME NULL"),
    ("reemplazado_by",   "ALTER TABLE impresoras ADD COLUMN reemplazado_by VARCHAR(36) NULL"),
]


def _tiene_columna(conn, col):
    return conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema=DATABASE() AND table_name='impresoras' AND column_name=:c"
    ), {"c": col}).scalar()


def _tiene_indice(conn, idx):
    return conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema=DATABASE() AND table_name='impresoras' AND index_name=:i"
    ), {"i": idx}).scalar()


def _tiene_fk_reemplaza(conn):
    return conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.key_column_usage "
        "WHERE table_schema=DATABASE() AND table_name='impresoras' "
        "AND column_name='reemplaza_a' AND referenced_table_name IS NOT NULL"
    )).scalar()


def migrate():
    with engine.begin() as conn:
        for col, ddl in COLUMNAS:
            if _tiene_columna(conn, col):
                print(f"  [=] Columna ya existe: {col}")
            else:
                conn.execute(text(ddl))
                print(f"  [+] Columna agregada:  {col}")

        if _tiene_indice(conn, "ix_impresoras_reemplaza_a"):
            print("  [=] Índice ya existe: ix_impresoras_reemplaza_a")
        else:
            conn.execute(text("ALTER TABLE impresoras ADD INDEX ix_impresoras_reemplaza_a (reemplaza_a)"))
            print("  [+] Índice agregado:  ix_impresoras_reemplaza_a")

        if _tiene_fk_reemplaza(conn):
            print("  [=] FK self-referencial ya existe (reemplaza_a)")
        else:
            conn.execute(text(
                "ALTER TABLE impresoras ADD CONSTRAINT fk_impresoras_reemplaza_a "
                "FOREIGN KEY (reemplaza_a) REFERENCES impresoras(id)"))
            print("  [+] FK self-referencial agregada (reemplaza_a -> impresoras.id)")
    print("\nMigracion Impresoras reemplazo completada.")


if __name__ == "__main__":
    migrate()
