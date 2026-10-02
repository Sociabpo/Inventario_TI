from datetime import datetime, timedelta, date
from typing import Optional
from sqlalchemy.orm import Session
from models.acta import Acta
from models.firma_token import FirmaToken
from models.recordatorio_firma import RecordatorioFirma
from models.usuario import Usuario
from models.usuario_sistema import UsuarioSistema
from models.empresa import Empresa
from database import SessionLocal
from config import settings
import asyncio
import uuid

RECORDATORIO_DIAS = [2, 4, 7]   # días desde la fecha de referencia para cada recordatorio
MAX_RECORDATORIOS = 3
ESCALAR_DESDE_DIA = 5


def _fecha_referencia(acta: Acta) -> Optional[date]:
    if acta.es_anticipada:
        return acta.fecha_inicio_vigencia  # puede ser None → se ignora
    return acta.fecha_entrega.date() if acta.fecha_entrega else None


def _get_or_create_token(db: Session, acta: Acta) -> Optional[FirmaToken]:
    token = db.query(FirmaToken).filter(
        FirmaToken.acta_id == acta.id,
        FirmaToken.usado == False,
        FirmaToken.expires_at > datetime.utcnow(),
    ).first()
    if not token:
        token = FirmaToken(
            id=str(uuid.uuid4()),
            acta_id=acta.id,
            token=str(uuid.uuid4()),
            usado=False,
            expires_at=datetime.utcnow() + timedelta(days=30),
        )
        db.add(token)
        db.flush()
    return token


def _ultimo_recordatorio_hace_horas(db: Session, acta_id: str, horas: int = 23) -> bool:
    cutoff = datetime.utcnow() - timedelta(hours=horas)
    return db.query(RecordatorioFirma).filter(
        RecordatorioFirma.acta_id == acta_id,
        RecordatorioFirma.fecha_envio > cutoff,
        RecordatorioFirma.escalado_admin == False,
    ).first() is not None


def _ya_escalado(db: Session, acta_id: str) -> bool:
    return db.query(RecordatorioFirma).filter(
        RecordatorioFirma.acta_id == acta_id,
        RecordatorioFirma.escalado_admin == True,
    ).first() is not None


def procesar_recordatorios():
    from services.email_service import enviar_recordatorio_firma

    db = SessionLocal()
    hoy = date.today()
    try:
        enviados = escalados = ignoradas = 0
        candidatas = db.query(Acta).filter(
            Acta.tipo == "entrega",
            Acta.firmada == False,
            Acta.recordatorios_enviados < MAX_RECORDATORIOS,
        ).all()
        print(f"[RECORDATORIOS] {datetime.now().strftime('%Y-%m-%d %H:%M')} — {len(candidatas)} actas candidatas")

        for acta in candidatas:
            try:
                fecha_ref = _fecha_referencia(acta)
                if not fecha_ref:
                    ignoradas += 1
                    print(f"[RECORDATORIOS] Acta {acta.id} ignorada — anticipada sin fecha de ingreso")
                    continue
                if fecha_ref > hoy:
                    ignoradas += 1
                    print(f"[RECORDATORIOS] Acta {acta.id} ignorada — empleado ingresa el {fecha_ref} (faltan {(fecha_ref - hoy).days} días)")
                    continue

                dias_pendiente = (hoy - fecha_ref).days
                num_recordatorio = acta.recordatorios_enviados + 1
                umbral = RECORDATORIO_DIAS[num_recordatorio - 1] if num_recordatorio <= len(RECORDATORIO_DIAS) else None
                if umbral is None or dias_pendiente < umbral:
                    continue
                if _ultimo_recordatorio_hace_horas(db, acta.id, 23):
                    continue

                usuario = db.query(Usuario).filter(Usuario.id == acta.id_usuario).first()
                empresa = db.query(Empresa).filter(Empresa.id == acta.empresa_id).first()

                if not usuario or not usuario.correo:
                    _notificar_sin_correo(db, acta, usuario, empresa)
                    continue

                token = _get_or_create_token(db, acta)
                if not token:
                    continue

                recursos = _obtener_recursos(db, acta)
                numero_acta = acta.url_pdf.split("/")[-1].replace(".pdf", "") if acta.url_pdf else acta.id[:8]
                firma_url = f"{settings.APP_BASE_URL}/firmar/{token.token}"
                contexto_anticipada = (
                    f"(el acta fue generada anticipadamente — tu fecha de ingreso fue el "
                    f"{acta.fecha_inicio_vigencia.strftime('%d/%m/%Y')})"
                    if acta.es_anticipada and acta.fecha_inicio_vigencia else ""
                )

                enviado = asyncio.run(enviar_recordatorio_firma(
                    destinatario_email=usuario.correo,
                    destinatario_nombre=usuario.nombre_completo,
                    numero_acta=numero_acta,
                    dias_pendiente=dias_pendiente,
                    firma_url=firma_url,
                    recursos=recursos,
                    numero_recordatorio=num_recordatorio,
                    empresa_nombre=empresa.nombre_empresa if empresa else "Inventario TI",
                    token_expires_at=token.expires_at,
                    contexto_anticipada=contexto_anticipada,
                ))

                if enviado:
                    db.add(RecordatorioFirma(
                        acta_id=acta.id, token_id=token.id, enviado_a=usuario.correo,
                        numero_recordatorio=num_recordatorio, escalado_admin=False,
                    ))
                    acta.recordatorios_enviados = num_recordatorio
                    enviados += 1
                    print(f"[RECORDATORIOS] #{num_recordatorio} enviado a {usuario.correo} — {numero_acta}")

                if dias_pendiente >= ESCALAR_DESDE_DIA and not _ya_escalado(db, acta.id):
                    _escalar_a_admin(db, acta, usuario, empresa, numero_acta, firma_url, dias_pendiente)
                    escalados += 1

            except Exception as e:
                print(f"[RECORDATORIOS] Error en acta {acta.id}: {e}")
                continue

        db.commit()
        print(f"[RECORDATORIOS] Completado — {enviados} enviados, {escalados} escalados, {ignoradas} ignoradas")
    except Exception as e:
        print(f"[RECORDATORIOS] Error general: {e}")
        db.rollback()
    finally:
        db.close()


