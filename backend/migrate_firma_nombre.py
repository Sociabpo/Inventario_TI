"""
Migration: add nombre_firmante to firma_tokens.
Run once: venv\Scripts\python.exe migrate_firma_nombre.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text(
            "ALTER TABLE firma_tokens ADD COLUMN nombre_firmante VARCHAR(150) NULL"
        ))
        conn.commit()
        print("Migration applied: nombre_firmante added to firma_tokens")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("Already applied — column exists.")
        else:
            print(f"Error: {e}")
            sys.exit(1)
