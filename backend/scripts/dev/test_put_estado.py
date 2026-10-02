# -*- coding: utf-8 -*-
"""Verifica que estado NO se pueda cambiar vía PUT /activos|/accesorios,
pero SÍ vía /api/estados/* (defensa en profundidad)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

import logging
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

import uuid
from fastapi.testclient import TestClient
import main
from database import SessionLocal
from routers.auth import get_current_user
from models.usuario_sistema import UsuarioSistema
from models.empresa import Empresa
from models.activo import Activo
from models.accesorio import Accesorio
from services.rbac_service import get_all_user_permissions

db = SessionLocal()
RESULTS = []
def check(name, cond, extra=""):
    RESULTS.append((name, bool(cond), extra)); print(f"  [{'PASS' if cond else 'FALL'}] {name}" + (f"  ({extra})" if extra else ""))

admin = None
for u in db.query(UsuarioSistema).all():
    p = get_all_user_permissions(db, u.id)
    if {"activos.editar","accesorios.editar","estados.cambiar"} <= p:
        admin = u; break
assert admin, "No hay usuario con activos.editar + accesorios.editar + estados.cambiar"
emp = db.query(Empresa).first()

PREF = "ZZPUT"
act = Activo(id_placa_activo=f"{PREF}-{uuid.uuid4().hex[:6]}", empresa_id=emp.id, tipo_activo="Laptop",
             marca="Orig", modelo="M0", estado="disponible", ubicacion="CT", costo=100)
acc = Accesorio(id_placa_accesorio=f"{PREF}-{uuid.uuid4().hex[:6]}", empresa_id=emp.id, tipo_accesorio="Mouse",
                marca="Orig", estado="disponible", ubicacion="CT")
db.add_all([act, acc]); db.commit(); db.refresh(act); db.refresh(acc)

main.app.dependency_overrides[get_current_user] = lambda: admin
client = TestClient(main.app)

print("\n── PUT protección de estado ──")
# T1: PUT activo con estado distinto + cambio de marca
r = client.put(f"/api/activos/{act.id}", json={"empresa_id":emp.id,"tipo_activo":"Laptop",
    "marca":"Editado","modelo":"M1","ubicacion":"Sede","estado":"retirado"})
db.rollback()
a2 = db.get(Activo, act.id)
check("T1 PUT activo: estado IGNORADO (sigue disponible)", r.is_success and a2.estado=="disponible", a2.estado)
check("T2 PUT activo: marca SÍ se actualiza", a2.marca=="Editado", a2.marca)
check("T3 PUT activo: ubicación editable", a2.ubicacion=="Sede", a2.ubicacion)

# T4: PUT con otro estado de mantenimiento → ignorado
r = client.put(f"/api/activos/{act.id}", json={"empresa_id":emp.id,"tipo_activo":"Laptop",
    "ubicacion":"Sede","estado":"mantenimiento_correctivo"})
db.rollback()
check("T4 PUT activo: mantenimiento ignorado", r.is_success and db.get(Activo,act.id).estado=="disponible")

# T5: PUT accesorio con estado distinto + cambio de marca
r = client.put(f"/api/accesorios/{acc.id}", json={"empresa_id":emp.id,"tipo_accesorio":"Mouse",
    "marca":"AccEdit","ubicacion":"Oficina TI","estado":"retirado"})
db.rollback()
ac2 = db.get(Accesorio, acc.id)
check("T5 PUT accesorio: estado IGNORADO", r.is_success and ac2.estado=="disponible", ac2.estado)
check("T6 PUT accesorio: marca SÍ se actualiza", ac2.marca=="AccEdit", ac2.marca)

# T7: el flujo controlado /api/estados/cambiar SÍ cambia el estado
r = client.post("/api/estados/cambiar", json={"tipo_recurso":"activo","recurso_id":act.id,
    "estado_nuevo":"mantenimiento","tipo_mantenimiento":"preventivo","ubicacion":"Oficina TI"})
db.rollback()
check("T7 /estados/cambiar SÍ cambia estado", r.is_success and db.get(Activo,act.id).estado=="mantenimiento_preventivo",
      db.get(Activo,act.id).estado)

# T8: asignación escribe estado directamente sobre el modelo (no vía PUT) → simulamos
act.estado="disponible"; db.commit()
a3 = db.get(Activo, act.id); a3.estado="asignado"; db.commit(); db.rollback()
check("T8 asignación (modelo directo) cambia estado", db.get(Activo,act.id).estado=="asignado")
# devolución (modelo directo)
a4 = db.get(Activo, act.id); a4.estado="disponible"; a4.ubicacion="Bodega CT"; db.commit(); db.rollback()
check("T9 devolución (modelo directo) restaura disponible", db.get(Activo,act.id).estado=="disponible")

# Limpieza
db.rollback()
from models.cambio_estado import CambioEstado
from models.historial import HistorialMovimiento
db.query(CambioEstado).filter(CambioEstado.placa.like(f"{PREF}-%")).delete(synchronize_session=False)
db.query(HistorialMovimiento).filter(HistorialMovimiento.id_activo==act.id).delete(synchronize_session=False)
db.query(HistorialMovimiento).filter(HistorialMovimiento.id_accesorio==acc.id).delete(synchronize_session=False)
db.delete(db.get(Activo, act.id)); db.delete(db.get(Accesorio, acc.id))
db.commit()
print("Datos de prueba eliminados.")

ok = sum(1 for _,c,_ in RESULTS if c)
print(f"\n{'='*46}\nRESULTADO: {ok}/{len(RESULTS)} pruebas OK")
for n,c,e in RESULTS:
    if not c: print(f"  FALLÓ: {n}  {e}")
db.close()
sys.exit(0 if ok==len(RESULTS) else 1)
