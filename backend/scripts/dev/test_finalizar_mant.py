# -*- coding: utf-8 -*-
"""Verifica el flujo de finalización de mantenimiento (CASO A: vuelve a asignado;
CASO B: pide destino)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass
import logging; logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

import uuid
from datetime import datetime
from fastapi.testclient import TestClient
import main
from database import SessionLocal
from routers.auth import get_current_user
from models.usuario_sistema import UsuarioSistema
from models.usuario import Usuario
from models.empresa import Empresa
from models.activo import Activo
from models.asignacion import Asignacion
from models.acta import Acta, ActaDetalle
from models.firma_token import FirmaToken
from models.cambio_estado import CambioEstado
from models.historial import HistorialMovimiento
from services.rbac_service import get_all_user_permissions

db = SessionLocal()
RESULTS = []
def check(n, c, e=""):
    RESULTS.append((n, bool(c), e)); print(f"  [{'PASS' if c else 'FALL'}] {n}" + (f"  ({e})" if e else ""))

admin = None
for u in db.query(UsuarioSistema).all():
    if {"estados.cambiar"} <= get_all_user_permissions(db, u.id):
        admin = u; break
assert admin
emp = db.query(Empresa).first()
empleado = db.query(Usuario).filter(Usuario.empresa_id == emp.id).first()
PREF = "ZZFM"
created = []
def mk(estado="disponible", asignado=False):
    a = Activo(id_placa_activo=f"{PREF}-{uuid.uuid4().hex[:6]}", empresa_id=emp.id, tipo_activo="Laptop",
               marca="T", estado=estado, ubicacion=None if asignado else "CT",
               id_usuario=empleado.id if asignado else None, costo=500)
    db.add(a); db.commit(); db.refresh(a); created.append(a); return a

main.app.dependency_overrides[get_current_user] = lambda: admin
client = TestClient(main.app)
print("\n── Finalización de mantenimiento ──")

# T1: asignado → mantenimiento SIN retiro
a1 = mk(estado="asignado", asignado=True)
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a1.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"correctivo","ubicacion":"Oficina TI","retira_del_usuario":False})
db.rollback()
a1o = db.get(Activo, a1.id)
ce1 = db.query(CambioEstado).filter(CambioEstado.recurso_id==a1.id).order_by(CambioEstado.fecha.desc()).first()
check("T1 mant sin retiro: id_usuario conservado", a1o.id_usuario==empleado.id, a1o.id_usuario)
check("T1b usuario_previo guardado en CambioEstado", ce1 and ce1.usuario_previo==empleado.id)
check("T1c estado en mantenimiento", a1o.estado=="mantenimiento_correctivo", a1o.estado)
check("T1d genero_acta=False", ce1 and ce1.genero_acta==False)

# T3 (info endpoint, antes de finalizar): CASO A detectado
r = client.get(f"/api/estados/mantenimiento-activo/activo/{a1.id}")
info = r.json()
check("T3 info: genero_acta False + usuario_previo_nombre presente",
      r.is_success and info["genero_acta"]==False and info["usuario_previo_nombre"]==empleado.nombre_completo,
      info.get("usuario_previo_nombre"))

# T2: finalizar CASO A → vuelve a asignado, sin pedir destino
r = client.post("/api/estados/finalizar-mantenimiento", json={"tipo_recurso":"activo","recurso_id":a1.id,
    "resultado":"exitoso","costo_real":80})
db.rollback()
a1o = db.get(Activo, a1.id)
check("T2 CASO A: vuelve a asignado", r.is_success and r.json().get("volvio_a_asignado")==True and a1o.estado=="asignado", a1o.estado)
check("T2b CASO A: mismo usuario restaurado", a1o.id_usuario==empleado.id and r.json().get("usuario_nombre")==empleado.nombre_completo)

# T7: CASO A con requiere_baja → 400 (re-creamos un activo en CASO A)
a7 = mk(estado="asignado", asignado=True)
client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a7.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"correctivo","ubicacion":"Oficina TI","retira_del_usuario":False})
db.rollback()
r = client.post("/api/estados/finalizar-mantenimiento", json={"tipo_recurso":"activo","recurso_id":a7.id,"resultado":"requiere_baja"})
check("T7 CASO A + requiere_baja → 400", r.status_code==400, f"HTTP {r.status_code}")

# T4: asignado → mantenimiento CON retiro → acta + id_usuario null
a4 = mk(estado="asignado", asignado=True)
asig = Asignacion(empresa_id=emp.id, id_activo=a4.id, id_usuario=empleado.id, estado="activa",
                  fecha_asignacion=datetime.utcnow(), asignado_por=admin.nombre, recibido_por=empleado.nombre_completo)
db.add(asig); db.commit()
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a4.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"correctivo","ubicacion":"Oficina TI","retira_del_usuario":True})
db.rollback()
a4o = db.get(Activo, a4.id)
check("T4 mant con retiro: acta generada + id_usuario null", r.json().get("genero_acta")==True and a4o.id_usuario is None)

# T5: finalizar CASO B destino disponible
r = client.post("/api/estados/finalizar-mantenimiento", json={"tipo_recurso":"activo","recurso_id":a4.id,
    "resultado":"exitoso","destino":"disponible","ubicacion":"CT"})
db.rollback()
a4o = db.get(Activo, a4.id)
check("T5 CASO B: vuelve a disponible", r.is_success and r.json().get("volvio_a_asignado")==False and a4o.estado=="disponible", a4o.estado)

# T6: disponible → mantenimiento (sin usuario) → CASO B
a6 = mk(estado="disponible")
client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a6.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"preventivo","ubicacion":"Oficina TI"})
db.rollback()
info6 = client.get(f"/api/estados/mantenimiento-activo/activo/{a6.id}").json()
caseA_front = (info6["genero_acta"]==False) and bool(info6["usuario_previo"])
r = client.post("/api/estados/finalizar-mantenimiento", json={"tipo_recurso":"activo","recurso_id":a6.id,
    "resultado":"exitoso","destino":"disponible","ubicacion":"Sede"})
db.rollback()
check("T6 sin usuario = CASO B (no vuelve a asignado)", caseA_front==False and r.json().get("volvio_a_asignado")==False and db.get(Activo,a6.id).estado=="disponible")

# T8: CASO B con requiere_baja → instruccion solicitar_baja
a8 = mk(estado="disponible")
client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":a8.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"correctivo","ubicacion":"Oficina TI"})
db.rollback()
r = client.post("/api/estados/finalizar-mantenimiento", json={"tipo_recurso":"activo","recurso_id":a8.id,"resultado":"requiere_baja"})
check("T8 CASO B + requiere_baja → solicitar_baja", r.is_success and r.json().get("instruccion")=="solicitar_baja")

# T9: HistorialMovimiento con mensaje correcto
db.rollback()
h_a1 = db.query(HistorialMovimiento).filter(HistorialMovimiento.id_activo==a1.id).all()
hist_caseA = any("asignado" in (h.observaciones or "") and "devuelto a" in (h.observaciones or "") for h in h_a1)
h_a4 = db.query(HistorialMovimiento).filter(HistorialMovimiento.id_activo==a4.id).all()
hist_caseB = any("→ disponible" in (h.observaciones or "") for h in h_a4)
check("T9 historial CASO A ('devuelto a ...') y CASO B ('→ disponible')", hist_caseA and hist_caseB)

# T10: hoja de vida muestra inicio y fin de mantenimiento
hv = client.get(f"/api/activos/{a1.id}/hoja-de-vida").json()
evs = hv.get("timeline") or hv.get("eventos") or []
s = str(hv).lower()
tiene_inicio = "mantenim" in s
tiene_fin = "finalizado" in s or "asignado" in s
check("T10 hoja de vida: inicio y fin de mantenimiento", tiene_inicio and tiene_fin, f"{len(evs)} eventos")

# Limpieza
db.rollback()
for a in created:
    db.query(FirmaToken).filter(FirmaToken.acta_id.in_(db.query(Acta.id).filter(Acta.id_activo==a.id))).delete(synchronize_session=False)
    db.query(ActaDetalle).filter(ActaDetalle.id_activo==a.id).delete(synchronize_session=False)
    db.query(Acta).filter(Acta.id_activo==a.id).delete(synchronize_session=False)
    db.query(Asignacion).filter(Asignacion.id_activo==a.id).delete(synchronize_session=False)
    db.query(HistorialMovimiento).filter(HistorialMovimiento.id_activo==a.id).delete(synchronize_session=False)
    db.query(CambioEstado).filter(CambioEstado.recurso_id==a.id).delete(synchronize_session=False)
for a in created:
    o = db.get(Activo, a.id)
    if o: db.delete(o)
db.commit()
print("Datos de prueba eliminados.")

ok = sum(1 for _,c,_ in RESULTS if c)
print(f"\n{'='*46}\nRESULTADO: {ok}/{len(RESULTS)} pruebas OK")
for n,c,e in RESULTS:
    if not c: print(f"  FALLÓ: {n}  {e}")
db.close()
sys.exit(0 if ok==len(RESULTS) else 1)
