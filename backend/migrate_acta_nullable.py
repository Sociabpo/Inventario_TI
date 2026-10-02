"""
Migración: hace nullable el campo id_activo en actas_entrega
para soportar actas de entrega exclusivas de accesorios.

Ejecutar una sola vez:
    cd backend
    python migrate_acta_nullable.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from database import engine
from sqlalchemy import text

def run():
    with engine.connect() as conn:
        # MySQL: cambiar la columna a nullable manteniendo el FK
        conn.execute(text("""
            ALTER TABLE actas_entrega
            MODIFY COLUMN id_activo VARCHAR(36) NULL;
        """))
        conn.commit()
    print("✓ Migración aplicada: actas_entrega.id_activo ahora es nullable.")

if __name__ == "__main__":
    run()
