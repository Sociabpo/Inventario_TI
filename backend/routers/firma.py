from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta
import uuid
import random
import asyncio
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from database import get_db
from models.acta import Acta, ActaDetalle
from models.activo import Activo
from models.accesorio import Accesorio
from models.usuario import Usuario
from models.empresa import Empresa
from models.firma_token import FirmaToken
from models.otp_token import OtpToken
from dependencies.rbac import require_permission
from services.pdf_service import generar_pdf_acta, generar_pdf_acta_accesorios, _MESES_ES
from services.email_service import enviar_otp
from config import settings


def _fecha_constancia_es(dt: datetime) -> str:
    return f"{dt.day} días del mes de {_MESES_ES[dt.month]} del {dt.year}"


def _correo_parcial(correo: str) -> str:
    """jua***@empresa.com — enmascara el correo para mostrarlo sin revelarlo."""
    if not correo or "@" not in correo:
        return "tu correo registrado"
    local, dominio = correo.split("@", 1)
    visible = local[:3] if len(local) >= 3 else local
    return f"{visible}***@{dominio}"

router = APIRouter(tags=["Firma Digital"])

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
BASE_DIR = Path(__file__).parent.parent


def _generar_pdf_sin_firma(acta: Acta, db: Session):
    """Genera (o regenera) el PDF del acta sin firma y guarda la URL en la BD."""
    usuario = db.query(Usuario).filter(Usuario.id == acta.id_usuario).first()
    empresa = db.query(Empresa).filter(Empresa.id == acta.empresa_id).first()

    nombre_ti = acta.responsable_entrega
    usuario_ti = db.query(Usuario).filter(Usuario.nombre_completo == nombre_ti).first() if nombre_ti else None

    detalles = db.query(ActaDetalle).filter(ActaDetalle.acta_id == acta.id).all()
    activos_acta, accesorios_acta = [], []
    for d in detalles:
        if d.tipo_item == "activo" and d.id_activo:
            a = db.query(Activo).filter(Activo.id == d.id_activo).first()
            if a: activos_acta.append(a)
        elif d.tipo_item == "accesorio" and d.id_accesorio:
            acc = db.query(Accesorio).filter(Accesorio.id == d.id_accesorio).first()
            if acc: accesorios_acta.append(acc)

    activo_principal = None
    if acta.id_activo:
        activo_principal = db.query(Activo).filter(Activo.id == acta.id_activo).first()
    if not activo_principal and activos_acta:
        activo_principal = activos_acta[0]

    if activo_principal:
        ruta_pdf, hash_pdf = generar_pdf_acta(
            acta=acta,
            activo=activo_principal,
            activos_extra=[a for a in activos_acta if a.id != activo_principal.id],
            usuario=usuario,
            empresa=empresa,
            accesorios=accesorios_acta,
            usuario_ti=usuario_ti,
        )
    else:
        ruta_pdf, hash_pdf = generar_pdf_acta_accesorios(
            acta=acta,
            usuario=usuario,
            empresa=empresa,
            accesorios=accesorios_acta,
            usuario_ti=usuario_ti,
        )

    acta.url_pdf  = ruta_pdf
    acta.hash_pdf = hash_pdf
    db.commit()


# ── Generar token de firma ────────────────────────────────
@router.post("/api/actas/{acta_id}/generar-token-firma")
def generar_token_firma(
    acta_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("actas.generar")
):
    acta = db.query(Acta).filter(Acta.id == acta_id).first()
    if not acta:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    if acta.firmada:
        raise HTTPException(status_code=400, detail="Esta acta ya fue firmada y no puede modificarse")

    # Invalidar tokens anteriores no usados
    db.query(FirmaToken).filter(
        FirmaToken.acta_id == acta_id,
        FirmaToken.usado == False
    ).update({"usado": True})

    token = FirmaToken(
        acta_id=acta_id,
        token=str(uuid.uuid4()),
        expires_at=datetime.now() + timedelta(hours=72)
    )
    db.add(token)
    db.commit()
    db.refresh(token)

    link = f"{settings.BASE_URL}/firmar/{token.token}"
    return {
        "token": token.token,
        "link": link,
        "expires_at": token.expires_at
    }


