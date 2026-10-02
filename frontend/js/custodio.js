// ── CUSTODIO (empleado responsable de un recurso DISPONIBLE) ─────────────────
// Custodia NO es un estado: el recurso sigue "disponible" (asignable/reservable).
// El custodio puede ser de la misma empresa o de una hermana (misma regla que
// asignaciones). Reutiliza el lookup buscar-para-asignacion.

let _custEmpId = null;   // empresa del recurso en edición
let _custDoc   = null;   // documento del empleado resuelto por el lookup
let _custTimer = null;

// Badge para la celda de estado (solo disponible + con custodio)
function custodioBadge(r) {
  if (r.estado === 'disponible' && r.custodio_nombre) {
    return `<div class="td-sub" style="font-size:10px;color:#2DD4BF">🛡 Custodio: ${r.custodio_nombre}</div>`;
  }
  return '';
}

// Acción "Custodio" (solo disponible, gated por asignaciones.crear)
function custodioAction(tipo, r) {
  if (r.estado !== 'disponible' || !hasPermiso('asignaciones.crear')) return '';
  const placa = tipo === 'activo' ? r.id_placa_activo : r.id_placa_accesorio;
  const lbl = r.custodio_nombre ? '🛡 Custodio ✓' : '🛡 Custodio';
  const nombre = (r.custodio_nombre || '').replace(/'/g, "\\'");
  return `<button class="btn btn-ghost btn-sm" style="color:#2DD4BF;border-color:rgba(45,212,191,.35)" onclick="event.stopPropagation();abrirModalCustodio('${tipo}','${r.id}','${placa}','${r.empresa_id}','${nombre}','${r.custodio_documento || ''}')">${lbl}</button>`;
}

function abrirModalCustodio(tipo, id, placa, empresaId, custNombre, custDoc) {
  if (!hasPermiso('asignaciones.crear')) { notif('Sin permiso para gestionar custodios', 'error'); return; }
  document.getElementById('cust-tipo').value    = tipo;
  document.getElementById('cust-id').value      = id;
  document.getElementById('cust-empresa').value = empresaId;
  document.getElementById('cust-placa').textContent = placa;
  document.getElementById('cust-cedula').value  = '';
  _custEmpId = empresaId; _custDoc = null;
  document.getElementById('cust-info').style.display = 'none';
  document.getElementById('cust-msg').style.display = 'none';
  document.getElementById('cust-btn-guardar').disabled = true;
  const actual = document.getElementById('cust-actual');
  const btnQuitar = document.getElementById('cust-btn-quitar');
  if (custNombre) {
    actual.style.display = '';
    actual.innerHTML = `🛡 Custodio actual: <strong>${custNombre}</strong>${custDoc ? ' · ' + custDoc : ''}`;
    btnQuitar.style.display = '';
  } else {
    actual.style.display = 'none';
    btnQuitar.style.display = 'none';
  }
  abrirModal('modal-custodio');
}

function custBuscar() {
  clearTimeout(_custTimer);
  _custTimer = setTimeout(async () => {
    const ced = document.getElementById('cust-cedula').value.trim();
    const info = document.getElementById('cust-info');
    const btn = document.getElementById('cust-btn-guardar');
    _custDoc = null; btn.disabled = true;
    if (ced.length < 4) { info.style.display = 'none'; return; }
    const data = await api(`/usuarios/buscar-para-asignacion?documento=${encodeURIComponent(ced)}&empresa_id=${encodeURIComponent(_custEmpId)}`);
    if (data && data.length) {
      const e = data[0];
      _custDoc = e.documento; btn.disabled = false;
      const badge = e.es_empresa_relacionada
        ? ` <span style="background:rgba(255,176,32,.15);color:var(--amber);border:1px solid rgba(255,176,32,.35);border-radius:10px;padding:1px 8px;font-size:10px;font-weight:600">${e.nombre_empresa} · empresa relacionada</span>`
        : ` · <span style="color:var(--text3)">${e.nombre_empresa || ''}</span>`;
      info.style.display = ''; info.style.color = 'var(--cyan)';
      info.innerHTML = `👤 ${e.nombre_completo} — ${e.cargo || ''}${badge}`;
    } else {
      info.style.display = ''; info.style.color = 'var(--amber)';
      info.innerHTML = '⚠ No se encontró un empleado activo con esa cédula en la empresa o sus relacionadas.';
    }
  }, 350);
}

async function guardarCustodio() {
  if (!_custDoc) return;
  const tipo = document.getElementById('cust-tipo').value;
  const id = document.getElementById('cust-id').value;
  const base = tipo === 'activo' ? '/activos' : '/accesorios';
  const res = await apiRaw(`${base}/${id}/custodio`, {
    method: 'POST', body: JSON.stringify({ custodio_documento: _custDoc }) });
  if (res.ok) { notif('Custodio asignado'); cerrarModal('modal-custodio'); _custRecargar(tipo); }
  else { const e = await res.json().catch(() => ({})); _custMostrarMsg(e.detail || 'Error al asignar custodio'); }
}

async function quitarCustodio() {
  const tipo = document.getElementById('cust-tipo').value;
  const id = document.getElementById('cust-id').value;
  const base = tipo === 'activo' ? '/activos' : '/accesorios';
  const res = await apiRaw(`${base}/${id}/custodio`, { method: 'DELETE' });
  if (res.ok) { notif('Custodio retirado'); cerrarModal('modal-custodio'); _custRecargar(tipo); }
  else { const e = await res.json().catch(() => ({})); _custMostrarMsg(e.detail || 'Error al quitar custodio'); }
}

function _custMostrarMsg(m) {
  const el = document.getElementById('cust-msg');
  el.style.cssText = 'display:block;border-radius:8px;padding:8px 12px;font-size:12px;background:rgba(255,77,109,.1);border:1px solid rgba(255,77,109,.3);color:var(--red)';
  el.textContent = '❌ ' + m;
}
function _custRecargar(tipo) {
  if (tipo === 'activo' && typeof cargarActivos === 'function') cargarActivos();
  if (tipo === 'accesorio' && typeof cargarAccesorios === 'function') cargarAccesorios();
  if (typeof cargarDashboard === 'function') cargarDashboard();
}
