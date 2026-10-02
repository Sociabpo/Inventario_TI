"""
Agrega las columnas observaciones_firma y correo_movil a firma_tokens.
Run: python scripts/migrate_firma_entrega_campos.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine

COLUMNAS = [
    "ALTER TABLE firma_tokens ADD COLUMN observaciones_firma TEXT NULL",
    "ALTER TABLE firma_tokens ADD COLUMN correo_movil TINYINT(1) NULL",
]

with engine.connect() as conn:
    for sql in COLUMNAS:
        col = sql.split("ADD COLUMN ")[1].split(" ")[0]
        try:
            conn.execute(__import__("sqlalchemy").text(sql))
            conn.commit()
            print(f"  + Columna agregada: {col}")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e):
                print(f"  ~ Columna ya existe: {col}")
            else:
                print(f"  ! Error en {col}: {e}")

print("Migración completada.")
