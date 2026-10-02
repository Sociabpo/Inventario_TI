r"""
Migración: APLICABILIDAD por empresa en servidores (ADITIVO).

Añade (idempotente):
  - servidores.aplica_todas   TINYINT(1) NOT NULL DEFAULT 0
  - tabla servidor_empresas (servidor_id, empresa_id)  — empresas específicas a las que aplica

empresa_id NO se toca: sigue siendo la empresa OWNER/creadora (uniqueness, display, stats).

Backfill (Opción 1 — PRESERVAR visibilidad exacta):
  - Todos los servidores existentes quedan con aplica_todas=0 (el DEFAULT del ADD COLUMN
    ya lo aplica a las filas existentes).
  - Se siembra servidor_empresas con el empresa_id actual de cada servidor.
  => Post-migración el sistema se ve IDÉNTICO a ahora: cada servidor aplica solo a la
     empresa a la que aplica hoy. Nada cambia hasta que alguien edite un servidor.

INVARIANTE (la aplica la app en create/edit): si aplica_todas=0, la owner (empresa_id)
siempre está en servidor_empresas.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_servidores_aplicabilidad.py
"""
import sys, os, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text


def _tiene_columna(conn, tabla, col):
    return conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.columns "
        "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"
    ), {"t": tabla, "c": col}).scalar()


def _tiene_tabla(conn, tabla):
    return conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_schema = DATABASE() AND table_name = :t"
    ), {"t": tabla}).scalar()


def migrate():
    with engine.begin() as conn:
        # 1) columna aplica_todas (DEFAULT 0 => filas existentes = 0)
        if _tiene_columna(conn, "servidores", "aplica_todas"):
            print("  [=] Columna ya existe: servidores.aplica_todas")
        else:
            conn.execute(text(
                "ALTER TABLE servidores ADD COLUMN aplica_todas TINYINT(1) NOT NULL DEFAULT 0"))
            print("  [+] Columna agregada:  servidores.aplica_todas (DEFAULT 0)")

        # 2) tabla servidor_empresas
        if _tiene_tabla(conn, "servidor_empresas"):
            print("  [=] Tabla ya existe:   servidor_empresas")
        else:
            conn.execute(text("""
                CREATE TABLE servidor_empresas (
                    id          VARCHAR(36) NOT NULL,
                    servidor_id VARCHAR(36) NOT NULL,
                    empresa_id  VARCHAR(36) NOT NULL,
                    PRIMARY KEY (id),
                    UNIQUE KEY uq_servidor_empresa_aplica (servidor_id, empresa_id),
                    KEY ix_servidor_empresas_servidor_id (servidor_id),
                    KEY ix_servidor_empresas_empresa_id (empresa_id),
                    CONSTRAINT fk_se_servidor FOREIGN KEY (servidor_id) REFERENCES servidores (id),
                    CONSTRAINT fk_se_empresa  FOREIGN KEY (empresa_id)  REFERENCES empresas (id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            print("  [+] Tabla creada:      servidor_empresas")

        # 3) Backfill idempotente: sembrar owner de cada servidor que aún no tenga fila.
        faltantes = conn.execute(text("""
            SELECT s.id, s.empresa_id FROM servidores s
            WHERE s.empresa_id IS NOT NULL AND s.empresa_id <> ''
              AND NOT EXISTS (
                  SELECT 1 FROM servidor_empresas se
                  WHERE se.servidor_id = s.id AND se.empresa_id = s.empresa_id)
        """)).fetchall()
        for sid, eid in faltantes:
            conn.execute(text(
                "INSERT INTO servidor_empresas (id, servidor_id, empresa_id) "
                "VALUES (:id, :sid, :eid)"),
                {"id": str(uuid.uuid4()), "sid": sid, "eid": eid})
        print(f"  [+] Backfill owner sembrado en servidor_empresas: {len(faltantes)} fila(s)")

    print("\nMigracion servidores-aplicabilidad completada.")


if __name__ == "__main__":
    migrate()
