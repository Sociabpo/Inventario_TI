"""
6 verification tests for the redesigned devolucion signature flow.
"""
import requests, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE  = "http://127.0.0.1:8000/api"
SOCIA = "09a4a3d5-2286-45da-99e9-54c0f5de5a7a"
FAKE_SIG = "data:image/png;base64," + "A" * 200

def login(email, pw):
    r = requests.post(f"{BASE}/auth/login", data={"username": email, "password": pw})
    assert r.ok, f"Login failed: {r.text}"
    return r.json()["access_token"]

tok = login("admin@inventario.com", "Admin1234!")
h   = {"Authorization": f"Bearer {tok}"}

results = []
def check(n, desc, expected, got, detail=""):
    ok   = got == expected
    mark = "PASS" if ok else "FAIL"
    results.append((n, mark, desc, expected, got, detail))
    return ok

# ── helpers ───────────────────────────────────────────────
from database import SessionLocal
from models.acta import Acta

def reset_acta(acta_id):
    db = SessionLocal()
    a = db.query(Acta).filter(Acta.id == acta_id).first()
    if a:
        a.firmada = False; a.fecha_firma = None
        db.commit()
    db.close()

def get_token(acta_id):
    r = requests.post(f"{BASE}/actas/{acta_id}/generar-token-firma", headers=h)
    assert r.ok, f"Token gen failed: {r.text}"
    return r.json()["token"]

# find an unsigned devolucion acta
actas = requests.get(f"{BASE}/actas?empresa_id={SOCIA}", headers=h).json()
devs  = [a for a in actas if a["tipo"] == "devolucion"]
if not devs:
    print("No devolucion actas found"); sys.exit(1)

# ensure one is unsigned and has PDF
dev = next((a for a in devs if not a.get("firmada")), devs[0])
reset_acta(dev["id"])
if not dev.get("tiene_pdf"):
    requests.post(f"{BASE}/actas/{dev['id']}/generar-pdf", headers=h)
dev_id = dev["id"]
print(f"Using devolucion acta: {dev_id[:8]}...")

# ── find an unsigned entrega acta ────────────────────────
entrega_actas = [a for a in actas if a["tipo"] == "entrega" and not a.get("firmada")]
if entrega_actas:
    entrega_id = entrega_actas[0]["id"]
    if not entrega_actas[0].get("tiene_pdf"):
        requests.post(f"{BASE}/actas/{entrega_id}/generar-pdf", headers=h)
    print(f"Using entrega acta:    {entrega_id[:8]}...")
else:
    entrega_id = None
    print("No unsigned entrega acta available")

# ══ TEST 1 ══ Employee delivers directly ─────────────────
reset_acta(dev_id)
t = get_token(dev_id)

# Verify signing page shows radio buttons and receiver input
page = requests.get(f"http://127.0.0.1:8000/firmar/{t}").text
has_radio   = "radio-directo" in page and "radio-tercero" in page
has_receptor = "input-receptor" in page
has_tercero_card = "card-tercero" in page
check(1, "firmar.html devolucion: radios + receptor input + tercero card present",
      True, has_radio and has_receptor and has_tercero_card,
      f"radio={has_radio} receptor={has_receptor} tercero_card={has_tercero_card}")

# Submit without tercero — employee delivers directly
r = requests.post(f"http://127.0.0.1:8000/firmar/{t}",
                  json={"firma_base64": FAKE_SIG,
                        "nombre_firmante": "Maria Tecnologia",
                        "entrega_por_tercero": False})
check(1, "Test 1 — direct delivery submit -> 200", 200, r.status_code,
      r.json().get("mensaje","") or r.json().get("detail",""))

# ══ TEST 2 ══ Third party delivers ───────────────────────
reset_acta(dev_id)
t = get_token(dev_id)

r = requests.post(f"http://127.0.0.1:8000/firmar/{t}",
                  json={"firma_base64": FAKE_SIG,
                        "nombre_firmante": "Maria Tecnologia",
                        "entrega_por_tercero": True,
                        "nombre_tercero": "Carlos Martinez",
                        "relacion_tercero": "Jefe directo"})
check(2, "Test 2 — third party delivery submit -> 200", 200, r.status_code,
      r.json().get("mensaje","") or r.json().get("detail",""))

