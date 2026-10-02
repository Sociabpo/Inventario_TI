"""
Migration: add firmada and fecha_firma columns to actas_entrega.
Run once: venv\Scripts\python.exe migrate_acta_firmada.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    try:
        conn.execute(text(
            "ALTER TABLE actas_entrega "
            "ADD COLUMN firmada BOOLEAN NOT NULL DEFAULT FALSE, "
            "ADD COLUMN fecha_firma DATETIME NULL"
        ))
        conn.commit()
        print("Migration applied: firmada, fecha_firma added to actas_entrega")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("Already applied — columns exist.")
        else:
            print(f"Error: {e}")
            sys.exit(1)
