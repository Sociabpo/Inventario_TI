r"""
Migración: agrega la columna `codigo_contable` a activos.
Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_codigo_contable.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE activos ADD COLUMN codigo_contable VARCHAR(50) NULL"))
        conn.commit()
        print("[+] Columna agregada: activos.codigo_contable")
    except Exception as e:
        msg = str(e).lower()
        if "duplicate column" in msg or "already exists" in msg or "1060" in msg:
            print("[=] Ya existe — columna codigo_contable")
        else:
            print(f"[ERROR] {e}")
            sys.exit(1)
    print("\nMigración codigo_contable completada.")
