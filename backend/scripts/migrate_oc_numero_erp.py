r"""
Migración: renombra ordenes_compra.referencia_proveedor → numero_orden_erp.

El campo pasa a representar el "número de orden del ERP/contable" (referencia
externa para cruzar la OC de inventario con el ERP). Sigue siendo opcional
(nullable) y VARCHAR(100). Idempotente: comprueba qué columna existe antes de
alterar, así re-ejecutarlo es seguro. Solo esquema — sin datos.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_oc_numero_erp.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLA = "ordenes_compra"
VIEJA = "referencia_proveedor"
NUEVA = "numero_orden_erp"
TIPO = "VARCHAR(100) NULL"


def _existe(conn, columna) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": TABLA, "c": columna}).scalar())


with engine.connect() as conn:
    try:
        if _existe(conn, NUEVA):
            print(f"[=] {TABLA}.{NUEVA} ya existe - nada que hacer")
        elif _existe(conn, VIEJA):
            conn.execute(text(f"ALTER TABLE {TABLA} CHANGE COLUMN {VIEJA} {NUEVA} {TIPO}"))
            conn.commit()
            print(f"[+] {TABLA}.{VIEJA} renombrada a {NUEVA}")
        else:
            # Ninguna existe (BD muy antigua): crear la nueva
            conn.execute(text(f"ALTER TABLE {TABLA} ADD COLUMN {NUEVA} {TIPO}"))
            conn.commit()
            print(f"[+] {TABLA}.{NUEVA} creada (no existía {VIEJA})")
    except Exception as e:
        print(f"[ERROR] rename {VIEJA} -> {NUEVA}: {e}")
        sys.exit(1)
    print("\nMigracion numero_orden_erp completada.")
