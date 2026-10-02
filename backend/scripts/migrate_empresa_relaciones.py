r"""
Migración: tabla empresa_relaciones (relaciones bidireccionales entre empresas).

Una fila canónica por relación (empresa_a_id < empresa_b_id por string).
Idempotente: CREATE TABLE IF NOT EXISTS. Solo esquema — sin inserción de datos.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_empresa_relaciones.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS empresa_relaciones (
    id           VARCHAR(36) PRIMARY KEY,
    empresa_a_id VARCHAR(36) NOT NULL,
    empresa_b_id VARCHAR(36) NOT NULL,
    created_at   DATETIME DEFAULT NOW(),
    CONSTRAINT uq_empresa_relacion UNIQUE (empresa_a_id, empresa_b_id),
    INDEX ix_emp_rel_a (empresa_a_id),
    INDEX ix_emp_rel_b (empresa_b_id),
    FOREIGN KEY (empresa_a_id) REFERENCES empresas(id),
    FOREIGN KEY (empresa_b_id) REFERENCES empresas(id)
)
"""

with engine.connect() as conn:
    try:
        conn.execute(text(DDL))
        conn.commit()
        print("[+] Tabla 'empresa_relaciones' lista")
    except Exception as e:
        print(f"[ERROR] empresa_relaciones: {e}")
        sys.exit(1)
    print("Migracion de empresa_relaciones completada.")
