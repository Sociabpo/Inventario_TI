"""
Lógica reutilizable de creación de inventario (activos / accesorios).

El núcleo de creación vive aquí para que TANTO el endpoint normal
(POST /activos, POST /accesorios) COMO el flujo de "crear inventario desde
recepción" usen exactamente la misma lógica: numeración consecutiva de placa,
cálculo automático de fecha de obsolescencia (catálogo) e historial de creación.

Las funciones *_core hacen db.add + db.flush() pero NO commitean, para que el
llamador pueda agregar registros relacionados (RecepcionItemCreado, garantías)
en la misma transacción y commitear una sola vez.

Aquí también viven los helpers de obsolescencia (antes en routers/activos.py)
para evitar import circular service↔router.
"""
from datetime import date
from typing import Optional
import calendar
import re
import unicodedata
from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from models.activo import Activo
from models.accesorio import Accesorio
from models.empresa import Empresa
from models.usuario import Usuario
from models.catalogo import Catalogo
from models.historial import HistorialMovimiento
from services.consecutivo_service import generar_placa_activo, generar_placa_accesorio
from services.rbac_service import get_user_empresa_ids, empresas_pueden_compartir


# ── Custodio: resolver empleado responsable (activo + misma empresa o hermana) ──
def resolver_custodio(db: Session, empresa_recurso_id: str, documento: str) -> Usuario:
    """Resuelve un empleado por documento para custodia. Debe estar activo y
    pertenecer a la empresa del recurso o a una relacionada. Lanza 400 si no."""
    doc = (documento or "").strip()
    if not doc:
        raise HTTPException(status_code=400, detail="Indica la cédula del custodio")
    empleados = db.query(Usuario).filter(
        Usuario.documento == doc, Usuario.estado == "activo").all()
    elegible = next(
        (u for u in empleados if empresas_pueden_compartir(db, empresa_recurso_id, u.empresa_id)), None)
    if not empleados:
        raise HTTPException(status_code=400, detail=f"No existe un empleado activo con cédula '{doc}'")
    if not elegible:
        raise HTTPException(status_code=400,
                            detail=f"El empleado '{doc}' no pertenece a la empresa del recurso ni a una empresa relacionada")
    return elegible


# ── Ubicación contra el catálogo per-empresa ──────────────
def _norm_txt(s) -> str:
    """minúsculas, sin acentos, espacios colapsados (para match flexible)."""
    if s is None:
        return ""
    s = str(s).strip().lower()
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return re.sub(r"\s+", " ", s)


def resolver_catalogo_empresa(db: Session, empresa_id: str, categoria: str, valor):
    """Resuelve un valor contra un catálogo per-empresa (ubicacion, sede, area…).
    Match flexible (case/acento-insensible); devuelve el valor CANÓNICO del catálogo.
    Retorna (valor_canonico_o_None, ok):
      - valor vacío → (None, True)   (el llamador decide si es obligatorio)
      - coincide con una entrada activa de la empresa (o global) → (canónico, True)
      - no coincide → (valor_tal_cual, False)
    """
    if valor is None or not str(valor).strip():
        return None, True
    objetivo = _norm_txt(valor)
    rows = db.query(Catalogo).filter(
        Catalogo.categoria == categoria,
        Catalogo.activo == True,
        or_(Catalogo.empresa_id == empresa_id, Catalogo.empresa_id.is_(None)),
    ).all()
    for c in rows:
        if _norm_txt(c.valor) == objetivo:
            return c.valor, True
    return str(valor).strip(), False


def validar_catalogo_o_400(db: Session, empresa_id: str, categoria: str, valor, etiqueta: str):
    """Devuelve el valor canónico o lanza 400 si no existe en el catálogo per-empresa."""
    canonico, ok = resolver_catalogo_empresa(db, empresa_id, categoria, valor)
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"{etiqueta} '{valor}' no existe en el catálogo de la empresa. Créala en Administración → Catálogos.")
    return canonico


def resolver_ubicacion_catalogo(db: Session, empresa_id: str, valor):
    """Wrapper de compatibilidad para 'ubicacion' (activos/accesorios)."""
    return resolver_catalogo_empresa(db, empresa_id, "ubicacion", valor)


def _validar_ubicacion_o_400(db: Session, empresa_id: str, valor):
    """Devuelve la ubicación canónica o lanza 400 si no existe en el catálogo."""
    return validar_catalogo_o_400(db, empresa_id, "ubicacion", valor, "La ubicación")


# ── Obsolescencia (años por tipo, desde el catálogo) ──────
def lookup_anios_obsolescencia(db: Session, tipo_activo: Optional[str]):
    """Años de obsolescencia configurados para un tipo_activo en el catálogo.
    tipo_activo es categoría global; si existiera una entrada por empresa se
    prefiere esa. Devuelve None si no hay match o no tiene años definidos."""
    if not tipo_activo:
        return None
    cat = db.query(Catalogo).filter(
        Catalogo.categoria == "tipo_activo",
        Catalogo.valor == tipo_activo,
        Catalogo.activo == True,
    ).order_by(Catalogo.empresa_id.isnot(None).desc()).first()
    return cat.anios_obsolescencia if cat else None


