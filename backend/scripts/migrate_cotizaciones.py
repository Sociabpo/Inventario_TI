r"""
Migración: tabla `cotizaciones` (etapa de cotizaciones en el flujo de compras).

Una solicitud tiene múltiples cotizaciones; cada una referencia un proveedor,
un valor, una fecha y UN adjunto (guardado en disco bajo storage/cotizaciones/;
la BD solo guarda la referencia). Una se marca como ganadora (es_ganadora).

Idempotente (CREATE TABLE IF NOT EXISTS). Solo esquema — sin datos.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_cotizaciones.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

DDL = """
CREATE TABLE IF NOT EXISTS cotizaciones (
    id             VARCHAR(36) PRIMARY KEY,
    solicitud_id   VARCHAR(36) NOT NULL,
    proveedor_id   VARCHAR(36) NOT NULL,
    referencia     VARCHAR(100) NULL,
    valor_total    DECIMAL(14,2) NULL,
    fecha          DATE NULL,
    observaciones  TEXT NULL,
    es_ganadora    TINYINT(1) DEFAULT 0,
    archivo_nombre VARCHAR(255) NULL,
    archivo_path   VARCHAR(400) NULL,
    archivo_tipo   VARCHAR(100) NULL,
    created_at     DATETIME DEFAULT NOW(),
    INDEX ix_cotizaciones_solicitud_id (solicitud_id),
    INDEX ix_cotizaciones_es_ganadora (es_ganadora),
    FOREIGN KEY (solicitud_id) REFERENCES solicitudes_compra(id),
    FOREIGN KEY (proveedor_id) REFERENCES proveedores(id)
)
"""

with engine.connect() as conn:
    try:
        conn.execute(text(DDL))
        conn.commit()
        print("[+] Tabla 'cotizaciones' lista")
    except Exception as e:
        print(f"[ERROR] tabla cotizaciones: {e}")
        sys.exit(1)
    print("\nMigracion de cotizaciones completada.")
