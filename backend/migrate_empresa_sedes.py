r"""
Migration: add `sedes` column (JSON array de nombres de sede) to empresas.
Run once: venv\Scripts\python.exe migrate_empresa_sedes.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text(
            "ALTER TABLE empresas ADD COLUMN sedes TEXT NULL"
        ))
        conn.commit()
        print("Migration applied: sedes added to empresas")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("Already applied — column exists.")
        else:
            print(f"Error: {e}")
            sys.exit(1)
