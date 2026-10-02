"""
8 verification tests for the Servidores module.
Run after the server is up: python scripts/test_servidores.py
"""
import requests, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BASE = "http://127.0.0.1:8000/api"

results = []
def check(n, desc, expected, got, detail=""):
    ok   = got == expected
    mark = "PASS" if ok else "FAIL"
    results.append((n, mark, desc, expected, got, detail))
    return ok

# ── Auth ──────────────────────────────────────────────────────────────────────
def login(email, pw):
    r = requests.post(f"{BASE}/auth/login", data={"username": email, "password": pw})
    assert r.ok, f"Login failed: {r.text}"
    return r.json()["access_token"]

tok = login("admin@inventario.com", "Admin1234!")
h   = {"Authorization": f"Bearer {tok}"}

# ── Get first empresa ─────────────────────────────────────────────────────────
empresas = requests.get(f"{BASE}/rbac/empresas-disponibles", headers=h).json()
assert empresas, "No empresas found"
empresa_id = empresas[0]["id"]
print(f"Using empresa: {empresas[0].get('nombre_empresa','?')} ({empresa_id[:8]}...)")

# ══ TEST 1 ══ Catalogos load ──────────────────────────────────────────────────
r = requests.get(f"{BASE}/servidores/catalogos", headers=h)
check(1, "GET /catalogos -> 200", 200, r.status_code)
if r.ok:
    cat = r.json()
    has_all = all(k in cat for k in ["tipos_servidor","ambientes","criticidades","estados_servidor","sistemas_operativos","herramientas"])
    check(1, "catalogos has all 6 keys", True, has_all, str(list(cat.keys())))
    check(1, "herramientas count >= 20", True, len(cat.get("herramientas",[])) >= 20,
          f"got {len(cat.get('herramientas',[]))}")
else:
    results.append((1, "FAIL", "catalogos not ok", 200, r.status_code, r.text[:80]))
    cat = {}

# ══ TEST 2 ══ Create servidor ─────────────────────────────────────────────────
tipo_id    = cat.get("tipos_servidor",[{}])[0].get("id","")
ambiente_id = cat.get("ambientes",[{}])[0].get("id","")
estado_id  = cat.get("estados_servidor",[{}])[0].get("id","")

new_srv = {
    "empresa_id":       empresa_id,
    "nombre":           "SRV-TEST-VERIF-01",
    "hostname":         "srv-test-verif-01.local",
    "tipo_servidor_id": tipo_id,
    "ambiente_id":      ambiente_id,
    "estado_id":        estado_id,
    "ip_lan":           "10.0.0.251",
    "procesador":       "Intel Xeon E5-2680",
    "memoria_ram":      "64 GB DDR4",
    "herramienta_ids":  [],
}
r = requests.post(f"{BASE}/servidores", json=new_srv, headers=h)
check(2, "POST /servidores -> 201", 201, r.status_code, r.text[:120] if not r.ok else "")
srv_id = None
if r.ok:
    srv_id = r.json().get("id")
    check(2, "created servidor has id", True, bool(srv_id))
    check(2, "hostname matches",
          "srv-test-verif-01.local", r.json().get("hostname"), "")

# ══ TEST 3 ══ Duplicate hostname blocked ──────────────────────────────────────
if srv_id:
    r2 = requests.post(f"{BASE}/servidores", json=new_srv, headers=h)
    check(3, "duplicate hostname -> 409", 409, r2.status_code, r2.json().get("detail",""))

# ══ TEST 4 ══ List & empresa filter ──────────────────────────────────────────
r = requests.get(f"{BASE}/servidores?empresa_id={empresa_id}", headers=h)
check(4, "GET /servidores?empresa_id -> 200", 200, r.status_code)
if r.ok:
    lista = r.json()
    found = any(s.get("id") == srv_id for s in lista)
    check(4, "created servidor appears in list", True, found, f"list has {len(lista)} items")

