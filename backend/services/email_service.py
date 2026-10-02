from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig
from starlette.datastructures import UploadFile
from pathlib import Path
from io import BytesIO
from config import settings
import logging

_log = logging.getLogger("email_service")


def _get_mail_config() -> ConnectionConfig:
    return ConnectionConfig(
        MAIL_USERNAME=settings.MAIL_USERNAME,
        MAIL_PASSWORD=settings.MAIL_PASSWORD,
        MAIL_FROM=settings.MAIL_FROM,
        MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
        MAIL_PORT=settings.MAIL_PORT,
        MAIL_SERVER=settings.MAIL_SERVER,
        MAIL_STARTTLS=settings.MAIL_STARTTLS,
        MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
        USE_CREDENTIALS=True,
        VALIDATE_CERTS=True,
    )


def _cuerpo_entrega(destinatario_nombre: str, numero_acta: str, empresa_nombre: str) -> str:
    return f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">
  <div style="background:#1e3a5f;padding:20px;text-align:center;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0">Acta de Entrega de Recursos Tecnol&#xf3;gicos</h2>
    <p style="color:#a0c4e8;margin:6px 0 0">{empresa_nombre}</p>
  </div>
  <div style="padding:24px;background:#f9f9f9;border:1px solid #e0e0e0">
    <p>Estimado/a <strong>{destinatario_nombre}</strong>,</p>
    <p>Se adjunta el acta de entrega <strong>{numero_acta}</strong> firmada digitalmente,
       correspondiente a los recursos tecnol&#xf3;gicos que le fueron asignados.</p>
    <p>Por favor guarde este documento como constancia de la asignaci&#xf3;n.</p>
    <div style="background:#e8f4e8;border-left:4px solid #28a745;padding:12px;margin:16px 0;border-radius:4px">
      <p style="margin:0;font-size:13px">&#10003; Este documento ha sido firmado digitalmente
         y tiene validez como constancia de entrega.</p>
    </div>
    <p style="font-size:12px;color:#666">Si tiene alguna pregunta, com&#xfa;niquese con el &#xe1;rea de Servicios TIC.</p>
  </div>
  <div style="padding:12px;text-align:center;background:#f0f0f0;border-radius:0 0 8px 8px">
    <p style="margin:0;font-size:11px;color:#999">{empresa_nombre} &#x2014; Sistema de Inventario Tecnol&#xf3;gico</p>
  </div>
</body></html>"""


def _cuerpo_devolucion(destinatario_nombre: str, numero_acta: str, empresa_nombre: str) -> str:
    return f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">
  <div style="background:#1e3a5f;padding:20px;text-align:center;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0">Acta de Devoluci&#xf3;n de Recursos Tecnol&#xf3;gicos</h2>
    <p style="color:#a0c4e8;margin:6px 0 0">{empresa_nombre}</p>
  </div>
  <div style="padding:24px;background:#f9f9f9;border:1px solid #e0e0e0">
    <p>Estimado/a <strong>{destinatario_nombre}</strong>,</p>
    <p>Se adjunta el acta de devoluci&#xf3;n <strong>{numero_acta}</strong> firmada digitalmente,
       correspondiente a los recursos tecnol&#xf3;gicos devueltos.</p>
    <div style="background:#fff3cd;border-left:4px solid #ffc107;padding:12px;margin:16px 0;border-radius:4px">
      <p style="margin:0;font-size:13px">&#10003; La devoluci&#xf3;n ha sido confirmada y registrada en el sistema.</p>
    </div>
    <p style="font-size:12px;color:#666">Si tiene alguna pregunta, com&#xfa;niquese con el &#xe1;rea de Servicios TIC.</p>
  </div>
  <div style="padding:12px;text-align:center;background:#f0f0f0;border-radius:0 0 8px 8px">
    <p style="margin:0;font-size:11px;color:#999">{empresa_nombre} &#x2014; Sistema de Inventario Tecnol&#xf3;gico</p>
  </div>
</body></html>"""


