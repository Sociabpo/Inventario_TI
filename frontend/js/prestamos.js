// ── PRÉSTAMOS TEMPORALES (loans) ────────────────────────────
// El préstamo NO es un estado: el recurso sigue "asignado". La fecha límite vive
// sobre el recurso (activo/accesorio). Endpoints: /api/prestamos/{tipo}/{id}/...

function _tomorrowISO() {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().slice(0, 10);
}

function fFechaCorta(iso) {
  if (!iso) return '—';
  const d = new Date(String(iso).slice(0, 10) + 'T00:00:00');
  return d.toLocaleDateString('es-CO', { day: '2-digit', month: '2-digit', year: 'numeric' });
}

// Badge del préstamo para la celda de estado de los listados.
function loanBadge(a) {
  if (a.estado !== 'asignado' || !a.es_prestamo || !a.fecha_limite_devolucion) return '';
  const d = a.dias_para_vencer;
  if (a.prestamo_vencido) {
    return `<div class="td-sub" style="font-size:10px;color:var(--red);font-weight:600">⏰ Préstamo vencido (${Math.abs(d)}d)</div>`;
  }
  if (d != null && d <= 3) {
    return `<div class="td-sub" style="font-size:10px;color:var(--amber);font-weight:600">⏳ Vence en ${d}d</div>`;
  }
  return `<div class="td-sub" style="font-size:10px;color:var(--info)">📅 Préstamo hasta ${fFechaCorta(a.fecha_limite_devolucion)}</div>`;
}

// Marca de alquiler (rental): el recurso NO es propiedad, pertenece a un contrato.
function rentalBadge(a) {
  if (!a || !a.es_alquiler) return '';
  return `<div class="td-sub" style="font-size:10px;color:#A78BFF;font-weight:600">🔑 Alquilado</div>`;
}

// Acciones de préstamo para la celda de acción (gated por asignaciones.crear).
// tipo: 'activo' | 'accesorio'  ·  placa: texto a mostrar en el modal.
function loanActions(tipo, a, placa) {
  if (!hasPermiso('asignaciones.crear') || a.estado !== 'asignado') return '';
  const fl = a.fecha_limite_devolucion || '';
  if (a.es_prestamo && fl) {
    return `
      <button class="btn btn-ghost btn-sm" style="color:var(--info);border-color:rgba(var(--info-rgb),0.3)" onclick="event.stopPropagation();abrirModalPrestamo('${tipo}','${a.id}','${placa}','${fl}')" title="Extender préstamo"><i class="ti ti-calendar-plus"></i> Extender</button>
      <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();convertirIndefinido('${tipo}','${a.id}','${placa}')" title="Convertir a asignación indefinida"><i class="ti ti-infinity"></i> Indefinido</button>`;
  }
  return `<button class="btn btn-ghost btn-sm" style="color:var(--info);border-color:rgba(var(--info-rgb),0.3)" onclick="event.stopPropagation();abrirModalPrestamo('${tipo}','${a.id}','${placa}','')" title="Definir préstamo"><i class="ti ti-calendar"></i> Préstamo</button>`;
}

// ── Modal de fecha límite ────────────────────────────────────
function abrirModalPrestamo(tipo, recursoId, placa, fechaActual) {
  if (!hasPermiso('asignaciones.crear')) { notif('Sin permiso para gestionar préstamos', 'error'); return; }
  document.getElementById('prestamo-tipo').value       = tipo;
  document.getElementById('prestamo-recurso-id').value = recursoId;
  document.getElementById('prestamo-recurso-label').textContent =
    `${tipo === 'activo' ? '🖥' : '🖱'} ${placa || ''}`;
  document.getElementById('prestamo-modal-title').textContent =
    fechaActual ? 'Extender préstamo' : 'Definir préstamo';
  const inp = document.getElementById('prestamo-fecha-limite');
  inp.min = _tomorrowISO();
  inp.value = fechaActual ? String(fechaActual).slice(0, 10) : '';
  const msg = document.getElementById('prestamo-msg');
  msg.style.display = 'none';
  abrirModal('modal-prestamo');
}

