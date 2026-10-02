"""Verificación end-to-end del módulo Compras (in-process con TestClient)."""
import sys, os, logging, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

from database import engine, SessionLocal
engine.echo = False

from fastapi.testclient import TestClient
import main
from routers.auth import get_current_user
from models.usuario_sistema import UsuarioSistema

EMP_SOCIA = "09a4a3d5-2286-45da-99e9-54c0f5de5a7a"
EMP_AUTO  = "3a7a8133-25a7-44ab-a345-70fa0b6d8f6b"

db = SessionLocal()
SUPER = db.query(UsuarioSistema).filter_by(email="admin@inventario.com").first()
AUDIT = db.query(UsuarioSistema).filter_by(email="auditor_sociabpo@test.com").first()
client = TestClient(main.app)

def actuar_como(u):
    main.app.dependency_overrides[get_current_user] = lambda: u

resultados = []
def chk(n, desc, esperado, obtenido, ok):
    resultados.append((n, desc, esperado, obtenido, "PASS" if ok else "FAIL"))

ctx = {}

# 1. Crear proveedor
actuar_como(SUPER)
r = client.post("/api/compras/proveedores", json={
    "empresa_id": EMP_SOCIA, "nombre": "Proveedor Demo SAS", "nit": "900-" + uuid.uuid4().hex[:8], "tipo": "vendedor"})
ctx["proveedor_id"] = r.json().get("id") if r.status_code == 201 else None
chk(1, "POST /proveedores", "201", r.status_code, r.status_code == 201)

# 2. Crear solicitud con 2 ítems + título + numero autogenerado
r = client.post("/api/compras/solicitudes", json={
    "empresa_id": EMP_SOCIA, "titulo": "Renovación equipos comercial", "justificacion": "Renovación de equipos", "observaciones": "Urgente",
    "items": [
        {"descripcion": "Portátil Dell", "tipo_item": "activo", "tipo_adquisicion": "compra", "cantidad": 1, "valor_unitario_estimado": 3000000},
        {"descripcion": "Mouse inalámbrico", "tipo_item": "accesorio", "tipo_adquisicion": "compra", "cantidad": 1},
    ]})
j = r.json() if r.status_code == 201 else {}
ctx["solicitud_id"] = j.get("id")
import re as _re
num_ok = bool(_re.match(r"^SC-\d{4}-\d{3}$", j.get("numero_solicitud", "")))
ok2 = r.status_code == 201 and j.get("items_count") == 2 and j.get("titulo") == "Renovación equipos comercial" and num_ok
chk(2, "POST /solicitudes (título+N°+2 ítems)", "201 + N° SC-YYYY-NNN", f"{r.status_code} {j.get('numero_solicitud')} items={j.get('items_count')}", ok2)

# 3. Enviar a aprobación
r = client.put(f"/api/compras/solicitudes/{ctx['solicitud_id']}/enviar")
est = r.json().get("estado") if r.is_success else None
chk(3, "PUT /solicitudes/{id}/enviar", "200 + pendiente_aprobacion", f"{r.status_code} {est}",
    r.status_code == 200 and est == "pendiente_aprobacion")

# 4. Aprobar
r = client.post(f"/api/compras/solicitudes/{ctx['solicitud_id']}/aprobar", json={})
est = r.json().get("estado") if r.is_success else None
chk(4, "POST /solicitudes/{id}/aprobar", "200 + aprobada", f"{r.status_code} {est}",
    r.status_code == 200 and est == "aprobada")

# 5. Crear OC
r = client.post("/api/compras/ordenes", json={
    "solicitud_id": ctx["solicitud_id"], "proveedor_id": ctx["proveedor_id"],
    "numero_oc": "OC-0001", "tipo": "compra", "fecha_emision": "2026-06-01", "valor_total": 3050000})
ctx["orden_id"] = r.json().get("id") if r.status_code == 201 else None
chk(5, "POST /ordenes", "201", r.status_code, r.status_code == 201)

# 6. Crear recepción
r = client.post("/api/compras/recepciones", json={
    "orden_compra_id": ctx["orden_id"], "fecha_recepcion": "2026-06-02",
    "items": [{"descripcion": "Portátil Dell", "cantidad_esperada": 1, "cantidad_recibida": 1, "estado": "ok", "serial": "SN-DEMO-001"}]})
j = r.json() if r.status_code == 201 else {}
ctx["recepcion_id"] = j.get("id")
ctx["rec_item_id"] = j.get("items", [{}])[0].get("id") if j.get("items") else None
chk(6, "POST /recepciones", "201", r.status_code, r.status_code == 201)

