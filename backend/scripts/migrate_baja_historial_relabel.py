r"""
Corrección de datos: reetiqueta las bajas mal registradas en el historial.

El antiguo `aprobar_baja` escribía el movimiento de baja como
`tipo_movimiento='cambio_estado'`, que la línea de tiempo de la Hoja de Vida
descarta a propósito (los cambio_estado se toman de la tabla CambioEstado). El
tipo canónico de una baja es `'baja'` (ver models/historial.py). Este script
reetiqueta SOLO esas filas de baja mal marcadas para que aparezcan retroactivamente
en la línea de tiempo — sin tocar los cambio_estado legítimos.

Criterio (preciso, no ambiguo): tipo_movimiento='cambio_estado' Y la observación
tiene el formato que sólo escribe aprobar_baja: "Baja <num> aprobada — motivo: ...".

Idempotente: al reetiquetar a 'baja', una segunda corrida no encuentra nada.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_baja_historial_relabel.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.historial import HistorialMovimiento


def migrate():
    db = SessionLocal()
    try:
        rows = db.query(HistorialMovimiento).filter(
            HistorialMovimiento.tipo_movimiento == "cambio_estado",
            HistorialMovimiento.observaciones.like("Baja %aprobada%motivo:%"),
        ).all()
        for h in rows:
            h.tipo_movimiento = "baja"
        db.commit()
        print(f"  [+] Filas de baja reetiquetadas cambio_estado -> baja: {len(rows)}")
        for h in rows:
            print(f"      · {(h.observaciones or '')[:60]}")
        print("\nCorrección completada (idempotente).")
    except Exception as e:
        db.rollback()
        print(f"[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate()
