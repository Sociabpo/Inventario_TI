r"""
Migración: tabla de catálogos (listas desplegables gestionables).
Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_catalogos.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

DDL = """
CREATE TABLE catalogos (
    id VARCHAR(36) PRIMARY KEY,
    categoria VARCHAR(50) NOT NULL,
    valor VARCHAR(150) NOT NULL,
    descripcion VARCHAR(300) NULL,
    empresa_id VARCHAR(36) NULL,
    activo BOOLEAN NOT NULL DEFAULT TRUE,
    orden INTEGER DEFAULT 0,
    color VARCHAR(7) NULL,
    icono VARCHAR(50) NULL,
    created_at DATETIME DEFAULT NOW(),
    updated_at DATETIME DEFAULT NOW() ON UPDATE NOW(),
    CONSTRAINT uq_catalogo_categoria_valor_empresa UNIQUE (categoria, valor, empresa_id),
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
)
"""

with engine.connect() as conn:
    try:
        conn.execute(text(DDL))
        conn.commit()
        print("[+] Tabla 'catalogos' creada")
    except Exception as e:
        msg = str(e).lower()
        if "already exists" in msg or "1050" in msg:
            print("[=] La tabla 'catalogos' ya existe")
        else:
            print(f"[ERROR] {e}")
            sys.exit(1)
    print("\nMigración de catálogos completada.")