async def enviar_recordatorio_firma(
    destinatario_email: str,
    destinatario_nombre: str,
    numero_acta: str,
    dias_pendiente: int,
    firma_url: str,
    recursos: list,
    numero_recordatorio: int,
    empresa_nombre: str,
    token_expires_at,
    contexto_anticipada: str = "",
) -> bool:
    try:
        urgencia_color = "#1e3a5f"
        if numero_recordatorio == 2:
            urgencia_prefijo = "Segundo recordatorio — "
            urgencia_color = "#856404"
        elif numero_recordatorio >= 3:
            urgencia_prefijo = "Último recordatorio — "
            urgencia_color = "#8B1A1A"
        else:
            urgencia_prefijo = ""

        recursos_html = "".join(
            f'<li style="padding:3px 0;font-size:13px;color:#333">{r}</li>' for r in recursos
        ) if recursos else '<li style="color:#666">Ver detalle en el acta</li>'

        expires_str = token_expires_at.strftime("%d/%m/%Y") if token_expires_at else "próximamente"
        anticipada_html = (
            f'<p style="font-size:12px;color:#666;font-style:italic;margin:0 0 12px">{contexto_anticipada}</p>'
            if contexto_anticipada else ""
        )

        asunto = f"{urgencia_prefijo}Acta pendiente de firma — {numero_acta}"
        cuerpo = f"""
<html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">
  <div style="background:{urgencia_color};padding:20px;text-align:center;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0">Acta pendiente de firma</h2>
    <p style="color:#a0c4e8;margin:6px 0 0">{empresa_nombre}</p>
  </div>
  <div style="padding:28px 24px;background:#f9f9f9;border:1px solid #e0e0e0">
    <p style="margin:0 0 12px">Hola <strong>{destinatario_nombre}</strong>,</p>
    {anticipada_html}
    <p style="margin:0 0 16px;color:#555">
      Han pasado <strong>{dias_pendiente} días</strong> desde que se generó el acta de entrega
      <strong>{numero_acta}</strong> y aún no registra tu firma digital.
    </p>
    <div style="background:#fff3cd;border-left:4px solid #ffc107;padding:12px 16px;border-radius:0 6px 6px 0;margin:0 0 20px">
      <p style="margin:0;font-size:13px;color:#856404">
        Tu firma es necesaria para formalizar la entrega de los siguientes recursos:
      </p>
    </div>
    <ul style="background:#fff;border:1px solid #e0e0e0;border-radius:6px;padding:12px 12px 12px 32px;margin:0 0 24px">
      {recursos_html}
    </ul>
    <div style="text-align:center;margin:0 0 20px">
      <a href="{firma_url}" style="display:inline-block;background:{urgencia_color};color:#fff;font-size:15px;font-weight:600;padding:14px 32px;border-radius:8px;text-decoration:none;letter-spacing:0.3px">
        Firmar acta ahora
      </a>
    </div>
    <p style="font-size:11px;color:#999;text-align:center;margin:0 0 8px">
      O copia este enlace en tu navegador:<br>
      <span style="color:{urgencia_color};word-break:break-all">{firma_url}</span>
    </p>
    <p style="font-size:11px;color:#999;text-align:center;margin:0">
      Este enlace es personal e intransferible. Válido hasta el <strong>{expires_str}</strong>.
    </p>
  </div>
  <div style="padding:12px;text-align:center;background:#f0f0f0;border-radius:0 0 8px 8px">
    <p style="margin:0;font-size:11px;color:#999">
      {empresa_nombre} — Sistema de Inventario Tecnológico<br>
      Si ya firmaste este documento, ignora este mensaje.
    </p>
  </div>
</body></html>"""

        message = MessageSchema(subject=asunto, recipients=[destinatario_email], body=cuerpo, subtype=MessageType.html)
        fm = FastMail(_get_mail_config())
        await fm.send_message(message)
        return True
    except Exception as e:
        _log.error("[EMAIL ERROR] Recordatorio firma: %s", e, exc_info=True)
        return False


