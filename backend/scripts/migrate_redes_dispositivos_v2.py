r"""
Migración: Redes — rediseño de dispositivos como MONTAJES de activos.

El dispositivo deja de ser un inventario aparte: ahora referencia un Activo
existente (activo_id) y guarda SOLO datos de red/montaje. Se eliminan las
columnas tipo/nombre/hostname/marca/modelo (vienen del activo).

Idempotente y seguro:
  - Si `dispositivos_red` YA tiene la columna `activo_id` → ya migrada, no-op.
  - Si tiene el esquema viejo (o no existe) → DROP + CREATE con el esquema nuevo.
    (Las filas de la fase 2 son datos de prueba desechables que nunca tocaron el
    estado de ningún activo — su borrado es aprobado y no deja activos "asignado"
    huérfanos.)

Unicidad "un solo montaje ACTIVO por activo": columna generada `activo_uniq`
(= activo_id cuando activo=1, NULL si está desmontado) con índice UNIQUE. Así un
activo no puede estar montado en dos sitios a la vez, pero el historial de
montajes desmontados (activo=0 → NULL) no colisiona.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_redes_dispositivos_v2.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

DDL = """
    CREATE TABLE dispositivos_red (
        id VARCHAR(36) PRIMARY KEY,
        activo_id VARCHAR(36) NOT NULL,
        cuarto_tecnico_id VARCHAR(36) NOT NULL,
        rack_id VARCHAR(36) NULL,
        posicion_u INT NULL,
        tamano_u INT NULL DEFAULT 1,
        ubicacion_fisica VARCHAR(200) NULL,
        ip_gestion VARCHAR(45) NULL,
        num_puertos INT NULL,
        conexion VARCHAR(300) NULL,
        datos_adicionales TEXT NULL,
        activo TINYINT(1) NOT NULL DEFAULT 1,
        created_at DATETIME DEFAULT NOW(),
        created_by VARCHAR(36) NULL,
        activo_uniq VARCHAR(36) GENERATED ALWAYS AS (IF(activo = 1, activo_id, NULL)) STORED,
        INDEX ix_disp_activo (activo_id),
        INDEX ix_disp_cuarto (cuarto_tecnico_id),
        INDEX ix_disp_rack (rack_id),
        INDEX ix_disp_activo_flag (activo),
        UNIQUE KEY uq_disp_activo_montado (activo_uniq),
        FOREIGN KEY (activo_id) REFERENCES activos(id),
        FOREIGN KEY (cuarto_tecnico_id) REFERENCES cuartos_tecnicos(id),
        FOREIGN KEY (rack_id) REFERENCES racks(id)
    )
"""


def migrate():
    with engine.begin() as conn:
        tiene_tabla = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = 'dispositivos_red'"
        )).scalar()
        tiene_activo_id = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'dispositivos_red' "
            "AND column_name = 'activo_id'"
        )).scalar()

        if tiene_tabla and tiene_activo_id:
            print("  [=] dispositivos_red ya tiene el esquema nuevo (activo_id) — no-op.")
            return

        if tiene_tabla:
            conn.execute(text("DROP TABLE dispositivos_red"))
            print("  [~] Tabla vieja eliminada (datos de prueba desechables).")
        conn.execute(text(DDL))
        print("  [+] Tabla dispositivos_red creada con esquema de montaje (activo_id).")
    print("\nMigración de rediseño de dispositivos completada.")


if __name__ == "__main__":
    migrate()
