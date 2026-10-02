"""Verificación del sistema de recordatorios de firma (in-process)."""
import sys, os, logging, io, uuid
from contextlib import redirect_stdout
from datetime import datetime, timedelta, date
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
try: sys.stdout.reconfigure(encoding="utf-8")
except Exception: pass

from database import engine, SessionLocal; engine.echo = False
import services.email_service as es
import main
from routers.auth import get_current_user
from models.usuario_sistema import UsuarioSistema
from models.usuario import Usuario
from models.acta import Acta
from models.firma_token import FirmaToken
from models.recordatorio_firma import RecordatorioFirma
from sqlalchemy import text

EMP = "09a4a3d5-2286-45da-99e9-54c0f5de5a7a"  # Socia BPO
sent = []
async def fake_rec(**k): sent.append(k); return True
async def fake_adm(**k): sent.append({"__admin__": True, **k}); return True
es.enviar_recordatorio_firma = fake_rec
es.enviar_alerta_admin_firma = fake_adm

from services.recordatorio_service import procesar_recordatorios

db = SessionLocal()
R = []
def chk(n, d, ok): R.append((n, d, "PASS" if ok else "FAIL"))

# Snapshot de recordatorios_enviados de actas existentes (para restaurar)
snapshot = {a.id: a.recordatorios_enviados for a in db.query(Acta).all()}

# Usuarios de prueba
u_ok = Usuario(empresa_id=EMP, documento="REC-"+uuid.uuid4().hex[:6], nombre_completo="Empleado Rec", correo="rec.test@empresa.com", estado="activo")
u_no = Usuario(empresa_id=EMP, documento="REC-"+uuid.uuid4().hex[:6], nombre_completo="Empleado SinCorreo", correo=None, estado="activo")
db.add_all([u_ok, u_no]); db.flush()

def mk(**kw):
    base = dict(empresa_id=EMP, id_usuario=u_ok.id, tipo="entrega", responsable_entrega="TI Test",
                responsable_recibe="X", firmada=False, recordatorios_enviados=0)
    base.update(kw)
    a = Acta(**base); db.add(a); db.flush(); return a

ahora = datetime.now()
A3      = mk(fecha_entrega=ahora - timedelta(days=3))                                   # test 3,4,15
A_fut   = mk(fecha_entrega=ahora, es_anticipada=True, fecha_inicio_vigencia=date.today()+timedelta(days=10))  # 5
A_ant3  = mk(fecha_entrega=ahora, es_anticipada=True, fecha_inicio_vigencia=date.today()-timedelta(days=3))   # 6
A_antN  = mk(fecha_entrega=ahora, es_anticipada=True, fecha_inicio_vigencia=None)       # 7
A_firm  = mk(fecha_entrega=ahora - timedelta(days=3), firmada=True)                     # 8
A_dev   = mk(fecha_entrega=ahora - timedelta(days=3), tipo="devolucion")               # 9
A_max   = mk(fecha_entrega=ahora - timedelta(days=5), recordatorios_enviados=3)        # 10
A6      = mk(fecha_entrega=ahora - timedelta(days=6))                                   # 11 (escala)
A_nc    = mk(fecha_entrega=ahora - timedelta(days=3), id_usuario=u_no.id)              # 12
db.commit()
ids = {x.id for x in [A3,A_fut,A_ant3,A_antN,A_firm,A_dev,A_max,A6,A_nc]}

# ── Ejecutar (capturando logs) ──
buf = io.StringIO()
with redirect_stdout(buf):
    procesar_recordatorios()
log = buf.getvalue()

def rec(a_id):
    db.rollback()
    return db.query(Acta).filter(Acta.id == a_id).first().recordatorios_enviados
def tiene_recordatorio(a_id, escalado=False):
    db.rollback()
    return db.query(RecordatorioFirma).filter(RecordatorioFirma.acta_id == a_id, RecordatorioFirma.escalado_admin == escalado).first() is not None