# ── Página pública de firma (GET) ─────────────────────────
@router.get("/firmar/{token}", response_class=HTMLResponse)
def pagina_firma(token: str, db: Session = Depends(get_db)):
    firma_token = db.query(FirmaToken).filter(FirmaToken.token == token).first()

    if not firma_token:
        return HTMLResponse(_error_page("Link inválido o no existe"), status_code=404)
    if firma_token.usado:
        return HTMLResponse(_error_page("Este link ya fue utilizado — el acta ya fue firmada"), status_code=410)
    if firma_token.expires_at and datetime.now() > firma_token.expires_at:
        return HTMLResponse(_error_page("Este link ha expirado (válido 72 h)"), status_code=410)

    acta    = db.query(Acta).filter(Acta.id == firma_token.acta_id).first()
    usuario = db.query(Usuario).filter(Usuario.id == acta.id_usuario).first()
    empresa = db.query(Empresa).filter(Empresa.id == acta.empresa_id).first()

    detalles = db.query(ActaDetalle).filter(ActaDetalle.acta_id == acta.id).all()
    activos_list, accesorios_list = [], []
    for d in detalles:
        if d.tipo_item == "activo" and d.id_activo:
            a = db.query(Activo).filter(Activo.id == d.id_activo).first()
            if a: activos_list.append(a)
        elif d.tipo_item == "accesorio" and d.id_accesorio:
            acc = db.query(Accesorio).filter(Accesorio.id == d.id_accesorio).first()
            if acc: accesorios_list.append(acc)

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("firmar.html")
    html = template.render(
        token=token,
        acta=acta,
        usuario=usuario,
        empresa=empresa,
        activos=activos_list,
        accesorios=accesorios_list,
        fecha_constancia=_fecha_constancia_es(datetime.now()),
        correo_parcial=_correo_parcial(usuario.correo) if usuario else "tu correo registrado",
    )
    return HTMLResponse(html)


# ── Ver PDF del acta (sin firmar) desde el link público ───
@router.get("/firmar/{token}/acta-pdf")
def ver_acta_pdf(token: str, db: Session = Depends(get_db)):
    firma_token = db.query(FirmaToken).filter(FirmaToken.token == token).first()

    if not firma_token:
        raise HTTPException(status_code=404, detail="Link inválido o no existe")
    if firma_token.usado:
        raise HTTPException(status_code=410, detail="Este link ya fue utilizado")
    if firma_token.expires_at and datetime.now() > firma_token.expires_at:
        raise HTTPException(status_code=410, detail="Este link ha expirado")

    acta = db.query(Acta).filter(Acta.id == firma_token.acta_id).first()
    if not acta:
        raise HTTPException(status_code=404, detail="Acta no encontrada")

    # Generar el PDF (sin firma) si aún no existe en disco
    if not acta.url_pdf or not (BASE_DIR / acta.url_pdf).exists():
        try:
            _generar_pdf_sin_firma(acta, db)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error generando PDF del acta: {str(e)}")

    ruta = BASE_DIR / acta.url_pdf
    if not ruta.exists():
        raise HTTPException(status_code=404, detail="No se pudo generar el PDF del acta")

    return FileResponse(
        path=str(ruta),
        media_type="application/pdf",
        content_disposition_type="inline",
        filename=f"acta_{acta.id[:8]}.pdf",
    )


# ── OTP: solicitar código ─────────────────────────────────
@router.post("/firmar/{token}/solicitar-otp")
def solicitar_otp(token: str, db: Session = Depends(get_db)):
    firma_token = db.query(FirmaToken).filter(FirmaToken.token == token).first()
    if not firma_token or firma_token.usado:
        raise HTTPException(status_code=400, detail="Link inválido o ya utilizado")
    if firma_token.expires_at and datetime.now() > firma_token.expires_at:
        raise HTTPException(status_code=400, detail="Este link ha expirado")

    acta = db.query(Acta).filter(Acta.id == firma_token.acta_id).first()
    if not acta:
        raise HTTPException(status_code=404, detail="Acta no encontrada")
    usuario = db.query(Usuario).filter(Usuario.id == acta.id_usuario).first()
    if not usuario or not usuario.correo:
        raise HTTPException(status_code=400, detail="El empleado no tiene correo registrado para enviar el OTP")

    # Invalidar OTPs anteriores no usados
    db.query(OtpToken).filter(
        OtpToken.firma_token_id == firma_token.id,
        OtpToken.usado == False,
    ).update({"usado": True})

    codigo = str(random.randint(100000, 999999))
    otp = OtpToken(
        firma_token_id=firma_token.id,
        codigo=codigo,
        expires_at=datetime.now() + timedelta(minutes=10),
    )
    db.add(otp)
    db.commit()

    empresa = db.query(Empresa).filter(Empresa.id == acta.empresa_id).first()
    empresa_nombre = empresa.nombre_empresa if empresa else "Inventario TI"

    # Enviar el correo (síncrono: necesitamos confirmar la entrega)
    enviado = asyncio.run(enviar_otp(
        destinatario_email=usuario.correo,
        destinatario_nombre=usuario.nombre_completo,
        codigo=codigo,
        empresa_nombre=empresa_nombre,
    ))
    if not enviado:
        raise HTTPException(status_code=500, detail="No se pudo enviar el código por correo. Contacta al área de TI.")

    return {
        "mensaje": f"Código enviado a {_correo_parcial(usuario.correo)}",
        "expires_in_seconds": 600,
    }


