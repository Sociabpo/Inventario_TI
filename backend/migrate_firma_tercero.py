"""
Migration: add entrega_por_tercero, nombre_tercero, relacion_tercero to firma_tokens.
Run once: ..\venv\Scripts\python.exe migrate_firma_tercero.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import engine
from sqlalchemy import text

COLUMNS = [
    "ALTER TABLE firma_tokens ADD COLUMN entrega_por_tercero BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE firma_tokens ADD COLUMN nombre_tercero VARCHAR(150) NULL",
    "ALTER TABLE firma_tokens ADD COLUMN relacion_tercero VARCHAR(150) NULL",
]

with engine.connect() as conn:
    for sql in COLUMNS:
        col = sql.split("ADD COLUMN ")[1].split(" ")[0]
        try:
            conn.execute(text(sql))
            conn.commit()
            print(f"  Added: {col}")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print(f"  Already exists: {col}")
            else:
                print(f"  Error on {col}: {e}")
                sys.exit(1)

print("Migration complete.")
