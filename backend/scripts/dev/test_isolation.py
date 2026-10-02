"""
Three-case isolation test for multi-tenant RBAC.
Run: venv\Scripts\python.exe scripts\test_isolation.py
"""
import requests

BASE = "http://127.0.0.1:8000/api"

def login(email, password):
    r = requests.post(f"{BASE}/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]

def get_activos(token, empresa_id=None):
    params = {}
    if empresa_id:
        params["empresa_id"] = empresa_id
    r = requests.get(f"{BASE}/activos", headers={"Authorization": f"Bearer {token}"}, params=params)
    return r.status_code, r.json()

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("TEST 1: auditor_sociabpo@test.com → GET /api/activos (no filter)")
print("        Expected: only Socia BPO records (empresa 09a4a3d5-...)")
print("=" * 70)

tok_auditor = login("auditor_sociabpo@test.com", "Test1234!")
status, data = get_activos(tok_auditor)
print(f"  HTTP {status}")
if status == 200:
    empresas_vistas = set(a["empresa_id"] for a in data)
    socia_id = "09a4a3d5-2286-45da-99e9-54c0f5de5a7a"
    if empresas_vistas == {socia_id} or empresas_vistas == set():
        print(f"  PASS — {len(data)} activo(s) devueltos, solo Socia BPO")
    elif not empresas_vistas:
        print("  PASS — 0 activos (aceptable si no hay activos asignados)")
    else:
        print(f"  FAIL — empresas vistas: {empresas_vistas}")
    for a in data:
        print(f"    · {a['id_placa_activo']} | empresa: {a['empresa_id']} | {a.get('nombre_empresa','')}")
else:
    print(f"  FAIL — error: {data}")

print()

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("TEST 2: admin@inventario.com (super_admin) → GET /api/activos")
print("        Expected: ALL records from ALL companies")
print("=" * 70)

tok_super = login("admin@inventario.com", "Admin1234!")
status2, data2 = get_activos(tok_super)
print(f"  HTTP {status2}")
if status2 == 200:
    empresas_vistas2 = set(a["empresa_id"] for a in data2)
    if len(empresas_vistas2) > 1:
        print(f"  PASS — {len(data2)} activo(s), {len(empresas_vistas2)} empresa(s) distintas")
    elif len(data2) >= 1:
        print(f"  INFO — {len(data2)} activo(s), {len(empresas_vistas2)} empresa(s) (puede haber solo 1 empresa con activos)")
    else:
        print("  WARN — 0 activos devueltos")
    for a in data2:
        print(f"    · {a['id_placa_activo']} | empresa: {a['empresa_id']} | {a.get('nombre_empresa','')}")
else:
    print(f"  FAIL — error: {data2}")

print()

# ─────────────────────────────────────────────────────────────────────────────
print("=" * 70)
print("TEST 3: auditor_sociabpo@test.com → GET /api/activos?empresa_id=OTRA")
print("        Expected: 403 Forbidden")
print("=" * 70)

voce_id = "4676ae6d-5793-4630-8610-787c68005b49"
status3, data3 = get_activos(tok_auditor, empresa_id=voce_id)
print(f"  HTTP {status3}")
if status3 == 403:
    print("  PASS — 403 recibido correctamente")
    print(f"    detail: {data3.get('detail','')}")
elif status3 == 200 and len(data3) == 0:
    print("  PARTIAL — returned 200 with empty list (filter worked but no 403)")
else:
    print(f"  FAIL — status={status3}, data={data3}")

print()
print("=" * 70)
print("DONE")
print("=" * 70)