chk(3, "acta normal 3d -> recordatorio enviado (rec=1)", rec(A3.id) == 1 and tiene_recordatorio(A3.id))
# 4: segunda corrida inmediata -> cooldown
buf2 = io.StringIO()
with redirect_stdout(buf2): procesar_recordatorios()
chk(4, "segunda corrida -> NO reenvía (cooldown 23h)", rec(A3.id) == 1)
chk(5, "anticipada futura -> ignorada", rec(A_fut.id) == 0 and "ignorada — empleado ingresa el" in log)
chk(6, "anticipada con fecha pasada -> enviado", rec(A_ant3.id) == 1)
chk(7, "anticipada sin fecha -> ignorada", rec(A_antN.id) == 0 and "anticipada sin fecha de ingreso" in log)
chk(8, "acta firmada -> no procesada", rec(A_firm.id) == 0)
chk(9, "acta devolucion -> no procesada", rec(A_dev.id) == 0)
chk(10, "acta con MAX recordatorios -> no procesada", rec(A_max.id) == 3)
chk(11, "acta 6d -> enviado + escalado a admin", rec(A6.id) == 1 and tiene_recordatorio(A6.id, escalado=True))
chk(12, "empleado sin correo -> aviso manual", rec(A_nc.id) == 0 and "sin correo registrado" in log)
# 15: firma_url correcto
url_a3 = next((k.get("firma_url") for k in sent if k.get("numero_acta") and A3.id[:8] in (k.get("numero_acta") or "")), None)
db.rollback()
tok = db.query(FirmaToken).filter(FirmaToken.acta_id == A3.id).first()
chk(15, "firma_url correcto con token válido", bool(tok) and any((k.get("firma_url") or "").endswith(tok.token) for k in sent))

# 13,14: datos para UI (GET /actas devuelve es_anticipada + configurar-vigencia)
from fastapi.testclient import TestClient
SUP = db.query(UsuarioSistema).filter_by(email="admin@inventario.com").first()
AUD = db.query(UsuarioSistema).filter_by(email="auditor_sociabpo@test.com").first()
c = TestClient(main.app)
main.app.dependency_overrides[get_current_user] = lambda: SUP
r = c.post(f"/api/actas/{A_firm.id}/configurar-vigencia", json={"es_anticipada": False})  # firmada -> 400
r2 = c.post(f"/api/actas/{A3.id}/configurar-vigencia", json={"es_anticipada": True, "fecha_inicio_vigencia": "2026-01-15"})
lst = c.get("/api/actas?empresa_id="+EMP).json()
a3row = next((x for x in lst if x["id"] == A3.id), {})
chk(13, "configurar-vigencia (firmada->400, ok->200)", r.status_code == 400 and r2.status_code == 200)
chk(14, "GET /actas expone es_anticipada/fecha", a3row.get("es_anticipada") is True and "recordatorios_enviados" in a3row)

# Test 1 y 2: scheduler + endpoint admin
buf3 = io.StringIO()
with redirect_stdout(buf3):
    with TestClient(main.app) as cc:
        pass  # dispara startup/shutdown
sched_log = buf3.getvalue()
chk(1, "startup registra scheduler 2:00 PM", "Recordatorio de firmas programado" in sched_log)
r_sa = c.post("/api/admin/recordatorios/ejecutar-ahora")
main.app.dependency_overrides[get_current_user] = lambda: AUD
r_au = c.post("/api/admin/recordatorios/ejecutar-ahora")
chk(2, "trigger manual: super_admin 200 / auditoria 403", r_sa.status_code == 200 and r_au.status_code == 403)
main.app.dependency_overrides.clear()

# ── Limpieza ──
import time; time.sleep(1)  # dejar terminar el thread del trigger manual
db.rollback()
db.execute(text("DELETE FROM recordatorios_firma"))  # tabla nueva, estaba vacía
db.execute(text("DELETE FROM firma_tokens WHERE acta_id IN :ids").bindparams(__import__('sqlalchemy').bindparam('ids', expanding=True)), {"ids": list(ids)})
db.execute(text("DELETE FROM acta_detalle WHERE acta_id IN :ids").bindparams(__import__('sqlalchemy').bindparam('ids', expanding=True)), {"ids": list(ids)})
db.execute(text("DELETE FROM actas_entrega WHERE id IN :ids").bindparams(__import__('sqlalchemy').bindparam('ids', expanding=True)), {"ids": list(ids)})
db.execute(text("DELETE FROM usuarios WHERE id IN :ids").bindparams(__import__('sqlalchemy').bindparam('ids', expanding=True)), {"ids": [u_ok.id, u_no.id]})
# restaurar contadores de actas existentes
for aid, val in snapshot.items():
    db.execute(text("UPDATE actas_entrega SET recordatorios_enviados=:v WHERE id=:i"), {"v": val, "i": aid})
db.commit(); db.close()

print()
for n, d, e in sorted(R):
    print(f"  [{e}] {n:>2}. {d}")
ok = sum(1 for *_, e in R if e == "PASS")
print(f"\n{ok}/{len(R)} PASARON")