# ── OTP: verificar código ─────────────────────────────────
class VerificarOtpRequest(BaseModel):
    codigo: str

@router.post("/firmar/{token}/verificar-otp")
def verificar_otp(token: str, data: VerificarOtpRequest, db: Session = Depends(get_db)):
    firma_token = db.query(FirmaToken).filter(FirmaToken.token == token).first()
    if not firma_token or firma_token.usado:
        raise HTTPException(status_code=400, detail="Link inválido o ya utilizado")

    otp = db.query(OtpToken).filter(
        OtpToken.firma_token_id == firma_token.id,
        OtpToken.usado == False,
    ).order_by(OtpToken.created_at.desc()).first()

    if not otp:
        raise HTTPException(status_code=400, detail="No hay código OTP activo. Solicita uno nuevo.")
    if otp.expires_at < datetime.now():
        raise HTTPException(status_code=400, detail="El código ha expirado. Solicita uno nuevo.")
    if otp.intentos_fallidos >= 3:
        otp.usado = True
        db.commit()
        raise HTTPException(status_code=400, detail="Demasiados intentos fallidos. Solicita un nuevo código.")

    if otp.codigo != (data.codigo or "").strip():
        otp.intentos_fallidos += 1
        if otp.intentos_fallidos >= 3:
            otp.usado = True
        db.commit()
        restantes = max(0, 3 - otp.intentos_fallidos)
        raise HTTPException(status_code=400, detail=f"Código incorrecto. Intentos restantes: {restantes}")

    otp.usado = True
    otp.verificado = True
    firma_token.otp_verificado = True
    db.commit()
    return {"verificado": True, "mensaje": "Identidad verificada correctamente"}


# ── Guardar firma y regenerar PDF (POST) ──────────────────
class FirmarRequest(BaseModel):
    firma_base64:        str
    nombre_firmante:     Optional[str]  = None
    entrega_por_tercero: Optional[bool] = False
    nombre_tercero:      Optional[str]  = None
    relacion_tercero:    Optional[str]  = None
    observaciones_firma: Optional[str]  = None
    correo_movil:        Optional[bool] = None

