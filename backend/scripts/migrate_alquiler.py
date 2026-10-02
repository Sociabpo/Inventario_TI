r"""
Migración: feature de alquiler (rental) end-to-end.

  1. activos    + es_alquiler TINYINT(1) DEFAULT 0, contrato_alquiler_id VARCHAR(36) NULL
  2. accesorios + es_alquiler TINYINT(1) DEFAULT 0, contrato_alquiler_id VARCHAR(36) NULL
  3. contratos_alquiler: DROP COLUMN activo_id, accesorio_id (un contrato cubre
     muchos equipos; el vínculo pasa a vivir en el equipo). orden_compra_id UNIQUE
     se conserva (un contrato por OC de alquiler).

Idempotente (comprueba information_schema). Solo esquema — sin datos. Todo el
dato actual es de prueba, no hay back-fill.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_alquiler.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text


def _col_existe(conn, tabla, col) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": tabla, "c": col}).scalar())


ADD = [
    ("activos",    "es_alquiler",          "TINYINT(1) DEFAULT 0"),
    ("activos",    "contrato_alquiler_id", "VARCHAR(36) NULL"),
    ("accesorios", "es_alquiler",          "TINYINT(1) DEFAULT 0"),
    ("accesorios", "contrato_alquiler_id", "VARCHAR(36) NULL"),
]
DROP = [
    ("contratos_alquiler", "activo_id"),
    ("contratos_alquiler", "accesorio_id"),
]

with engine.connect() as conn:
    try:
        for tabla, col, tipo in ADD:
            if _col_existe(conn, tabla, col):
                print(f"[=] {tabla}.{col} ya existe - omitido")
            else:
                conn.execute(text(f"ALTER TABLE {tabla} ADD COLUMN {col} {tipo}"))
                conn.commit()
                print(f"[+] {tabla}.{col} agregada")

        for tabla, col in DROP:
            if _col_existe(conn, tabla, col):
                # soltar FK asociada si la hubiera (nombre desconocido → best-effort)
                try:
                    conn.execute(text(f"ALTER TABLE {tabla} DROP COLUMN {col}"))
                    conn.commit()
                    print(f"[+] {tabla}.{col} eliminada")
                except Exception as e:
                    # puede requerir soltar el FK primero
                    fk = conn.execute(text(
                        "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
                        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
                        "AND COLUMN_NAME = :c AND REFERENCED_TABLE_NAME IS NOT NULL"
                    ), {"t": tabla, "c": col}).scalar()
                    if fk:
                        conn.execute(text(f"ALTER TABLE {tabla} DROP FOREIGN KEY {fk}"))
                        conn.commit()
                    conn.execute(text(f"ALTER TABLE {tabla} DROP COLUMN {col}"))
                    conn.commit()
                    print(f"[+] {tabla}.{col} eliminada (FK {fk} soltada primero)")
            else:
                print(f"[=] {tabla}.{col} no existe - omitido")

        print("\nMigracion de alquiler completada.")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e}")
        sys.exit(1)
