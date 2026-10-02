"""Verificación del flujo OTP de firma (in-process, TestClient)."""
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from datetime import datetime, timedelta
import uuid
from database import engine, SessionLocal
engine.echo = False

from fastapi.testclient import TestClient
import main
import routers.firma as fm
from models.usuario import Usuario
from models.acta import Acta
from models.firma_token import FirmaToken
from models.otp_token import OtpToken

EMP_SOCIA = "09a4a3d5-2286-45da-99e9-54c0f5de5a7a"

# Simular envío de correo (no SMTP real) → True
async def _fake_enviar_otp(**kwargs):
    return True
fm.enviar_otp = _fake_enviar_otp

db = SessionLocal()
R = []
def chk(n, desc, esperado, obtenido, ok):
    R.append((n, desc, esperado, obtenido, "PASS" if ok else "FAIL"))

# ── Datos de prueba: usuario con correo + acta + firma_token ──
u = Usuario(empresa_id=EMP_SOCIA, documento="OTP-" + uuid.uuid4().hex[:6],
            nombre_completo="Empleado OTP Test", correo="juan.perez@empresa.com", estado="activo")
db.add(u); db.flush()
acta = Acta(empresa_id=EMP_SOCIA, id_usuario=u.id, tipo="entrega",
            responsable_entrega="TI Test", responsable_recibe="Empleado OTP Test")
db.add(acta); db.flush()
tok = FirmaToken(acta_id=acta.id, token=str(uuid.uuid4()),
                 expires_at=datetime.now() + timedelta(hours=72))
db.add(tok); db.commit()
TOKEN = tok.token
FT_ID = tok.id

client = TestClient(main.app)

def _codigo_activo():
    db.rollback()  # cerrar la transacción para ver commits de las peticiones
    return db.query(OtpToken).filter(OtpToken.firma_token_id == FT_ID, OtpToken.usado == False)\
        .order_by(OtpToken.created_at.desc()).first()

try:
    # Test 6 (precondición): firmar SIN OTP → 403
    r = client.post(f"/firmar/{TOKEN}", json={"firma_base64": "data:image/png;base64," + "A" * 80})
    chk(6, "POST /firmar sin OTP", "403", r.status_code, r.status_code == 403)

    # Test 1: la página muestra la tarjeta OTP y el resto gris
    r = client.get(f"/firmar/{TOKEN}")
    html = r.text
    ok1 = (r.status_code == 200 and "otp-card" in html and "btn-solicitar-otp" in html
           and "requires-otp" in html and "opacity:0.4" in html and "jua***@empresa.com" in html)
    chk(1, "GET /firmar: tarjeta OTP + resto gris", "OTP visible, resto opacity:0.4", f"{r.status_code}", ok1)

    # Test 2: solicitar OTP → 200, correo enmascarado, sin exponer el código
    r = client.post(f"/firmar/{TOKEN}/solicitar-otp")
    j = r.json()
    o = _codigo_activo()
    body_txt = r.text
    ok2 = (r.status_code == 200 and j.get("expires_in_seconds") == 600
           and "***@empresa.com" in j.get("mensaje", "") and o is not None
           and o.codigo not in body_txt)
    chk(2, "POST /solicitar-otp (correo enmascarado)", "200, sin código en respuesta", f"{r.status_code}", ok2)

    codigo_real = o.codigo

    # Test 3: código incorrecto → 400 con intentos restantes
    wrong = "000000" if codigo_real != "000000" else "111111"
    r = client.post(f"/firmar/{TOKEN}/verificar-otp", json={"codigo": wrong})
    ok3 = r.status_code == 400 and "restantes: 2" in r.json().get("detail", "")
    chk(3, "verificar-otp incorrecto", "400 + 'restantes: 2'", f"{r.status_code} {r.json().get('detail','')[:30]}", ok3)

    # Test 4: 3 intentos fallidos en total → código bloqueado, pide uno nuevo
    client.post(f"/firmar/{TOKEN}/verificar-otp", json={"codigo": wrong})  # 2º fallo
    r3 = client.post(f"/firmar/{TOKEN}/verificar-otp", json={"codigo": wrong})  # 3º fallo → bloquea
    r4 = client.post(f"/firmar/{TOKEN}/verificar-otp", json={"codigo": wrong})  # ya no hay código activo
    ok4 = (r3.status_code == 400 and "restantes: 0" in r3.json().get("detail", "")
           and r4.status_code == 400 and "nuevo" in r4.json().get("detail", "").lower())
    chk(4, "3 fallos → código bloqueado", "400 bloqueado + 'solicita uno nuevo'",
        f"{r3.status_code}/{r4.status_code}", ok4)

    # Test 5: nuevo código + código correcto → verificado, firma_token.otp_verificado=True
    client.post(f"/firmar/{TOKEN}/solicitar-otp")
    o2 = _codigo_activo()
    r = client.post(f"/firmar/{TOKEN}/verificar-otp", json={"codigo": o2.codigo})
    j = r.json()
    db.rollback()
    ft = db.query(FirmaToken).filter(FirmaToken.id == FT_ID).first()
    ok5 = r.status_code == 200 and j.get("verificado") is True and ft.otp_verificado is True
    chk(5, "verificar-otp correcto -> habilita firma", "200 verificado + flag DB", f"{r.status_code} flag={ft.otp_verificado}", ok5)

finally:
    # Limpieza
    db.query(OtpToken).filter(OtpToken.firma_token_id == FT_ID).delete()
    db.query(FirmaToken).filter(FirmaToken.id == FT_ID).delete()
    db.query(Acta).filter(Acta.id == acta.id).delete()
    db.query(Usuario).filter(Usuario.id == u.id).delete()
    db.commit()
    db.close()

print("\n" + "=" * 96)
print(f"| {'#':<2} | {'Prueba':<44} | {'Esperado':<26} | {'Resultado':<7} |")
print("=" * 96)
for n, desc, esp, obt, estado in sorted(R):
    print(f"| {n:<2} | {desc[:44]:<44} | {str(esp)[:26]:<26} | {estado:<7} |")
print("=" * 96)
ok = sum(1 for *_, e in R if e == "PASS")
print(f"\n{ok}/{len(R)} pruebas PASARON")
