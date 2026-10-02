from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func, distinct
from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from collections import defaultdict
from database import get_db
from models.servidor import (
    TipoServidor, Ambiente, Criticidad, EstadoServidor, Ubicacion,
    SistemaOperativo, Herramienta, Servidor, ServidorHerramienta,
    ServicioServidor, HistorialServidor, ServidorEmpresa,
)
from models.empresa import Empresa
from models.catalogo import Catalogo
from dependencies.rbac import require_permission
from services.rbac_service import get_user_empresa_ids

router = APIRouter(prefix="/api/servidores", tags=["Servidores"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class ServidorCreate(BaseModel):
    empresa_id:       str
    nombre:           str
    hostname:         str
    id_servicio:      Optional[str] = None
    kawak_id:         Optional[str] = None
    glpi_id:          Optional[str] = None
    tipo_servidor_id: Optional[str] = None
    ambiente_id:      Optional[str] = None
    criticidad_id:    Optional[str] = None
    estado_id:        Optional[str] = None
    ubicacion_catalogo_id: Optional[str] = None   # catálogo GLOBAL categoria='hosting'
    so_id:            Optional[str] = None
    procesador:       Optional[str] = None
    memoria_ram:      Optional[str] = None
    disco:            Optional[str] = None
    ip_lan:           Optional[str] = None
    ip_salida:        Optional[str] = None
    observaciones:    Optional[str] = None
    pendientes:       Optional[str] = None
    aplica_todas:     Optional[bool] = False
    empresa_ids:      Optional[List[str]] = []   # empresas específicas (si aplica_todas=False)
    herramienta_ids:  Optional[List[str]] = []


class ServidorUpdate(BaseModel):
    nombre:           Optional[str] = None
    hostname:         Optional[str] = None
    id_servicio:      Optional[str] = None
    kawak_id:         Optional[str] = None
    glpi_id:          Optional[str] = None
    tipo_servidor_id: Optional[str] = None
    ambiente_id:      Optional[str] = None
    criticidad_id:    Optional[str] = None
    estado_id:        Optional[str] = None
    ubicacion_catalogo_id: Optional[str] = None   # catálogo GLOBAL categoria='hosting'
    so_id:            Optional[str] = None
    procesador:       Optional[str] = None
    memoria_ram:      Optional[str] = None
    disco:            Optional[str] = None
    ip_lan:           Optional[str] = None
    ip_salida:        Optional[str] = None
    observaciones:    Optional[str] = None
    pendientes:       Optional[str] = None
    activo:           Optional[bool] = None
    aplica_todas:     Optional[bool] = None
    empresa_ids:      Optional[List[str]] = None   # None = no tocar; lista = reemplazar set


class HerramientaAsignar(BaseModel):
    herramienta_id:      str
    estado:              Optional[str] = "pendiente"
    version:             Optional[str] = None
    fecha_instalacion:   Optional[date] = None
    ultima_actualizacion: Optional[date] = None
    notas:               Optional[str] = None


class HerramientaUpdate(BaseModel):
    estado:              Optional[str] = None
    version:             Optional[str] = None
    fecha_instalacion:   Optional[date] = None
    ultima_actualizacion: Optional[date] = None
    notas:               Optional[str] = None


class ServicioCreate(BaseModel):
    nombre_servicio: str
    descripcion:     Optional[str] = None
    puerto:          Optional[int] = None
    protocolo:       Optional[str] = None
    activo:          Optional[bool] = True


class ServicioUpdate(BaseModel):
    nombre_servicio: Optional[str] = None
    descripcion:     Optional[str] = None
    puerto:          Optional[int] = None
    protocolo:       Optional[str] = None
    activo:          Optional[bool] = None


class HerramientaCatalogoCreate(BaseModel):
    nombre:      str
    categoria:   Optional[str] = "General"
    descripcion: Optional[str] = None


# ── Helper ────────────────────────────────────────────────────────────────────

def _servidor_to_dict(s: Servidor) -> dict:
    return {
        "id":               s.id,
        "empresa_id":       s.empresa_id,
        "nombre_empresa":   s.empresa.nombre_empresa if s.empresa else None,
        "nombre":           s.nombre,
        "hostname":         s.hostname,
        "id_servicio":      s.id_servicio,
        "kawak_id":         s.kawak_id,
        "glpi_id":          s.glpi_id,
        "tipo_servidor_id": s.tipo_servidor_id,
        "tipo_nombre":      s.tipo.nombre if s.tipo else None,
        "ambiente_id":      s.ambiente_id,
        "ambiente_nombre":  s.ambiente.nombre if s.ambiente else None,
        "ambiente_color":   s.ambiente.color if s.ambiente else None,
        "criticidad_id":    s.criticidad_id,
        "criticidad_nombre": s.criticidad.nombre if s.criticidad else None,
        "criticidad_nivel": s.criticidad.nivel if s.criticidad else None,
        "criticidad_color": s.criticidad.color if s.criticidad else None,
        "estado_id":        s.estado_id,
        "estado_nombre":    s.estado.nombre if s.estado else None,
        "estado_color":     s.estado.color if s.estado else None,
        "ubicacion_catalogo_id": s.ubicacion_catalogo_id,
        "ubicacion_nombre": s.hosting.valor if s.hosting else None,
        "so_id":            s.so_id,
        "so_nombre":        s.so.nombre if s.so else None,
        "so_familia":       s.so.familia if s.so else None,
        "procesador":       s.procesador,
        "memoria_ram":      s.memoria_ram,
        "disco":            s.disco,
        "ip_lan":           s.ip_lan,
        "ip_salida":        s.ip_salida,
        "observaciones":    s.observaciones,
        "pendientes":       s.pendientes,
        "activo":           s.activo,
        "aplica_todas":     s.aplica_todas,
        "empresas_aplicables": [
            {"id": se.empresa_id, "nombre": se.empresa.nombre_empresa if se.empresa else None}
            for se in s.empresas_aplicables
        ],
        "motivo_baja":      s.motivo_baja,
        "fecha_baja":       s.fecha_baja.isoformat() if s.fecha_baja else None,
        "dado_baja_por":    s.dado_baja_por,
        "created_at":       s.created_at.isoformat() if s.created_at else None,
        "updated_at":       s.updated_at.isoformat() if s.updated_at else None,
        "num_herramientas": len(s.herramientas),
        "num_servicios":    len([sv for sv in s.servicios if sv.activo]),
    }


def _log_cambio(db: Session, servidor_id: str, usuario_id: str, tipo: str,
                campo: str = None, anterior=None, nuevo=None, obs: str = None):
    db.add(HistorialServidor(
        servidor_id=servidor_id,
        usuario_sistema_id=usuario_id,
        tipo_cambio=tipo,
        campo_modificado=campo,
        valor_anterior=str(anterior) if anterior is not None else None,
        valor_nuevo=str(nuevo) if nuevo is not None else None,
        observacion=obs,
    ))


# ── Seed catalogos ────────────────────────────────────────────────────────────

@router.post("/seed-catalogos", status_code=status.HTTP_201_CREATED)
def seed_catalogos(
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.crear"),
):
    """Populate default catalog data. Safe to run multiple times (skip on conflict)."""
    inserted = defaultdict(int)

    tipos = [
        ("Físico", "Servidor físico on-premise"),
        ("Virtual", "Máquina virtual (VMware, Hyper-V, KVM)"),
        ("Contenedor", "Contenedor Docker / LXC"),
        ("Cloud", "Instancia de nube pública (AWS, Azure, GCP)"),
        ("Appliance", "Dispositivo appliance dedicado"),
        ("Bastión", "Servidor de salto / bastión SSH"),
    ]
    for nombre, desc in tipos:
        if not db.query(TipoServidor).filter_by(nombre=nombre).first():
            db.add(TipoServidor(nombre=nombre, descripcion=desc))
            inserted["tipos_servidor"] += 1

    ambientes = [
        ("Producción", "#e74c3c"),
        ("QA / Pruebas", "#f39c12"),
        ("Desarrollo", "#3498db"),
        ("Staging", "#9b59b6"),
        ("DR / Contingencia", "#e67e22"),
        ("Laboratorio", "#27ae60"),
    ]
    for nombre, color in ambientes:
        if not db.query(Ambiente).filter_by(nombre=nombre).first():
            db.add(Ambiente(nombre=nombre, color=color))
            inserted["ambientes"] += 1

    criticidades = [
        ("Crítico", 4, "#c0392b"),
        ("Alto", 3, "#e74c3c"),
        ("Medio", 2, "#f39c12"),
        ("Bajo", 1, "#27ae60"),
    ]
    for nombre, nivel, color in criticidades:
        if not db.query(Criticidad).filter_by(nombre=nombre).first():
            db.add(Criticidad(nombre=nombre, nivel=nivel, color=color))
            inserted["criticidades"] += 1

    estados = [
        ("Activo", "#27ae60"),
        ("Inactivo", "#95a5a6"),
        ("En mantenimiento", "#f39c12"),
        ("Dado de baja", "#7f8c8d"),
        ("En instalación", "#3498db"),
    ]
    for nombre, color in estados:
        if not db.query(EstadoServidor).filter_by(nombre=nombre).first():
            db.add(EstadoServidor(nombre=nombre, color=color))
            inserted["estados_servidor"] += 1

    so_list = [
        ("Red Hat Enterprise Linux 9", "Linux", True),
        ("Red Hat Enterprise Linux 8", "Linux", True),
        ("Red Hat Enterprise Linux 7", "Linux", False),
        ("Ubuntu Server 24.04 LTS", "Linux", True),
        ("Ubuntu Server 22.04 LTS", "Linux", True),
        ("Ubuntu Server 20.04 LTS", "Linux", True),
        ("Debian 12 (Bookworm)", "Linux", True),
        ("CentOS Stream 9", "Linux", True),
        ("Rocky Linux 9", "Linux", True),
        ("AlmaLinux 9", "Linux", True),
        ("SUSE Linux Enterprise Server 15", "Linux", True),
        ("Windows Server 2022", "Windows", True),
        ("Windows Server 2019", "Windows", True),
        ("Windows Server 2016", "Windows", True),
        ("Windows Server 2012 R2", "Windows", False),
        ("VMware ESXi 8.0", "Hypervisor", True),
        ("VMware ESXi 7.0", "Hypervisor", True),
        ("Proxmox VE 8", "Hypervisor", True),
        ("FreeBSD 14", "BSD", True),
    ]
    for nombre, familia, soporte in so_list:
        if not db.query(SistemaOperativo).filter_by(nombre=nombre).first():
            db.add(SistemaOperativo(nombre=nombre, familia=familia, soporte_activo=soporte))
            inserted["sistemas_operativos"] += 1

    herramientas = [
        ("Zabbix", "Monitoreo", "Monitoreo de infraestructura y alertas"),
        ("Nagios", "Monitoreo", "Monitoreo de servicios y hosts"),
        ("Prometheus", "Monitoreo", "Sistema de monitoreo y alertas"),
        ("Grafana", "Monitoreo", "Visualización de métricas y dashboards"),
        ("Splunk", "SIEM", "Plataforma SIEM y análisis de logs"),
        ("IBM QRadar", "SIEM", "Plataforma SIEM empresarial"),
        ("Wazuh", "SIEM", "SIEM open source y XDR"),
        ("Elastic SIEM", "SIEM", "SIEM basado en Elastic Stack"),
        ("Qualys VMDR", "Vulnerabilidades", "Gestión de vulnerabilidades"),
        ("Tenable Nessus", "Vulnerabilidades", "Escáner de vulnerabilidades"),
        ("Rapid7 InsightVM", "Vulnerabilidades", "Gestión de vulnerabilidades"),
        ("OpenVAS", "Vulnerabilidades", "Escáner open source"),
        ("CrowdStrike Falcon", "EDR/AV", "Plataforma EDR en la nube"),
        ("SentinelOne", "EDR/AV", "Plataforma EDR con IA"),
        ("Carbon Black", "EDR/AV", "Protección de endpoints"),
        ("Trend Micro Deep Security", "EDR/AV", "Seguridad de servidores"),
        ("Puppet", "Gestión de Configuración", "Automatización de configuración"),
        ("Ansible", "Gestión de Configuración", "Automatización y orquestación"),
        ("Chef", "Gestión de Configuración", "Gestión de configuración"),
        ("SolarWinds", "Monitoreo", "Monitoreo de redes e infraestructura"),
        ("Dynatrace", "APM", "Monitoreo de rendimiento de aplicaciones"),
        ("New Relic", "APM", "Observabilidad de aplicaciones"),
        ("Datadog", "APM", "Plataforma de observabilidad"),
        ("Backup Exec", "Backup", "Solución de backup Veritas"),
        ("Veeam", "Backup", "Backup y recuperación"),
        ("Commvault", "Backup", "Plataforma de protección de datos"),
    ]
    for nombre, categoria, desc in herramientas:
        if not db.query(Herramienta).filter_by(nombre=nombre).first():
            db.add(Herramienta(nombre=nombre, categoria=categoria, descripcion=desc))
            inserted["herramientas"] += 1

    db.commit()
    return {"message": "Seed completado", "insertados": dict(inserted)}


# ── Stats ─────────────────────────────────────────────────────────────────────

@router.get("/stats")
def get_stats(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.ver"),
):
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    query = db.query(Servidor)
    if empresa_ids is not None:
        if empresa_id:
            if empresa_id not in empresa_ids:
                raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
            query = query.filter(Servidor.empresa_id == empresa_id)
        else:
            query = query.filter(Servidor.empresa_id.in_(empresa_ids))
    elif empresa_id:
        query = query.filter(Servidor.empresa_id == empresa_id)

    servidores = query.all()
    ids = [s.id for s in servidores]

    total         = len(servidores)
    activos_count = sum(1 for s in servidores if s.activo)

    por_ambiente  = defaultdict(int)
    por_tipo      = defaultdict(int)
    por_estado    = defaultdict(int)
    por_criticidad = defaultdict(int)

    for s in servidores:
        por_ambiente[s.ambiente.nombre if s.ambiente else "Sin ambiente"] += 1
        por_tipo[s.tipo.nombre if s.tipo else "Sin tipo"] += 1
        por_estado[s.estado.nombre if s.estado else "Sin estado"] += 1
        por_criticidad[s.criticidad.nombre if s.criticidad else "Sin criticidad"] += 1

    servers_by_herramienta = defaultdict(int)
    servers_by_categoria   = defaultdict(int)

    if ids:
        herr_records = (
            db.query(ServidorHerramienta, Herramienta)
            .join(Herramienta)
            .filter(
                ServidorHerramienta.servidor_id.in_(ids),
                ServidorHerramienta.estado.in_(["instalado", "configurado"]),
            )
            .all()
        )
        seen_herr:    defaultdict = defaultdict(set)
        seen_cat:     defaultdict = defaultdict(set)
        for sh, h in herr_records:
            seen_herr[h.nombre].add(sh.servidor_id)
            seen_cat[h.categoria].add(sh.servidor_id)
        for k, v in seen_herr.items():
            servers_by_herramienta[k] = len(v)
        for k, v in seen_cat.items():
            servers_by_categoria[k] = len(v)

    return {
        "total":              total,
        "activos":            activos_count,
        "inactivos":          total - activos_count,
        "por_ambiente":       dict(por_ambiente),
        "por_tipo":           dict(por_tipo),
        "por_estado":         dict(por_estado),
        "por_criticidad":     dict(por_criticidad),
        "por_herramienta":    dict(servers_by_herramienta),
        "por_categoria_herr": dict(servers_by_categoria),
    }


# ── Catalogos ─────────────────────────────────────────────────────────────────

@router.get("/catalogos")
def get_catalogos(
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.ver"),
):
    return {
        "tipos_servidor": [
            {"id": t.id, "nombre": t.nombre, "descripcion": t.descripcion}
            for t in db.query(TipoServidor).order_by(TipoServidor.nombre).all()
        ],
        "ambientes": [
            {"id": a.id, "nombre": a.nombre, "color": a.color}
            for a in db.query(Ambiente).order_by(Ambiente.nombre).all()
        ],
        "criticidades": [
            {"id": c.id, "nombre": c.nombre, "nivel": c.nivel, "color": c.color}
            for c in db.query(Criticidad).order_by(Criticidad.nivel.desc()).all()
        ],
        "estados_servidor": [
            {"id": e.id, "nombre": e.nombre, "color": e.color}
            for e in db.query(EstadoServidor).order_by(EstadoServidor.nombre).all()
        ],
        # Hosting: catálogo GLOBAL categoria='hosting' (AWS / On-premise / Triara…).
        # Reemplaza la antigua tabla huérfana `ubicaciones`; NO es el 'ubicacion' de activos.
        "hosting": [
            {"id": c.id, "nombre": c.valor}
            for c in db.query(Catalogo).filter(
                Catalogo.categoria == "hosting",
                Catalogo.empresa_id.is_(None),
                Catalogo.activo == True,
            ).order_by(Catalogo.orden.asc(), Catalogo.valor.asc()).all()
        ],
        "sistemas_operativos": [
            {"id": s.id, "nombre": s.nombre, "familia": s.familia, "soporte_activo": s.soporte_activo}
            for s in db.query(SistemaOperativo).order_by(SistemaOperativo.familia, SistemaOperativo.nombre).all()
        ],
        "herramientas": [
            {"id": h.id, "nombre": h.nombre, "categoria": h.categoria, "descripcion": h.descripcion, "activo": h.activo}
            for h in db.query(Herramienta).filter(Herramienta.activo == True).order_by(Herramienta.categoria, Herramienta.nombre).all()
        ],
    }


# ── Opciones dinámicas para el filtro avanzado ────────────────────────────────

@router.get("/filtros")
def opciones_filtro(
    empresa_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.ver"),
):
    """Vocabulario REAL (empresa-scoped) para los filtros multi-valor:
       - herramientas: solo las efectivamente asignadas a algún servidor.
       - servicios:    nombre_servicio distintos almacenados (dedupe case-insensitive)."""
    empresa_ids = get_user_empresa_ids(db, current_user.id)

    def _scope(qq):
        if empresa_ids is not None:
            if empresa_id:
                if empresa_id not in empresa_ids:
                    raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
                return qq.filter(Servidor.empresa_id == empresa_id)
            return qq.filter(Servidor.empresa_id.in_(empresa_ids))
        if empresa_id:
            return qq.filter(Servidor.empresa_id == empresa_id)
        return qq

    herr_q = _scope(
        db.query(Herramienta.id, Herramienta.nombre)
          .join(ServidorHerramienta, ServidorHerramienta.herramienta_id == Herramienta.id)
          .join(Servidor, Servidor.id == ServidorHerramienta.servidor_id)
    ).distinct().all()
    herramientas = [{"id": hid, "nombre": nom}
                    for hid, nom in sorted(set(herr_q), key=lambda x: (x[1] or "").lower())]

    svc_rows = _scope(
        db.query(ServicioServidor.nombre_servicio)
          .join(Servidor, Servidor.id == ServicioServidor.servidor_id)
    ).all()
    seen = {}
    for (nom,) in svc_rows:
        if nom and nom.strip():
            k = nom.strip().lower()
            if k not in seen:
                seen[k] = nom.strip()
    servicios = sorted(seen.values(), key=lambda s: s.lower())

    return {"herramientas": herramientas, "servicios": servicios}


# ── Catálogo de herramientas (crear nueva) ────────────────────────────────────

@router.post("/herramientas-catalogo", status_code=status.HTTP_201_CREATED)
def crear_herramienta_catalogo(
    data: HerramientaCatalogoCreate,
    db:   Session = Depends(get_db),
    current_user = require_permission("servidores.editar"),
):
    nombre = data.nombre.strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")
    existing = db.query(Herramienta).filter(Herramienta.nombre == nombre).first()
    if existing:
        if not existing.activo:
            existing.activo = True
            existing.categoria   = data.categoria or existing.categoria
            existing.descripcion = data.descripcion or existing.descripcion
            db.commit()
            db.refresh(existing)
            return {"id": existing.id, "nombre": existing.nombre,
                    "categoria": existing.categoria, "descripcion": existing.descripcion}
        raise HTTPException(status_code=409, detail=f"Ya existe una herramienta llamada '{nombre}'")
    h = Herramienta(
        nombre=nombre,
        categoria=data.categoria or "General",
        descripcion=data.descripcion,
        activo=True,
    )
    db.add(h)
    db.commit()
    db.refresh(h)
    return {"id": h.id, "nombre": h.nombre,
            "categoria": h.categoria, "descripcion": h.descripcion}


# ── CRUD servidores ───────────────────────────────────────────────────────────

@router.get("")
def listar_servidores(
    empresa_id:       Optional[str] = None,
    ambiente_id:      Optional[str] = None,
    estado_id:        Optional[str] = None,
    tipo_servidor_id: Optional[str] = None,
    criticidad_id:    Optional[str] = None,
    so_id:            Optional[str] = None,
    ubicacion_catalogo_id: Optional[str] = None,   # hosting
    herramienta_ids:  Optional[List[str]] = Query(None, description="Filtrar por herramientas (ids)"),
    herr_match:       str = Query("any", description="any = tiene ALGUNA; all = tiene TODAS"),
    servicios:        Optional[List[str]] = Query(None, description="Filtrar por nombre_servicio"),
    svc_match:        str = Query("any", description="any = tiene ALGUNO; all = tiene TODOS"),
    activo:           Optional[bool] = None,
    q:                Optional[str] = Query(None, description="Buscar por nombre, hostname o IP"),
    db:               Session = Depends(get_db),
    current_user = require_permission("servidores.ver"),
):
    empresa_ids = get_user_empresa_ids(db, current_user.id)
    query = db.query(Servidor)
    # Aplicabilidad (Opción 1): un servidor es visible para la empresa X si aplica_todas
    # o si X está en servidor_empresas. La owner siempre está en el set (invariante), así
    # que la subconsulta cubre también la propiedad. RBAC = solo empresas accesibles.
    if empresa_id:
        # Selector global apunta a una empresa concreta.
        if empresa_ids is not None and empresa_id not in empresa_ids:
            raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")
        sub = db.query(ServidorEmpresa.servidor_id).filter(ServidorEmpresa.empresa_id == empresa_id)
        query = query.filter(or_(Servidor.aplica_todas == True, Servidor.id.in_(sub)))
    elif empresa_ids is not None:
        # "Todas las empresas" pero usuario no-super-admin: solo sus empresas.
        sub = db.query(ServidorEmpresa.servidor_id).filter(ServidorEmpresa.empresa_id.in_(empresa_ids))
        query = query.filter(or_(Servidor.aplica_todas == True, Servidor.id.in_(sub)))
    # super_admin + "Todas": sin filtro de aplicabilidad (ve todo).

    # Dropdowns de catálogo (AND entre dimensiones).
    if ambiente_id:
        query = query.filter(Servidor.ambiente_id == ambiente_id)
    if estado_id:
        query = query.filter(Servidor.estado_id == estado_id)
    if tipo_servidor_id:
        query = query.filter(Servidor.tipo_servidor_id == tipo_servidor_id)
    if criticidad_id:
        query = query.filter(Servidor.criticidad_id == criticidad_id)
    if so_id:
        query = query.filter(Servidor.so_id == so_id)
    if ubicacion_catalogo_id:
        query = query.filter(Servidor.ubicacion_catalogo_id == ubicacion_catalogo_id)

    # Por defecto la lista muestra solo VIGENTES (activo=True). Los dados de baja
    # (activo=False) solo aparecen si se piden explícitamente (?activo=false) o si el
    # usuario elige un Estado concreto en el filtro avanzado (entonces manda el estado).
    if activo is not None:
        query = query.filter(Servidor.activo == activo)
    elif not estado_id:
        query = query.filter(Servidor.activo == True)

    # Multi-valor (tablas relacionadas) — subconsultas set-based, sin N+1.
    herr_ids = [h for h in (herramienta_ids or []) if h]
    if herr_ids:
        if herr_match == "all":
            sub = (db.query(ServidorHerramienta.servidor_id)
                     .filter(ServidorHerramienta.herramienta_id.in_(herr_ids))
                     .group_by(ServidorHerramienta.servidor_id)
                     .having(func.count(distinct(ServidorHerramienta.herramienta_id)) == len(set(herr_ids))))
        else:
            sub = (db.query(ServidorHerramienta.servidor_id)
                     .filter(ServidorHerramienta.herramienta_id.in_(herr_ids)))
        query = query.filter(Servidor.id.in_(sub))

    svc_names = [s.strip() for s in (servicios or []) if s and s.strip()]
    if svc_names:
        svc_lower = [s.lower() for s in svc_names]
        base = db.query(ServicioServidor.servidor_id).filter(
            func.lower(ServicioServidor.nombre_servicio).in_(svc_lower))
        if svc_match == "all":
            sub = (base.group_by(ServicioServidor.servidor_id)
                       .having(func.count(distinct(func.lower(ServicioServidor.nombre_servicio))) == len(set(svc_lower))))
        else:
            sub = base
        query = query.filter(Servidor.id.in_(sub))

    if q:
        query = query.filter(or_(
            Servidor.nombre.ilike(f"%{q}%"),
            Servidor.hostname.ilike(f"%{q}%"),
            Servidor.ip_lan.ilike(f"%{q}%"),
            Servidor.ip_salida.ilike(f"%{q}%"),
            Servidor.id_servicio.ilike(f"%{q}%"),
        ))

    return [_servidor_to_dict(s) for s in query.order_by(Servidor.nombre).all()]


def _aplicar_aplicabilidad(db, servidor, aplica_todas, empresa_ids_sel, current_user):
    """Fija la aplicabilidad del servidor.
       - aplica_todas=True  -> visible para todas; se limpia servidor_empresas.
       - aplica_todas=False -> set = empresa_ids_sel ∪ {owner}  (INVARIANTE owner-in-set).
       Valida existencia + RBAC (no-super-admin no asigna empresas fuera de su alcance)."""
    servidor.aplica_todas = bool(aplica_todas)
    if servidor.aplica_todas:
        servidor.empresas_aplicables.clear()
        db.flush()
        return
    rbac = get_user_empresa_ids(db, current_user.id)   # None = super_admin
    ids = {e for e in (empresa_ids_sel or []) if e}
    ids.add(servidor.empresa_id)                       # invariante: owner siempre
    validas = {row[0] for row in db.query(Empresa.id).filter(Empresa.id.in_(ids)).all()} if ids else set()
    faltan = ids - validas
    if faltan:
        raise HTTPException(status_code=400, detail="Empresa(s) inexistente(s) en la selección")
    if rbac is not None:
        fuera = ids - set(rbac)
        if fuera:
            raise HTTPException(status_code=403, detail="No puedes asignar empresas fuera de tu alcance")
    servidor.empresas_aplicables.clear()
    db.flush()
    for eid in ids:
        db.add(ServidorEmpresa(servidor_id=servidor.id, empresa_id=eid))


@router.post("", status_code=status.HTTP_201_CREATED)
def crear_servidor(
    data: ServidorCreate,
    db:   Session = Depends(get_db),
    current_user = require_permission("servidores.crear"),
):
    empresa = db.query(Empresa).filter(Empresa.id == data.empresa_id).first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and data.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a esa empresa")

    existing = db.query(Servidor).filter(
        Servidor.empresa_id == data.empresa_id,
        Servidor.hostname == data.hostname,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Ya existe un servidor con hostname '{data.hostname}' en esa empresa")

    payload = data.model_dump(exclude={"herramienta_ids", "empresa_ids", "aplica_todas"})
    servidor = Servidor(**payload)
    db.add(servidor)
    db.flush()

    # Aplicabilidad por empresa (invariante owner-in-set aplicado en el helper).
    _aplicar_aplicabilidad(db, servidor, data.aplica_todas, data.empresa_ids, current_user)

    for hid in (data.herramienta_ids or []):
        h = db.query(Herramienta).filter(Herramienta.id == hid).first()
        if h:
            db.add(ServidorHerramienta(servidor_id=servidor.id, herramienta_id=hid))

    _log_cambio(db, servidor.id, current_user.id, "creacion", obs=f"Servidor {servidor.hostname} registrado")
    db.commit()
    db.refresh(servidor)
    return _servidor_to_dict(servidor)


@router.get("/{servidor_id}")
def obtener_servidor(
    servidor_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.ver"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    result = _servidor_to_dict(s)
    result["herramientas"] = [
        {
            "id": sh.id,
            "herramienta_id": sh.herramienta_id,
            "nombre": sh.herramienta.nombre,
            "categoria": sh.herramienta.categoria,
            "estado": sh.estado,
            "version": sh.version,
            "fecha_instalacion": sh.fecha_instalacion.isoformat() if sh.fecha_instalacion else None,
            "ultima_actualizacion": sh.ultima_actualizacion.isoformat() if sh.ultima_actualizacion else None,
            "notas": sh.notas,
        }
        for sh in s.herramientas
    ]
    result["servicios"] = [
        {
            "id": sv.id,
            "nombre_servicio": sv.nombre_servicio,
            "descripcion": sv.descripcion,
            "puerto": sv.puerto,
            "protocolo": sv.protocolo,
            "activo": sv.activo,
        }
        for sv in s.servicios
    ]
    return result


@router.put("/{servidor_id}")
def actualizar_servidor(
    servidor_id: str,
    data: ServidorUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.editar"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    cambios = data.model_dump(exclude_none=True)
    # La aplicabilidad no son columnas simples: se maneja aparte (helper con invariante).
    tocar_aplic = (data.aplica_todas is not None) or (data.empresa_ids is not None)
    cambios.pop("aplica_todas", None)
    cambios.pop("empresa_ids", None)

    for campo, nuevo_val in cambios.items():
        anterior = getattr(s, campo)
        if anterior != nuevo_val:
            _log_cambio(db, s.id, current_user.id, "edicion",
                        campo=campo, anterior=anterior, nuevo=nuevo_val)
            setattr(s, campo, nuevo_val)

    if tocar_aplic:
        nuevo_aplica = data.aplica_todas if data.aplica_todas is not None else s.aplica_todas
        _aplicar_aplicabilidad(db, s, nuevo_aplica, data.empresa_ids, current_user)

    db.commit()
    db.refresh(s)
    return _servidor_to_dict(s)


@router.delete("/{servidor_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_servidor(
    servidor_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.eliminar"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    s.activo = False
    _log_cambio(db, s.id, current_user.id, "baja", obs="Servidor desactivado")
    db.commit()


# ── Dar de baja (con motivo/fecha/usuario) — NO hard-delete ────────────────────

class DarDeBajaIn(BaseModel):
    motivo: str


@router.post("/{servidor_id}/dar-de-baja")
def dar_de_baja_servidor(
    servidor_id: str,
    data: DarDeBajaIn,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.eliminar"),
):
    """Da de baja un servidor (VM que ya no existe / no llegó a producción). Conserva
    el registro (activo=False), fija estado 'Dado de baja' y guarda motivo/fecha/usuario.
    Excluido de la lista principal; visible con ?activo=false."""
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    if not s.activo:
        raise HTTPException(status_code=400, detail="El servidor ya está dado de baja")

    motivo = (data.motivo or "").strip()
    if not motivo:
        raise HTTPException(status_code=400, detail="El motivo de la baja es obligatorio")

    s.activo = False
    s.motivo_baja = motivo
    s.fecha_baja = datetime.now()
    s.dado_baja_por = current_user.id
    # Fija el estado a "Dado de baja" (catálogo estados_servidor) para el detalle.
    est = db.query(EstadoServidor).filter(EstadoServidor.nombre == "Dado de baja").first()
    if est:
        s.estado_id = est.id
    _log_cambio(db, s.id, current_user.id, "baja",
                obs=f"Servidor dado de baja — motivo: {motivo}")
    db.commit()
    db.refresh(s)
    return _servidor_to_dict(s)


# ── Herramientas del servidor ─────────────────────────────────────────────────

@router.post("/{servidor_id}/herramientas", status_code=status.HTTP_201_CREATED)
def asignar_herramienta(
    servidor_id: str,
    data: HerramientaAsignar,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.editar"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    herramienta = db.query(Herramienta).filter(Herramienta.id == data.herramienta_id).first()
    if not herramienta:
        raise HTTPException(status_code=404, detail="Herramienta no encontrada")

    existing = db.query(ServidorHerramienta).filter(
        ServidorHerramienta.servidor_id == servidor_id,
        ServidorHerramienta.herramienta_id == data.herramienta_id,
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Esta herramienta ya está asignada al servidor")

    sh = ServidorHerramienta(**data.model_dump(), servidor_id=servidor_id)
    db.add(sh)
    _log_cambio(db, servidor_id, current_user.id, "herramienta_asignada",
                obs=f"Herramienta '{herramienta.nombre}' asignada")
    db.commit()
    db.refresh(sh)
    return {
        "id": sh.id,
        "herramienta_id": sh.herramienta_id,
        "nombre": sh.herramienta.nombre,
        "categoria": sh.herramienta.categoria,
        "estado": sh.estado,
        "version": sh.version,
        "fecha_instalacion": sh.fecha_instalacion.isoformat() if sh.fecha_instalacion else None,
        "ultima_actualizacion": sh.ultima_actualizacion.isoformat() if sh.ultima_actualizacion else None,
        "notas": sh.notas,
    }


@router.put("/{servidor_id}/herramientas/{sh_id}")
def actualizar_herramienta_servidor(
    servidor_id: str,
    sh_id: str,
    data: HerramientaUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.editar"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    sh = db.query(ServidorHerramienta).filter(
        ServidorHerramienta.id == sh_id,
        ServidorHerramienta.servidor_id == servidor_id,
    ).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Registro de herramienta no encontrado")

    cambios = data.model_dump(exclude_none=True)
    for campo, val in cambios.items():
        setattr(sh, campo, val)

    _log_cambio(db, servidor_id, current_user.id, "herramienta_actualizada",
                obs=f"Herramienta '{sh.herramienta.nombre}' actualizada")
    db.commit()
    db.refresh(sh)
    return {
        "id": sh.id,
        "herramienta_id": sh.herramienta_id,
        "nombre": sh.herramienta.nombre,
        "categoria": sh.herramienta.categoria,
        "estado": sh.estado,
        "version": sh.version,
        "fecha_instalacion": sh.fecha_instalacion.isoformat() if sh.fecha_instalacion else None,
        "ultima_actualizacion": sh.ultima_actualizacion.isoformat() if sh.ultima_actualizacion else None,
        "notas": sh.notas,
    }


@router.delete("/{servidor_id}/herramientas/{sh_id}", status_code=status.HTTP_204_NO_CONTENT)
def remover_herramienta(
    servidor_id: str,
    sh_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.editar"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    sh = db.query(ServidorHerramienta).filter(
        ServidorHerramienta.id == sh_id,
        ServidorHerramienta.servidor_id == servidor_id,
    ).first()
    if not sh:
        raise HTTPException(status_code=404, detail="Registro de herramienta no encontrado")

    nombre = sh.herramienta.nombre
    db.delete(sh)
    _log_cambio(db, servidor_id, current_user.id, "herramienta_removida",
                obs=f"Herramienta '{nombre}' removida")
    db.commit()


# ── Servicios del servidor ────────────────────────────────────────────────────

@router.post("/{servidor_id}/servicios", status_code=status.HTTP_201_CREATED)
def crear_servicio(
    servidor_id: str,
    data: ServicioCreate,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.editar"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    sv = ServicioServidor(**data.model_dump(), servidor_id=servidor_id)
    db.add(sv)
    db.commit()
    db.refresh(sv)
    return {
        "id": sv.id,
        "nombre_servicio": sv.nombre_servicio,
        "descripcion": sv.descripcion,
        "puerto": sv.puerto,
        "protocolo": sv.protocolo,
        "activo": sv.activo,
    }


@router.put("/{servidor_id}/servicios/{servicio_id}")
def actualizar_servicio(
    servidor_id: str,
    servicio_id: str,
    data: ServicioUpdate,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.editar"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    sv = db.query(ServicioServidor).filter(
        ServicioServidor.id == servicio_id,
        ServicioServidor.servidor_id == servidor_id,
    ).first()
    if not sv:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    for campo, val in data.model_dump(exclude_none=True).items():
        setattr(sv, campo, val)

    db.commit()
    db.refresh(sv)
    return {
        "id": sv.id,
        "nombre_servicio": sv.nombre_servicio,
        "descripcion": sv.descripcion,
        "puerto": sv.puerto,
        "protocolo": sv.protocolo,
        "activo": sv.activo,
    }


@router.delete("/{servidor_id}/servicios/{servicio_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_servicio(
    servidor_id: str,
    servicio_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.editar"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    sv = db.query(ServicioServidor).filter(
        ServicioServidor.id == servicio_id,
        ServicioServidor.servidor_id == servidor_id,
    ).first()
    if not sv:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    db.delete(sv)
    db.commit()


# ── Historial del servidor ────────────────────────────────────────────────────

@router.get("/{servidor_id}/historial")
def obtener_historial(
    servidor_id: str,
    db: Session = Depends(get_db),
    current_user = require_permission("servidores.ver"),
):
    s = db.query(Servidor).filter(Servidor.id == servidor_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Servidor no encontrado")

    empresa_ids = get_user_empresa_ids(db, current_user.id)
    if empresa_ids is not None and s.empresa_id not in empresa_ids:
        raise HTTPException(status_code=403, detail="No tienes acceso a ese servidor")

    registros = (
        db.query(HistorialServidor)
        .filter(HistorialServidor.servidor_id == servidor_id)
        .order_by(HistorialServidor.created_at.desc())
        .all()
    )
    return [
        {
            "id":               r.id,
            "tipo_cambio":      r.tipo_cambio,
            "campo_modificado": r.campo_modificado,
            "valor_anterior":   r.valor_anterior,
            "valor_nuevo":      r.valor_nuevo,
            "observacion":      r.observacion,
            "created_at":       r.created_at.isoformat() if r.created_at else None,
            "usuario":          r.usuario_sistema.nombre if r.usuario_sistema else None,
            "usuario_email":    r.usuario_sistema.email if r.usuario_sistema else None,
        }
        for r in registros
    ]
