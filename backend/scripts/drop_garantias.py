r"""
Migración: elimina el módulo FULL de garantías (huérfano/nunca terminado).

Hace (todo idempotente, guardado por comprobaciones de existencia):
  1. DROP TABLE garantias.
  2. DROP COLUMN cambios_estado.garantia_id (columna muerta, sin FK, nunca poblada).
  3. Elimina el permiso 'compras.gestionar_garantias': sus filas en rol_permisos
     y la fila en permisos.

NO toca la garantía SIMPLE (activos.garantia_meses/garantia_fin, accesorios idem).
Solo esquema/permisos — sin datos de negocio.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/drop_garantias.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

PERM = "compras.gestionar_garantias"


def _tabla_existe(conn, tabla) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t"
    ), {"t": tabla}).scalar())


def _columna_existe(conn, tabla, col) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": tabla, "c": col}).scalar())


with engine.connect() as conn:
    try:
        # 1) Tabla garantias
        if _tabla_existe(conn, "garantias"):
            conn.execute(text("DROP TABLE garantias"))
            conn.commit()
            print("[+] Tabla 'garantias' eliminada")
        else:
            print("[=] Tabla 'garantias' no existe - omitido")

        # 2) Columna muerta cambios_estado.garantia_id
        if _columna_existe(conn, "cambios_estado", "garantia_id"):
            conn.execute(text("ALTER TABLE cambios_estado DROP COLUMN garantia_id"))
            conn.commit()
            print("[+] Columna 'cambios_estado.garantia_id' eliminada")
        else:
            print("[=] Columna 'cambios_estado.garantia_id' no existe - omitido")

        # 3) Permiso compras.gestionar_garantias (asociaciones + definición)
        if _tabla_existe(conn, "permisos"):
            pid = conn.execute(text(
                "SELECT id FROM permisos WHERE codigo = :c"), {"c": PERM}).scalar()
            if pid:
                if _tabla_existe(conn, "rol_permisos"):
                    r = conn.execute(text(
                        "DELETE FROM rol_permisos WHERE permiso_id = :pid"), {"pid": pid})
                    print(f"[+] {r.rowcount} asociacion(es) rol-permiso eliminadas")
                conn.execute(text("DELETE FROM permisos WHERE id = :pid"), {"pid": pid})
                conn.commit()
                print(f"[+] Permiso '{PERM}' eliminado")
            else:
                print(f"[=] Permiso '{PERM}' no existe - omitido")

        print("\nMigracion drop_garantias completada.")
    except Exception as e:
        conn.rollback()
        print(f"[ERROR] {e}")
        sys.exit(1)