@router.post("/firmar/{token}")
def guardar_firma(token: str, data: FirmarRequest, request: Request, db: Session = Depends(get_db)):
    firma_token = db.query(FirmaToken).filter(FirmaToken.token == token).first()

    if not firma_token or firma_token.usado:
        raise HTTPException(status_code=410, detail="Link inválido o ya utilizado")
    if firma_token.expires_at and datetime.now() > firma_token.expires_at:
        raise HTTPException(status_code=410, detail="Link expirado")
    if not data.firma_base64 or len(data.firma_base64) < 50:
        raise HTTPException(status_code=400, detail="Firma inválida o vacía")

    acta_obj = db.query(Acta).filter(Acta.id == firma_token.acta_id).first()
    usuario  = db.query(Usuario).filter(Usuario.id == acta_obj.id_usuario).first()

    # El OTP solo se exige para actas de entrega/asignación (no para devolución)
    if acta_obj.tipo != "devolucion" and not firma_token.otp_verificado:
        raise HTTPException(status_code=403, detail="Debes verificar tu identidad con el código OTP antes de firmar")

    if acta_obj.tipo == "devolucion":
        # Employee (or representative) signs to confirm they are returning the device.
        # responsable_recibe (TI admin who receives) was set when the acta was created — do NOT overwrite.
        if data.entrega_por_tercero:
            if not data.nombre_tercero or not data.nombre_tercero.strip():
                raise HTTPException(status_code=400, detail="El nombre del representante es requerido")
            if not data.relacion_tercero or not data.relacion_tercero.strip():
                raise HTTPException(status_code=400, detail="La relación del representante con el empleado es requerida")
        nombre_resuelto = usuario.nombre_completo
    else:
        nombre_resuelto = (data.nombre_firmante or "").strip() or usuario.nombre_completo

    now = datetime.now()
    firma_token.firma_base64        = data.firma_base64
    firma_token.nombre_firmante     = nombre_resuelto
    firma_token.entrega_por_tercero = bool(data.entrega_por_tercero)
    firma_token.nombre_tercero      = data.nombre_tercero.strip() if data.nombre_tercero else None
    firma_token.relacion_tercero    = data.relacion_tercero.strip() if data.relacion_tercero else None
    firma_token.observaciones_firma = data.observaciones_firma.strip() if data.observaciones_firma else None
    firma_token.correo_movil        = data.correo_movil
    firma_token.usado               = True
    firma_token.ip_firmante         = request.client.host
    firma_token.firmado_at          = now
    db.flush()

    acta_obj.firmada     = True
    acta_obj.fecha_firma = now
    db.query(FirmaToken).filter(
        FirmaToken.acta_id == firma_token.acta_id,
        FirmaToken.id != firma_token.id,
        FirmaToken.usado == False,
    ).update({"usado": True})
    db.flush()

    empresa = db.query(Empresa).filter(Empresa.id == acta_obj.empresa_id).first()

    # TI user: responsable_entrega is always the TI admin (for both entrega and devolucion)
    nombre_ti = acta_obj.responsable_entrega
    usuario_ti = db.query(Usuario).filter(Usuario.nombre_completo == nombre_ti).first() if nombre_ti else None

    detalles = db.query(ActaDetalle).filter(ActaDetalle.acta_id == acta_obj.id).all()
    activos_pdf, accesorios_pdf = [], []
    for d in detalles:
        if d.tipo_item == "activo" and d.id_activo:
            a = db.query(Activo).filter(Activo.id == d.id_activo).first()
            if a: activos_pdf.append(a)
        elif d.tipo_item == "accesorio" and d.id_accesorio:
            acc = db.query(Accesorio).filter(Accesorio.id == d.id_accesorio).first()
            if acc: accesorios_pdf.append(acc)

    try:
        if activos_pdf:
            ruta_pdf, hash_pdf = generar_pdf_acta(
                acta=acta_obj,
                activo=activos_pdf[0],
                activos_extra=activos_pdf[1:],
                usuario=usuario,
                empresa=empresa,
                accesorios=accesorios_pdf,
                usuario_ti=usuario_ti,
                firma_base64=data.firma_base64,
                nombre_firmante=nombre_resuelto,
                entrega_por_tercero=bool(data.entrega_por_tercero),
                nombre_tercero=firma_token.nombre_tercero,
                relacion_tercero=firma_token.relacion_tercero,
                observaciones_firma=firma_token.observaciones_firma,
                correo_movil=firma_token.correo_movil,
            )
        else:
            ruta_pdf, hash_pdf = generar_pdf_acta_accesorios(
                acta=acta_obj,
                usuario=usuario,
                empresa=empresa,
                accesorios=accesorios_pdf,
                usuario_ti=usuario_ti,
                firma_base64=data.firma_base64,
                nombre_firmante=nombre_resuelto,
                entrega_por_tercero=bool(data.entrega_por_tercero),
                nombre_tercero=firma_token.nombre_tercero,
                relacion_tercero=firma_token.relacion_tercero,
                observaciones_firma=firma_token.observaciones_firma,
                correo_movil=firma_token.correo_movil,
            )
        acta_obj.url_pdf  = ruta_pdf
        acta_obj.hash_pdf = hash_pdf
    except Exception as e:
        db.commit()
        raise HTTPException(status_code=500, detail=f"Error regenerando PDF: {str(e)}")

    db.commit()

    # ── Enviar PDF firmado por correo al empleado (no bloquea la respuesta) ──
    if usuario and usuario.correo and acta_obj.url_pdf:
        import threading
        import asyncio
        from services.email_service import enviar_acta_por_correo
        from pathlib import Path as _Path

        pdf_full_path  = str(_Path(__file__).parent.parent / acta_obj.url_pdf)
        numero_acta_em = acta_obj.url_pdf.split("/")[-1].replace(".pdf", "")
        empresa_nombre = empresa.nombre_empresa if empresa else "Inventario TI"

        def _send():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(
                    enviar_acta_por_correo(
                        destinatario_email=usuario.correo,
                        destinatario_nombre=usuario.nombre_completo,
                        tipo_acta=acta_obj.tipo,
                        numero_acta=numero_acta_em,
                        pdf_path=pdf_full_path,
                        empresa_nombre=empresa_nombre,
                    )
                )
            finally:
                loop.close()

        threading.Thread(target=_send, daemon=True).start()

    return {"ok": True, "mensaje": "Firma registrada — el acta ha sido actualizada con tu firma"}


# ── Página de error pública ───────────────────────────────
def _error_page(msg: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Link no disponible</title>
<style>
  *{{margin:0;padding:0;box-sizing:border-box}}
  body{{font-family:'Segoe UI',sans-serif;display:flex;justify-content:center;align-items:center;
        min-height:100vh;background:#07101f;color:#e0e6f0}}
  .box{{text-align:center;padding:40px 32px;background:#0e1c34;border-radius:18px;
        border:1px solid #1e3256;max-width:380px;width:90%}}
  .icon{{font-size:48px;margin-bottom:16px}}
  h2{{color:#ff4d6d;font-size:20px;margin-bottom:10px}}
  p{{color:#7a8fa8;font-size:14px;line-height:1.6}}
</style>
</head>
<body>
  <div class="box">
    <div class="icon">⚠</div>
    <h2>Link no disponible</h2>
    <p>{msg}</p>
  </div>
</body>
</html>"""
