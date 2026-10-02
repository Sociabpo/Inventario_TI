"""
Catálogo COMPARTIDO y GLOBAL de proveedores (surface neutral).

Sirve la MISMA tabla `proveedores` que compras, pero bajo un prefijo neutral
(/api/proveedores) y con permisos neutrales (proveedores.ver / proveedores.gestionar),
para que el módulo de Impresoras (y cualquier módulo futuro) lo consuma sin depender
de permisos de compras.

Los proveedores son GLOBALES/transversales: no pertenecen a ninguna empresa. No hay
filtro ni validación por empresa. Cada proveedor declara a qué módulos aplica
(columna `modulos`, JSON list); el filtro ?modulo= es OPCIONAL.

Reutiliza el modelo Proveedor, el dict y los schemas del router de compras.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional

from database import get_db
from models.compra import Proveedor
from dependencies.rbac import require_permission
# Reutilizamos el mismo dict y schemas que compras (misma forma exacta)
from routers.compras import _proveedor_dict, ProveedorIn, ProveedorUpdate

router = APIRouter(prefix="/api/proveedores", tags=["Proveedores (catálogo compartido)"])


@router.get("")
def listar_proveedores(
    modulo: Optional[str] = None,      # opcional: filtra por módulo (compras, impresoras, …)
    activo: Optional[bool] = None,
    tipo: Optional[str] = None,
    q: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user = require_permission("proveedores.ver"),
):
    # Proveedores GLOBALES: sin filtro por empresa.
    query = db.query(Proveedor)
    if tipo:
        query = query.filter(Proveedor.tipo == tipo)
    if activo is not None:
        query = query.filter(Proveedor.activo == activo)
    if q:
        query = query.filter(or_(
            Proveedor.nombre.ilike(f"%{q}%"),
            Proveedor.nit.ilike(f"%{q}%"),
        ))
    rows = query.order_by(Proveedor.nombre).all()
    # Filtro por módulo en Python (respeta el fallback NULL→['compras'] de modulos_list).
    if modulo:
        rows = [p for p in rows if modulo in p.modulos_list]
    return [_proveedor_dict(p) for p in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_proveedor(
    data: ProveedorIn,
    db: Session = Depends(get_db),
    current_user = require_permission("proveedores.gestionar"),
):
    if data.nit:
        dup = db.query(Proveedor).filter(Proveedor.nit == data.nit).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Ya existe un proveedor con NIT {data.nit}")
    payload = data.model_dump(exclude={"modulos"})
    payload["modulos"] = json.dumps(data.modulos if data.modulos else ["compras"])
    p = Proveedor(**payload)
    db.add(p)
    db.commit()
    db.refresh(p)
    return _proveedor_dict(p)


@router.get("/{proveedor_id}")
def obtener_proveedor(
    proveedor_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("proveedores.ver"),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    return _proveedor_dict(p)


@router.put("/{proveedor_id}")
def actualizar_proveedor(
    proveedor_id: str,
    data: ProveedorUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("proveedores.gestionar"),
):
    p = db.query(Proveedor).filter(Proveedor.id == proveedor_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proveedor no encontrado")
    if data.nit:
        dup = db.query(Proveedor).filter(
            Proveedor.nit == data.nit, Proveedor.id != proveedor_id
        ).first()
        if dup:
            raise HTTPException(status_code=400, detail=f"Ya existe un proveedor con NIT {data.nit}")
    for campo, valor in data.model_dump(exclude_unset=True).items():
        if campo == "modulos":
            if valor is not None:
                p.modulos = json.dumps(valor)
            continue
        setattr(p, campo, valor)
    db.commit()
    db.refresh(p)
    return _proveedor_dict(p)
