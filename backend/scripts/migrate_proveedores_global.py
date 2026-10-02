r"""
Migración: proveedores GLOBALES / transversales.

Un proveedor deja de pertenecer a una empresa: es una entidad única del sistema.
ALTER IN PLACE (no drop/recreate — la tabla es destino de 4 FKs: cotizaciones,
ordenes_compra, facturas, contratos_alquiler, que quedan intactas).

Pasos (todos idempotentes, guardados por information_schema):
  1. Normaliza nit = '' → NULL (para que UNIQUE(nit) sea seguro; NULLs no colisionan).
  2. Elimina el UNIQUE compuesto uq_proveedor_empresa_nit.
  3. Elimina la FK de empresa_id (nombre resuelto dinámicamente) y luego la columna
     empresa_id (esto también elimina su índice ix_proveedores_empresa_id).
  4. Agrega UNIQUE(nit) → uq_proveedor_nit.

Las 7 filas de prueba sobreviven (pierden empresa_id); el backfill modulos queda intacto.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_proveedores_global.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLA = "proveedores"


def _existe_columna(conn, col):
    return conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema=DATABASE() AND table_name=:t AND column_name=:c"
    ), {"t": TABLA, "c": col}).scalar()


def _existe_indice(conn, idx):
    return conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.statistics "
        "WHERE table_schema=DATABASE() AND table_name=:t AND index_name=:i"
    ), {"t": TABLA, "i": idx}).scalar()


def _fk_de_empresa(conn):
    """Nombre de la FK sobre empresa_id (auto-nombrada por MySQL), o None."""
    return conn.execute(text(
        "SELECT constraint_name FROM information_schema.key_column_usage "
        "WHERE table_schema=DATABASE() AND table_name=:t AND column_name='empresa_id' "
        "AND referenced_table_name IS NOT NULL LIMIT 1"
    ), {"t": TABLA}).scalar()


def migrate():
    with engine.begin() as conn:
        # 1. Normalizar nit '' -> NULL
        res = conn.execute(text(f"UPDATE {TABLA} SET nit = NULL WHERE nit = ''"))
        print(f"  [1] nit '' -> NULL: {res.rowcount} fila(s)")

        # 2. Drop unique compuesto
        if _existe_indice(conn, "uq_proveedor_empresa_nit"):
            conn.execute(text(f"ALTER TABLE {TABLA} DROP INDEX uq_proveedor_empresa_nit"))
            print("  [2] UNIQUE uq_proveedor_empresa_nit eliminado")
        else:
            print("  [2] uq_proveedor_empresa_nit ya no existe — omitido")

        # 3. Drop FK + columna empresa_id
        if _existe_columna(conn, "empresa_id"):
            fk = _fk_de_empresa(conn)
            if fk:
                conn.execute(text(f"ALTER TABLE {TABLA} DROP FOREIGN KEY {fk}"))
                print(f"  [3a] FK {fk} (empresa_id) eliminada")
            conn.execute(text(f"ALTER TABLE {TABLA} DROP COLUMN empresa_id"))
            print("  [3b] columna empresa_id eliminada")
        else:
            print("  [3] empresa_id ya no existe — omitido")

        # 4. Add unique(nit)
        if _existe_indice(conn, "uq_proveedor_nit"):
            print("  [4] uq_proveedor_nit ya existe — omitido")
        else:
            conn.execute(text(f"ALTER TABLE {TABLA} ADD CONSTRAINT uq_proveedor_nit UNIQUE (nit)"))
            print("  [4] UNIQUE(nit) uq_proveedor_nit agregado")
    print("\nMigración proveedores-global completada.")


if __name__ == "__main__":
    migrate()
