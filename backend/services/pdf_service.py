import hashlib
import base64
from pathlib import Path
from jinja2 import Environment, FileSystemLoader
from weasyprint import HTML
from datetime import datetime

BASE_DIR      = Path(__file__).parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STORAGE_DIR   = BASE_DIR / "storage" / "actas"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

_MESES_ES = {
    1:'enero', 2:'febrero', 3:'marzo', 4:'abril', 5:'mayo', 6:'junio',
    7:'julio', 8:'agosto', 9:'septiembre', 10:'octubre', 11:'noviembre', 12:'diciembre',
}

def _fecha_constancia(dt: datetime) -> str:
    return f"{dt.day} días del mes de {_MESES_ES[dt.month]} del {dt.year}"


def get_logo_base64(prefijo_empresa: str) -> str:
    logo_path = TEMPLATES_DIR / "img" / f"logo_{prefijo_empresa}.png"
    if not logo_path.exists():
        logo_path = TEMPLATES_DIR / "img" / "logo.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return None


def generar_numero_acta(empresa_prefijo: str, acta_id: str, tipo: str) -> str:
    sufijo = acta_id.replace("-", "").upper()[:4]
    prefijo = "FTDEV" if tipo == "devolucion" else "FTIN"
    return f"{prefijo}{empresa_prefijo}{sufijo}"


