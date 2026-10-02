from datetime import datetime
from sqlalchemy.orm import Session
from models.consecutivo import Consecutivo
from models.empresa import Empresa


def generar_numero_documento(db: Session, empresa_id: str, tipo_base: str,
                             prefijo: str, anio: int = None) -> str:
    """Consecutivo robusto por empresa+año para documentos de compras
    (solicitudes, órdenes). El año se codifica en `tipo` (p. ej. 'SOLICITUD-2026')
    para que el contador reinicie solo en cada año nuevo. Usa SELECT FOR UPDATE,
    igual que las placas. Formato: '{prefijo}-{anio}-{NNN}' (ej. SC-2026-001)."""
    anio = anio or datetime.now().year
    tipo = f"{tipo_base}-{anio}"          # cabe en Consecutivo.tipo VARCHAR(20)
    consecutivo = db.query(Consecutivo).filter(
        Consecutivo.empresa_id == empresa_id,
        Consecutivo.tipo == tipo,
    ).with_for_update().first()
    if not consecutivo:
        consecutivo = Consecutivo(empresa_id=empresa_id, tipo=tipo, ultimo_numero=0)
        db.add(consecutivo)
    consecutivo.ultimo_numero += 1
    numero = consecutivo.ultimo_numero
    db.flush()  # mantiene el lock sin commit
    return f"{prefijo}-{anio}-{str(numero).zfill(3)}"

def generar_placa_activo(db: Session, empresa_id: str) -> str:
    """
    Genera el siguiente consecutivo para un activo.
    Formato: SC0001, AA0001, etc.
    Usa SELECT FOR UPDATE para evitar duplicados en concurrencia.
    """
    # Obtener o crear el registro de consecutivo
    consecutivo = db.query(Consecutivo).filter(
        Consecutivo.empresa_id == empresa_id,
        Consecutivo.tipo == "ACTIVO"
    ).with_for_update().first()

    if not consecutivo:
        consecutivo = Consecutivo(
            empresa_id=empresa_id,
            tipo="ACTIVO",
            ultimo_numero=0
        )
        db.add(consecutivo)

    consecutivo.ultimo_numero += 1
    numero = consecutivo.ultimo_numero

    # Obtener prefijo de la empresa
    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    prefijo = empresa.prefijo if empresa else "XX"

    db.flush()  # Escribe sin commit para mantener el lock

    # Formato: SC0001 (prefijo + 4 dígitos)
    return f"{prefijo}{str(numero).zfill(4)}"


def generar_placa_accesorio(db: Session, empresa_id: str) -> str:
    """
    Genera el siguiente consecutivo para un accesorio.
    Formato: SCA0001, AAA0001, etc.
    """
    consecutivo = db.query(Consecutivo).filter(
        Consecutivo.empresa_id == empresa_id,
        Consecutivo.tipo == "ACCESORIO"
    ).with_for_update().first()

    if not consecutivo:
        consecutivo = Consecutivo(
            empresa_id=empresa_id,
            tipo="ACCESORIO",
            ultimo_numero=0
        )
        db.add(consecutivo)

    consecutivo.ultimo_numero += 1
    numero = consecutivo.ultimo_numero

    empresa = db.query(Empresa).filter(Empresa.id == empresa_id).first()
    prefijo = empresa.prefijo if empresa else "XX"

    db.flush()

    # Formato: SCA0001 (prefijo + A + 4 dígitos)
    return f"{prefijo}A{str(numero).zfill(4)}"