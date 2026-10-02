r"""
Migración: flag `es_red` en el catálogo (categoria='tipo_activo').

Un tipo_activo marcado `es_red=1` es un dispositivo de red MONTABLE en el módulo
de Redes (reemplaza el match por palabra clave del regex). El flag no aplica a
otras categorías (sede, ubicacion, etc.) — ahí se ignora.

Idempotente:
  - ADD COLUMN es_red guardado por information_schema (no-op si ya existe).
  - PRE-MARK: sobre las filas EXISTENTES de categoria='tipo_activo', aplica en
    PYTHON el MISMO regex que usaba es_tipo_red() y pone es_red=1 en las que
    coinciden (Switch, Router, Firewall, Access Point, AP, UPS, ONT, Patch…),
    para que los tipos obvios queden marcados sin intervención. Solo toca
    filas de categoria='tipo_activo'. Idempotente: volver a correr no cambia nada.

Uso (desde backend/):
    venv\Scripts\python.exe scripts/migrate_catalogo_es_red.py
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import engine, SessionLocal
from sqlalchemy import text
from models.catalogo import Catalogo

# MISMO regex que usaba routers/redes.py: es_tipo_red()
_TIPO_RED_RE = re.compile(r"switch|router|firewall|access\s*point|\bap\b|ups|ont|patch", re.IGNORECASE)


def _add_column():
    with engine.begin() as conn:
        existe = conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = 'catalogos' "
            "AND column_name = 'es_red'"
        )).scalar()
        if existe:
            print("  [=] Columna es_red ya existe — no se agrega.")
        else:
            conn.execute(text(
                "ALTER TABLE catalogos ADD COLUMN es_red TINYINT(1) NOT NULL DEFAULT 0"
            ))
            print("  [+] Columna es_red agregada a catalogos.")


def _premark():
    db = SessionLocal()
    try:
        # SOLO categoria='tipo_activo'
        tipos = db.query(Catalogo).filter(Catalogo.categoria == "tipo_activo").all()
        marcados = 0
        for t in tipos:
            deberia = bool(_TIPO_RED_RE.search(t.valor or ""))
            if deberia and not t.es_red:
                t.es_red = True
                marcados += 1
        db.commit()
        total_red = db.query(Catalogo).filter(
            Catalogo.categoria == "tipo_activo", Catalogo.es_red == True).count()
        print(f"  [+] Pre-marcados en esta corrida: {marcados} "
              f"(de {len(tipos)} tipo_activo). Total con es_red=1 ahora: {total_red}.")
    finally:
        db.close()


def migrate():
    _add_column()
    _premark()
    print("\nMigración es_red completada.")


if __name__ == "__main__":
    migrate()
