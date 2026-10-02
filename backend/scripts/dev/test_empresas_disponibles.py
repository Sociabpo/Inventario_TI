import requests

BASE = "http://127.0.0.1:8000/api"

def login(email, pw):
    r = requests.post(f"{BASE}/auth/login", data={"username": email, "password": pw})
    if not r.ok:
        raise RuntimeError(f"Login failed for {email}: {r.status_code} {r.text}")
    return r.json()["access_token"]

def get_empresas(token):
    r = requests.get(f"{BASE}/rbac/empresas-disponibles",
                     headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.json()

cases = [
    ("super_admin", "admin@inventario.com", "Admin1234!"),
    ("auditoria (Socia only)", "auditor_sociabpo@test.com", "Test1234!"),
    ("analista (Socia only)", "analista_sociabpo@test.com", "Test1234!"),
]

for label, email, pw in cases:
    tok = login(email, pw)
    status, data = get_empresas(tok)
    print(f"--- {label} ---")
    print(f"  HTTP {status}  count={len(data)}")
    for e in data:
        nit = e.get("nit", "MISSING")
        print(f"  {e['prefijo']} | {e['nombre_empresa']} | nit={nit}")
    print()
