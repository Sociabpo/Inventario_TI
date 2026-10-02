"""Agrega 17 columnas de especificaciones extendidas a la tabla activos."""
import sys
sys.path.insert(0, '.')
from database import engine
import sqlalchemy as sa

NUEVAS_COLUMNAS = [
    ("resolucion",               "VARCHAR(100)"),
    ("tipo_conexion",            "VARCHAR(100)"),
    ("tamano_pantalla",          "VARCHAR(50)"),
    ("imei",                     "VARCHAR(20)"),
    ("numero_telefono",          "VARCHAR(30)"),
    ("capacidad_almacenamiento", "VARCHAR(50)"),
    ("color",                    "VARCHAR(50)"),
    ("tipo_impresora",           "VARCHAR(100)"),
    ("ip_dispositivo",           "VARCHAR(50)"),
    ("tipo_camara",              "VARCHAR(100)"),
    ("canales_dvr",              "INT"),
    ("con_microfono",            "TINYINT(1)"),
    ("extension",                "VARCHAR(20)"),
    ("linea_telefono",           "VARCHAR(30)"),
    ("tipo_telefono",            "VARCHAR(50)"),
    ("capacidad_ups",            "VARCHAR(50)"),
    ("tiempo_respaldo_ups",      "VARCHAR(50)"),
]

with engine.connect() as conn:
    for col, tipo in NUEVAS_COLUMNAS:
        try:
            conn.execute(sa.text(f"ALTER TABLE activos ADD COLUMN {col} {tipo} NULL"))
            conn.commit()
            print(f"OK — {col} agregada")
        except Exception as e:
            if "Duplicate column" in str(e) or "already exists" in str(e).lower():
                print(f"INFO — {col} ya existe")
            else:
                print(f"ERROR — {col}: {e}")
                sys.exit(1)
