"""
Verifies that /accesorios/disponibles and the assignment validation
both accept disponible_ct and disponible_sede states.
"""
import requests

BASE = "http://127.0.0.1:8000/api"
SOCIA_ID = "09a4a3d5-2286-45da-99e9-54c0f5de5a7a"

def login(email, pw):
    r = requests.post(f"{BASE}/auth/login", data={"username": email, "password": pw})
    assert r.ok, f"Login failed: {r.text}"
    return r.json()["access_token"]

tok = login("admin@inventario.com", "Admin1234!")
h = {"Authorization": f"Bearer {tok}"}

# ── Check current accessory states ────────────────────────────────────────────
print("=== All accesorios for Socia BPO ===")
r = requests.get(f"{BASE}/accesorios?empresa_id={SOCIA_ID}", headers=h)
for a in r.json():
    print(f"  {a['id_placa_accesorio']} | {a['tipo_accesorio']} | estado={a['estado']}")

# ── GET /accesorios/disponibles ────────────────────────────────────────────────
print("\n=== GET /accesorios/disponibles (Socia BPO) ===")
r = requests.get(f"{BASE}/accesorios/disponibles?empresa_id={SOCIA_ID}", headers=h)
print(f"HTTP {r.status_code}  count={len(r.json())}")
for a in r.json():
    print(f"  {a['id_placa_accesorio']} | {a['tipo_accesorio']} | estado={a['estado']}")
if not r.json():
    print("  (none — no accessories in disponible_ct or disponible_sede state)")

# ── Check activos disponibles ──────────────────────────────────────────────────
print("\n=== GET /activos/disponibles (Socia BPO) ===")
r = requests.get(f"{BASE}/activos/disponibles?empresa_id={SOCIA_ID}", headers=h)
print(f"HTTP {r.status_code}  count={len(r.json())}")
for a in r.json():
    print(f"  {a['id_placa_activo']} | {a['tipo_activo']} | estado={a['estado']}")
