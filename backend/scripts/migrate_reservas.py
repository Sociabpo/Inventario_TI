r"""
Migración: sistema de reservas (reservas + reserva_items).
Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_reservas.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLA_RESERVAS = """
CREATE TABLE IF NOT EXISTS reservas (
    id VARCHAR(36) PRIMARY KEY,
    numero_alta VARCHAR(100) NOT NULL,
    descripcion TEXT NULL,
    empresa_id VARCHAR(36) NOT NULL,
    fecha_limite DATE NOT NULL,
    estado VARCHAR(20) DEFAULT 'activa',
    creado_por_id VARCHAR(36) NOT NULL,
    created_at DATETIME DEFAULT NOW(),
    fecha_cierre DATETIME NULL,
    FOREIGN KEY (empresa_id) REFERENCES empresas(id)
)
"""

TABLA_RESERVA_ITEMS = """
CREATE TABLE IF NOT EXISTS reserva_items (
    id VARCHAR(36) PRIMARY KEY,
    reserva_id VARCHAR(36) NOT NULL,
    tipo_recurso VARCHAR(20) NOT NULL,
    recurso_id VARCHAR(36) NOT NULL,
    placa VARCHAR(50) NULL,
    estado VARCHAR(20) DEFAULT 'reservado',
    FOREIGN KEY (reserva_id) REFERENCES reservas(id)
)
"""

with engine.connect() as conn:
    for nombre, ddl in [("reservas", TABLA_RESERVAS), ("reserva_items", TABLA_RESERVA_ITEMS)]:
        try:
            conn.execute(text(ddl)); conn.commit()
            print(f"[+] Tabla '{nombre}' lista")
        except Exception as e:
            print(f"[ERROR] tabla {nombre}: {e}"); sys.exit(1)
    print("\nMigración de reservas completada.")