async def enviar_alerta_admin_firma(
    admin_email: str,
    admin_nombre: str,
    empleado_nombre: str,
    empleado_correo: str,
    numero_acta: str,
    dias_pendiente: int,
    firma_url: str,
    empresa_nombre: str,
    es_anticipada: bool = False,
    fecha_inicio=None,
) -> bool:
    try:
        anticipada_row = ""
        if es_anticipada and fecha_inicio:
            anticipada_row = f"""
            <tr style="background:#fff8e1">
              <td style="padding:8px;font-weight:600">Tipo acta</td>
              <td style="padding:8px;color:#856404">Anticipada — fecha de ingreso: {fecha_inicio.strftime('%d/%m/%Y')}</td>
            </tr>"""

        asunto = f"Alerta — Acta {numero_acta} sin firmar hace {dias_pendiente} días"
        cuerpo = f"""
<html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">
  <div style="background:#8B1A1A;padding:20px;text-align:center;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0">Acta sin firmar — Requiere atención</h2>
    <p style="color:#f5c6c6;margin:6px 0 0">{empresa_nombre}</p>
  </div>
  <div style="padding:24px;background:#f9f9f9;border:1px solid #e0e0e0">
    <p>Hola <strong>{admin_nombre}</strong>,</p>
    <p>El siguiente acta lleva <strong>{dias_pendiente} días</strong> sin ser firmada y requiere tu atención:</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr style="background:#f0f0f0"><td style="padding:8px;font-weight:600;width:160px">Acta</td><td style="padding:8px">{numero_acta}</td></tr>
      <tr><td style="padding:8px;font-weight:600">Empleado</td><td style="padding:8px">{empleado_nombre}</td></tr>
      <tr style="background:#f0f0f0"><td style="padding:8px;font-weight:600">Correo empleado</td><td style="padding:8px">{empleado_correo}</td></tr>
      <tr><td style="padding:8px;font-weight:600">Días sin firmar</td><td style="padding:8px;color:#c0392b"><strong>{dias_pendiente} días</strong></td></tr>
      {anticipada_row}
    </table>
    <div style="text-align:center;margin:20px 0">
      <a href="{firma_url}" style="display:inline-block;background:#8B1A1A;color:#fff;font-size:14px;font-weight:600;padding:12px 28px;border-radius:8px;text-decoration:none">
        Ver acta y link de firma
      </a>
    </div>
    <p style="font-size:11px;color:#999">Link directo: <span style="color:#8B1A1A;word-break:break-all">{firma_url}</span></p>
  </div>
  <div style="padding:12px;text-align:center;background:#f0f0f0;border-radius:0 0 8px 8px">
    <p style="margin:0;font-size:11px;color:#999">{empresa_nombre} — Sistema de Inventario Tecnológico</p>
  </div>
</body></html>"""

        message = MessageSchema(subject=asunto, recipients=[admin_email], body=cuerpo, subtype=MessageType.html)
        fm = FastMail(_get_mail_config())
        await fm.send_message(message)
        return True
    except Exception as e:
        _log.error("[EMAIL ERROR] Alerta admin firma: %s", e, exc_info=True)
        return False