def sumar_anios(base_date: date, anios: int) -> date:
    """base_date + N años. Maneja el 29-feb cayendo en año no bisiesto."""
    try:
        return base_date.replace(year=base_date.year + anios)
    except ValueError:
        return base_date.replace(month=2, day=28, year=base_date.year + anios)


def calcular_fecha_obsolescencia(db: Session, tipo_activo: Optional[str], fecha_compra: Optional[date]):
    """Devuelve (anios, fecha_obsolescencia) o (None, None) si no hay años definidos."""
    anios = lookup_anios_obsolescencia(db, tipo_activo)
    if anios is None:
        return None, None
    base = fecha_compra or date.today()
    return anios, sumar_anios(base, anios)


# ── Garantía simple (meses → fecha fin, desde fecha_compra o hoy) ──
def sumar_meses(base_date: date, meses: int) -> date:
    """base_date + N meses, recortando el día al último válido del mes destino
    (p. ej. 31-ene + 1 mes = 28/29-feb)."""
    total = base_date.month - 1 + meses
    anio = base_date.year + total // 12
    mes = total % 12 + 1
    dia = min(base_date.day, calendar.monthrange(anio, mes)[1])
    return date(anio, mes, dia)


def calcular_garantia_fin(meses: Optional[int], fecha_compra: Optional[date]):
    """Devuelve la fecha fin de garantía o None si no hay meses.
    Base = fecha_compra si existe, si no hoy."""
    if meses is None:
        return None
    base = fecha_compra or date.today()
    return sumar_meses(base, meses)


def _aplicar_garantia(obj, data):
    """Auto-calcula garantia_fin SOLO si no se envió explícitamente y hay meses.
    Valida que los meses no sean negativos. `data` puede o no tener fecha_compra."""
    meses = getattr(data, "garantia_meses", None)
    if meses is not None and meses < 0:
        raise HTTPException(status_code=400, detail="garantia_meses no puede ser negativo")
    fin = getattr(data, "garantia_fin", None)
    if fin is None and meses is not None:
        obj.garantia_fin = calcular_garantia_fin(meses, getattr(data, "fecha_compra", None))


# ── Validación de empresa (idéntica a los endpoints POST) ──
def _validar_empresa(db: Session, current_user, empresa_id: str):
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    return empresa


# ── Núcleo de creación (sin commit) ───────────────────────
def crear_activo_core(db: Session, data, current_user) -> Activo:
    """Crea un Activo con la MISMA lógica que POST /activos (placa, obsolescencia,
    historial). `data` es un ActivoCreate (o equivalente con .model_dump()).
    Hace flush pero NO commit."""
    _validar_empresa(db, current_user, data.empresa_id)
    placa = generar_placa_activo(db, data.empresa_id)
    activo = Activo(id_placa_activo=placa, **data.model_dump())
    # Ubicación contra el catálogo de la empresa (si se proporcionó)
    activo.ubicacion = _validar_ubicacion_o_400(db, data.empresa_id, activo.ubicacion)

    # Auto-calcular fecha de obsolescencia SOLO si no se envió explícitamente.
    if data.fecha_obsolescencia is None:
        _, fecha_obs = calcular_fecha_obsolescencia(db, activo.tipo_activo, activo.fecha_compra)
        if fecha_obs is not None:
            activo.fecha_obsolescencia = fecha_obs

    # Auto-calcular fin de garantía (mismo patrón; meses desde fecha_compra)
    _aplicar_garantia(activo, data)

    db.add(activo)
    db.add(HistorialMovimiento(
        id_activo=activo.id, tipo_movimiento="creacion",
        responsable=current_user.email,
        observaciones=f"Activo {placa} registrado en el sistema",
    ))
    db.flush()
    return activo


def crear_accesorio_core(db: Session, data, current_user) -> Accesorio:
    """Crea un Accesorio con la MISMA lógica que POST /accesorios (placa, historial).
    `data` es un AccesorioCreate. Hace flush pero NO commit."""
    _validar_empresa(db, current_user, data.empresa_id)
    placa = generar_placa_accesorio(db, data.empresa_id)
    accesorio = Accesorio(id_placa_accesorio=placa, **data.model_dump())
    # Ubicación contra el catálogo de la empresa (si se proporcionó)
    accesorio.ubicacion = _validar_ubicacion_o_400(db, data.empresa_id, accesorio.ubicacion)
    # Auto-calcular fin de garantía (accesorios no tienen fecha_compra → base hoy)
    _aplicar_garantia(accesorio, data)
    db.add(accesorio)
    db.add(HistorialMovimiento(
        id_accesorio=accesorio.id, tipo_movimiento="creacion",
        responsable=current_user.email,
        observaciones=f"Accesorio {placa} registrado en el sistema",
    ))
    db.flush()
    return accesorio
