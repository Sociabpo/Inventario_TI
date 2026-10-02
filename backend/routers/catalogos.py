from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional
from database import get_db
from models.catalogo import Catalogo
from routers.auth import get_current_user
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids, user_has_empresa_access

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos"])

CATEGORIAS_GLOBALES = {"tipo_activo", "tipo_accesorio", "tipo_mantenimiento", "tipo_proveedor", "ciudad", "hosting"}
# "hosting" = ubicación de hosting de servidores (AWS / On-premise / Triara…), GLOBAL.
# NO confundir con "ubicacion" (de activos/accesorios), que es per-empresa (ubicación física del activo).
# "ubicacion" (de activos/accesorios) es per-empresa, como area/cargo/sede.
# Distinta de "sede" (que pertenece a empleados): son conceptos separados.
CATEGORIAS_EMPRESA  = {"area", "cargo", "sede", "ubicacion"}
CATEGORIAS_VALIDAS  = CATEGORIAS_GLOBALES | CATEGORIAS_EMPRESA


# ── Schemas ──────────────────────────────────────────────
class CatalogoCreate(BaseModel):
    categoria:   str
    valor:       str
    descripcion: Optional[str] = None
    empresa_id:  Optional[str] = None
    orden:       Optional[int] = 0
    color:       Optional[str] = None
    icono:       Optional[str] = None
    anios_obsolescencia: Optional[int] = None   # solo para categoria="tipo_activo"
    es_red:      Optional[bool] = None           # solo para categoria="tipo_activo"


class CatalogoUpdate(BaseModel):
    valor:       Optional[str] = None
    descripcion: Optional[str] = None
    activo:      Optional[bool] = None
    orden:       Optional[int] = None
    color:       Optional[str] = None
    icono:       Optional[str] = None
    anios_obsolescencia: Optional[int] = None
    es_red:      Optional[bool] = None


def _dict(c: Catalogo) -> dict:
    return {
        "id": c.id, "categoria": c.categoria, "valor": c.valor,
        "descripcion": c.descripcion, "empresa_id": c.empresa_id,
        "activo": c.activo, "orden": c.orden, "color": c.color, "icono": c.icono,
        "anios_obsolescencia": c.anios_obsolescencia,
        "es_red": c.es_red,
    }