def _obtener_recursos(db: Session, acta: Acta) -> list:
    from models.acta import ActaDetalle
    from models.activo import Activo
    from models.accesorio import Accesorio
    recursos = []
    detalles = db.query(ActaDetalle).filter(ActaDetalle.acta_id == acta.id).all()
    for d in detalles:
        if d.tipo_item == "activo" and d.id_activo:
            a = db.query(Activo).filter(Activo.id == d.id_activo).first()
            if a:
                recursos.append(f"{a.tipo_activo} {a.marca or ''} {a.modelo or ''} · {a.id_placa_activo}".strip())
        elif d.tipo_item == "accesorio" and d.id_accesorio:
            acc = db.query(Accesorio).filter(Accesorio.id == d.id_accesorio).first()
            if acc:
                recursos.append(f"{acc.tipo_accesorio} {acc.marca or ''} · {acc.id_placa_accesorio}".strip())
    return recursos


def _escalar_a_admin(db, acta, usuario, empresa, numero_acta, firma_url, dias_pendiente):
    from services.email_service import enviar_alerta_admin_firma
    from models.rol import Rol
    from models.usuario_rol import UsuarioRol

    admin = db.query(UsuarioSistema).filter(
        UsuarioSistema.activo == True,
        UsuarioSistema.nombre == acta.responsable_entrega,
    ).first()

    if not admin:
        roles_admin = db.query(Rol).filter(Rol.nombre.in_(["admin", "super_admin"])).all()
        rol_ids = [r.id for r in roles_admin]
        ur = db.query(UsuarioRol).filter(
            UsuarioRol.empresa_id == acta.empresa_id,
            UsuarioRol.rol_id.in_(rol_ids),
            UsuarioRol.activo == True,
        ).first()
        if ur:
            admin = db.query(UsuarioSistema).filter(UsuarioSistema.id == ur.usuario_sistema_id).first()

    if not admin:
        print(f"[RECORDATORIOS] No se encontró admin para escalar acta {acta.id}")
        return

    try:
        asyncio.run(enviar_alerta_admin_firma(
            admin_email=admin.email, admin_nombre=admin.nombre,
            empleado_nombre=usuario.nombre_completo if usuario else "Desconocido",
            empleado_correo=usuario.correo if usuario else "—",
            numero_acta=numero_acta, dias_pendiente=dias_pendiente, firma_url=firma_url,
            empresa_nombre=empresa.nombre_empresa if empresa else "—",
            es_anticipada=acta.es_anticipada, fecha_inicio=acta.fecha_inicio_vigencia,
        ))
        db.add(RecordatorioFirma(
            acta_id=acta.id, enviado_a=admin.email, numero_recordatorio=0, escalado_admin=True,
        ))
        print(f"[RECORDATORIOS] Escalado a {admin.email}")
    except Exception as e:
        print(f"[RECORDATORIOS] Error escalando: {e}")


def _notificar_sin_correo(db, acta, usuario, empresa):
    print(
        f"[RECORDATORIOS] ATENCION: Acta {acta.id} — empleado "
        f"'{usuario.nombre_completo if usuario else 'desconocido'}' sin correo registrado. "
        f"Requiere atención manual."
    )
