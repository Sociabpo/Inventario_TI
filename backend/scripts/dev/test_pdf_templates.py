"""
Test: verify the styled TI block renders correctly in all three acta PDF templates.
Run: python scripts/test_pdf_templates.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.acta import Acta, ActaDetalle
from models.activo import Activo
from models.accesorio import Accesorio
from models.usuario import Usuario
from models.empresa import Empresa
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from datetime import datetime

db = SessionLocal()
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
now = datetime.now()
FECHA       = now.strftime("%d/%m/%Y")
FECHA_EMIS  = now.strftime("%d-%m-%Y")
FECHA_CONST = f"{now.day} dias de mayo del {now.year}"

MUST_HAVE = [
    "Autorizado por",
    "Gesti",          # "Gestion TI" - avoid special char issues
    "Generado digitalmente",
    "eef2f7",
]
MUST_NOT_HAVE = [
    "C.C. ___________________",
    # firma-espacio is still correct in LEFT (employee) block — only check RIGHT block below
    "Responsable Tecnolog",
    "Firma Responsable Tecnolog",
    ">Responsable que Recibe<",
]

# These must NOT appear in the RIGHT (TI) block specifically
# We verify by checking the section after the second <td>
RIGHT_MUST_NOT_HAVE = [
    "firma-espacio",
]

results = {}


def get_items(acta_id):
    detalles = db.query(ActaDetalle).filter(ActaDetalle.acta_id == acta_id).all()
    activos, accesorios = [], []
    for d in detalles:
        if d.tipo_item == "activo" and d.id_activo:
            a = db.query(Activo).filter(Activo.id == d.id_activo).first()
            if a:
                activos.append(a)
        elif d.tipo_item == "accesorio" and d.id_accesorio:
            acc = db.query(Accesorio).filter(Accesorio.id == d.id_accesorio).first()
            if acc:
                accesorios.append(acc)
    return activos, accesorios


def check(html, label, usuario_ti):
    ok = True
    fails = []
    for t in MUST_HAVE:
        if t not in html:
            fails.append("MISSING: " + repr(t))
            ok = False
    for t in MUST_NOT_HAVE:
        if t in html:
            fails.append("STILL PRESENT: " + repr(t))
            ok = False
    # Check RIGHT block specifically: extract everything after the second <td>
    parts = html.split("<td")
    right_block = "<td".join(parts[2:]) if len(parts) > 2 else ""
    for t in RIGHT_MUST_NOT_HAVE:
        if t in right_block:
            fails.append("IN RIGHT BLOCK: " + repr(t))
            ok = False
    if usuario_ti:
        if usuario_ti.nombre_completo not in html:
            fails.append("MISSING user name: " + repr(usuario_ti.nombre_completo))
            ok = False
        if usuario_ti.correo and usuario_ti.correo not in html:
            fails.append("MISSING user correo: " + repr(usuario_ti.correo))
            ok = False
    status = "PASS" if ok else "FAIL"
    print("  " + status + "  " + label)
    for f in fails:
        print("        " + f)
    results[label] = ok
    return ok


# --- 1. ENTREGA ---
print("")
print("-- 1. acta_entrega.html --")
acta = db.query(Acta).filter(Acta.id == "8021e542-6c5c-4ebc-a07b-7e67f06793b2").first()
usuario  = db.query(Usuario).filter(Usuario.id == acta.id_usuario).first()
empresa  = db.query(Empresa).filter(Empresa.id == acta.empresa_id).first()
nombre_ti = acta.responsable_entrega
usuario_ti = db.query(Usuario).filter(Usuario.nombre_completo == nombre_ti).first()
print("  acta_id   : " + acta.id[:8] + "...")
print("  firmada   : " + str(acta.firmada))
print("  nombre_ti : " + repr(nombre_ti) + "  found=" + str(usuario_ti is not None))
if usuario_ti:
    print("  correo    : " + repr(usuario_ti.correo))

activos, accesorios = get_items(acta.id)
tpl  = env.get_template("acta_entrega.html")
html = tpl.render(
    acta=acta, activo=activos[0] if activos else None,
    activos_extra=activos[1:], usuario=usuario, empresa=empresa,
    accesorios=accesorios, usuario_ti=usuario_ti,
    numero_acta="TEST-ENT-001", logo_base64=None,
    fecha=FECHA, fecha_emision=FECHA_EMIS, fecha_constancia=FECHA_CONST,
    firma_base64=None, nombre_firmante=None, entrega_por_tercero=False,
    nombre_tercero=None, relacion_tercero=None,
    observaciones_firma=None, correo_movil=None,
)
check(html, "acta_entrega.html", usuario_ti)


# --- 2. DEVOLUCION ---
print("")
print("-- 2. acta_devolucion.html --")
acta = db.query(Acta).filter(Acta.id == "b8c9b3a3-e4b2-44b9-9eda-d1508ca53210").first()
usuario  = db.query(Usuario).filter(Usuario.id == acta.id_usuario).first()
empresa  = db.query(Empresa).filter(Empresa.id == acta.empresa_id).first()
nombre_ti = acta.responsable_recibe
usuario_ti = db.query(Usuario).filter(Usuario.nombre_completo == nombre_ti).first()
print("  acta_id   : " + acta.id[:8] + "...")
print("  firmada   : " + str(acta.firmada))
print("  nombre_ti : " + repr(nombre_ti) + "  found=" + str(usuario_ti is not None))

activos, accesorios = get_items(acta.id)
tpl  = env.get_template("acta_devolucion.html")
html = tpl.render(
    acta=acta, activo=activos[0] if activos else None,
    activos_extra=activos[1:], usuario=usuario, empresa=empresa,
    accesorios=accesorios, usuario_ti=usuario_ti,
    numero_acta="TEST-DEV-001", logo_base64=None,
    fecha=FECHA, fecha_emision=FECHA_EMIS, fecha_constancia=FECHA_CONST,
    firma_base64=None, nombre_firmante=None, entrega_por_tercero=False,
    nombre_tercero=None, relacion_tercero=None,
    observaciones_firma=None, correo_movil=None,
)
check(html, "acta_devolucion.html", usuario_ti)


# --- 3. ACCESORIOS ---
print("")
print("-- 3. acta_entrega_accesorios.html --")
acta = db.query(Acta).filter(Acta.id == "924bbb50-3feb-4307-a98e-58b99011518d").first()
usuario  = db.query(Usuario).filter(Usuario.id == acta.id_usuario).first()
empresa  = db.query(Empresa).filter(Empresa.id == acta.empresa_id).first()
nombre_ti = acta.responsable_entrega
usuario_ti = db.query(Usuario).filter(Usuario.nombre_completo == nombre_ti).first()
print("  acta_id   : " + acta.id[:8] + "...")
print("  firmada   : " + str(acta.firmada))
print("  nombre_ti : " + repr(nombre_ti) + "  found=" + str(usuario_ti is not None))
if usuario_ti:
    print("  correo    : " + repr(usuario_ti.correo))

_, accesorios = get_items(acta.id)
tpl  = env.get_template("acta_entrega_accesorios.html")
html = tpl.render(
    acta=acta, usuario=usuario, empresa=empresa,
    accesorios=accesorios, usuario_ti=usuario_ti,
    numero_acta="TEST-ACC-001", logo_base64=None,
    fecha=FECHA, fecha_emision=FECHA_EMIS, fecha_constancia=FECHA_CONST,
    firma_base64=None, nombre_firmante=None,
    observaciones_firma=None, correo_movil=None,
)
check(html, "acta_entrega_accesorios.html", usuario_ti)

db.close()

# --- Summary ---
print("")
total  = len(results)
passed = sum(results.values())
print("=" * 50)
print("RESULT: " + str(passed) + "/" + str(total) + " passed")
for label, ok in results.items():
    print("  " + ("PASS" if ok else "FAIL") + "  " + label)
print("=" * 50)
