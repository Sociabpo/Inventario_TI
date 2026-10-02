r"""
Migración: numeración robusta de compras (solicitudes + órdenes).

1) Agrega ordenes_compra.referencia_proveedor VARCHAR(100) NULL (referencia
   propia del proveedor, separada del número de sistema).
2) Siembra la tabla `consecutivos` para que el nuevo generador robusto continúe
   sin colisionar con los números YA emitidos:
     - tipo 'SOLICITUD-{YYYY}' ← max(NNN) de numero_solicitud (patrón SC-YYYY-NNN)
     - tipo 'ORDEN-{YYYY}'     ← max(NNN) de numero_oc (patrón OC-YYYY-NNN; hoy
       no hay ninguno con ese patrón, así que arranca en 0)
   Se siembra por (empresa_id, tipo). Idempotente: fija el contador al máximo
   observado (no suma). Solo esquema/contadores — NO crea solicitudes/órdenes.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_compras_numeracion.py
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text
from models.consecutivo import Consecutivo
from models.compra import SolicitudCompra, OrdenCompra

TABLA = "ordenes_compra"
COLUMNA = "referencia_proveedor"


def _existe_columna(conn, tabla, columna) -> bool:
    return bool(conn.execute(text(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t AND COLUMN_NAME = :c"
    ), {"t": tabla, "c": columna}).scalar())


# ── 1) Columna referencia_proveedor ──
with engine.connect() as conn:
    try:
        if _existe_columna(conn, TABLA, COLUMNA):
            print(f"[=] {TABLA}.{COLUMNA} ya existe - omitido")
        else:
            conn.execute(text(f"ALTER TABLE {TABLA} ADD COLUMN {COLUMNA} VARCHAR(100) NULL"))
            conn.commit()
            print(f"[+] {TABLA}.{COLUMNA} agregada")
    except Exception as e:
        print(f"[ERROR] columna {COLUMNA}: {e}")
        sys.exit(1)


def _sembrar(db, rows, patron, tipo_base, campo):
    """rows: (empresa_id, numero). Fija Consecutivo[(empresa, '{tipo_base}-{YYYY}')]
    al max(NNN) observado. Devuelve cuántos contadores tocó."""
    rx = re.compile(patron)
    maximos = {}  # (empresa_id, anio) -> max_nnn
    for empresa_id, numero in rows:
        if not numero:
            continue
        m = rx.match(numero.strip())
        if not m:
            continue
        anio, nnn = m.group(1), int(m.group(2))
        clave = (empresa_id, anio)
        if nnn > maximos.get(clave, 0):
            maximos[clave] = nnn

    tocados = 0
    for (empresa_id, anio), max_nnn in maximos.items():
        tipo = f"{tipo_base}-{anio}"
        c = db.query(Consecutivo).filter(
            Consecutivo.empresa_id == empresa_id, Consecutivo.tipo == tipo
        ).first()
        if not c:
            c = Consecutivo(empresa_id=empresa_id, tipo=tipo, ultimo_numero=max_nnn)
            db.add(c)
        else:
            c.ultimo_numero = max(c.ultimo_numero or 0, max_nnn)
        tocados += 1
        print(f"    {tipo} (empresa {empresa_id[:8]}) -> ultimo_numero={max_nnn}")
    return tocados


# ── 2) Sembrar consecutivos ──
db = SessionLocal()
try:
    sols = [(s.empresa_id, s.numero_solicitud) for s in db.query(SolicitudCompra).all()]
    ords = [(o.empresa_id, o.numero_oc) for o in db.query(OrdenCompra).all()]
    print("[*] Sembrando SOLICITUD-*:")
    n1 = _sembrar(db, sols, r"^SC-(\d{4})-(\d+)$", "SOLICITUD", "numero_solicitud")
    print("[*] Sembrando ORDEN-*:")
    n2 = _sembrar(db, ords, r"^OC-(\d{4})-(\d+)$", "ORDEN", "numero_oc")
    db.commit()
    print(f"\n[+] Contadores sembrados: {n1} solicitud(es), {n2} orden(es).")
    print("Migracion de numeracion de compras completada.")
except Exception as e:
    db.rollback()
    print(f"[ERROR] siembra de consecutivos: {e}")
    sys.exit(1)
finally:
    db.close()
