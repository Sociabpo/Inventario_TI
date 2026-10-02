from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import settings
from database import engine, Base, get_db
import models
from routers import auth, empresas, usuarios, activos, accesorios, asignaciones, actas, firma, rbac, servidores, export, compras, catalogos, estados, reservas, prestamos, dashboard, importacion, mantenimiento, redes, proveedores, impresoras, pendientes, impresoras_reportes
from routers.auth import get_current_user

app = FastAPI(
    title="SIT — Sistema de Inventario Tecnológico",
    version="1.0.0",
    # Docs abiertas solo en DEBUG (dev). En prod (DEBUG=False) → cerradas.
    docs_url="/api/docs" if settings.DEBUG else None,
    redoc_url="/api/redoc" if settings.DEBUG else None,
    openapi_url="/api/openapi.json" if settings.DEBUG else None,
)

if settings.DEBUG:
    # Dev: cualquier puerto de localhost/127.0.0.1. Regex explícito (no "*"),
    # válido junto con allow_credentials=True.
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # Prod: orígenes explícitos desde ALLOWED_ORIGINS (nunca "*" con credentials).
    origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

Base.metadata.create_all(bind=engine)

scheduler = BackgroundScheduler(timezone="America/Bogota")

app.include_router(auth.router)
app.include_router(empresas.router)
app.include_router(usuarios.router)
app.include_router(activos.router)
app.include_router(accesorios.router)
app.include_router(asignaciones.router)
app.include_router(actas.router)
app.include_router(firma.router)
app.include_router(rbac.router)
app.include_router(servidores.router)
app.include_router(export.router)
app.include_router(compras.router)
app.include_router(catalogos.router)
app.include_router(estados.router)
app.include_router(reservas.router)
app.include_router(prestamos.router)
app.include_router(dashboard.router)
app.include_router(importacion.router)
app.include_router(mantenimiento.router)
app.include_router(redes.router)
app.include_router(proveedores.router)
app.include_router(impresoras.router)
app.include_router(pendientes.router)
app.include_router(impresoras_reportes.router)


# ── Trigger manual de recordatorios (solo super_admin, para pruebas) ──
@app.post("/api/admin/recordatorios/ejecutar-ahora", tags=["Admin"])
async def ejecutar_recordatorios_ahora(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    from services.rbac_service import is_super_admin
    if not is_super_admin(db, current_user.id):
        raise HTTPException(status_code=403, detail="Solo super_admin")
    from services.recordatorio_service import procesar_recordatorios
    import threading
    threading.Thread(target=procesar_recordatorios, daemon=True).start()
    return {"mensaje": "Proceso de recordatorios iniciado en background"}


# ── Trigger manual de liberación de reservas vencidas (solo super_admin) ──
@app.post("/api/admin/reservas/liberar-ahora", tags=["Admin"])
async def liberar_reservas_ahora(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    from services.rbac_service import is_super_admin
    if not is_super_admin(db, current_user.id):
        raise HTTPException(status_code=403, detail="Solo super_admin")
    from services.reserva_service import liberar_reservas_vencidas
    import threading
    threading.Thread(target=liberar_reservas_vencidas, daemon=True).start()
    return {"mensaje": "Liberación de reservas vencidas iniciada en background"}


# ── Trigger manual de alerta de préstamos vencidos (solo super_admin) ──
@app.post("/api/admin/prestamos/alertar-ahora", tags=["Admin"])
async def alertar_prestamos_ahora(
    current_user=Depends(get_current_user),
    db=Depends(get_db),
):
    from services.rbac_service import is_super_admin
    if not is_super_admin(db, current_user.id):
        raise HTTPException(status_code=403, detail="Solo super_admin")
    from services.prestamo_service import alertar_prestamos_vencidos
    import threading
    threading.Thread(target=alertar_prestamos_vencidos, daemon=True).start()
    return {"mensaje": "Alerta de préstamos vencidos iniciada en background"}


# ── Scheduler de recordatorios de firma ──
@app.on_event("startup")
async def startup_event():
    from services.recordatorio_service import procesar_recordatorios
    from services.reserva_service import liberar_reservas_vencidas
    from services.prestamo_service import alertar_prestamos_vencidos
    scheduler.add_job(
        procesar_recordatorios,
        CronTrigger(hour=14, minute=0),
        id="recordatorio_firma",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        liberar_reservas_vencidas,
        CronTrigger(hour=14, minute=5),   # 2:05 PM, justo después de recordatorios
        id="liberar_reservas",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        alertar_prestamos_vencidos,
        CronTrigger(hour=14, minute=10),  # 2:10 PM, después de recordatorios y reservas
        id="alertar_prestamos",
        replace_existing=True,
        misfire_grace_time=3600,
    )
    scheduler.start()
    print("[SCHEDULER] Recordatorio de firmas programado — 2:00 PM diario (America/Bogota)")
    print("[SCHEDULER] Liberación de reservas vencidas programada — 2:05 PM diario (America/Bogota)")
    print("[SCHEDULER] Alerta de préstamos vencidos programada — 2:10 PM diario (America/Bogota)")


@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown(wait=False)
    print("[SCHEDULER] Scheduler detenido")


# Logos de empresa (públicos, para etiquetas y actas) — debe ir ANTES del mount "/"
app.mount("/logos-empresa", StaticFiles(directory="templates/img"), name="logos-empresa")

app.mount("/", StaticFiles(directory="../frontend", html=True), name="frontend")