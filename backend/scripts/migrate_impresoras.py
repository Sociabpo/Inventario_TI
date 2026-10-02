r"""
Migración: módulo de Impresoras (Fase 1 — inventario).

Crea la tabla `impresoras` (idempotente, CREATE TABLE IF NOT EXISTS) con FKs a
empresas, catalogos (sede + ciudad) y proveedores, e índices. Solo esquema.

El serial NO lleva UNIQUE en BD (la unicidad se valida en la app entre impresoras
ACTIVAS de la empresa; un UNIQUE de BD contaría filas soft-deleted y chocaría con
el reemplazo-con-historial de la Fase 2).

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_impresoras.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLAS = {
    "impresoras": """
        CREATE TABLE IF NOT EXISTS impresoras (
            id VARCHAR(36) PRIMARY KEY,
            empresa_id VARCHAR(36) NOT NULL,
            sede_catalogo_id VARCHAR(36) NULL,
            ciudad_catalogo_id VARCHAR(36) NULL,
            dependencia VARCHAR(150) NULL,
            modelo VARCHAR(150) NULL,
            tipo VARCHAR(20) NULL,
            serial VARCHAR(100) NULL,
            ip VARCHAR(45) NULL,
            estado VARCHAR(20) NOT NULL DEFAULT 'en_servicio',
            correo_escaneo VARCHAR(150) NULL,
            proveedor_id VARCHAR(36) NULL,
            activo TINYINT(1) NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT NOW(),
            created_by VARCHAR(36) NULL,
            INDEX ix_impresoras_empresa (empresa_id),
            INDEX ix_impresoras_sede (sede_catalogo_id),
            INDEX ix_impresoras_ciudad (ciudad_catalogo_id),
            INDEX ix_impresoras_proveedor (proveedor_id),
            INDEX ix_impresoras_serial (serial),
            INDEX ix_impresoras_activo (activo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (sede_catalogo_id) REFERENCES catalogos(id),
            FOREIGN KEY (ciudad_catalogo_id) REFERENCES catalogos(id),
            FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
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
            print(f"  [=] Tabla ya existia: {nombre}" if existe else f"  [+] Tabla creada:     {nombre}")
    print("\nMigracion de Impresoras completada.")


if __name__ == "__main__":
    migrate()
