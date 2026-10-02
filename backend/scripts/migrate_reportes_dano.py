r"""
Migración: Impresoras Fase 3 — reportes de daño (trazabilidad).

Crea la tabla `reportes_dano_impresora` (idempotente, CREATE TABLE IF NOT EXISTS)
+ FKs a impresoras y empresas + índices. Solo esquema. Las imágenes NO se
almacenan: solo num_imagenes (conteo).

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_reportes_dano.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLAS = {
    "reportes_dano_impresora": """
        CREATE TABLE IF NOT EXISTS reportes_dano_impresora (
            id VARCHAR(36) PRIMARY KEY,
            impresora_id VARCHAR(36) NOT NULL,
            empresa_id VARCHAR(36) NOT NULL,
            descripcion_dano TEXT NULL,
            asunto VARCHAR(300) NULL,
            cuerpo TEXT NULL,
            destinatarios TEXT NULL,
            cc TEXT NULL,
            num_imagenes INT NOT NULL DEFAULT 0,
            generado_por VARCHAR(36) NULL,
            generado_por_email VARCHAR(150) NULL,
            created_at DATETIME DEFAULT NOW(),
            INDEX ix_repdano_impresora (impresora_id),
            INDEX ix_repdano_empresa (empresa_id),
            FOREIGN KEY (impresora_id) REFERENCES impresoras(id),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
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
    print("\nMigracion reportes de dano completada.")


if __name__ == "__main__":
    migrate()
