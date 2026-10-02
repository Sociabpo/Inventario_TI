"""Agrega columna unidad_negocio a la tabla usuarios."""
import sys
sys.path.insert(0, '.')
from database import engine

with engine.connect() as conn:
    try:
        conn.execute(__import__('sqlalchemy').text(
            "ALTER TABLE usuarios ADD COLUMN unidad_negocio VARCHAR(100) NULL"
        ))
        conn.commit()
        print("OK — columna unidad_negocio agregada a usuarios")
    except Exception as e:
        if "Duplicate column" in str(e) or "already exists" in str(e).lower():
            print("INFO — columna ya existe, no se requiere cambio")
        else:
            print(f"ERROR — {e}")
            sys.exit(1)
