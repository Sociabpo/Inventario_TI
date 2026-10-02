r"""
Migración: módulo de cambio de estado (cambios_estado + bajas_activos).
Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_cambio_estado.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLAS = {
    "cambios_estado": """
        CREATE TABLE IF NOT EXISTS cambios_estado (
            id VARCHAR(36) PRIMARY KEY,
            tipo_recurso VARCHAR(20) NOT NULL,
            recurso_id VARCHAR(36) NOT NULL,
            placa VARCHAR(50) NULL,
            empresa_id VARCHAR(36) NOT NULL,
            estado_anterior VARCHAR(30) NOT NULL,
            estado_nuevo VARCHAR(30) NOT NULL,
            ubicacion VARCHAR(100) NULL,
            tipo_mantenimiento VARCHAR(20) NULL,
            cubierto_garantia BOOLEAN DEFAULT FALSE,
            cubre_garantia VARCHAR(20) NULL,
            garantia_id VARCHAR(36) NULL,
            tiempo_estimado_dias INTEGER NULL,
            responsable_mant VARCHAR(150) NULL,
            descripcion TEXT NULL,
            resultado_mant VARCHAR(30) NULL,
            costo_real NUMERIC(14,2) NULL,
            genero_acta BOOLEAN DEFAULT FALSE,
            acta_id VARCHAR(36) NULL,
            realizado_por_id VARCHAR(36) NOT NULL,
            fecha DATETIME DEFAULT NOW(),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    """,
    "bajas_activos": """
        CREATE TABLE IF NOT EXISTS bajas_activos (
            id VARCHAR(36) PRIMARY KEY,
            numero_baja VARCHAR(20) NOT NULL,
            tipo_recurso VARCHAR(20) NOT NULL,
            recurso_id VARCHAR(36) NOT NULL,
            placa VARCHAR(50) NULL,
            empresa_id VARCHAR(36) NOT NULL,
            tipo_activo VARCHAR(50) NULL,
            marca VARCHAR(100) NULL,
            modelo VARCHAR(100) NULL,
            serial VARCHAR(100) NULL,
            fecha_compra DATE NULL,
            costo_original NUMERIC(14,2) NULL,
            motivo VARCHAR(30) NOT NULL,
            justificacion TEXT NOT NULL,
            estado_fisico TEXT NULL,
            valor_venta NUMERIC(14,2) NULL,
            comprador VARCHAR(200) NULL,
            entidad_receptora VARCHAR(200) NULL,
            metodo_destruccion VARCHAR(200) NULL,
            estado_aprobacion VARCHAR(20) DEFAULT 'pendiente',
            solicitado_por_id VARCHAR(36) NOT NULL,
            aprobado_por_id VARCHAR(36) NULL,
            fecha_solicitud DATETIME DEFAULT NOW(),
            fecha_aprobacion DATETIME NULL,
            observaciones_aprobador TEXT NULL,
            url_pdf VARCHAR(300) NULL,
            created_at DATETIME DEFAULT NOW(),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    """,
}

with engine.connect() as conn:
    for nombre, ddl in TABLAS.items():
        try:
            conn.execute(text(ddl)); conn.commit()
            print(f"[+] Tabla lista: {nombre}")
        except Exception as e:
            print(f"[ERROR] {nombre}: {e}"); sys.exit(1)
    print("\nMigración de cambio de estado completada.")