async def enviar_alerta_prestamo_vencido(
    destinatario_email: str,
    destinatario_nombre: str,
    recurso: str,
    empleado_nombre: str,
    fecha_limite,
    dias_vencido: int,
) -> bool:
    try:
        if not settings.MAIL_USERNAME or not settings.MAIL_FROM:
            _log.warning("[PRESTAMO EMAIL] Skipped — MAIL_USERNAME / MAIL_FROM not configured in .env")
            return False

        fecha_str = fecha_limite.strftime("%d/%m/%Y") if hasattr(fecha_limite, "strftime") else str(fecha_limite)
        asunto = f"⏰ Préstamo vencido — {recurso} ({dias_vencido} días)"
        cuerpo = f"""
<html><body style="font-family:Arial,sans-serif;color:#333;max-width:600px;margin:0 auto">
  <div style="background:#B25E00;padding:20px;text-align:center;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0">Préstamo de equipo vencido</h2>
    <p style="color:#ffe2bf;margin:6px 0 0">Sistema de Inventario Tecnológico</p>
  </div>
  <div style="padding:24px;background:#f9f9f9;border:1px solid #e0e0e0">
    <p>Hola <strong>{destinatario_nombre}</strong>,</p>
    <p>El siguiente equipo en préstamo superó su fecha límite de devolución:</p>
    <table style="width:100%;border-collapse:collapse;margin:16px 0">
      <tr style="background:#f0f0f0"><td style="padding:8px;font-weight:600;width:160px">Recurso</td><td style="padding:8px">{recurso}</td></tr>
      <tr><td style="padding:8px;font-weight:600">Asignado a</td><td style="padding:8px">{empleado_nombre}</td></tr>
      <tr style="background:#f0f0f0"><td style="padding:8px;font-weight:600">Fecha límite</td><td style="padding:8px">{fecha_str}</td></tr>
      <tr><td style="padding:8px;font-weight:600">Días vencido</td><td style="padding:8px;color:#B25E00"><strong>{dias_vencido} días</strong></td></tr>
    </table>
    <div style="background:#fff3cd;border-left:4px solid #ffc107;padding:12px 16px;border-radius:0 6px 6px 0;margin:0 0 16px">
      <p style="margin:0;font-size:13px;color:#856404">
        Por favor valida con el usuario si devolverá el equipo o si el préstamo se extiende.
      </p>
    </div>
    <p style="font-size:12px;color:#666">Puedes extender el préstamo o convertirlo a indefinido desde el módulo de inventario.</p>
  </div>
  <div style="padding:12px;text-align:center;background:#f0f0f0;border-radius:0 0 8px 8px">
    <p style="margin:0;font-size:11px;color:#999">Sistema de Inventario Tecnológico</p>
  </div>
</body></html>"""

        message = MessageSchema(subject=asunto, recipients=[destinatario_email], body=cuerpo, subtype=MessageType.html)
        fm = FastMail(_get_mail_config())
        await fm.send_message(message)
        _log.info("[PRESTAMO EMAIL] Sent to %s", destinatario_email)
        return True
    except Exception as e:
        _log.error("[PRESTAMO EMAIL ERROR] %s", e, exc_info=True)
        return False


async def enviar_otp(
    destinatario_email: str,
    destinatario_nombre: str,
    codigo: str,
    empresa_nombre: str,
) -> bool:
    try:
        if not settings.MAIL_USERNAME or not settings.MAIL_FROM:
            _log.warning("[OTP EMAIL] Skipped — MAIL_USERNAME / MAIL_FROM not configured in .env")
            return False
        asunto = f"Código de verificación para firma de acta — {codigo}"
        cuerpo = f"""
<html><body style="font-family:Arial,sans-serif;color:#333;max-width:500px;margin:0 auto">
  <div style="background:#1e3a5f;padding:20px;text-align:center;border-radius:8px 8px 0 0">
    <h2 style="color:#fff;margin:0">Verificación de identidad</h2>
    <p style="color:#a0c4e8;margin:6px 0 0">{empresa_nombre}</p>
  </div>
  <div style="padding:32px 24px;background:#f9f9f9;border:1px solid #e0e0e0;text-align:center">
    <p style="margin:0 0 8px">Hola <strong>{destinatario_nombre}</strong>,</p>
    <p style="margin:0 0 24px;color:#666">Tu código de verificación para firmar el acta es:</p>
    <div style="background:#fff;border:2px solid #1e3a5f;border-radius:12px;padding:20px;margin:0 auto 24px;max-width:240px">
      <span style="font-size:36px;font-weight:700;letter-spacing:10px;color:#1e3a5f">{codigo}</span>
    </div>
    <p style="font-size:13px;color:#666;margin:0 0 8px">Este código es válido por <strong>10 minutos</strong>.</p>
    <p style="font-size:12px;color:#999;margin:0">No compartas este código con nadie.<br>Si no solicitaste este código, ignora este mensaje.</p>
  </div>
  <div style="padding:12px;text-align:center;background:#f0f0f0;border-radius:0 0 8px 8px">
    <p style="margin:0;font-size:11px;color:#999">{empresa_nombre} — Sistema de Inventario Tecnológico</p>
  </div>
</body></html>"""
        message = MessageSchema(
            subject=asunto,
            recipients=[destinatario_email],
            body=cuerpo,
            subtype=MessageType.html,
        )
        fm = FastMail(_get_mail_config())
        await fm.send_message(message)
        _log.info("[OTP EMAIL] Sent to %s", destinatario_email)
        return True
    except Exception as e:
        _log.error("[OTP EMAIL ERROR] %s", e, exc_info=True)
        return False


