# -*- coding: utf-8 -*-
"""Verificación end-to-end del módulo de cambio de estado / bajas (18 pruebas)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from fastapi.testclient import TestClient
from datetime import datetime
import uuid

import main
from database import SessionLocal
from routers.auth import get_current_user
from models.usuario_sistema import UsuarioSistema
from models.usuario import Usuario
from models.empresa import Empresa
from models.activo import Activo
from models.accesorio import Accesorio
from models.asignacion import Asignacion
from models.acta import Acta
from models.firma_token import FirmaToken
from models.cambio_estado import CambioEstado
from models.baja_activo import BajaActivo
from services.rbac_service import get_all_user_permissions

import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

db = SessionLocal()

RESULTS = []
def check(name, cond, extra=""):
    RESULTS.append((name, bool(cond), extra))
    print(f"  [{'PASS' if cond else 'FALL'}] {name}" + (f"  ({extra})" if extra else ""))

# ── Setup ──────────────────────────────────────────────────
admin = None
for u in db.query(UsuarioSistema).all():
    p = get_all_user_permissions(db, u.id)
    if "estados.cambiar" in p and "estados.aprobar_baja" in p:
        admin = u; break
assert admin, "No hay usuario con permisos estados.cambiar + aprobar_baja"
emp = db.query(Empresa).first()
empleado = db.query(Usuario).filter(Usuario.empresa_id == emp.id).first()
if not empleado:
    empleado = Usuario(empresa_id=emp.id, nombre_completo="Empleado Prueba CE",
                       documento="CE-TEST-001", cargo="Tester")
    db.add(empleado); db.commit(); db.refresh(empleado)

print(f"Empresa: {emp.nombre_empresa} | Admin: {admin.nombre} ({admin.rol}) | Empleado: {empleado.nombre_completo}")

PREF = "ZZTEST"
def _mk_activo(estado="disponible", asignado=False):
    a = Activo(id_placa_activo=f"{PREF}-{uuid.uuid4().hex[:6]}", empresa_id=emp.id,
               tipo_activo="Laptop", marca="TestBrand", modelo="T1", serial=uuid.uuid4().hex[:8],
               estado=estado, ubicacion=None if asignado else "CT",
               id_usuario=empleado.id if asignado else None, costo=1000)
    db.add(a); db.commit(); db.refresh(a)
    return a
def _mk_acc(estado="disponible"):
    a = Accesorio(id_placa_accesorio=f"{PREF}-{uuid.uuid4().hex[:6]}", empresa_id=emp.id,
                  tipo_accesorio="Mouse", marca="TestBrand", estado=estado, ubicacion="CT")
    db.add(a); db.commit(); db.refresh(a)
    return a

created_activos, created_acc, created_bajas = [], [], []

main.app.dependency_overrides[get_current_user] = lambda: admin
client = TestClient(main.app)
H = {}  # auth provided by override

print("\n── Pruebas ──")
# T1/T2: permisos sembrados
perms = get_all_user_permissions(db, admin.id)
check("T1 permiso estados.cambiar asignado", "estados.cambiar" in perms)
check("T2 permiso estados.aprobar_baja asignado", "estados.aprobar_baja" in perms)

# T3: disponible -> mantenimiento preventivo
a1 = _mk_activo(); created_activos.append(a1)
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a1.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"preventivo","ubicacion":"Oficina TI"})
db.rollback()
check("T3 mant preventivo", r.is_success and db.get(Activo,a1.id).estado=="mantenimiento_preventivo",
      r.json().get("estado") if r.is_success else r.text)

# T4: mantenimiento cubierto por garantía -> en_garantia
a2 = _mk_activo(); created_activos.append(a2)
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a2.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"correctivo","cubierto_garantia":True,
    "cubre_garantia":"fabricante","ubicacion":"Oficina TI"})
db.rollback()
check("T4 en_garantia", r.is_success and db.get(Activo,a2.id).estado=="en_garantia", r.json().get("estado") if r.is_success else r.text)

# T5: activo a reparación externa -> en_reparacion
a3 = _mk_activo(); created_activos.append(a3)
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a3.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"correctivo","ubicacion":"Donde proveedor"})
db.rollback()
check("T5 en_reparacion (externa)", r.is_success and db.get(Activo,a3.id).estado=="en_reparacion", r.json().get("estado") if r.is_success else r.text)

# T6: accesorio NO acepta reparación externa
ac1 = _mk_acc(); created_acc.append(ac1)
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"accesorio","recurso_id":ac1.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"correctivo","ubicacion":"Donde proveedor"})
check("T6 accesorio rechaza reparación externa", r.status_code==400, f"HTTP {r.status_code}")

# T7: finalizar mantenimiento -> disponible
r = client.post("/api/estados/finalizar-mantenimiento", json={"tipo_recurso":"activo","recurso_id":a1.id,
    "resultado":"exitoso","costo_real":120.5,"destino":"disponible","ubicacion":"CT"})
db.rollback()
check("T7 finalizar mant -> disponible", r.is_success and db.get(Activo,a1.id).estado=="disponible", r.text if not r.is_success else "")

# T8: asignado -> mantenimiento con retiro => acta devolución + firma token + asignación devuelta
a4 = _mk_activo(estado="asignado", asignado=True); created_activos.append(a4)
asig = Asignacion(empresa_id=emp.id, id_activo=a4.id, id_usuario=empleado.id, estado="activa",
                  fecha_asignacion=datetime.utcnow(), asignado_por=admin.nombre, recibido_por=empleado.nombre_completo)
db.add(asig); db.commit(); db.refresh(asig)
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a4.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"correctivo","ubicacion":"Oficina TI",
    "retira_del_usuario":True})
db.rollback()
acta_id = r.json().get("acta_id") if r.is_success else None
ft = db.query(FirmaToken).filter(FirmaToken.acta_id==acta_id).first() if acta_id else None
check("T8 acta devolución generada", r.is_success and r.json().get("genero_acta") and acta_id is not None)
check("T8b firma token creado", ft is not None)
check("T8c asignación marcada devuelta", db.get(Asignacion,asig.id).estado=="devuelta")
check("T8d activo sin usuario", db.get(Activo,a4.id).id_usuario is None)

# T9: asignado -> mantenimiento SIN retiro => conserva asignación
a5 = _mk_activo(estado="asignado", asignado=True); created_activos.append(a5)
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a5.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"preventivo","ubicacion":"Oficina TI",
    "retira_del_usuario":False})
db.rollback()
check("T9 sin retiro conserva usuario", r.is_success and db.get(Activo,a5.id).id_usuario==empleado.id
      and not r.json().get("genero_acta"))

# T10: /cambiar con retirado => rechazado (usar baja)
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a2.id,
    "estado_nuevo":"retirado","ubicacion":"CT"})
check("T10 /cambiar retirado rechazado", r.status_code==400, f"HTTP {r.status_code}")

# T11: solicitar-baja sobre asignado => rechazado
a6 = _mk_activo(estado="asignado", asignado=True); created_activos.append(a6)
r = client.post("/api/estados/solicitar-baja", json={"tipo_recurso":"activo","recurso_id":a6.id,
    "motivo":"retiro_operacion","justificacion":"prueba"})
check("T11 baja sobre asignado rechazada", r.status_code==400, f"HTTP {r.status_code}")

# T12: solicitar-baja sobre disponible => BAJA-YYYY-NNN
a7 = _mk_activo(); created_activos.append(a7)
r = client.post("/api/estados/solicitar-baja", json={"tipo_recurso":"activo","recurso_id":a7.id,
    "motivo":"vendido","justificacion":"obsoleto","valor_venta":50,"comprador":"Juan"})
nb1 = r.json().get("numero_baja") if r.is_success else None
if r.is_success: created_bajas.append(r.json()["id"])
import re
check("T12 baja creada formato BAJA-YYYY-NNN", bool(nb1 and re.match(r"^BAJA-\d{4}-\d{3}$", nb1)), nb1 or r.text)

# T13: numeración secuencial por empresa/año
a8 = _mk_activo(); created_activos.append(a8)
r = client.post("/api/estados/solicitar-baja", json={"tipo_recurso":"activo","recurso_id":a8.id,
    "motivo":"donado","justificacion":"donación","entidad_receptora":"Fundación"})
nb2 = r.json().get("numero_baja") if r.is_success else None
if r.is_success: created_bajas.append(r.json()["id"])
seq_ok = nb1 and nb2 and int(nb2.split("-")[-1]) == int(nb1.split("-")[-1]) + 1
check("T13 numeración secuencial", seq_ok, f"{nb1} -> {nb2}")

# T14: GET /bajas incluye pendientes
r = client.get(f"/api/estados/bajas?empresa_id={emp.id}&estado=pendiente")
ids = [b["id"] for b in r.json()] if r.is_success else []
check("T14 listado de bajas pendientes", r.is_success and created_bajas[0] in ids, f"{len(ids)} pendientes")

# T15: aprobar baja => recurso retirado + pdf + estado aprobada
baja_id = created_bajas[0]
r = client.post(f"/api/estados/bajas/{baja_id}/aprobar", json={"observaciones_aprobador":"OK"})
db.rollback()
b_obj = db.get(BajaActivo, baja_id)
check("T15 baja aprobada", r.is_success and b_obj.estado_aprobacion=="aprobada", r.text if not r.is_success else "")
check("T15b recurso retirado", db.get(Activo,a7.id).estado=="retirado")
check("T15c PDF generado", bool(b_obj.url_pdf), b_obj.url_pdf or "sin pdf")

# T16: retirado excluido del listado por defecto
r = client.get(f"/api/activos?empresa_id={emp.id}")
placas = [x["id_placa_activo"] for x in r.json()] if r.is_success else []
check("T16 retirado excluido del listado", a7.id_placa_activo not in placas)

# T17: retirado visible con incluir_retirados=true
r = client.get(f"/api/activos?empresa_id={emp.id}&incluir_retirados=true")
placas2 = [x["id_placa_activo"] for x in r.json()] if r.is_success else []
check("T17 retirado visible con incluir_retirados", a7.id_placa_activo in placas2)

# T18: rechazar baja => rechazada, recurso NO retirado
baja_id2 = created_bajas[1]
r = client.post(f"/api/estados/bajas/{baja_id2}/rechazar", json={"observaciones_aprobador":"no procede"})
db.rollback()
check("T18 baja rechazada", r.is_success and db.get(BajaActivo,baja_id2).estado_aprobacion=="rechazada"
      and db.get(Activo,a8.id).estado!="retirado")

# Extra: cambio aparece en hoja de vida
r = client.get(f"/api/activos/{a3.id}/hoja-de-vida")
hv = r.json() if r.is_success else {}
tl = str(hv)
check("EXTRA cambio en hoja de vida", r.is_success and ("reparaci" in tl.lower() or "en_reparacion" in tl.lower() or "mantenim" in tl.lower()))

# ── Limpieza ───────────────────────────────────────────────
print("\n── Limpieza de datos de prueba ──")
db.rollback()
for bid in created_bajas:
    b = db.get(BajaActivo, bid)
    if b: db.delete(b)
db.query(CambioEstado).filter(CambioEstado.placa.like(f"{PREF}-%")).delete(synchronize_session=False)
# actas/firmas/asignaciones de prueba
for a in created_activos:
    db.query(FirmaToken).filter(FirmaToken.acta_id.in_(
        db.query(Acta.id).filter(Acta.id_activo==a.id))).delete(synchronize_session=False)
    from models.acta import ActaDetalle
    db.query(ActaDetalle).filter(ActaDetalle.id_activo==a.id).delete(synchronize_session=False)
    db.query(Acta).filter(Acta.id_activo==a.id).delete(synchronize_session=False)
    db.query(Asignacion).filter(Asignacion.id_activo==a.id).delete(synchronize_session=False)
    from models.historial import HistorialMovimiento
    db.query(HistorialMovimiento).filter(HistorialMovimiento.id_activo==a.id).delete(synchronize_session=False)
for a in created_activos:
    obj = db.get(Activo, a.id)
    if obj: db.delete(obj)
for a in created_acc:
    obj = db.get(Accesorio, a.id)
    if obj: db.delete(obj)
db.commit()
print("Datos de prueba eliminados.")

# ── Resumen ────────────────────────────────────────────────
ok = sum(1 for _,c,_ in RESULTS if c)
print(f"\n{'='*48}\nRESULTADO: {ok}/{len(RESULTS)} pruebas OK")
for name, c, extra in RESULTS:
    if not c:
        print(f"  FALLÓ: {name}  {extra}")
db.close()
sys.exit(0 if ok==len(RESULTS) else 1)
