"""
Write/mutation isolation tests.
Run: venv\\Scripts\\python.exe scripts\\test_write_isolation.py
"""
import requests, json

BASE = "http://127.0.0.1:8000/api"
SOCIA_ID = "09a4a3d5-2286-45da-99e9-54c0f5de5a7a"
VOCE_ID  = "4676ae6d-5793-4630-8610-787c68005b49"

def login(email, password):
    r = requests.post(f"{BASE}/auth/login", data={"username": email, "password": password})
    assert r.status_code == 200, f"Login failed ({r.status_code}): {r.text}"
    return r.json()["access_token"]

def post_activo(token, empresa_id, tipo="Laptop"):
    payload = {"empresa_id": empresa_id, "tipo_activo": tipo, "marca": "Test", "modelo": "TestModel"}
    r = requests.post(f"{BASE}/activos", json=payload, headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json()

def post_asignacion(token, empresa_id):
    payload = {"empresa_id": empresa_id, "id_activo": "fake-id", "id_usuario": "fake-id",
               "responsable_entrega": "Test", "responsable_recibe": "Test"}
    r = requests.post(f"{BASE}/asignaciones", json=payload, headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json()

results = []

def check(n, desc, expected, status, data, created_id=None):
    ok = status == expected
    mark = "PASS" if ok else "FAIL"
    detail = data.get("detail", "") if isinstance(data, dict) else str(data)[:60]
    results.append((n, mark, desc, expected, status, detail))
    if created_id and ok:
        results[-1] = results[-1] + (created_id,)
    return ok

print("Setting up tokens...")
tok_auditor  = login("auditor_sociabpo@test.com", "Test1234!")
tok_analista = login("analista_sociabpo@test.com", "Test1234!")
tok_super    = login("admin@inventario.com", "Admin1234!")
print("Tokens OK\n")

# ── Test 1 ────────────────────────────────────────────────────────────────────
# auditoria user, POST activos with Voce empresa_id -> 403 (no activos.crear perm)
s, d = post_activo(tok_auditor, VOCE_ID)
check(1, "auditoria -> POST /activos (Voce ID) -> 403 (no perm)", 403, s, d)

# ── Test 2 ────────────────────────────────────────────────────────────────────
# auditoria user, POST activos with Socia empresa_id -> 403 (no activos.crear perm)
s, d = post_activo(tok_auditor, SOCIA_ID)
check(2, "auditoria -> POST /activos (Socia ID) -> 403 (no perm)", 403, s, d)

# ── Test 3 ────────────────────────────────────────────────────────────────────
# auditoria user, POST asignaciones with Socia empresa_id -> 403 (no asignaciones.crear perm)
s, d = post_asignacion(tok_auditor, SOCIA_ID)
check(3, "auditoria -> POST /asignaciones (Socia ID) -> 403 (no perm)", 403, s, d)

# ── Test 4 ────────────────────────────────────────────────────────────────────
# analista_activos user (Socia only), POST activos with Socia empresa_id -> 201
s, d = post_activo(tok_analista, SOCIA_ID)
check(4, "analista (Socia) -> POST /activos (Socia ID) -> 201", 201, s, d)
created_placa = d.get("id_placa_activo", "") if s == 201 else None
created_id    = d.get("id", "") if s == 201 else None
if created_placa:
    print(f"  [Test 4] Created activo: {created_placa} (id={created_id})")

# ── Test 5 ────────────────────────────────────────────────────────────────────
# analista_activos user (Socia only), POST activos with Voce empresa_id -> 403
s, d = post_activo(tok_analista, VOCE_ID)
check(5, "analista (Socia) -> POST /activos (Voce ID) -> 403", 403, s, d)

# ── Cleanup: delete the test activo created in test 4 ─────────────────────────
if created_id:
    r = requests.delete(f"{BASE}/activos/{created_id}", headers={"Authorization": f"Bearer {tok_super}"})
    if r.status_code == 200:
        print(f"  [Cleanup] Deleted test activo {created_placa}")
    else:
        print(f"  [Cleanup] Note: DELETE /activos/{created_id} => {r.status_code} (no cleanup endpoint or not needed)")

# ── Print table ───────────────────────────────────────────────────────────────
print()
print(f"{'#':<3} {'Result':<6} {'Expected':>8} {'Got':>6}  Description")
print("-" * 75)
for row in results:
    n, mark, desc, exp, got, detail = row[:6]
    print(f"{n:<3} {mark:<6} {exp:>8} {got:>6}  {desc}")
    if mark == "FAIL":
        print(f"    {'':>14}  detail: {detail}")
print()
all_pass = all(r[1] == "PASS" for r in results)
print("ALL TESTS PASSED" if all_pass else "SOME TESTS FAILED — see above")