def generar_pdf_acta_accesorios(acta, usuario, empresa, accesorios: list, usuario_ti=None, firma_base64: str = None, nombre_firmante: str = None, entrega_por_tercero: bool = False, nombre_tercero: str = None, relacion_tercero: str = None, observaciones_firma: str = None, correo_movil: bool = None) -> tuple:
    """
    Genera el PDF de un acta de accesorios (entrega o devolución sin activo principal).
    Retorna (ruta_relativa, hash_sha256).
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    if acta.tipo == "devolucion":
        template = env.get_template("acta_devolucion_accesorios.html")
    else:
        template = env.get_template("acta_entrega_accesorios.html")

    numero_acta  = generar_numero_acta(empresa.prefijo, str(acta.id), acta.tipo)
    logo_base64  = get_logo_base64(empresa.prefijo)
    now          = datetime.now()
    fecha        = now.strftime("%d/%m/%Y")
    fecha_emision= now.strftime("%d-%m-%Y")

    html_content = template.render(
        acta=acta,
        usuario=usuario,
        empresa=empresa,
        accesorios=accesorios,
        usuario_ti=usuario_ti,
        numero_acta=numero_acta,
        logo_base64=logo_base64,
        fecha=fecha,
        fecha_emision=fecha_emision,
        fecha_constancia=_fecha_constancia(now),
        firma_base64=firma_base64,
        nombre_firmante=nombre_firmante,
        entrega_por_tercero=entrega_por_tercero,
        nombre_tercero=nombre_tercero,
        relacion_tercero=relacion_tercero,
        observaciones_firma=observaciones_firma,
        correo_movil=correo_movil,
    )

    empresa_dir = STORAGE_DIR / empresa.prefijo
    empresa_dir.mkdir(exist_ok=True)

    nombre_archivo = f"{numero_acta}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    ruta_pdf       = empresa_dir / nombre_archivo

    HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf(str(ruta_pdf))

    with open(ruta_pdf, "rb") as f:
        hash_pdf = hashlib.sha256(f.read()).hexdigest()

    ruta_relativa = f"storage/actas/{empresa.prefijo}/{nombre_archivo}"
    return ruta_relativa, hash_pdf


def generar_pdf_acta(acta, activo, usuario, empresa, accesorios: list, usuario_ti=None, activos_extra: list = None, firma_base64: str = None, nombre_firmante: str = None, entrega_por_tercero: bool = False, nombre_tercero: str = None, relacion_tercero: str = None, observaciones_firma: str = None, correo_movil: bool = None) -> tuple:
    """
    Genera el PDF del acta (entrega o devolución) y lo guarda en storage.
    activos_extra: lista de activos adicionales al principal (para actas acumuladas).
    Retorna (ruta_relativa, hash_sha256).
    """
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))

    if acta.tipo == "devolucion":
        template = env.get_template("acta_devolucion.html")
    else:
        template = env.get_template("acta_entrega.html")

    numero_acta   = generar_numero_acta(empresa.prefijo, str(acta.id), acta.tipo)
    logo_base64   = get_logo_base64(empresa.prefijo)
    now           = datetime.now()
    fecha         = now.strftime("%d/%m/%Y")
    fecha_emision = now.strftime("%d-%m-%Y")

    html_content = template.render(
        acta=acta,
        activo=activo,
        activos_extra=activos_extra or [],
        usuario=usuario,
        empresa=empresa,
        accesorios=accesorios,
        usuario_ti=usuario_ti,
        numero_acta=numero_acta,
        logo_base64=logo_base64,
        fecha=fecha,
        fecha_emision=fecha_emision,
        fecha_constancia=_fecha_constancia(now),
        firma_base64=firma_base64,
        nombre_firmante=nombre_firmante,
        entrega_por_tercero=entrega_por_tercero,
        nombre_tercero=nombre_tercero,
        relacion_tercero=relacion_tercero,
        observaciones_firma=observaciones_firma,
        correo_movil=correo_movil,
    )

    empresa_dir = STORAGE_DIR / empresa.prefijo
    empresa_dir.mkdir(exist_ok=True)

    nombre_archivo = f"{numero_acta}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    ruta_pdf       = empresa_dir / nombre_archivo

    HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf(str(ruta_pdf))

    with open(ruta_pdf, "rb") as f:
        hash_pdf = hashlib.sha256(f.read()).hexdigest()

    ruta_relativa = f"storage/actas/{empresa.prefijo}/{nombre_archivo}"
    return ruta_relativa, hash_pdf


# ── PDF de Formulario de Baja ─────────────────────────────
BAJAS_DIR = BASE_DIR / "storage" / "bajas"
BAJAS_DIR.mkdir(parents=True, exist_ok=True)

_MOTIVO_BAJA = {
    "donado": "Donación", "vendido": "Venta",
    "destruido": "Destrucción", "retiro_operacion": "Retiro de operación",
    "hurto": "Hurto", "traslado": "Traslado",
}


def generar_pdf_baja(baja, db) -> str:
    """Genera el PDF del formulario de baja y devuelve la ruta relativa."""
    from models.empresa import Empresa
    from models.usuario_sistema import UsuarioSistema

    empresa = db.query(Empresa).filter(Empresa.id == baja.empresa_id).first()
    solic = db.query(UsuarioSistema).filter(UsuarioSistema.id == baja.solicitado_por_id).first()
    aprob = db.query(UsuarioSistema).filter(UsuarioSistema.id == baja.aprobado_por_id).first() if baja.aprobado_por_id else None
    logo_b64 = get_logo_base64(empresa.prefijo) if empresa else None
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="max-height:48px">' if logo_b64 else ''

    def _fecha(d):
        return d.strftime("%d/%m/%Y") if d else "—"
    def _dt(d):
        return d.strftime("%d/%m/%Y %H:%M") if d else "—"
    def _money(v):
        return "$" + format(float(v), ",.0f") if v is not None else "—"

    # Campos específicos por motivo
    esp = []
    if baja.motivo == "vendido":
        esp.append(("Valor de venta", _money(baja.valor_venta)))
        esp.append(("Comprador", baja.comprador or "—"))
    elif baja.motivo == "donado":
        esp.append(("Entidad receptora", baja.entidad_receptora or "—"))
    elif baja.motivo == "destruido":
        esp.append(("Método de destrucción", baja.metodo_destruccion or "—"))
    elif baja.motivo == "hurto":
        esp.append(("Número de denuncia", baja.numero_denuncia or "—"))
    elif baja.motivo == "traslado":
        esp.append(("Empresa destino", baja.empresa_destino_nombre or "—"))
    esp_html = "".join(
        f'<tr><td class="lbl">{l}</td><td>{v}</td></tr>' for l, v in esp)

    html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="utf-8"><style>
      @page {{ size: A4; margin: 1.6cm; }}
      * {{ font-family:'Helvetica Neue',Arial,sans-serif; color:#1f2d3d; }}
      .head {{ display:flex; justify-content:space-between; align-items:center; border-bottom:2px solid #0e1c34; padding-bottom:10px; margin-bottom:16px; }}
      h1 {{ font-size:18px; color:#0e1c34; margin:0; }}
      .num {{ font-family:monospace; font-size:13px; color:#8B1A1A; font-weight:700; }}
      .sec {{ font-size:11px; text-transform:uppercase; letter-spacing:1px; color:#06729a; font-weight:700; margin:18px 0 6px; border-bottom:1px solid #e3e9f1; padding-bottom:4px; }}
      table {{ width:100%; border-collapse:collapse; }}
      td {{ padding:5px 8px; font-size:12px; border-bottom:1px solid #eef2f7; vertical-align:top; }}
      td.lbl {{ font-weight:600; width:200px; color:#42566b; }}
      .just {{ background:#f7f9fc; border:1px solid #e3e9f1; border-radius:6px; padding:10px; font-size:12px; margin-top:4px; }}
      .firmas {{ display:flex; gap:40px; margin-top:50px; }}
      .firma {{ flex:1; border-top:1px solid #333; padding-top:6px; font-size:11px; text-align:center; color:#42566b; }}
      .badge {{ display:inline-block; padding:2px 10px; border-radius:10px; font-size:11px; font-weight:700; }}
    </style></head><body>
      <div class="head">
        <div><h1>Formulario de Baja de Activo</h1>
          <div style="font-size:12px;color:#6a7e96">{empresa.nombre_empresa if empresa else ''}</div></div>
        <div style="text-align:right">{logo_html}<div class="num">{baja.numero_baja}</div></div>
      </div>

      <div class="sec">Datos del recurso</div>
      <table>
        <tr><td class="lbl">Placa</td><td>{baja.placa or '—'}</td><td class="lbl">Tipo</td><td>{baja.tipo_activo or '—'}</td></tr>
        <tr><td class="lbl">Marca / Modelo</td><td>{(baja.marca or '')} {(baja.modelo or '')}</td><td class="lbl">Serial</td><td>{baja.serial or '—'}</td></tr>
        <tr><td class="lbl">Fecha de compra</td><td>{_fecha(baja.fecha_compra)}</td><td class="lbl">Costo original</td><td>{_money(baja.costo_original)}</td></tr>
      </table>

      <div class="sec">Motivo de la baja</div>
      <table>
        <tr><td class="lbl">Motivo</td><td><span class="badge" style="background:#fde8ea;color:#8B1A1A">{_MOTIVO_BAJA.get(baja.motivo, baja.motivo)}</span></td></tr>
        {esp_html}
      </table>
      <div class="just"><strong>Justificación:</strong><br>{baja.justificacion or '—'}</div>
      {f'<div class="just"><strong>Estado físico:</strong><br>{baja.estado_fisico}</div>' if baja.estado_fisico else ''}

      <div class="sec">Aprobación</div>
      <table>
        <tr><td class="lbl">Solicitado por</td><td>{solic.nombre if solic else '—'}</td><td class="lbl">Fecha solicitud</td><td>{_dt(baja.fecha_solicitud)}</td></tr>
        <tr><td class="lbl">Aprobado por</td><td>{aprob.nombre if aprob else '—'}</td><td class="lbl">Fecha aprobación</td><td>{_dt(baja.fecha_aprobacion)}</td></tr>
        <tr><td class="lbl">Estado</td><td colspan="3"><span class="badge" style="background:#e8f6ee;color:#1f7a4d">{baja.estado_aprobacion.upper()}</span></td></tr>
        {f'<tr><td class="lbl">Observaciones</td><td colspan="3">{baja.observaciones_aprobador}</td></tr>' if baja.observaciones_aprobador else ''}
      </table>

      <div class="firmas">
        <div class="firma">Solicitante<br>{solic.nombre if solic else ''}</div>
        <div class="firma">Aprobador<br>{aprob.nombre if aprob else ''}</div>
      </div>
    </body></html>"""

    pdf_bytes = HTML(string=html).write_pdf()
    nombre = f"{baja.numero_baja}.pdf"
    prefijo = empresa.prefijo if empresa else "GEN"
    dest_dir = BAJAS_DIR / prefijo
    dest_dir.mkdir(parents=True, exist_ok=True)
    with open(dest_dir / nombre, "wb") as f:
        f.write(pdf_bytes)
    return f"storage/bajas/{prefijo}/{nombre}"


