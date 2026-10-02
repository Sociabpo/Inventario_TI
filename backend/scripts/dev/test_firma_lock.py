"""
Verifies acta locking after digital signature.
Tests:
  1. Signed acta -> generar-token-firma returns 400
  2. Signed acta -> generar-pdf returns 400
  3. Unsigned acta -> generar-token-firma returns 200 (link generated)
  4. GET /actas response includes firmada + fecha_firma fields
  5. Simulate full sign flow: generate token -> mark acta as signed -> confirm lock
"""
import requests, uuid

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

# ── Get an existing acta to work with ─────────────────────────────────────────
actas = requests.get(f"{BASE}/actas?empresa_id={SOCIA}", headers=h).json()
if not actas:
    print("No actas found — run an asignacion first")
    exit(1)

# Find an unsigned entrega acta
unsigned = next((a for a in actas if a["tipo"] == "entrega" and not a.get("firmada")), None)
if not unsigned:
    print("No unsigned entrega acta found — all are already signed")
    exit(1)

acta_id = unsigned["id"]
print(f"Using acta: {acta_id[:8]}... (placa={unsigned.get('placa_activo','—')})")

# ── TEST 4: GET /actas includes firmada + fecha_firma ─────────────────────────
has_firmada    = "firmada" in unsigned
has_fecha_firma = "fecha_firma" in unsigned
check(4, "GET /actas includes 'firmada' and 'fecha_firma' fields", True,
      has_firmada and has_fecha_firma,
      f"firmada={unsigned.get('firmada')} fecha_firma={unsigned.get('fecha_firma')}")

# ── TEST 3: Unsigned acta → generar-token-firma returns 200 ───────────────────
r = requests.post(f"{BASE}/actas/{acta_id}/generar-token-firma", headers=h)
check(3, "Unsigned acta -> POST generar-token-firma -> 200", 200, r.status_code,
      r.json().get("link","") or r.json().get("detail",""))
token_val = r.json().get("token") if r.ok else None

# ── TEST 5: Simulate signature via DB to create a locked acta ─────────────────
# We mark the acta as firmada directly so we can test the lock without a browser
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import SessionLocal
from models.acta import Acta
from datetime import datetime

db = SessionLocal()
acta_obj = db.query(Acta).filter(Acta.id == acta_id).first()
acta_obj.firmada     = True
acta_obj.fecha_firma = datetime.utcnow()
db.commit()
db.close()
print(f"  [Setup] Marked acta {acta_id[:8]} as firmada=True")

# ── TEST 1: Signed acta → generar-token-firma returns 400 ─────────────────────
r = requests.post(f"{BASE}/actas/{acta_id}/generar-token-firma", headers=h)
check(1, "Signed acta -> POST generar-token-firma -> 400", 400, r.status_code,
      r.json().get("detail",""))

# ── TEST 2: Signed acta → generar-pdf returns 400 ────────────────────────────
r = requests.post(f"{BASE}/actas/{acta_id}/generar-pdf", headers=h)
check(2, "Signed acta -> POST generar-pdf -> 400", 400, r.status_code,
      r.json().get("detail",""))

# ── TEST 5: GET /actas shows firmada=True for the signed acta ─────────────────
actas2  = requests.get(f"{BASE}/actas?empresa_id={SOCIA}", headers=h).json()
signed  = next((a for a in actas2 if a["id"] == acta_id), None)
is_locked = signed and signed.get("firmada") == True and signed.get("fecha_firma") is not None
check(5, "Signed acta reflected in GET /actas (firmada=True, fecha_firma set)", True,
      is_locked,
      f"firmada={signed.get('firmada')} fecha_firma={signed.get('fecha_firma')}" if signed else "not found")

# ── Cleanup: restore acta to unsigned ─────────────────────────────────────────
db = SessionLocal()
acta_obj = db.query(Acta).filter(Acta.id == acta_id).first()
acta_obj.firmada     = False
acta_obj.fecha_firma = None
db.commit()
db.close()
print(f"  [Cleanup] Restored acta {acta_id[:8]} to firmada=False")

# ── Results table ─────────────────────────────────────────────────────────────
print()
print(f"{'#':<3} {'Result':<6} {'Expected':>8} {'Got':>6}  Description")
print("-" * 80)
for row in results:
    n, mark, desc, exp, got, detail = row
    exp_s = "True" if exp is True else "False" if exp is False else str(exp)
    got_s = "True" if got is True else "False" if got is False else str(got)
    print(f"{n:<3} {mark:<6} {exp_s:>8} {got_s:>6}  {desc}")
    if mark == "FAIL":
        print(f"    {'':>14}  detail: {detail}")
    elif detail:
        print(f"    {'':>14}  → {detail[:80]}")
print()
all_pass = all(r[1] == "PASS" for r in results)
print("ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED")