# ── GET lista por categoría (lectura para todos) ──────────
@router.get("")
def listar_catalogo(
    categoria: str,
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    query = db.query(Catalogo).filter(
        Catalogo.activo == True,
        Catalogo.categoria == categoria,
    )
    if empresa_id:
        query = query.filter(or_(Catalogo.empresa_id == empresa_id, Catalogo.empresa_id.is_(None)))
    else:
        query = query.filter(Catalogo.empresa_id.is_(None))
    rows = query.order_by(Catalogo.orden.asc(), Catalogo.valor.asc()).all()
    return [_dict(c) for c in rows]


# ── GET todas las categorías agrupadas (admin) ────────────
@router.get("/todas")
def listar_todas(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("catalogos.ver"),
):
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    # Validar el empresa_id entrante contra el scope del usuario (no confiar en el cliente).
    # super_admin (empresa_ids is None) pasa; empresa_id omitido conserva el comportamiento anterior.
    if empresa_id and empresa_ids is not None and empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    resultado = {}
    for cat in CATEGORIAS_GLOBALES:
        rows = db.query(Catalogo).filter(
            Catalogo.categoria == cat, Catalogo.empresa_id.is_(None)
        ).order_by(Catalogo.orden.asc(), Catalogo.valor.asc()).all()
        resultado[cat] = [_dict(c) for c in rows]
    for cat in CATEGORIAS_EMPRESA:
        q = db.query(Catalogo).filter(Catalogo.categoria == cat)
        if empresa_id:
            q = q.filter(Catalogo.empresa_id == empresa_id)
        elif empresa_ids is not None:
            q = q.filter(Catalogo.empresa_id.in_(empresa_ids))
        resultado[cat] = [_dict(c) for c in q.order_by(Catalogo.orden.asc(), Catalogo.valor.asc()).all()]
    return resultado


# ── POST crear ────────────────────────────────────────────
@router.post("", status_code=status.HTTP_201_CREATED)
def crear_catalogo(
    data: CatalogoCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("catalogos.editar"),
):
    if data.categoria not in CATEGORIAS_VALIDAS:
        raise HTTPException(status_code=400, detail=f"Categoría inválida. Use: {', '.join(sorted(CATEGORIAS_VALIDAS))}")
    if not data.valor or not data.valor.strip():
        raise HTTPException(status_code=400, detail="El valor no puede estar vacío")
    if data.anios_obsolescencia is not None and data.anios_obsolescencia < 0:
        raise HTTPException(status_code=400, detail="Los años de obsolescencia no pueden ser negativos")

    empresa_id = data.empresa_id
    if data.categoria in CATEGORIAS_GLOBALES:
        empresa_id = None  # las globales no llevan empresa
    if empresa_id:
        if not user_has_empresa_access(db, current_user.id, empresa_id):
            raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    valor = data.valor.strip()
    dup = db.query(Catalogo).filter(
        Catalogo.categoria == data.categoria,
        Catalogo.valor == valor,
        Catalogo.empresa_id == empresa_id if empresa_id else Catalogo.empresa_id.is_(None),
    ).first()
    if dup:
        raise HTTPException(status_code=400, detail=f"Ya existe el valor '{valor}' en esta categoría")

    c = Catalogo(
        categoria=data.categoria, valor=valor, descripcion=data.descripcion,
        empresa_id=empresa_id, orden=data.orden or 0, color=data.color, icono=data.icono,
        anios_obsolescencia=(data.anios_obsolescencia if data.categoria == "tipo_activo" else None),
        es_red=(bool(data.es_red) if data.categoria == "tipo_activo" else False),
        activo=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return _dict(c)


# ── PUT actualizar ────────────────────────────────────────
@router.put("/{catalogo_id}")
def actualizar_catalogo(
    catalogo_id: str,
    data: CatalogoUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("catalogos.editar"),
):
    c = db.query(Catalogo).filter(Catalogo.id == catalogo_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Valor de catálogo no encontrado")
    if c.empresa_id and not user_has_empresa_access(db, current_user.id, c.empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    # No se permite desactivar el último valor activo de la categoría
    if data.activo is False and c.activo:
        activos = db.query(Catalogo).filter(
            Catalogo.categoria == c.categoria,
            Catalogo.activo == True,
            Catalogo.empresa_id == c.empresa_id if c.empresa_id else Catalogo.empresa_id.is_(None),
        ).count()
        if activos <= 1:
            raise HTTPException(status_code=400, detail="No puedes desactivar el último valor activo de la categoría")

    if data.valor is not None:
        nuevo = data.valor.strip()
        if not nuevo:
            raise HTTPException(status_code=400, detail="El valor no puede estar vacío")
        if nuevo != c.valor:
            dup = db.query(Catalogo).filter(
                Catalogo.categoria == c.categoria, Catalogo.valor == nuevo,
                Catalogo.empresa_id == c.empresa_id if c.empresa_id else Catalogo.empresa_id.is_(None),
                Catalogo.id != c.id,
            ).first()
            if dup:
                raise HTTPException(status_code=400, detail=f"Ya existe el valor '{nuevo}' en esta categoría")
        c.valor = nuevo
    if data.descripcion is not None: c.descripcion = data.descripcion
    if data.activo is not None:      c.activo = data.activo
    if data.orden is not None:       c.orden = data.orden
    if data.color is not None:       c.color = data.color
    if data.icono is not None:       c.icono = data.icono
    if data.anios_obsolescencia is not None:
        if data.anios_obsolescencia < 0:
            raise HTTPException(status_code=400, detail="Los años de obsolescencia no pueden ser negativos")
        c.anios_obsolescencia = data.anios_obsolescencia
    # es_red: solo aplica a tipo_activo (para otras categorías se ignora)
    if data.es_red is not None and c.categoria == "tipo_activo":
        c.es_red = bool(data.es_red)

    db.commit()
    db.refresh(c)
    return _dict(c)


# ── DELETE (soft) ─────────────────────────────────────────
@router.delete("/{catalogo_id}")
def eliminar_catalogo(
    catalogo_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("catalogos.editar"),
):
    c = db.query(Catalogo).filter(Catalogo.id == catalogo_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Valor de catálogo no encontrado")
    if c.empresa_id and not user_has_empresa_access(db, current_user.id, c.empresa_id):
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
    if c.activo:
        activos = db.query(Catalogo).filter(
            Catalogo.categoria == c.categoria,
            Catalogo.activo == True,
            Catalogo.empresa_id == c.empresa_id if c.empresa_id else Catalogo.empresa_id.is_(None),
        ).count()
        if activos <= 1:
            raise HTTPException(status_code=400, detail="No puedes desactivar el último valor activo de la categoría")
    c.activo = False
    db.commit()
    return {"ok": True, "mensaje": f"'{c.valor}' desactivado"}
