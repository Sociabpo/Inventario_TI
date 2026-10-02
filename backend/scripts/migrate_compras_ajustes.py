r"""
Migración: ajustes al módulo Compras.
  - solicitudes_compra: numero_solicitud, titulo, motivo_cancelacion
  - backfill de numero_solicitud y titulo para filas existentes (idempotente)

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_compras_ajustes.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine
from sqlalchemy import text

COLUMNS = [
    ("numero_solicitud", "ALTER TABLE solicitudes_compra ADD COLUMN numero_solicitud VARCHAR(20) NOT NULL DEFAULT ''"),
    ("titulo",           "ALTER TABLE solicitudes_compra ADD COLUMN titulo VARCHAR(200) NOT NULL DEFAULT ''"),
    ("motivo_cancelacion","ALTER TABLE solicitudes_compra ADD COLUMN motivo_cancelacion TEXT NULL"),
]

with engine.connect() as conn:
    for nombre, ddl in COLUMNS:
        try:
            conn.execute(text(ddl))
            conn.commit()
            print(f"[+] Columna agregada: {nombre}")
        except Exception as e:
            msg = str(e).lower()
            if "duplicate column" in msg or "already exists" in msg or "1060" in msg:
                print(f"[=] Columna ya existe: {nombre}")
            else:
                print(f"[ERROR] {nombre}: {e}")
                sys.exit(1)

    # ── Backfill de filas existentes sin numero/titulo ──
    try:
        filas = conn.execute(text(
            "SELECT id, empresa_id, justificacion, YEAR(created_at) AS anio "
            "FROM solicitudes_compra WHERE numero_solicitud = '' OR numero_solicitud IS NULL "
            "ORDER BY empresa_id, created_at"
        )).fetchall()
        contador = {}
        backfilled = 0
        for fila in filas:
            sid, empresa_id, justificacion, anio = fila
            anio = anio or 2024
            clave = (empresa_id, anio)
            contador[clave] = contador.get(clave, 0) + 1
            numero = f"SC-{anio}-{contador[clave]:03d}"
            titulo = (justificacion or "Solicitud")[:60].strip() or "Solicitud"
            conn.execute(
                text("UPDATE solicitudes_compra SET numero_solicitud = :n, "
                     "titulo = CASE WHEN titulo = '' OR titulo IS NULL THEN :t ELSE titulo END "
                     "WHERE id = :id"),
                {"n": numero, "t": titulo, "id": sid},
            )
            backfilled += 1
        conn.commit()
        print(f"[+] Backfill aplicado a {backfilled} solicitud(es) existente(s).")
    except Exception as e:
        print(f"[!] Backfill omitido: {e}")

    print("\nMigración de ajustes de Compras completada.")
