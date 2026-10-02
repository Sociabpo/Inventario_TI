r"""
Migración: catálogo COMPARTIDO de proveedores — columna `modulos`.

Añade `modulos` (TEXT, JSON array de strings, ej. ["compras","impresoras"]) a la
tabla `proveedores`, para indicar a qué módulos aplica cada proveedor. Mismo patrón
que empresas.sedes. Se comparte con el módulo de Impresoras (y compras).

Idempotente:
  - ADD COLUMN guardado por information_schema (no-op si ya existe).
  - BACKFILL: todas las filas existentes son proveedores de compras → se marcan
    con modulos = ["compras"] para que compras las siga viendo. Solo rellena filas
    con modulos NULL/'' (idempotente: re-correr no cambia nada).

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_proveedores_modulos.py
"""
import sys, os, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text


def migrate():
    with engine.begin() as conn:
        existe = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'proveedores' "
            "AND column_name = 'modulos'"
        )).scalar()
        if existe:
            print("  [=] Columna modulos ya existe — no se agrega.")
        else:
            conn.execute(text("ALTER TABLE proveedores ADD COLUMN modulos TEXT NULL"))
            print("  [+] Columna modulos agregada a proveedores.")

        # Backfill: filas sin modulos → ["compras"]
        valor = json.dumps(["compras"])
        res = conn.execute(
            text("UPDATE proveedores SET modulos = :v WHERE modulos IS NULL OR modulos = ''"),
            {"v": valor},
        )
        print(f"  [+] Filas backfilled a ['compras']: {res.rowcount}")
    print("\nMigración proveedores.modulos completada.")


if __name__ == "__main__":
    migrate()
