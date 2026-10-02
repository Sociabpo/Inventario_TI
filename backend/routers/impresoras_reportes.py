"""
Sección "Reportes de daño · Impresoras" (solo lectura / reporting).

Lee los ReporteDano guardados en la Fase 3 del módulo de Impresoras y ofrece:
  - lista filtrable (mes / empresa / sede) + ranking "impresoras más reportadas"
  - detalle de un reporte
  - export Excel (reutiliza el builder de routers/export.py)
  - export PDF (WeasyPrint + plantilla + get_logo_base64), en memoria

Prefijo NO anidado (/api/impresoras-reportes) para evitar colisión con la ruta
/api/impresoras/{impresora_id} del router de impresoras. Empresa-scoped; gated impresoras.ver.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from collections import Counter

from database import get_db
from routers.auth import get_current_user
from services.rbac_service import get_all_user_permissions, get_user_empresa_ids

from models.reporte_dano import ReporteDano
from models.impresoras import Impresora
from models.empresa import Empresa
from models.catalogo import Catalogo

router = APIRouter(prefix="/api/impresoras-reportes", tags=["Impresoras · Reportes"])

_LIST_CAP = 500
_RANKING_TOP = 10


def _requiere_ver(db: Session, current_user):
    if "impresoras.ver" not in get_all_user_permissions(db, current_user.id):
        raise HTTPException(status_code=403, detail="Permiso requerido: 'impresoras.ver'")


def _mes_rango(mes: Optional[str]):
    """'YYYY-MM' → (desde, hasta_exclusivo) o (None, None)."""
    if not mes:
        return None, None
    try:
        y, m = mes.split("-"); y, m = int(y), int(m)
        desde = datetime(y, m, 1)
        hasta = datetime(y + 1, 1, 1) if m == 12 else datetime(y, m + 1, 1)
        return desde, hasta
    except (ValueError, AttributeError):
        raise HTTPException(status_code=400, detail="Parámetro 'mes' inválido (use YYYY-MM)")


def _base_query(db, current_user, mes, empresa_id, sede_id, aplicar_sede=True):
    """Query de ReporteDano con scope de empresa + filtros. sede vía join Impresora."""
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    q = db.query(ReporteDano)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            q = q.filter(ReporteDano.empresa_id == empresa_id)
        else:
            q = q.filter(ReporteDano.empresa_id.in_(empresa_ids))
    elif empresa_id:
        q = q.filter(ReporteDano.empresa_id == empresa_id)

    desde, hasta = _mes_rango(mes)
    if desde:
        q = q.filter(ReporteDano.created_at >= desde, ReporteDano.created_at < hasta)

    if aplicar_sede and sede_id:
        q = q.join(Impresora, Impresora.id == ReporteDano.impresora_id)\
             .filter(Impresora.sede_catalogo_id == sede_id)
    return q


def _maps(db, reportes):
    """Carga en lote impresoras + sedes + empresas para los reportes (sin N+1)."""
    imp_ids = {r.impresora_id for r in reportes if r.impresora_id}
    emp_ids = {r.empresa_id for r in reportes if r.empresa_id}
    impresoras = {i.id: i for i in db.query(Impresora).filter(Impresora.id.in_(imp_ids)).all()} if imp_ids else {}
    sede_ids = {i.sede_catalogo_id for i in impresoras.values() if i.sede_catalogo_id}
    sedes = {c.id: c.valor for c in db.query(Catalogo.id, Catalogo.valor).filter(Catalogo.id.in_(sede_ids)).all()} if sede_ids else {}
    empresas = {e.id: e.nombre_empresa for e in db.query(Empresa.id, Empresa.nombre_empresa).filter(Empresa.id.in_(emp_ids)).all()} if emp_ids else {}
    return impresoras, sedes, empresas


def _fila(r, impresoras, sedes, empresas):
    imp = impresoras.get(r.impresora_id)
    sede_nombre = sedes.get(imp.sede_catalogo_id) if (imp and imp.sede_catalogo_id) else None
    desc = r.descripcion_dano or ""
    return {
        "id": r.id,
        "fecha": r.created_at.isoformat() if r.created_at else None,
        "impresora_id": r.impresora_id,
        "modelo": imp.modelo if imp else None,
        "serial": imp.serial if imp else None,
        "sede": sede_nombre,
        "empresa": empresas.get(r.empresa_id),
        "snippet": (desc[:80] + "…") if len(desc) > 80 else desc,
        "generado_por": r.generado_por_email,
        "num_imagenes": r.num_imagenes,
        "enviado": True,   # invariante Fase 3: solo se persiste tras envío exitoso
    }


@router.get("")
def listar_reportes(
    mes: Optional[str] = None,
    empresa_id: Optional[str] = None,
    sede_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _requiere_ver(db, current_user)
    q = _base_query(db, current_user, mes, empresa_id, sede_id)
    reportes = q.order_by(ReporteDano.created_at.desc()).limit(_LIST_CAP).all()
    impresoras, sedes, empresas = _maps(db, reportes)

    lista = [_fila(r, impresoras, sedes, empresas) for r in reportes]

    # Ranking "más reportadas": cuenta por impresora sobre el MISMO set filtrado.
    cont = Counter(r.impresora_id for r in reportes)
    ranking = []
    for imp_id, n in cont.most_common(_RANKING_TOP):
        imp = impresoras.get(imp_id)
        ranking.append({
            "impresora_id": imp_id,
            "modelo": imp.modelo if imp else None,
            "serial": imp.serial if imp else None,
            "sede": sedes.get(imp.sede_catalogo_id) if (imp and imp.sede_catalogo_id) else None,
            "count": n,
        })

    # Opciones de sede para el filtro: sedes presentes con mes+empresa (sin filtrar por sede).
    q_sede = _base_query(db, current_user, mes, empresa_id, None, aplicar_sede=False)
    sede_ids_all = {i.sede_catalogo_id for i in
                    db.query(Impresora).filter(Impresora.id.in_({r.impresora_id for r in q_sede.all()})).all()
                    if i.sede_catalogo_id} if True else set()
    sedes_opt = [{"id": cid, "nombre": val} for cid, val in
                 db.query(Catalogo.id, Catalogo.valor).filter(Catalogo.id.in_(sede_ids_all)).all()] if sede_ids_all else []
    sedes_opt.sort(key=lambda x: (x["nombre"] or "").lower())

    return {
        "total": len(lista),
        "reportes": lista,
        "ranking": ranking,
        "sedes": sedes_opt,
        "truncado": len(reportes) >= _LIST_CAP,
    }


@router.get("/export-excel")
def export_excel_reportes(
    mes: Optional[str] = None,
    empresa_id: Optional[str] = None,
    sede_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _requiere_ver(db, current_user)
    from routers.export import export_excel, ExportRequest, ColumnaExport

    q = _base_query(db, current_user, mes, empresa_id, sede_id)
    reportes = q.order_by(ReporteDano.created_at.desc()).limit(_LIST_CAP).all()
    impresoras, sedes, empresas = _maps(db, reportes)
    prov_ids = {i.proveedor_id for i in impresoras.values() if i.proveedor_id}
    from models.compra import Proveedor
    provs = {p.id: p.nombre for p in db.query(Proveedor.id, Proveedor.nombre).filter(Proveedor.id.in_(prov_ids)).all()} if prov_ids else {}

    columnas = [ColumnaExport(key=k, label=l) for k, l in [
        ("fecha", "Fecha"), ("empresa", "Empresa"), ("sede", "Sede"),
        ("modelo", "Impresora"), ("serial", "Serial"), ("proveedor", "Proveedor"),
        ("descripcion", "Descripción del daño"), ("reporto", "Reportó"),
        ("destinatarios", "Destinatarios"), ("enviado", "Enviado"),
    ]]
    filas = []
    for r in reportes:
        imp = impresoras.get(r.impresora_id)
        filas.append({
            "fecha": r.created_at.strftime("%d/%m/%Y %H:%M") if r.created_at else "",
            "empresa": empresas.get(r.empresa_id, ""),
            "sede": (sedes.get(imp.sede_catalogo_id) if (imp and imp.sede_catalogo_id) else "") or "",
            "modelo": (imp.modelo if imp else "") or "",
            "serial": (imp.serial if imp else "") or "",
            "proveedor": (provs.get(imp.proveedor_id) if (imp and imp.proveedor_id) else "") or "",
            "descripcion": r.descripcion_dano or "",
            "reporto": r.generado_por_email or "",
            "destinatarios": ", ".join(r.destinatarios_list),
            "enviado": "Sí",
        })
    data = ExportRequest(titulo="Reportes de daño · Impresoras",
                         subtitulo=f"{len(filas)} reporte(s)" + (f" — {mes}" if mes else ""),
                         columnas=columnas, filas=filas)
    return export_excel(data=data, current_user=current_user)


@router.get("/export-pdf")
def export_pdf_reportes(
    mes: Optional[str] = None,
    empresa_id: Optional[str] = None,
    sede_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _requiere_ver(db, current_user)
    data = listar_reportes(mes=mes, empresa_id=empresa_id, sede_id=sede_id, db=db, current_user=current_user)

    empresa_nombre, empresa_prefijo = "Todas las empresas", None
    if empresa_id:
        e = db.query(Empresa).filter(Empresa.id == empresa_id).first()
        if e:
            empresa_nombre, empresa_prefijo = e.nombre_empresa, e.prefijo

    ctx = {
        "empresa_nombre": empresa_nombre,
        "empresa_prefijo": empresa_prefijo,
        "periodo": mes or "Todo el histórico",
        "fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "total": data["total"],
        "ranking": data["ranking"],
        "reportes": data["reportes"],
    }
    from services.pdf_service import generar_pdf_reportes_impresoras
    pdf = generar_pdf_reportes_impresoras(ctx)
    fname = "reportes_impresoras" + (f"_{mes}" if mes else "") + ".pdf"
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{fname}"'})


@router.get("/{reporte_id}")
def detalle_reporte(
    reporte_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    _requiere_ver(db, current_user)
    r = db.query(ReporteDano).filter(ReporteDano.id == reporte_id).first()
    if not r:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and r.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese reporte")
    impresoras, sedes, empresas = _maps(db, [r])
    imp = impresoras.get(r.impresora_id)
    return {
        **_fila(r, impresoras, sedes, empresas),
        "descripcion_dano": r.descripcion_dano,
        "asunto": r.asunto,
        "destinatarios": r.destinatarios_list,
        "cc": r.cc_list,
    }
