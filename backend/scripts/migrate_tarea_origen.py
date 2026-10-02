r"""
Migración: columna 'origen' en tareas_mantenimiento (de dónde nació la tarea).
Idempotente y solo-esquema. Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_tarea_origen.py

Valores: planificacion | devolucion | adhoc. Las filas previas al cambio se
rellenan con 'planificacion' (que es lo que casi todas eran).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    existe = conn.execute(text(
        """SELECT COUNT(*) FROM information_schema.columns
           WHERE table_schema = DATABASE()
             AND table_name = 'tareas_mantenimiento'
             AND column_name = 'origen'"""
    )).scalar()

    if existe:
        print("[=] La columna 'origen' ya existe — nada que hacer")
    else:
        conn.execute(text(
            "ALTER TABLE tareas_mantenimiento "
            "ADD COLUMN origen VARCHAR(20) DEFAULT 'planificacion'"
        ))
        conn.commit()
        print("[+] Columna 'origen' agregada")

    # Backfill defensivo (por si quedaran NULL de un ADD previo sin default)
    actualizadas = conn.execute(text(
        "UPDATE tareas_mantenimiento SET origen = 'planificacion' WHERE origen IS NULL"
    )).rowcount
    conn.commit()
    print(f"[+] Filas backfilled a 'planificacion': {actualizadas}")

    # Índice (idempotente)
    idx = conn.execute(text(
        """SELECT COUNT(*) FROM information_schema.statistics
           WHERE table_schema = DATABASE()
             AND table_name = 'tareas_mantenimiento'
             AND index_name = 'ix_tareas_mantenimiento_origen'"""
    )).scalar()
    if not idx:
        conn.execute(text(
            "CREATE INDEX ix_tareas_mantenimiento_origen "
            "ON tareas_mantenimiento (origen)"
        ))
        conn.commit()
        print("[+] Índice ix_tareas_mantenimiento_origen creado")
    else:
        print("[=] Índice de 'origen' ya existe")

print("[OK] Migración de 'origen' completada")
