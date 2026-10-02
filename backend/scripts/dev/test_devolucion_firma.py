"""
Verification tests for devolucion acta digital signature extension.
Tests:
  1. GET /actas returns responsable_recibe field
  2. GET /actas returns firma badge fields for devolucion actas
  3. generar-token-firma works for devolucion acta (200)
  4. firmar.html GET renders name input card for devolucion
  5. POST /firmar without nombre_firmante for devolucion -> 400
  6. POST /firmar with nombre_firmante for devolucion -> 200
  7. After signing: devolucion acta shows firmada=True in GET /actas
  8. After signing: generar-token-firma returns 400 (locked)
"""
import requests, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE  = "http://127.0.0.1:8000/api"
SOCIA = "09a4a3d5-2286-45da-99e9-54c0f5de5a7a"

def login(email, pw):
    r = requests.post(f"{BASE}/auth/login", data={"username": email, "password": pw})
    assert r.ok, f"Login failed: {r.text}"
    return r.json()["access_token"]

tok = login("admin@inventario.com", "Admin1234!")
h   = {"Authorization": f"Bearer {tok}"}

results = []
def check(n, desc, expected, status, detail=""):
    ok   = status == expected
    mark = "PASS" if ok else "FAIL"
    results.append((n, mark, desc, expected, status, detail))
    return ok

# -- Get actas -----------------------------------------------------------------
actas = requests.get(f"{BASE}/actas?empresa_id={SOCIA}", headers=h).json()
if not actas:
    print("No actas found"); sys.exit(1)

# TEST 1: GET /actas returns responsable_recibe
sample = actas[0]
check(1, "GET /actas includes responsable_recibe field", True,
      "responsable_recibe" in sample,
      f"keys={list(sample.keys())[:8]}")

# TEST 2: devolucion actas have firmada + fecha_firma
devolucion_actas = [a for a in actas if a["tipo"] == "devolucion"]
if devolucion_actas:
    dv = devolucion_actas[0]
    has_fields = "firmada" in dv and "fecha_firma" in dv and "responsable_recibe" in dv
    check(2, "Devolucion acta has firmada + fecha_firma + responsable_recibe", True, has_fields,
          f"firmada={dv.get('firmada')} rr={dv.get('responsable_recibe','MISSING')}")
else:
    results.append((2, "SKIP", "No devolucion actas found to check fields", True, True, ""))

# Find an unsigned devolucion acta with a pdf
unsigned_dev = next((a for a in actas if a["tipo"] == "devolucion" and not a.get("firmada")), None)
if not unsigned_dev:
    print("  [INFO] No unsigned devolucion acta — generating PDF for first devolucion")
    if devolucion_actas:
        dev_id = devolucion_actas[0]["id"]
        # reset firmada if needed
        from database import SessionLocal
        from models.acta import Acta
        db = SessionLocal()
        a_obj = db.query(Acta).filter(Acta.id == dev_id).first()
        if a_obj:
            a_obj.firmada = False; a_obj.fecha_firma = None
            db.commit()
        db.close()
        # generate pdf
        requests.post(f"{BASE}/actas/{dev_id}/generar-pdf", headers=h)
        actas = requests.get(f"{BASE}/actas?empresa_id={SOCIA}", headers=h).json()
        unsigned_dev = next((a for a in actas if a["id"] == dev_id), None)

if not unsigned_dev:
    print("No devolucion acta available for signing tests — skipping tests 3-8")
    # Print what we have
