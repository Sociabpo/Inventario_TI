r"""
Migración: módulo de Mantenimiento Preventivo (Fase 1 — esquema completo).

Crea las 5 tablas del módulo (idempotente, CREATE TABLE IF NOT EXISTS). En la
Fase 1 solo los PLANES tienen endpoints; las tablas de TAREAS se crean ya para
evitar migraciones futuras. Solo esquema — sin datos.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_mantenimiento.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

TABLAS = {
    "planes_mantenimiento": """
        CREATE TABLE IF NOT EXISTS planes_mantenimiento (
            id VARCHAR(36) PRIMARY KEY,
            empresa_id VARCHAR(36) NOT NULL,
            nombre VARCHAR(150) NOT NULL,
            descripcion TEXT NULL,
            periodicidad_meses INT DEFAULT 12,
            activo TINYINT(1) DEFAULT 1,
            codigo_formato VARCHAR(30) DEFAULT 'FTIN09',
            version_formato VARCHAR(20) DEFAULT '1.1',
            fecha_emision_formato DATE NULL,
            clasificacion VARCHAR(50) DEFAULT 'Interno',
            proceso VARCHAR(50) DEFAULT 'Servicio',
            created_at DATETIME DEFAULT NOW(),
            created_by VARCHAR(36) NULL,
            INDEX ix_planes_mant_empresa (empresa_id),
            INDEX ix_planes_mant_activo (activo),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id)
        )
    """,
    "plan_tipo_activo": """
        CREATE TABLE IF NOT EXISTS plan_tipo_activo (
            id VARCHAR(36) PRIMARY KEY,
            plan_id VARCHAR(36) NOT NULL,
            tipo_activo VARCHAR(50) NOT NULL,
            INDEX ix_plan_tipo_plan (plan_id),
            FOREIGN KEY (plan_id) REFERENCES planes_mantenimiento(id)
        )
    """,
    "plan_checklist_items": """
        CREATE TABLE IF NOT EXISTS plan_checklist_items (
            id VARCHAR(36) PRIMARY KEY,
            plan_id VARCHAR(36) NOT NULL,
            seccion VARCHAR(20) NOT NULL,
            tipo_item VARCHAR(10) NOT NULL,
            texto VARCHAR(300) NOT NULL,
            orden INT DEFAULT 0,
            INDEX ix_plan_chk_plan (plan_id),
            FOREIGN KEY (plan_id) REFERENCES planes_mantenimiento(id)
        )
    """,
    "tareas_mantenimiento": """
        CREATE TABLE IF NOT EXISTS tareas_mantenimiento (
            id VARCHAR(36) PRIMARY KEY,
            empresa_id VARCHAR(36) NOT NULL,
            activo_id VARCHAR(36) NOT NULL,
            plan_id VARCHAR(36) NOT NULL,
            tecnico_id VARCHAR(36) NULL,
            estado VARCHAR(20) DEFAULT 'pendiente',
            fecha_programada DATE NULL,
            fecha_inicio_ejec DATETIME NULL,
            fecha_fin_ejec DATETIME NULL,
            estado_activo_previo VARCHAR(30) NULL,
            usuario_previo VARCHAR(36) NULL,
            observaciones TEXT NULL,
            motivo_cancelacion TEXT NULL,
            url_acta_pdf VARCHAR(300) NULL,
            created_at DATETIME DEFAULT NOW(),
            created_by VARCHAR(36) NULL,
            INDEX ix_tareas_mant_empresa (empresa_id),
            INDEX ix_tareas_mant_activo (activo_id),
            INDEX ix_tareas_mant_estado (estado),
            FOREIGN KEY (empresa_id) REFERENCES empresas(id),
            FOREIGN KEY (activo_id) REFERENCES activos(id),
            FOREIGN KEY (plan_id) REFERENCES planes_mantenimiento(id),
            FOREIGN KEY (tecnico_id) REFERENCES usuarios_sistema(id)
        )
    """,
    "tarea_checklist_items": """
        CREATE TABLE IF NOT EXISTS tarea_checklist_items (
            id VARCHAR(36) PRIMARY KEY,
            tarea_id VARCHAR(36) NOT NULL,
            seccion VARCHAR(20) NOT NULL,
            tipo_item VARCHAR(10) NOT NULL,
            texto VARCHAR(300) NOT NULL,
            orden INT DEFAULT 0,
            realizado TINYINT(1) NULL,
            valor_dato VARCHAR(200) NULL,
            INDEX ix_tarea_chk_tarea (tarea_id),
            FOREIGN KEY (tarea_id) REFERENCES tareas_mantenimiento(id)
        )
    """,
}

with engine.connect() as conn:
    for nombre, ddl in TABLAS.items():
        try:
            conn.execute(text(ddl))
            conn.commit()
            print(f"[+] Tabla '{nombre}' lista")
        except Exception as e:
            print(f"[ERROR] tabla {nombre}: {e}")
            sys.exit(1)
    print("\nMigracion de mantenimiento (Fase 1) completada.")
