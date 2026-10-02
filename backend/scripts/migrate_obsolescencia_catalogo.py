r"""
Migración: años de obsolescencia por tipo de activo en el catálogo.

1) Agrega a `catalogos`:
       anios_obsolescencia INTEGER NULL
2) Pobla los tipo_activo existentes (match por valor, solo categoria='tipo_activo').

Idempotente: comprueba information_schema antes del ALTER y hace UPSERT de los años.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_obsolescencia_catalogo.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

# Años por tipo (acentuado y sin acento)
ANIOS_OBSOLESCENCIA = {
    "PC": 5, "Portátil": 5, "Portatil": 5, "AIO": 5,
    "Monitor": 7, "Televisor": 7,
    "Video Beam": 6,
    "Celular": 3, "Teléfono": 7, "Telefono": 7,
    "Tablet": 4, "Ipad": 4,
    "Impresora": 5, "Escaner": 6,
    "Camara": 6, "DVR": 6,
    "Diadema": 3, "UPS": 4,
}


def _columna_existe(conn, tabla, columna) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": tabla, "c": columna}).scalar())


with engine.connect() as conn:
    # 1) ALTER
    try:
        if _columna_existe(conn, "catalogos", "anios_obsolescencia"):
            print("[=] catalogos.anios_obsolescencia ya existe — omitido")
        else:
            conn.execute(text("ALTER TABLE catalogos ADD COLUMN anios_obsolescencia INTEGER NULL"))
            conn.commit()
            print("[+] catalogos.anios_obsolescencia agregada")
    except Exception as e:
        print(f"[ERROR] ALTER: {e}")
        sys.exit(1)

    # 2) UPDATE de los tipo_activo existentes
    actualizados = 0
    for valor, anios in ANIOS_OBSOLESCENCIA.items():
        res = conn.execute(text(
            "UPDATE catalogos SET anios_obsolescencia = :a "
            "WHERE categoria = 'tipo_activo' AND valor = :v"
        ), {"a": anios, "v": valor})
        if res.rowcount:
            actualizados += res.rowcount
            print(f"  [.] {valor} = {anios} anios ({res.rowcount} fila/s)")
    conn.commit()
    print(f"\n[+] {actualizados} tipo_activo actualizados con años de obsolescencia.")
    print("Migración de obsolescencia completada.")