# verify acta shows firmada + responsable_recibe updated
actas2 = requests.get(f"{BASE}/actas?empresa_id={SOCIA}", headers=h).json()
signed = next((a for a in actas2 if a["id"] == dev_id), None)
rr_ok  = signed and signed.get("firmada") and signed.get("responsable_recibe") == "Maria Tecnologia"
check(2, "Test 2 — firmada=True and responsable_recibe = Maria Tecnologia",
      True, bool(rr_ok),
      f"firmada={signed.get('firmada')} rr={signed.get('responsable_recibe')}" if signed else "not found")

# ══ TEST 3 ══ Submit devolucion without receiver name -> blocked ──────────────
reset_acta(dev_id)
t = get_token(dev_id)

r = requests.post(f"http://127.0.0.1:8000/firmar/{t}",
                  json={"firma_base64": FAKE_SIG,
                        "entrega_por_tercero": False})
check(3, "Test 3 — submit without nombre_firmante -> 400", 400, r.status_code,
      r.json().get("detail",""))

# ══ TEST 4 ══ Tercero selected but no tercero name -> blocked ────────────────
# token from test 3 is still valid (400 didn't consume it)
r = requests.post(f"http://127.0.0.1:8000/firmar/{t}",
                  json={"firma_base64": FAKE_SIG,
                        "nombre_firmante": "Receptor OK",
                        "entrega_por_tercero": True,
                        "nombre_tercero": "",
                        "relacion_tercero": "Jefe"})
check(4, "Test 4 — tercero=True but nombre_tercero empty -> 400", 400, r.status_code,
      r.json().get("detail",""))

# also missing relacion
r = requests.post(f"http://127.0.0.1:8000/firmar/{t}",
                  json={"firma_base64": FAKE_SIG,
                        "nombre_firmante": "Receptor OK",
                        "entrega_por_tercero": True,
                        "nombre_tercero": "Carlos",
                        "relacion_tercero": ""})
check(4, "Test 4 — tercero=True but relacion_tercero empty -> 400", 400, r.status_code,
      r.json().get("detail",""))

# ══ TEST 5 ══ Entrega acta — no regression ───────────────────────────────────
if entrega_id:
    reset_acta(entrega_id)
    t_e = get_token(entrega_id)
    page_e = requests.get(f"http://127.0.0.1:8000/firmar/{t_e}").text
    no_radio  = "radio-directo" not in page_e
    has_canvas = "firma-canvas" in page_e
    check(5, "Test 5 — entrega page has no radio buttons, has canvas", True,
          no_radio and has_canvas, f"no_radio={no_radio} has_canvas={has_canvas}")

    r = requests.post(f"http://127.0.0.1:8000/firmar/{t_e}",
                      json={"firma_base64": FAKE_SIG})
    check(5, "Test 5 — entrega sign without nombre_firmante -> 200", 200, r.status_code,
          r.json().get("mensaje","") or r.json().get("detail",""))
    reset_acta(entrega_id)
else:
    results.append((5, "SKIP", "No unsigned entrega acta available", True, True, ""))

# ══ TEST 6 ══ Signed devolucion -> generar-token-firma -> 400 ────────────────
reset_acta(dev_id)
t6 = get_token(dev_id)
requests.post(f"http://127.0.0.1:8000/firmar/{t6}",
              json={"firma_base64": FAKE_SIG,
                    "nombre_firmante": "Receptor Test6",
                    "entrega_por_tercero": False})
r = requests.post(f"{BASE}/actas/{dev_id}/generar-token-firma", headers=h)
check(6, "Test 6 — signed devolucion -> generar-token-firma -> 400", 400, r.status_code,
      r.json().get("detail",""))

# cleanup
reset_acta(dev_id)
print(f"  [Cleanup] Restored devolucion acta to firmada=False")

# ── Results ───────────────────────────────────────────────
print()
print(f"{'#':<3} {'Result':<6} {'Expected':>8} {'Got':>6}  Description")
print("-" * 80)
for row in results:
    n, mark, desc, exp, got, detail = row
    es = "True" if exp is True else "False" if exp is False else str(exp)
    gs = "True" if got is True else "False" if got is False else str(got)
    print(f"{n:<3} {mark:<6} {es:>8} {gs:>6}  {desc}")
    if mark == "FAIL":
        print(f"    detail: {detail}")
    elif detail and mark == "PASS":
        print(f"    -> {str(detail)[:90]}")
print()
all_ok = all(r[1] in ("PASS", "SKIP") for r in results)
print("ALL TESTS PASSED" if all_ok else "SOME TESTS FAILED")