async def enviar_acta_por_correo(
    destinatario_email: str,
    destinatario_nombre: str,
    tipo_acta: str,
    numero_acta: str,
    pdf_path: str,
    empresa_nombre: str,
) -> bool:
    try:
        if not settings.MAIL_USERNAME or not settings.MAIL_FROM:
            _log.warning("[EMAIL] Skipped — MAIL_USERNAME / MAIL_FROM not configured in .env")
            return False

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            _log.warning("[EMAIL] Skipped — PDF not found at %s", pdf_path)
            return False

        if tipo_acta == "devolucion":
            asunto = f"Acta de devolucion de recursos tecnologicos — {numero_acta}"
            cuerpo = _cuerpo_devolucion(destinatario_nombre, numero_acta, empresa_nombre)
        else:
            asunto = f"Acta de entrega de recursos tecnologicos — {numero_acta}"
            cuerpo = _cuerpo_entrega(destinatario_nombre, numero_acta, empresa_nombre)

        message = MessageSchema(
            subject=asunto,
            recipients=[destinatario_email],
            body=cuerpo,
            subtype=MessageType.html,
            attachments=[str(pdf_file)],
        )

        fm = FastMail(_get_mail_config())
        await fm.send_message(message)
        _log.info("[EMAIL] Sent acta %s to %s", numero_acta, destinatario_email)
        return True

    except Exception as e:
        _log.error("[EMAIL ERROR] Failed to send to %s: %s", destinatario_email, e, exc_info=True)
        return False


async def enviar_reporte_dano(
    destinatarios: list,
    cc: list,
    asunto: str,
    cuerpo_html: str,
    imagenes: list,          # [{"filename": str, "bytes": bytes, "subtype": "png"|"jpeg"}]
) -> bool:
    """Envía un reporte de daño de impresora al proveedor (Fase 3 Impresoras).

    Adjunta las imágenes EN MEMORIA (sin escribir a disco): cada una se envuelve en
    un UploadFile(BytesIO) y se pasa como dict de adjunto a MessageSchema. CC al
    usuario que reporta. Devuelve True si se envió.
    """
    try:
        if not settings.MAIL_USERNAME or not settings.MAIL_FROM:
            _log.warning("[REPORTE DANO EMAIL] Skipped — MAIL_USERNAME / MAIL_FROM not configured in .env")
            return False

        attachments = []
        for img in (imagenes or []):
            uf = UploadFile(filename=img["filename"], file=BytesIO(img["bytes"]))
            attachments.append({
                "file": uf,
                "mime_type": "image",
                "mime_subtype": img.get("subtype", "png"),
                "headers": {"Content-Disposition": f'attachment; filename="{img["filename"]}"'},
            })

        message = MessageSchema(
            subject=asunto,
            recipients=destinatarios,
            cc=(cc or []),
            body=cuerpo_html,
            subtype=MessageType.html,
            attachments=attachments,
        )
        fm = FastMail(_get_mail_config())
        await fm.send_message(message)
        _log.info("[REPORTE DANO EMAIL] Sent to %s (cc %s) with %d image(s)",
                  destinatarios, cc, len(attachments))
        return True
    except Exception as e:
        _log.error("[REPORTE DANO EMAIL ERROR] %s", e, exc_info=True)
        return False
