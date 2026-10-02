r"""
Migración: recordatorios de firma + actas anticipadas.
Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_recordatorios.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

COLS = [
    ("actas_entrega.fecha_inicio_vigencia",
     "ALTER TABLE actas_entrega ADD COLUMN fecha_inicio_vigencia DATE NULL"),
    ("actas_entrega.es_anticipada",
     "ALTER TABLE actas_entrega ADD COLUMN es_anticipada BOOLEAN NOT NULL DEFAULT FALSE"),
    ("actas_entrega.recordatorios_enviados",
     "ALTER TABLE actas_entrega ADD COLUMN recordatorios_enviados INTEGER NOT NULL DEFAULT 0"),
]

TABLA = """
CREATE TABLE IF NOT EXISTS recordatorios_firma (
    id VARCHAR(36) PRIMARY KEY,
    acta_id VARCHAR(36) NOT NULL,
    token_id VARCHAR(36) NULL,
    enviado_a VARCHAR(150) NOT NULL,
    numero_recordatorio INTEGER NOT NULL DEFAULT 1,
    fecha_envio DATETIME DEFAULT NOW(),
    escalado_admin BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT NOW(),
    FOREIGN KEY (acta_id) REFERENCES actas_entrega(id),
    FOREIGN KEY (token_id) REFERENCES firma_tokens(id)
)
"""

with engine.connect() as conn:
    for nombre, ddl in COLS:
        try:
            conn.execute(text(ddl)); conn.commit()
            print(f"[+] Columna agregada: {nombre}")
        except Exception as e:
            msg = str(e).lower()
            if any(k in msg for k in ("duplicate column", "already exists", "1060")):
                print(f"[=] Ya existe: {nombre}")
            else:
                print(f"[ERROR] {nombre}: {e}"); sys.exit(1)
    try:
        conn.execute(text(TABLA)); conn.commit()
        print("[+] Tabla 'recordatorios_firma' lista")
    except Exception as e:
        print(f"[ERROR] tabla recordatorios_firma: {e}"); sys.exit(1)
    print("\nMigración de recordatorios completada.")
