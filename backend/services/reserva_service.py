"""
Servicio de reservas — liberación automática de reservas vencidas.
Se ejecuta a diario desde el scheduler (2:05 PM, America/Bogota).
"""
from datetime import date, datetime
from database import SessionLocal
from models.reserva import Reserva, ReservaItem
from models.activo import Activo
from models.accesorio import Accesorio
from models.historial import HistorialMovimiento


def _historial(db, tipo_recurso, recurso_id, obs):
    db.add(HistorialMovimiento(
        id_activo=recurso_id if tipo_recurso == "activo" else None,
        id_accesorio=recurso_id if tipo_recurso == "accesorio" else None,
        tipo_movimiento="reserva",
        responsable="sistema",
        observaciones=obs,
    ))


def cerrar_reserva_al_asignar(db, tipo_recurso: str, recurso_id: str):
    """
    Al asignar un recurso que estaba "reservado", cierra su línea en la reserva.
    Si la reserva ya no tiene items pendientes ("reservado"), queda "completada".
    Usado por el flujo de asignación de activos Y accesorios (sin duplicar lógica).
    """
    item = db.query(ReservaItem).filter(
        ReservaItem.tipo_recurso == tipo_recurso,
        ReservaItem.recurso_id == recurso_id,
        ReservaItem.estado == "reservado",
    ).first()
    if not item:
        return
    item.estado = "asignado"
    db.flush()   # la sesión usa autoflush=False; forzamos para que el conteo lo vea
    pendientes = db.query(ReservaItem).filter(
        ReservaItem.reserva_id == item.reserva_id,
        ReservaItem.estado == "reservado",
    ).count()
    if pendientes == 0:
        reserva = db.query(Reserva).filter(Reserva.id == item.reserva_id).first()
        if reserva and reserva.estado == "activa":
            reserva.estado = "completada"
            reserva.fecha_cierre = datetime.utcnow()


def liberar_reservas_vencidas():
    """Runs daily — releases resources whose reservation deadline has passed."""
    db = SessionLocal()
    hoy = date.today()
    try:
        reservas_vencidas = db.query(Reserva).filter(
            Reserva.estado == "activa",
            Reserva.fecha_limite < hoy
        ).all()
        liberados = 0
        for reserva in reservas_vencidas:
            items = db.query(ReservaItem).filter(
                ReservaItem.reserva_id == reserva.id,
                ReservaItem.estado == "reservado"
            ).all()
            for item in items:
                # release the resource back to disponible (only if still reservado)
                if item.tipo_recurso == "activo":
                    rec = db.query(Activo).filter(Activo.id == item.recurso_id).first()
                else:
                    rec = db.query(Accesorio).filter(Accesorio.id == item.recurso_id).first()
                if rec and rec.estado == "reservado":
                    rec.estado = "disponible"
                    item.estado = "liberado"
                    liberados += 1
                    _historial(db, item.tipo_recurso, rec.id,
                               f"Reserva {reserva.numero_alta} vencida, recurso liberado automáticamente")
            reserva.estado = "vencida"
            reserva.fecha_cierre = datetime.utcnow()
        db.commit()
        print(f"[RESERVAS] {hoy} — {len(reservas_vencidas)} reservas vencidas, {liberados} recursos liberados")
    except Exception as e:
        print(f"[RESERVAS] Error: {e}")
        db.rollback()
    finally:
        db.close()
