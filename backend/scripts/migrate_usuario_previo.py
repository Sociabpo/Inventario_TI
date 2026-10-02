# -*- coding: utf-8 -*-
"""Agrega la columna usuario_previo a cambios_estado."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from sqlalchemy import text
from database import engine

DDL = "ALTER TABLE cambios_estado ADD COLUMN usuario_previo VARCHAR(36) NULL"

with engine.begin() as conn:
    cols = conn.execute(text(
        "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'cambios_estado' "
        "AND COLUMN_NAME = 'usuario_previo'"
    )).fetchall()
    if cols:
        print("La columna usuario_previo ya existe. Nada que hacer.")
    else:
        conn.execute(text(DDL))
        print("Columna usuario_previo agregada a cambios_estado.")
print("Migración completada.")