# ── ACTA DE MANTENIMIENTO PREVENTIVO ──────────────────────
MANT_DIR = BASE_DIR / "storage" / "mantenimiento"

_SEC_TITULOS = {"hardware": "Mantenimiento de hardware", "software": "Mantenimiento de software",
                "diagnostico": "Diagnóstico (verificaciones)"}


def get_servicios_tic_logo_base64() -> str:
    """Logo corporativo FIJO de Servicios TIC (no el de la empresa)."""
    logo_path = BASE_DIR.parent / "frontend" / "img" / "ServiciosTIC_FullColor.png"
    if logo_path.exists():
        with open(logo_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    return None


def generar_pdf_mantenimiento(tarea, activo, empresa, plan, tecnico_nombre, items) -> str:
    """Genera el acta de mantenimiento preventivo (formato corporativo, sin OTP).
    `items` = snapshot del checklist de la tarea (TareaChecklistItem).
    Devuelve la ruta server-relative (storage/mantenimiento/{prefijo}/...)."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("acta_mantenimiento.html")

    # Agrupar: 'dato' → diagnóstico; 'check' → por sección
    datos = [i for i in items if i.tipo_item == "dato"]
    orden_sec = ["diagnostico", "hardware", "software"]
    secciones_check = []
    for sec in orden_sec:
        its = [i for i in items if i.tipo_item == "check" and i.seccion == sec]
        if its:
            secciones_check.append({"titulo": _SEC_TITULOS.get(sec, sec.title()),
                                    "filas": sorted(its, key=lambda x: x.orden)})

    now = datetime.now()
    logo_base64 = get_servicios_tic_logo_base64()
    fecha_emision_fmt = plan.fecha_emision_formato.strftime("%d-%m-%Y") if plan.fecha_emision_formato else None

    html_content = template.render(
        tarea=tarea, activo=activo, empresa=empresa, plan=plan,
        tecnico_nombre=tecnico_nombre,
        datos=sorted(datos, key=lambda x: x.orden),
        secciones_check=secciones_check,
        observaciones=tarea.observaciones,
        logo_base64=logo_base64,
        fecha=now.strftime("%d/%m/%Y"),
        fecha_emision_formato=fecha_emision_fmt,
    )

    prefijo = empresa.prefijo if empresa else "GEN"
    dest_dir = MANT_DIR / prefijo
    dest_dir.mkdir(parents=True, exist_ok=True)
    nombre = f"MANT_{activo.id_placa_activo}_{now.strftime('%Y%m%d_%H%M%S')}.pdf"
    ruta_pdf = dest_dir / nombre
    HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf(str(ruta_pdf))
    return f"storage/mantenimiento/{prefijo}/{nombre}"


def generar_pdf_cuarto_red(ctx: dict) -> bytes:
    """Renderiza el PDF de un cuarto técnico (módulo Redes) EN MEMORIA y devuelve
    los bytes (no persiste — es un documento de consulta del estado actual).
    `ctx` ya trae racks (con sus filas/colores), fuera-de-rack y datos de cabecera;
    aquí solo se añade el logo de la empresa y se renderiza la plantilla."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("cuarto_red.html")
    logo_base64 = get_logo_base64(ctx.get("empresa_prefijo")) if ctx.get("empresa_prefijo") else None
    html_content = template.render(logo_base64=logo_base64, **ctx)
    return HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()


def generar_pdf_reportes_impresoras(ctx: dict) -> bytes:
    """PDF (en memoria) de la sección Reportes de daño · Impresoras: cabecera con
    logo de empresa + período, ranking 'más reportadas' y tabla de reportes.
    Reutiliza el motor WeasyPrint + get_logo_base64 (como cuarto_red)."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("reportes_impresoras.html")
    logo_base64 = get_logo_base64(ctx.get("empresa_prefijo")) if ctx.get("empresa_prefijo") else None
    # Formatear fecha por fila (la lista trae ISO en 'fecha').
    reportes = []
    for r in ctx.get("reportes", []):
        rr = dict(r)
        iso = rr.get("fecha")
        try:
            rr["fecha_fmt"] = datetime.fromisoformat(iso).strftime("%d/%m/%Y") if iso else "—"
        except (ValueError, TypeError):
            rr["fecha_fmt"] = (iso or "—")[:10]
        reportes.append(rr)
    render_ctx = {**ctx, "reportes": reportes, "logo_base64": logo_base64}
    html_content = template.render(**render_ctx)
    return HTML(string=html_content, base_url=str(TEMPLATES_DIR)).write_pdf()
