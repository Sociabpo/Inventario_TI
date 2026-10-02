r"""
Migración: módulo de Redes (Fase 1 — esquema).

Crea las 2 tablas del módulo (idempotente, CREATE TABLE IF NOT EXISTS):
  - cuartos_tecnicos : cuarto técnico (empresa + sede) — nivel 1
  - racks            : racks dentro de un cuarto — nivel 2

Los dispositivos son fase 2 (no se crean aquí), pero `racks` queda diseñado para
que una futura tabla de dispositivos haga FK a racks.id sin migraciones extra.
Solo esquema — sin datos.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_redes.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLAS = {
    "cuartos_tecnicos": """
        CREATE TABLE IF NOT EXISTS cuartos_tecnicos (
            id VARCHAR(36) PRIMARY KEY,
            empresa_id VARCHAR(36) NOT NULL,
            sede_catalogo_id VARCHAR(36) NOT NULL,
            identificador VARCHAR(100) NOT NULL,
            nombre VARCHAR(150) NULL,
            descripcion TEXT NULL,
            ubicacion_detalle VARCHAR(200) NULL,
            activo TINYINT(1) NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT NOW(),
            created_by VARCHAR(36) NULL,
            INDEX ix_cuartos_empresa (empresa_id),
            INDEX ix_cuartos_sede (sede_catalogo_id),
            INDEX ix_cuartos_activo (activo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (sede_catalogo_id) REFERENCES catalogos(id)
        )
    """,
    "racks": """
        CREATE TABLE IF NOT EXISTS racks (
            id VARCHAR(36) PRIMARY KEY,
            cuarto_tecnico_id VARCHAR(36) NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            capacidad_u INT NOT NULL DEFAULT 42,
            descripcion VARCHAR(300) NULL,
            orden INT NULL DEFAULT 0,
            activo TINYINT(1) NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT NOW(),
            created_by VARCHAR(36) NULL,
            INDEX ix_racks_cuarto (cuarto_tecnico_id),
            INDEX ix_racks_activo (activo),
            FOREIGN KEY (cuarto_tecnico_id) REFERENCES cuartos_tecnicos(id)
        )
    """,
}


def migrate():
    with engine.begin() as conn:
        for nombre, ddl in TABLAS.items():
            existe = conn.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_schema = DATABASE() AND table_name = :t"
            ), {"t": nombre}).scalar()
            conn.execute(text(ddl))
            if existe:
                print(f"  [=] Tabla ya existía: {nombre}")
            else:
                print(f"  [+] Tabla creada:     {nombre}")
    print("\nMigración de Redes completada.")


if __name__ == "__main__":
    migrate()
