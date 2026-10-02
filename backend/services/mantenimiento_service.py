"""
Servicio compartido del módulo Mantenimiento Preventivo.

Reúne la lógica de creación de tareas + snapshot del checklist y las consultas
de cobertura/elegibilidad, para que las TRES vías que crean tareas preventivas
—planificación, ad-hoc y la integración con la devolución— produzcan tareas
IDÉNTICAS y compartan una sola implementación.

router → service → models (no importa routers) ⇒ sin import circular.
"""
from sqlalchemy.orm import Session
from datetime import date

from models.activo import Activo
from models.mantenimiento import (
    PlanMantenimiento, PlanTipoActivo, TareaMantenimiento, TareaChecklistItem,
)
from models.usuario_rol import UsuarioRol
from models.rol import Rol
from models.permiso import Permiso
from models.rol_permiso import RolPermiso
from services.rbac_service import is_super_admin

# Estados de tarea que cuentan como "abierta" (no permitir duplicar).
ESTADOS_TAREA_ABIERTA = ("pendiente", "en_ejecucion")


def coverage_activa(db: Session) -> dict:
    """Mapa GLOBAL tipo_activo → PlanMantenimiento activo que lo cubre.
    Los planes son globales; los equipos se siguen filtrando por empresa aparte."""
    q = db.query(PlanTipoActivo, PlanMantenimiento).join(
        PlanMantenimiento, PlanTipoActivo.plan_id == PlanMantenimiento.id).filter(
        PlanMantenimiento.activo == True)
    cobertura = {}
    for pta, plan in q.all():
        cobertura[pta.tipo_activo] = plan
    return cobertura


def activos_con_tarea_abierta(db: Session, activo_ids) -> set:
    """activo_ids con una tarea pendiente o en ejecución."""
    if not activo_ids:
        return set()
    rows = db.query(TareaMantenimiento.activo_id).filter(
        TareaMantenimiento.activo_id.in_(activo_ids),
        TareaMantenimiento.estado.in_(ESTADOS_TAREA_ABIERTA),
    ).all()
    return {r[0] for r in rows}


def tecnico_puede_ejecutar(db: Session, tecnico_id: str) -> bool:
    """True si el usuario puede ejecutar mantenimientos (permiso mantenimiento.ejecutar
    por rol activo, o super_admin)."""
    if is_super_admin(db, tecnico_id):
        return True
    n = db.query(Permiso).join(RolPermiso, RolPermiso.permiso_id == Permiso.id).join(
        Rol, Rol.id == RolPermiso.rol_id).join(
        UsuarioRol, UsuarioRol.rol_id == Rol.id).filter(
        UsuarioRol.usuario_sistema_id == tecnico_id,
        UsuarioRol.activo == True, Rol.activo == True,
        Permiso.codigo == "mantenimiento.ejecutar",
    ).first()
    return n is not None


def crear_tarea_preventiva(db: Session, activo: Activo, plan: PlanMantenimiento,
                           tecnico_id: str, fecha: date, created_by: str,
                           origen: str = "planificacion") -> TareaMantenimiento:
    """Crea una TareaMantenimiento PENDIENTE + snapshot inmutable del checklist del
    plan. NO hace commit (el llamador controla la transacción).

    Única implementación usada por planificación, ad-hoc y devolución ⇒ todas las
    tareas nacen idénticas (mismo snapshot, mismos campos). 'origen' indica de dónde
    nació: planificacion | devolucion | adhoc."""
    tarea = TareaMantenimiento(
        empresa_id=activo.empresa_id, activo_id=activo.id, plan_id=plan.id,
        tecnico_id=tecnico_id, estado="pendiente", origen=origen,
        fecha_programada=fecha, created_by=created_by,
    )
    db.add(tarea)
    db.flush()
    # SNAPSHOT del checklist del plan (historia inmutable)
    for it in sorted(plan.checklist_items, key=lambda x: (x.seccion, x.orden)):
        db.add(TareaChecklistItem(
            tarea_id=tarea.id, seccion=it.seccion, tipo_item=it.tipo_item,
            texto=it.texto, orden=it.orden))
    return tarea
