r"""
Migración: campo de HOSTING en servidores.

Añade a `servidores` (idempotente, information_schema-guarded ADD COLUMN):
  - ubicacion_catalogo_id  VARCHAR(36) NULL   -> FK lógica a catalogos.id (categoria='hosting', GLOBAL)

La "Ubicación" del servidor pasa a leer del catálogo GLOBAL categoria='hosting'
(AWS / On-premise / Triara…). NO confundir con el catálogo 'ubicacion' (activos, per-empresa),
que queda intacto. El antiguo servidores.ubicacion_id (FK a la tabla huérfana `ubicaciones`)
se deja inerte: 0 servidores lo usan, no requiere migración de datos.
Solo esquema.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_servidores_hosting.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

COLUMNAS = [
    ("ubicacion_catalogo_id", "ALTER TABLE servidores ADD COLUMN ubicacion_catalogo_id VARCHAR(36) NULL"),
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
    print("\nMigracion servidores-hosting completada.")


if __name__ == "__main__":
    migrate()
