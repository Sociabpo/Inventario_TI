"""
Seed de catálogos globales + permisos RBAC del módulo.
Idempotente: puede ejecutarse varias veces.

Uso (desde backend/):
    python scripts/seed_catalogos.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal
from models.catalogo import Catalogo
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso

# ── Valores por defecto (globales, empresa_id=NULL) ───────────────────────────
DEFAULTS = {
    "tipo_activo": [
        "AIO", "Camara", "Celular", "Diadema", "DVR", "Escaner", "Impresora",
        "Ipad", "Monitor", "PC", "Portatil", "Tablet", "Telefono", "Televisor",
        "UPS", "Video Beam",
    ],
    "tipo_accesorio": [
        "Mouse", "Teclado", "Diadema", "Hub USB", "Cargador", "Bolso/Maletín",
        "Cable HDMI", "Cable USB", "Webcam", "Micrófono", "Base portátil",
        "Pad mouse", "Lector huella", "Token USB",
    ],
    "tipo_mantenimiento": [
        "Preventivo", "Correctivo", "Predictivo", "Garantía", "Limpieza",
        "Actualización software", "Cambio de pieza", "Revisión técnica",
    ],
    "tipo_proveedor": ["vendedor", "arrendador", "fabricante"],
}

# Años de obsolescencia por tipo de activo (acentuado y sin acento)
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

# ── Permisos RBAC ─────────────────────────────────────────────────────────────
PERMISOS = [
    ("catalogos.ver",    "Ver catálogos / listas desplegables"),
    ("catalogos.editar", "Crear y editar valores de catálogos"),
]
ROL_PERMISOS = {
    "super_admin":      {"catalogos.ver", "catalogos.editar"},
    "admin":            {"catalogos.ver", "catalogos.editar"},
    "analista_activos": {"catalogos.ver"},
    "soporte_ti":       {"catalogos.ver"},
    "auditoria":        {"catalogos.ver"},
    "rrhh":             {"catalogos.ver"},
}


def seed():
    db = SessionLocal()
    try:
        print("Seed de catálogos...\n")
        nuevos = 0
        anios_set = 0
        for categoria, valores in DEFAULTS.items():
            for i, valor in enumerate(valores, start=1):
                anios = ANIOS_OBSOLESCENCIA.get(valor) if categoria == "tipo_activo" else None
                existe = db.query(Catalogo).filter(
                    Catalogo.categoria == categoria,
                    Catalogo.valor == valor,
                    Catalogo.empresa_id.is_(None),
                ).first()
                if not existe:
                    db.add(Catalogo(categoria=categoria, valor=valor, orden=i, activo=True,
                                    anios_obsolescencia=anios))
                    nuevos += 1
                elif anios is not None and existe.anios_obsolescencia != anios:
                    # idempotente: actualiza los años si el tipo_activo ya existe
                    existe.anios_obsolescencia = anios
                    anios_set += 1
        db.commit()
        print(f"  [+] {nuevos} valores de catálogo nuevos insertados.")
        print(f"  [+] {anios_set} tipo_activo existentes actualizados con años de obsolescencia.")

        # Permisos
        print("\nSeed de permisos RBAC de catálogos...")
        permisos_map = {}
        for codigo, desc in PERMISOS:
            modulo, accion = codigo.split(".", 1)
            p = db.query(Permiso).filter_by(codigo=codigo).first()
            if not p:
                p = Permiso(codigo=codigo, descripcion=desc, modulo=modulo, accion=accion)
                db.add(p); db.flush()
                print(f"  [+] Permiso creado: {codigo}")
            else:
                print(f"  [=] Permiso existente: {codigo}")
            permisos_map[codigo] = p

        nuevas = 0
        for nombre_rol, codigos in ROL_PERMISOS.items():
            rol = db.query(Rol).filter_by(nombre=nombre_rol).first()
            if not rol:
                print(f"  [!] Rol no encontrado (omitido): {nombre_rol}")
                continue
            for codigo in codigos:
                exists = db.query(RolPermiso).filter_by(
                    rol_id=rol.id, permiso_id=permisos_map[codigo].id
                ).first()
                if not exists:
                    db.add(RolPermiso(rol_id=rol.id, permiso_id=permisos_map[codigo].id))
                    nuevas += 1
        db.commit()
        print(f"  [+] {nuevas} asociaciones rol-permiso nuevas.")
        print("\nSeed de catálogos completado.")
    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
