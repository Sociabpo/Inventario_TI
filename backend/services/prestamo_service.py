"""
Servicio de préstamos temporales (loans).

El préstamo NO es un estado nuevo: el recurso sigue "asignado". La info del
préstamo (fecha_limite_devolucion, es_prestamo, alerta_vencimiento_enviada) vive
directamente sobre el recurso (Activo / Accesorio), de modo que funciona tanto
para activos como para accesorios (incluidas asignaciones solo-accesorios, que no
crean fila en `asignaciones`).

Incluye:
  - loan_dict(recurso): info de préstamo para los listados (badge / vencimiento).
  - resolver_responsable(db, tipo, recurso): correo/nombre del TI que asignó.
  - alertar_prestamos_vencidos(): job diario que avisa por correo (una vez por evento).
"""
from datetime import date
from sqlalchemy.orm import Session
from database import SessionLocal
from models.activo import Activo
from models.accesorio import Accesorio
from models.asignacion import Asignacion
from models.historial import HistorialMovimiento
from models.usuario import Usuario
from models.usuario_sistema import UsuarioSistema
import asyncio


def loan_dict(recurso) -> dict:
    """Campos de préstamo para serializar un recurso en los listados."""
    f   = getattr(recurso, "fecha_limite_devolucion", None)
    es  = bool(getattr(recurso, "es_prestamo", False))
    asignado = getattr(recurso, "estado", None) == "asignado"
    hoy = date.today()
    dias = (f - hoy).days if f else None       # negativo si ya venció
    return {
        "es_prestamo":             es,
        "fecha_limite_devolucion": f,
        "prestamo_vencido":        bool(f and asignado and f < hoy),
        "dias_para_vencer":        dias,
    }


def resolver_responsable(db: Session, tipo: str, recurso):
    """
    Devuelve el UsuarioSistema que registró la asignación del recurso.
    - Activos: `asignado_por` de la asignación activa (es el correo del usuario).
    - Accesorios: último HistorialMovimiento de tipo 'asignacion' (responsable = correo).
    Fallback en ambos casos al historial si no hay asignación.
    """
    correo = None
    if tipo == "activo":
        asig = db.query(Asignacion).filter(
            Asignacion.id_activo == recurso.id,
            Asignacion.estado == "activa",
        ).order_by(Asignacion.fecha_asignacion.desc()).first()
        if asig:
            correo = asig.asignado_por
    if not correo:
        col = HistorialMovimiento.id_activo if tipo == "activo" else HistorialMovimiento.id_accesorio
        mov = db.query(HistorialMovimiento).filter(
            col == recurso.id,
            HistorialMovimiento.tipo_movimiento == "asignacion",
        ).order_by(HistorialMovimiento.fecha_movimiento.desc()).first()
        if mov:
            correo = mov.responsable
    if not correo:
        return None
    return db.query(UsuarioSistema).filter(UsuarioSistema.email == correo).first()


def _recurso_label(tipo: str, recurso) -> str:
    if tipo == "activo":
        return f"{recurso.tipo_activo} {recurso.marca or ''} {recurso.modelo or ''} · {recurso.id_placa_activo}".strip()
    return f"{recurso.tipo_accesorio} {recurso.marca or ''} {recurso.modelo or ''} · {recurso.id_placa_accesorio}".strip()


def alertar_prestamos_vencidos():
    """Runs daily — emails the assigner about overdue loans (once per overdue event)."""
    from services.email_service import enviar_alerta_prestamo_vencido
    db = SessionLocal()
    hoy = date.today()
    try:
        vencidos = []
        for tipo, modelo in (("activo", Activo), ("accesorio", Accesorio)):
            filas = db.query(modelo).filter(
                modelo.estado == "asignado",
                modelo.es_prestamo == True,
                modelo.fecha_limite_devolucion < hoy,
                modelo.alerta_vencimiento_enviada == False,
            ).all()
            vencidos.extend((tipo, r) for r in filas)

        enviados = 0
        for tipo, recurso in vencidos:
            assigner = resolver_responsable(db, tipo, recurso)
            if not assigner or not assigner.email:
                print(f"[PRESTAMOS] {tipo} {recurso.id} — no se pudo resolver correo del responsable")
                continue
            empleado = db.query(Usuario).filter(Usuario.id == recurso.id_usuario).first()
            dias_vencido = (hoy - recurso.fecha_limite_devolucion).days
            ok = asyncio.run(enviar_alerta_prestamo_vencido(
                destinatario_email=assigner.email,
                destinatario_nombre=assigner.nombre,
                recurso=_recurso_label(tipo, recurso),
                empleado_nombre=empleado.nombre_completo if empleado else "—",
                fecha_limite=recurso.fecha_limite_devolucion,
                dias_vencido=dias_vencido,
            ))
            if ok:
                recurso.alerta_vencimiento_enviada = True
                enviados += 1
        db.commit()
        print(f"[PRESTAMOS] {hoy} — {len(vencidos)} préstamos vencidos, {enviados} alertas enviadas")
    except Exception as e:
        print(f"[PRESTAMOS] Error: {e}")
        db.rollback()
    finally:
        db.close()