# ══ TEST 5 ══ Get detail with herramientas/servicios keys ────────────────────
if srv_id:
    r = requests.get(f"{BASE}/servidores/{srv_id}", headers=h)
    check(5, "GET /{id} -> 200", 200, r.status_code)
    if r.ok:
        d = r.json()
        check(5, "detail has herramientas list", True, "herramientas" in d)
        check(5, "detail has servicios list",    True, "servicios" in d)
        check(5, "ip_lan correct", "10.0.0.251", d.get("ip_lan"))

# ══ TEST 6 ══ Add herramienta + verify ───────────────────────────────────────
if srv_id and cat.get("herramientas"):
    herr_id = cat["herramientas"][0]["id"]
    r = requests.post(f"{BASE}/servidores/{srv_id}/herramientas",
                      json={"herramienta_id": herr_id, "estado": "instalado", "version": "6.4"},
                      headers=h)
    check(6, "POST /{id}/herramientas -> 201", 201, r.status_code,
          r.text[:100] if not r.ok else "")
    if r.ok:
        sh_id = r.json().get("id")
        # confirm it shows in detail
        detail = requests.get(f"{BASE}/servidores/{srv_id}", headers=h).json()
        in_list = any(h2["id"] == sh_id for h2 in detail.get("herramientas", []))
        check(6, "herramienta appears in detail", True, in_list)
        # remove it
        r_del = requests.delete(f"{BASE}/servidores/{srv_id}/herramientas/{sh_id}", headers=h)
        check(6, "DELETE herramienta -> 204", 204, r_del.status_code)

# ══ TEST 7 ══ Update + historial ─────────────────────────────────────────────
if srv_id:
    r = requests.put(f"{BASE}/servidores/{srv_id}",
                     json={"observaciones": "Test observacion verificacion"},
                     headers=h)
    check(7, "PUT /{id} -> 200", 200, r.status_code,
          r.text[:100] if not r.ok else "")
    if r.ok:
        check(7, "observaciones updated",
              "Test observacion verificacion", r.json().get("observaciones"))
    # historial
    rh = requests.get(f"{BASE}/servidores/{srv_id}/historial", headers=h)
    check(7, "GET /{id}/historial -> 200", 200, rh.status_code)
    if rh.ok:
        hist = rh.json()
        has_edicion = any(h2.get("tipo_cambio") == "edicion" for h2 in hist)
        check(7, "historial has edicion record", True, has_edicion,
              f"records: {[h2.get('tipo_cambio') for h2 in hist]}")

# ══ TEST 8 ══ Stats endpoint ─────────────────────────────────────────────────
r = requests.get(f"{BASE}/servidores/stats?empresa_id={empresa_id}", headers=h)
check(8, "GET /stats -> 200", 200, r.status_code)
if r.ok:
    s = r.json()
    check(8, "stats has total key", True, "total" in s)
    check(8, "stats total >= 1", True, s.get("total", 0) >= 1, f"total={s.get('total')}")

# ── Cleanup ───────────────────────────────────────────────────────────────────
if srv_id:
    requests.delete(f"{BASE}/servidores/{srv_id}", headers=h)
    print(f"  [Cleanup] Desactivado servidor de prueba {srv_id[:8]}...")

# ── Results ───────────────────────────────────────────────────────────────────
print()
print(f"{'#':<3} {'Result':<6} {'Expected':>8} {'Got':>6}  Description")
print("-" * 90)
for row in results:
    n, mark, desc, exp, got, detail = row
    es = str(exp) if not isinstance(exp, bool) else ("True" if exp else "False")
    gs = str(got) if not isinstance(got, bool) else ("True" if got else "False")
    print(f"{n:<3} {mark:<6} {es:>8} {gs:>6}  {desc}")
    if mark == "FAIL":
        print(f"    detail: {detail}")
print()
all_ok = all(r[1] in ("PASS", "SKIP") for r in results)
print("ALL TESTS PASSED" if all_ok else "SOME TESTS FAILED")