async function guardarFechaLimitePrestamo() {
  const tipo = document.getElementById('prestamo-tipo').value;
  const id   = document.getElementById('prestamo-recurso-id').value;
  const fecha = document.getElementById('prestamo-fecha-limite').value;
  const msg  = document.getElementById('prestamo-msg');
  if (!fecha) {
    msg.textContent = '⚠ Selecciona una fecha límite';
    msg.style.cssText = 'display:block;border-radius:8px;padding:10px 14px;font-size:12px;background:rgba(255,176,32,0.1);border:1px solid rgba(255,176,32,0.3);color:var(--amber)';
    return;
  }
  if (fecha <= new Date().toISOString().slice(0, 10)) {
    msg.textContent = '⚠ La fecha límite debe ser posterior a hoy';
    msg.style.cssText = 'display:block;border-radius:8px;padding:10px 14px;font-size:12px;background:rgba(255,176,32,0.1);border:1px solid rgba(255,176,32,0.3);color:var(--amber)';
    return;
  }
  const res = await apiRaw(`/prestamos/${tipo}/${id}/fecha-limite`, {
    method: 'POST', body: JSON.stringify({ fecha_limite_devolucion: fecha })
  });
  if (res.ok) {
    cerrarModal('modal-prestamo');
    notif('Fecha límite de préstamo guardada');
    _recargarTrasPrestamo(tipo);
  } else {
    const err = await res.json();
    msg.textContent = `❌ ${err.detail || 'Error al guardar la fecha límite'}`;
    msg.style.cssText = 'display:block;border-radius:8px;padding:10px 14px;font-size:12px;background:rgba(255,77,109,0.1);border:1px solid rgba(255,77,109,0.3);color:var(--red)';
  }
}

async function convertirIndefinido(tipo, recursoId, placa) {
  if (!hasPermiso('asignaciones.crear')) { notif('Sin permiso para gestionar préstamos', 'error'); return; }
  if (!confirm(`¿Convertir ${placa || 'el recurso'} a asignación indefinida? Se quitará la fecha límite de préstamo.`)) return;
  const res = await apiRaw(`/prestamos/${tipo}/${recursoId}/convertir-indefinido`, { method: 'POST' });
  if (res.ok) {
    notif('Préstamo convertido a asignación indefinida');
    _recargarTrasPrestamo(tipo);
  } else {
    const err = await res.json();
    notif(err.detail || 'Error al convertir el préstamo', 'error');
  }
}

function _recargarTrasPrestamo(tipo) {
  if (tipo === 'activo' && typeof cargarActivos === 'function') cargarActivos();
  if (tipo === 'accesorio' && typeof cargarAccesorios === 'function') cargarAccesorios();
  if (typeof cargarDashboard === 'function') cargarDashboard();
}

// ── Chips de alerta en el dashboard ──────────────────────────
async function cargarPrestamosStats() {
  const cont = document.getElementById('dash-prestamos-alerts');
  if (!cont) return;
  const p = empresaActual ? `?empresa_id=${empresaActual}` : '';
  const s = await api(`/prestamos/stats${p}`);
  if (!s) { cont.style.display = 'none'; return; }
  const chips = [];
  if (s.prestamos_vencidos > 0) {
    chips.push(`<span onclick="irAPrestamos('vencido')" style="cursor:pointer;display:inline-flex;align-items:center;gap:6px;background:rgba(255,77,109,0.12);border:1px solid rgba(255,77,109,0.35);color:var(--red);border-radius:20px;padding:6px 14px;font-size:12px;font-weight:600">⏰ ${s.prestamos_vencidos} préstamos vencidos</span>`);
  }
  if (s.prestamos_por_vencer > 0) {
    chips.push(`<span onclick="irAPrestamos('prestamo')" style="cursor:pointer;display:inline-flex;align-items:center;gap:6px;background:rgba(255,176,32,0.12);border:1px solid rgba(255,176,32,0.35);color:var(--amber);border-radius:20px;padding:6px 14px;font-size:12px;font-weight:600">⏳ ${s.prestamos_por_vencer} préstamos por vencer</span>`);
  }
  cont.innerHTML = chips.join('');
  cont.style.display = chips.length ? 'flex' : 'none';
}

// Navega a Activos y aplica el filtro de préstamos (clic en un chip).
function irAPrestamos(modo) {
  const f = document.getElementById('filtro-activos-prestamo');
  if (f) f.value = modo;
  const panel = document.getElementById('filtros-activos');
  if (panel) panel.classList.add('open');
  showView('activos', null);
}
