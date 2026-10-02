"""
Reemplaza el catálogo de herramientas: desactiva todas las existentes
y deja solo Zabbix, Wazuh, EDR, Forticlient, Bitdefender y Atera.
Run: python scripts/migrate_herramientas_catalogo.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.servidor import Herramienta

db = SessionLocal()

# Desactivar todas las herramientas existentes
desactivadas = db.query(Herramienta).filter(Herramienta.activo == True).count()
db.query(Herramienta).update({"activo": False})
db.flush()
print(f"  Desactivadas: {desactivadas} herramientas anteriores")

# Catálogo nuevo
NUEVAS = [
    ("Zabbix",      "Monitoreo", "Monitoreo de infraestructura, métricas y alertas"),
    ("Wazuh",       "SIEM",      "SIEM open source, XDR y detección de amenazas"),
    ("EDR",         "EDR/AV",    "Solución de detección y respuesta en endpoints"),
    ("Forticlient", "EDR/AV",    "Endpoint security y VPN de Fortinet"),
    ("Bitdefender", "EDR/AV",    "Plataforma de seguridad y protección avanzada"),
    ("Atera",       "RMM",       "Plataforma RMM de monitoreo y gestión remota"),
]

for nombre, categoria, descripcion in NUEVAS:
    existing = db.query(Herramienta).filter(Herramienta.nombre == nombre).first()
    if existing:
        existing.activo      = True
        existing.categoria   = categoria
        existing.descripcion = descripcion
        print(f"  ~ Reactivada: {nombre}")
    else:
        db.add(Herramienta(nombre=nombre, categoria=categoria, descripcion=descripcion, activo=True))
        print(f"  + Creada:     {nombre}")

db.commit()
db.close()
print("\nCatálogo actualizado correctamente.")
