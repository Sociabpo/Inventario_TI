r"""
Migración: módulo de Redes — Fase 2 (dispositivos de red).

Crea la tabla `dispositivos_red` (idempotente, CREATE TABLE IF NOT EXISTS) con
FKs a cuartos_tecnicos (requerida) y racks (nullable = fuera de rack) e índices.
Solo esquema — sin datos.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_redes_dispositivos.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLAS = {
    "dispositivos_red": """
        CREATE TABLE IF NOT EXISTS dispositivos_red (
            id VARCHAR(36) PRIMARY KEY,
            cuarto_tecnico_id VARCHAR(36) NOT NULL,
            rack_id VARCHAR(36) NULL,
            posicion_u INT NULL,
            tamano_u INT NULL DEFAULT 1,
            ubicacion_fisica VARCHAR(200) NULL,
            tipo VARCHAR(100) NULL,
            nombre VARCHAR(150) NOT NULL,
            hostname VARCHAR(150) NOT NULL,
            marca VARCHAR(100) NULL,
            modelo VARCHAR(100) NULL,
            ip_gestion VARCHAR(45) NULL,
            num_puertos INT NULL,
            conexion VARCHAR(300) NULL,
            datos_adicionales TEXT NULL,
            activo TINYINT(1) NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT NOW(),
            created_by VARCHAR(36) NULL,
            INDEX ix_disp_cuarto (cuarto_tecnico_id),
            INDEX ix_disp_rack (rack_id),
            INDEX ix_disp_activo (activo),
            FOREIGN KEY (cuarto_tecnico_id) REFERENCES cuartos_tecnicos(id),
            FOREIGN KEY (rack_id) REFERENCES racks(id)
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
    print("\nMigración de Redes (dispositivos) completada.")


if __name__ == "__main__":
    migrate()
