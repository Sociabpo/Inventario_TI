"""
Standalone seed script for servidores catalogs.
Run from backend/: python scripts/seed_servidores.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.servidor import (
    TipoServidor, Ambiente, Criticidad, EstadoServidor,
    SistemaOperativo, Herramienta,
)

db = SessionLocal()

def upsert(model, filters: dict, defaults: dict):
    obj = db.query(model).filter_by(**filters).first()
    if not obj:
        obj = model(**filters, **defaults)
        db.add(obj)
        return True
    return False


inserted = {}

tipos = [
    ("Físico",    "Servidor físico on-premise"),
    ("Virtual",   "Máquina virtual (VMware, Hyper-V, KVM)"),
    ("Contenedor","Contenedor Docker / LXC"),
    ("Cloud",     "Instancia de nube pública (AWS, Azure, GCP)"),
    ("Appliance", "Dispositivo appliance dedicado"),
    ("Bastión",   "Servidor de salto / bastión SSH"),
]
n = 0
for nombre, desc in tipos:
    if upsert(TipoServidor, {"nombre": nombre}, {"descripcion": desc}):
        n += 1
inserted["tipos_servidor"] = n

ambientes = [
    ("Producción",        "#e74c3c"),
    ("QA / Pruebas",      "#f39c12"),
    ("Desarrollo",        "#3498db"),
    ("Staging",           "#9b59b6"),
    ("DR / Contingencia", "#e67e22"),
    ("Laboratorio",       "#27ae60"),
]
n = 0
for nombre, color in ambientes:
    if upsert(Ambiente, {"nombre": nombre}, {"color": color}):
        n += 1
inserted["ambientes"] = n

criticidades = [
    ("Crítico", 4, "#c0392b"),
    ("Alto",    3, "#e74c3c"),
    ("Medio",   2, "#f39c12"),
    ("Bajo",    1, "#27ae60"),
]
n = 0
for nombre, nivel, color in criticidades:
    if upsert(Criticidad, {"nombre": nombre}, {"nivel": nivel, "color": color}):
        n += 1
inserted["criticidades"] = n

estados = [
    ("Activo",           "#27ae60"),
    ("Inactivo",         "#95a5a6"),
    ("En mantenimiento", "#f39c12"),
    ("Dado de baja",     "#7f8c8d"),
    ("En instalación",   "#3498db"),
]
n = 0
for nombre, color in estados:
    if upsert(EstadoServidor, {"nombre": nombre}, {"color": color}):
        n += 1
inserted["estados_servidor"] = n

so_list = [
    ("Red Hat Enterprise Linux 9",       "Linux",      True),
    ("Red Hat Enterprise Linux 8",       "Linux",      True),
    ("Red Hat Enterprise Linux 7",       "Linux",      False),
    ("Ubuntu Server 24.04 LTS",          "Linux",      True),
    ("Ubuntu Server 22.04 LTS",          "Linux",      True),
    ("Ubuntu Server 20.04 LTS",          "Linux",      True),
    ("Debian 12 (Bookworm)",             "Linux",      True),
    ("CentOS Stream 9",                  "Linux",      True),
    ("Rocky Linux 9",                    "Linux",      True),
    ("AlmaLinux 9",                      "Linux",      True),
    ("SUSE Linux Enterprise Server 15",  "Linux",      True),
    ("Windows Server 2022",              "Windows",    True),
    ("Windows Server 2019",              "Windows",    True),
    ("Windows Server 2016",              "Windows",    True),
    ("Windows Server 2012 R2",           "Windows",    False),
    ("VMware ESXi 8.0",                  "Hypervisor", True),
    ("VMware ESXi 7.0",                  "Hypervisor", True),
    ("Proxmox VE 8",                     "Hypervisor", True),
    ("FreeBSD 14",                       "BSD",        True),
]
n = 0
for nombre, familia, soporte in so_list:
    if upsert(SistemaOperativo, {"nombre": nombre}, {"familia": familia, "soporte_activo": soporte}):
        n += 1
inserted["sistemas_operativos"] = n

herramientas = [
    ("Zabbix",                  "Monitoreo",               "Monitoreo de infraestructura y alertas"),
    ("Nagios",                  "Monitoreo",               "Monitoreo de servicios y hosts"),
    ("Prometheus",              "Monitoreo",               "Sistema de monitoreo y alertas"),
    ("Grafana",                 "Monitoreo",               "Visualización de métricas y dashboards"),
    ("SolarWinds",              "Monitoreo",               "Monitoreo de redes e infraestructura"),
    ("Splunk",                  "SIEM",                    "Plataforma SIEM y análisis de logs"),
    ("IBM QRadar",              "SIEM",                    "Plataforma SIEM empresarial"),
    ("Wazuh",                   "SIEM",                    "SIEM open source y XDR"),
    ("Elastic SIEM",            "SIEM",                    "SIEM basado en Elastic Stack"),
    ("Qualys VMDR",             "Vulnerabilidades",        "Gestión de vulnerabilidades"),
    ("Tenable Nessus",          "Vulnerabilidades",        "Escáner de vulnerabilidades"),
    ("Rapid7 InsightVM",        "Vulnerabilidades",        "Gestión de vulnerabilidades"),
    ("OpenVAS",                 "Vulnerabilidades",        "Escáner open source"),
    ("CrowdStrike Falcon",      "EDR/AV",                  "Plataforma EDR en la nube"),
    ("SentinelOne",             "EDR/AV",                  "Plataforma EDR con IA"),
    ("Carbon Black",            "EDR/AV",                  "Protección de endpoints"),
    ("Trend Micro Deep Security","EDR/AV",                 "Seguridad de servidores"),
    ("Puppet",                  "Gestión de Configuración","Automatización de configuración"),
    ("Ansible",                 "Gestión de Configuración","Automatización y orquestación"),
    ("Chef",                    "Gestión de Configuración","Gestión de configuración"),
    ("Dynatrace",               "APM",                     "Monitoreo de rendimiento de aplicaciones"),
    ("New Relic",               "APM",                     "Observabilidad de aplicaciones"),
    ("Datadog",                 "APM",                     "Plataforma de observabilidad"),
    ("Backup Exec",             "Backup",                  "Solución de backup Veritas"),
    ("Veeam",                   "Backup",                  "Backup y recuperación"),
    ("Commvault",               "Backup",                  "Plataforma de protección de datos"),
]
n = 0
for nombre, categoria, desc in herramientas:
    if upsert(Herramienta, {"nombre": nombre}, {"categoria": categoria, "descripcion": desc, "activo": True}):
        n += 1
inserted["herramientas"] = n

db.commit()
db.close()

print("Seed completado:")
for k, v in inserted.items():
    print(f"  {k}: {v} nuevos registros")