# 7. Crear inventario
r = client.post(f"/api/compras/recepciones/{ctx['recepcion_id']}/crear-inventario", json={
    "items": [{"recepcion_item_id": ctx["rec_item_id"], "empresa_id": EMP_SOCIA,
               "tipo_activo": "Portátil", "marca": "Dell", "modelo": "Latitude", "serial": "SN-DEMO-001"}]})
j = r.json() if r.status_code == 201 else {}
creados = j.get("creados", [])
ok7 = r.status_code == 201 and len(creados) == 1 and creados[0].get("tipo") == "activo"
chk(7, "POST /recepciones/{id}/crear-inventario", "201 + activo creado", f"{r.status_code} creados={len(creados)}", ok7)

# 8. Stats
r = client.get("/api/compras/stats")
j = r.json() if r.is_success else {}
claves = {"solicitudes_pendientes_aprobacion", "ordenes_pendientes_recepcion", "facturas_por_vencer",
          "facturas_vencidas", "garantias_por_vencer", "contratos_por_vencer", "total_compras_mes", "equipos_en_alquiler"}
ok8 = r.status_code == 200 and claves.issubset(j.keys())
chk(8, "GET /stats", "200 + 8 claves", f"{r.status_code} keys={len(j)}", ok8)

# 9. auditoria no puede crear solicitud
actuar_como(AUDIT)
r = client.post("/api/compras/solicitudes", json={"empresa_id": EMP_SOCIA, "justificacion": "x", "items": []})
chk(9, "auditoria POST /solicitudes", "403", r.status_code, r.status_code == 403)

# 10. Scoping multiempresa: crear solicitud en Autoamerica (super) y verificar que auditor (solo Socia) NO la ve
actuar_como(SUPER)
r = client.post("/api/compras/solicitudes", json={
    "empresa_id": EMP_AUTO, "titulo": "Compra Autoamerica", "justificacion": "Solicitud Autoamerica",
    "items": [{"descripcion": "Equipo", "tipo_item": "activo", "tipo_adquisicion": "compra", "cantidad": 1}]})
otra_id = r.json().get("id") if r.status_code == 201 else None
actuar_como(AUDIT)
r = client.get("/api/compras/solicitudes")
lista = r.json() if r.is_success else []
empresas_vistas = {s["empresa_id"] for s in lista}
ok10 = (r.status_code == 200 and otra_id not in {s["id"] for s in lista}
        and empresas_vistas.issubset({EMP_SOCIA}))
chk(10, "GET /solicitudes scoping (auditor solo Socia)", "solo Socia BPO",
    f"empresas_vistas={empresas_vistas}", ok10)

# 11. Cancelar una solicitud en borrador → 200 + cancelada
actuar_como(SUPER)
r = client.post("/api/compras/solicitudes", json={
    "empresa_id": EMP_SOCIA, "titulo": "A cancelar", "justificacion": "prueba cancelación",
    "items": [{"descripcion": "X", "tipo_item": "activo", "tipo_adquisicion": "compra", "cantidad": 1}]})
cid = r.json().get("id")
r = client.post(f"/api/compras/solicitudes/{cid}/cancelar", json={"motivo_cancelacion": "Ya no se requiere"})
est = r.json().get("estado") if r.is_success else None
chk(11, "POST /solicitudes/{id}/cancelar (borrador)", "200 + cancelada", f"{r.status_code} {est}",
    r.status_code == 200 and est == "cancelada")

# 12. Cancelar una solicitud aprobada → 400 bloqueado
r = client.post("/api/compras/solicitudes", json={
    "empresa_id": EMP_SOCIA, "titulo": "Aprobada no cancelable", "justificacion": "x",
    "items": [{"descripcion": "Y", "tipo_item": "activo", "tipo_adquisicion": "compra", "cantidad": 1}]})
aid = r.json().get("id")
client.put(f"/api/compras/solicitudes/{aid}/enviar")
client.post(f"/api/compras/solicitudes/{aid}/aprobar", json={})
r = client.post(f"/api/compras/solicitudes/{aid}/cancelar", json={"motivo_cancelacion": "tarde"})
chk(12, "cancelar solicitud aprobada", "400 bloqueado", r.status_code, r.status_code == 400)

main.app.dependency_overrides.clear()
db.close()

# ── Reporte ──
print("\n" + "=" * 92)
print(f"| {'#':<2} | {'Prueba':<42} | {'Esperado':<22} | {'Resultado':<7} |")
print("=" * 92)
for n, desc, esp, obt, estado in resultados:
    print(f"| {n:<2} | {desc[:42]:<42} | {str(esp)[:22]:<22} | {estado:<7} |")
print("=" * 92)
ok = sum(1 for *_, e in resultados if e == "PASS")
print(f"\n{ok}/{len(resultados)} pruebas PASARON")
sys.exit(0 if ok == len(resultados) else 1)
