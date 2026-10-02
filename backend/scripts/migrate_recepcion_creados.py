r"""
Migración: tabla recepcion_items_creados.

Registra cada unidad de inventario (activo/accesorio) creada a partir de un ítem
de recepción, para soportar cantidades (un ítem con cantidad_recibida=N genera N
unidades, cada una con su propia fila).

Idempotente: usa CREATE TABLE IF NOT EXISTS.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_recepcion_creados.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS recepcion_items_creados (
    id                VARCHAR(36) PRIMARY KEY,
    recepcion_item_id VARCHAR(36) NOT NULL,
    tipo_recurso      VARCHAR(20) NOT NULL,
    recurso_id        VARCHAR(36) NOT NULL,
    placa             VARCHAR(50) NULL,
    created_at        DATETIME DEFAULT NOW(),
    INDEX ix_ric_recepcion_item (recepcion_item_id),
    FOREIGN KEY (recepcion_item_id) REFERENCES recepcion_items(id)
)
"""

with engine.connect() as conn:
    try:
        conn.execute(text(DDL))
        conn.commit()
        print("[+] Tabla 'recepcion_items_creados' lista")
    except Exception as e:
        print(f"[ERROR] recepcion_items_creados: {e}")
        sys.exit(1)
    print("Migración de recepcion_items_creados completada.")