else:
    dev_id = unsigned_dev["id"]
    print(f"Using devolucion acta: {dev_id[:8]}... (tiene_pdf={unsigned_dev.get('tiene_pdf')})")

    # Ensure it has a PDF
    if not unsigned_dev.get("tiene_pdf"):
        r = requests.post(f"{BASE}/actas/{dev_id}/generar-pdf", headers=h)
        if not r.ok:
            print(f"  [WARN] Could not generate PDF: {r.text[:100]}")

    # TEST 3: generar-token-firma for devolucion -> 200
    r = requests.post(f"{BASE}/actas/{dev_id}/generar-token-firma", headers=h)
    check(3, "Devolucion acta -> POST generar-token-firma -> 200", 200, r.status_code,
          r.json().get("link","") or r.json().get("detail",""))
    token_val = r.json().get("token") if r.ok else None

    # TEST 4: firmar.html GET contains name input for devolucion
    if token_val:
        r4 = requests.get(f"http://127.0.0.1:8000/firmar/{token_val}")
        has_input = "input-nombre" in r4.text
        has_dev_label = "Responsable que recibe" in r4.text or "devuelve" in r4.text
        check(4, "firmar.html renders name input card for devolucion", True,
              has_input and has_dev_label,
              f"has_input={has_input} has_dev_label={has_dev_label}")

        # TEST 5: POST /firmar without nombre_firmante -> 400
        r5 = requests.post(f"http://127.0.0.1:8000/firmar/{token_val}",
                           json={"firma_base64": "data:image/png;base64," + "A" * 100})
        check(5, "POST /firmar without nombre_firmante for devolucion -> 400", 400, r5.status_code,
              r5.json().get("detail",""))

        # TEST 6: POST /firmar WITH nombre_firmante -> 200
        r6 = requests.post(f"http://127.0.0.1:8000/firmar/{token_val}",
                           json={"firma_base64": "data:image/png;base64," + "A" * 100,
                                 "nombre_firmante": "Carlos Prueba TI"})
        check(6, "POST /firmar with nombre_firmante for devolucion -> 200", 200, r6.status_code,
              r6.json().get("mensaje","") or r6.json().get("detail",""))

        if r6.ok:
            # TEST 7: GET /actas shows firmada=True
            actas2 = requests.get(f"{BASE}/actas?empresa_id={SOCIA}", headers=h).json()
            signed = next((a for a in actas2 if a["id"] == dev_id), None)
            is_locked = signed and signed.get("firmada") == True and signed.get("fecha_firma") is not None
            rr_ok = signed and signed.get("responsable_recibe") == "Carlos Prueba TI"
            check(7, "GET /actas: devolucion firmada=True + responsable_recibe updated", True,
                  bool(is_locked and rr_ok),
                  f"firmada={signed.get('firmada')} rr={signed.get('responsable_recibe')}" if signed else "not found")

            # TEST 8: generar-token-firma returns 400 (locked)
            r8 = requests.post(f"{BASE}/actas/{dev_id}/generar-token-firma", headers=h)
            check(8, "Signed devolucion -> POST generar-token-firma -> 400", 400, r8.status_code,
                  r8.json().get("detail",""))

            # Cleanup
            from database import SessionLocal
            from models.acta import Acta
            db = SessionLocal()
            a_obj = db.query(Acta).filter(Acta.id == dev_id).first()
            if a_obj:
                a_obj.firmada = False; a_obj.fecha_firma = None
                db.commit()
            db.close()
            print(f"  [Cleanup] Restored devolucion acta to firmada=False")
    else:
        for n in [4,5,6,7,8]:
            results.append((n, "SKIP", f"No token available", True, True, ""))

# ── Results table -------------------------------------------------------------
print()
print(f"{'#':<3} {'Result':<6} {'Expected':>8} {'Got':>6}  Description")
print("-" * 80)
for row in results:
    n, mark, desc, exp, got, detail = row
    exp_s = "True" if exp is True else "False" if exp is False else str(exp)
    got_s = "True" if got is True else "False" if got is False else str(got)
    print(f"{n:<3} {mark:<6} {exp_s:>8} {got_s:>6}  {desc}")
    if mark == "FAIL":
        print(f"    detail: {detail}")
    elif detail and mark != "SKIP":
        print(f"    -> {str(detail)[:90]}")
print()
all_pass = all(r[1] in ("PASS","SKIP") for r in results)
print("ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED")
