// ── Módulo Mantenimiento Preventivo — Fase 1: gestión de PLANES ───────────────

let planesMantCache = [];
let _planTipos = [];   // tipos de activo seleccionados en el modal de plan

const _SECC_LBL = { diagnostico: 'Diagnóstico', hardware: 'Hardware', software: 'Software' };

async function cargarPlanesMant() {
  // Planes GLOBALES: no se filtran por empresa
  planesMantCache = await api(`/mantenimiento/planes`) || [];
  renderPlanesMant();
}

function renderPlanesMant() {
  const tbody = document.getElementById('tbl-planes-body');
  if (!tbody) return;
  const q = (document.getElementById('mant-search')?.value || '').toLowerCase().trim();
  const fAct = document.getElementById('mant-filtro-activo')?.value ?? '';
  let list = planesMantCache;
  if (fAct !== '') list = list.filter(p => (p.activo ? '1' : '0') === fAct);
  if (q) list = list.filter(p =>
    (p.nombre || '').toLowerCase().includes(q) ||
    (p.tipos || []).some(t => (t || '').toLowerCase().includes(q)));

  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:22px">Sin planes de mantenimiento</td></tr>';
    return;
  }
  const puede = hasPermiso('mantenimiento.planes');
  tbody.innerHTML = list.map(p => {
    const tipos = (p.tipos || []).map(t => `<span class="mono-tag" style="font-size:9px">${t}</span>`).join(' ') || '<span style="color:var(--text3)">—</span>';
    const estado = p.activo
      ? _badge('Activo', 'var(--green)')
      : _badge('Inactivo', 'var(--text3)');
    let acc = '';
    if (puede) {
      acc += `<button class="btn btn-ghost btn-sm" onclick="abrirModalPlan('${p.id}')">✎ Editar</button>`;
      acc += p.activo
        ? ` <button class="btn btn-ghost btn-sm" style="color:var(--text3)" onclick="togglePlanActivo('${p.id}',false)">Desactivar</button>`
        : ` <button class="btn btn-ghost btn-sm" style="color:var(--green);border-color:rgba(0,229,160,.3)" onclick="togglePlanActivo('${p.id}',true)">Reactivar</button>`;
    }
    return `<tr>
      <td><div class="td-name">${p.nombre}</div>${p.descripcion ? `<div class="td-sub" style="max-width:260px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${p.descripcion}</div>` : ''}</td>
      <td>${tipos}</td>
      <td style="text-align:center">${p.periodicidad_meses} m</td>
      <td style="text-align:center"><span class="mono-tag">${p.checklist_count}</span></td>
      <td>${estado}</td>
      <td style="white-space:nowrap">${acc || '<span style="color:var(--text3)">—</span>'}</td>
    </tr>`;
  }).join('');
}

// ── Tipos de activo cubiertos ──
function _llenarTipoActivoSelect() {
  const sel = document.getElementById('plan-tipo-sel');
  if (!sel) return;
  const items = (typeof getCatalogo === 'function' ? getCatalogo('tipo_activo') : []) || [];
  sel.innerHTML = '<option value="">Seleccionar tipo...</option>' +
    items.map(i => `<option value="${i.valor}">${i.valor}</option>`).join('');
}
function agregarTipoPlan() {
  const sel = document.getElementById('plan-tipo-sel');
  const v = sel.value;
  if (!v) return;
  if (!_planTipos.includes(v)) _planTipos.push(v);
  sel.value = '';
  renderTiposPlan();
}
function quitarTipoPlan(t) {
  _planTipos = _planTipos.filter(x => x !== t);
  renderTiposPlan();
}
function renderTiposPlan() {
  const cont = document.getElementById('plan-tipos-lista');
  if (!cont) return;
  cont.innerHTML = _planTipos.map(t => `
    <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(6,191,255,0.12);border:1px solid rgba(6,191,255,0.3);border-radius:20px;padding:3px 10px;font-size:11px;color:var(--cyan)">
      ${t}
      <button onclick="quitarTipoPlan('${t.replace(/'/g,'')}')" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:13px;padding:0;line-height:1">×</button>
    </span>`).join('') || '<span style="color:var(--text3);font-size:11px">Ningún tipo agregado</span>';
}

// ── Checklist builder ──
function _filaItemPlan(it) {
  const d = it || {};
  const sel = (a, b) => a === b ? ' selected' : '';
  const txt = (d.texto || '').replace(/"/g, '&quot;');
  return `<div class="plan-item-row" style="display:grid;grid-template-columns:1.1fr .8fr 2.4fr auto auto auto;gap:6px;align-items:center;margin-bottom:6px">
    <select class="fselect plan-it-seccion">
      <option value="diagnostico"${sel(d.seccion,'diagnostico')}>Diagnóstico</option>
      <option value="hardware"${sel(d.seccion,'hardware')}>Hardware</option>
      <option value="software"${sel(d.seccion,'software')}>Software</option>
    </select>
    <select class="fselect plan-it-tipo">
      <option value="check"${sel(d.tipo_item,'check')}>Check</option>
      <option value="dato"${sel(d.tipo_item,'dato')}>Dato</option>
    </select>
    <input class="finput plan-it-texto" placeholder="Texto del ítem" value="${txt}">
    <button type="button" class="btn btn-ghost btn-sm" title="Subir" onclick="_moverItemPlan(this,-1)">↑</button>
    <button type="button" class="btn btn-ghost btn-sm" title="Bajar" onclick="_moverItemPlan(this,1)">↓</button>
    <button type="button" class="btn btn-ghost btn-sm" style="color:var(--red)" onclick="this.closest('.plan-item-row').remove()">×</button>
  </div>`;
}
function agregarItemPlan(it) {
  document.getElementById('plan-checklist-container').insertAdjacentHTML('beforeend', _filaItemPlan(it));
}
function _moverItemPlan(btn, dir) {
  const row = btn.closest('.plan-item-row');
  if (!row) return;
  if (dir < 0 && row.previousElementSibling) row.parentNode.insertBefore(row, row.previousElementSibling);
  if (dir > 0 && row.nextElementSibling) row.parentNode.insertBefore(row.nextElementSibling, row);
}

// ── Crear / editar ──
async function abrirModalPlan(id) {
  if (!hasPermiso('mantenimiento.planes')) { notif('Sin permiso', 'error'); return; }
  document.getElementById('plan-id').value = id || '';
  document.getElementById('modal-plan-title').textContent = id ? 'Editar plan de mantenimiento' : 'Nuevo plan de mantenimiento';
  _planTipos = [];
  _llenarTipoActivoSelect();
  const msg = document.getElementById('plan-msg'); msg.style.display = 'none';
  const cont = document.getElementById('plan-checklist-container');

  if (id) {
    const p = await api(`/mantenimiento/planes/${id}`);
    if (!p) { notif('No se pudo cargar el plan', 'error'); return; }
    document.getElementById('plan-nombre').value = p.nombre || '';
    document.getElementById('plan-periodicidad').value = p.periodicidad_meses || 12;
    document.getElementById('plan-descripcion').value = p.descripcion || '';
    document.getElementById('plan-codigo').value = p.codigo_formato || 'FTIN09';
    document.getElementById('plan-version').value = p.version_formato || '1.1';
    document.getElementById('plan-fecha-emision').value = p.fecha_emision_formato ? String(p.fecha_emision_formato).slice(0,10) : '';
    document.getElementById('plan-clasificacion').value = p.clasificacion || 'Interno';
    document.getElementById('plan-proceso').value = p.proceso || 'Servicio';
    _planTipos = [...(p.tipos || [])];
    cont.innerHTML = (p.checklist && p.checklist.length) ? p.checklist.map(it => _filaItemPlan(it)).join('') : '';
  } else {
    document.getElementById('plan-nombre').value = '';
    document.getElementById('plan-periodicidad').value = 12;
    document.getElementById('plan-descripcion').value = '';
    document.getElementById('plan-codigo').value = 'FTIN09';
    document.getElementById('plan-version').value = '1.1';
    document.getElementById('plan-fecha-emision').value = '';
    document.getElementById('plan-clasificacion').value = 'Interno';
    document.getElementById('plan-proceso').value = 'Servicio';
    cont.innerHTML = _filaItemPlan();   // una fila inicial
  }
  renderTiposPlan();
  abrirModal('modal-plan');
}

async function guardarPlan() {
  const id = document.getElementById('plan-id').value;
  const nombre = document.getElementById('plan-nombre').value.trim();
  const msg = document.getElementById('plan-msg');
  const showErr = (t) => { msg.textContent = '⚠ ' + t; msg.style.cssText = 'display:block;font-size:12px;border-radius:8px;padding:8px 12px;margin-top:8px;background:rgba(255,176,32,0.1);border:1px solid rgba(255,176,32,0.3);color:var(--amber)'; };

  if (!nombre) { showErr('El nombre es obligatorio'); return; }
  if (!_planTipos.length) { showErr('Agrega al menos un tipo de activo'); return; }

  const checklist = [...document.querySelectorAll('#plan-checklist-container .plan-item-row')].map((r, idx) => ({
    seccion: r.querySelector('.plan-it-seccion').value,
    tipo_item: r.querySelector('.plan-it-tipo').value,
    texto: r.querySelector('.plan-it-texto').value.trim(),
    orden: idx,
  })).filter(i => i.texto);

  const body = {
    nombre,
    descripcion: document.getElementById('plan-descripcion').value.trim() || null,
    periodicidad_meses: parseInt(document.getElementById('plan-periodicidad').value) || 12,
    codigo_formato: document.getElementById('plan-codigo').value.trim() || 'FTIN09',
    version_formato: document.getElementById('plan-version').value.trim() || '1.1',
    fecha_emision_formato: document.getElementById('plan-fecha-emision').value || null,
    clasificacion: document.getElementById('plan-clasificacion').value.trim() || 'Interno',
    proceso: document.getElementById('plan-proceso').value.trim() || 'Servicio',
    tipos: _planTipos,
    checklist,
  };

  let res;
  if (id) {
    res = await apiRaw(`/mantenimiento/planes/${id}`, { method: 'PUT', body: JSON.stringify(body) });
  } else {
    res = await apiRaw('/mantenimiento/planes', { method: 'POST', body: JSON.stringify(body) });
  }
  if (res.ok) { notif(id ? 'Plan actualizado' : 'Plan creado'); cerrarModal('modal-plan'); cargarPlanesMant(); }
  else { const e = await res.json().catch(()=>({})); showErr(e.detail || 'Error al guardar el plan'); }
}

async function togglePlanActivo(id, activar) {
  const accion = activar ? 'activar' : 'desactivar';
  const res = await apiRaw(`/mantenimiento/planes/${id}/${accion}`, { method: 'POST' });
  if (res.ok) { notif(activar ? 'Plan reactivado' : 'Plan desactivado'); cargarPlanesMant(); }
  else { const e = await res.json().catch(()=>({})); notif(e.detail || 'Error', 'error'); }
}

// ══ FASE 2 — PLANIFICACIÓN ══════════════════════════════════════════════════
let recomendadosCache = [];
let _planificarCargado = false;

// Punto de entrada al abrir el módulo (llamado desde showView): oculta las
// pestañas cuyo permiso el usuario no tiene y abre la PRIMERA visible. Así un
// técnico con solo 'ejecutar' entra directo a "Mis mantenimientos" y nunca se
// dispara un fetch de planes (que daría 403).
function initMantView() {
  const tabs = [...document.querySelectorAll('#tabs-mant .tab')];
  let primeraVisible = null;
  tabs.forEach(btn => {
    const perm = btn.dataset.permiso;
    const visible = !perm || hasPermiso(perm);
    btn.style.display = visible ? '' : 'none';
    if (visible && !primeraVisible) primeraVisible = btn;
  });
  if (primeraVisible) switchMantTab(primeraVisible.dataset.mtab, primeraVisible);
}

function switchMantTab(tab, el) {
  document.querySelectorAll('#tabs-mant .tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  document.querySelectorAll('.mant-panel').forEach(p => p.style.display = 'none');
  const panel = document.getElementById(`mant-panel-${tab}`);
  if (panel) panel.style.display = '';
  if (tab === 'planes') cargarPlanesMant();
  if (tab === 'planificar') {
    if (!_planificarCargado) { _planificarCargado = true; _initPlanificar(); }
    else { cargarRecomendados(); cargarTecnicosConTareas(); cargarTareasProg(); }
  }
  if (tab === 'mis-tareas') cargarMisTareas();
  if (tab === 'calendario') {
    if (!_calInit) { _calInit = true; _initCalendario(); }
    else cargarCalendario();
  }
  if (tab === 'tableros') {
    if (!_tablerosInit) { _tablerosInit = true; _initTableros(); }
    else cargarTableroActual();
  }
}

async function _initPlanificar() {
  llenarSelectEmpresas('rec-filtro-empresa');
  const empSel = document.getElementById('rec-filtro-empresa');
  if (!empSel.querySelector('option[value=""]')) {
    empSel.insertAdjacentHTML('afterbegin', '<option value="">Todas las empresas</option>');
  }
  empSel.value = empresaActual || '';
  const tipoSel = document.getElementById('rec-filtro-tipo');
  const tipos = (typeof getCatalogo === 'function' ? getCatalogo('tipo_activo') : []) || [];
  tipoSel.innerHTML = '<option value="">Todos los tipos</option>' +
    tipos.map(t => `<option value="${t.valor}">${t.valor}</option>`).join('');
  await cargarTecnicos();
  await cargarRecomendados();
  await cargarTecnicosConTareas();
  await cargarTareasProg();
}

async function cargarTecnicos() {
  const p = new URLSearchParams();
  const emp = document.getElementById('rec-filtro-empresa')?.value || empresaActual;
  if (emp) p.set('empresa_id', emp);
  const tecs = await api(`/mantenimiento/tecnicos?${p}`) || [];
  document.getElementById('plan-tecnico').innerHTML = '<option value="">Seleccionar...</option>' +
    tecs.map(t => `<option value="${t.id}">${t.nombre}${t.email ? ' — ' + t.email : ''}</option>`).join('');
}

async function cargarRecomendados() {
  const p = new URLSearchParams();
  const emp = document.getElementById('rec-filtro-empresa')?.value;
  const tipo = document.getElementById('rec-filtro-tipo')?.value;
  if (emp) p.set('empresa_id', emp);
  if (tipo) p.set('tipo_activo', tipo);
  recomendadosCache = await api(`/mantenimiento/recomendados?${p}`) || [];
  renderRecomendados();
  cargarTecnicos();
}

function renderRecomendados() {
  const tbody = document.getElementById('tbl-recomendados-body');
  if (!tbody) return;
  const sa = document.getElementById('rec-select-all');
  if (sa) sa.checked = false;
  if (!recomendadosCache.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:22px">No hay equipos recomendados (todo al día o sin plan activo)</td></tr>';
    _recActualizarConteo();
    return;
  }
  tbody.innerHTML = recomendadosCache.map(r => `
    <tr>
      <td style="text-align:center"><input type="checkbox" class="rec-chk" value="${r.activo_id}" onchange="_recActualizarConteo()"></td>
      <td><span class="mono-tag">${r.placa || '—'}</span></td>
      <td>${r.tipo_activo || '—'}</td>
      <td>${[r.marca, r.modelo].filter(Boolean).join(' ') || '—'}</td>
      <td>${r.tenedor || '<span style="color:var(--text3)">En bodega</span>'}</td>
      <td>${r.ultimo_mantenimiento === 'Nunca'
            ? '<span class="badge" style="background:#FFB02022;color:#FFB020;border:1px solid #FFB02055">Nunca</span>'
            : `<span style="color:var(--text2)">${r.ultimo_mantenimiento}</span>`}</td>
    </tr>`).join('');
  _recActualizarConteo();
}

function recToggleAll(checked) {
  document.querySelectorAll('#tbl-recomendados-body .rec-chk').forEach(c => c.checked = checked);
  _recActualizarConteo();
}
function _recActualizarConteo() {
  const n = document.querySelectorAll('#tbl-recomendados-body .rec-chk:checked').length;
  const el = document.getElementById('rec-count');
  if (el) el.textContent = n;
}

function planToggleRango() {
  const custom = document.getElementById('plan-rango').value === 'custom';
  document.getElementById('plan-rango-custom').style.display = custom ? '' : 'none';
}

async function asignarTareas() {
  const activos_ids = [...document.querySelectorAll('#tbl-recomendados-body .rec-chk:checked')].map(c => c.value);
  const tecnico_id = document.getElementById('plan-tecnico').value;
  const tipoRango = document.getElementById('plan-rango').value;
  const dias = [...document.querySelectorAll('#plan-dias input:checked')].map(c => parseInt(c.value));
  const resultDiv = document.getElementById('plan-result');

  if (!activos_ids.length) { notif('Selecciona al menos un equipo recomendado', 'error'); return; }
  if (!tecnico_id) { notif('Selecciona un técnico', 'error'); return; }
  if (!dias.length) { notif('Marca al menos un día de referencia', 'error'); return; }

  const rango = { tipo: tipoRango };
  if (tipoRango === 'custom') {
    rango.desde = document.getElementById('plan-desde').value || null;
    rango.hasta = document.getElementById('plan-hasta').value || null;
    if (!rango.desde || !rango.hasta) { notif('Indica desde y hasta para el rango personalizado', 'error'); return; }
  }

  const res = await apiRaw('/mantenimiento/tareas', {
    method: 'POST',
    body: JSON.stringify({ activos_ids, tecnico_id, rango, dias_referencia: dias })
  });
  if (!res.ok) { const e = await res.json().catch(()=>({})); notif(e.detail || 'Error al asignar', 'error'); return; }
  const data = await res.json();

  notif(`${data.total_creadas} mantenimiento(s) asignado(s)${data.total_omitidos ? ` · ${data.total_omitidos} omitido(s)` : ''}`);
  let html = `<div style="color:var(--green)">✓ ${data.total_creadas} tarea(s) creada(s).</div>`;
  if (data.total_omitidos) {
    html += `<div style="margin-top:6px;color:var(--amber)">Omitidos (${data.total_omitidos}):</div>` +
      data.omitidos.map(o => `<div style="font-size:11px;color:var(--text3)">• ${o.placa || o.activo_id} — ${o.motivo}</div>`).join('');
  }
  resultDiv.innerHTML = html;
  resultDiv.style.display = 'block';

  await cargarRecomendados();
  await cargarTecnicosConTareas();   // recién asignadas → el técnico ya puede aparecer en el filtro
  await cargarTareasProg();
}

// ── Filtro avanzado de "Tareas programadas" (técnico + estado + fecha) ──
async function cargarTecnicosConTareas() {
  const sel = document.getElementById('tp-filtro-tecnico');
  if (!sel) return;
  const prev = sel.value;
  const p = new URLSearchParams();
  const emp = document.getElementById('rec-filtro-empresa')?.value;
  if (emp) p.set('empresa_id', emp);
  const tecs = await api(`/mantenimiento/tecnicos-con-tareas?${p}`) || [];
  sel.innerHTML = '<option value="">Todos los técnicos</option>' +
    tecs.map(t => `<option value="${t.id}">${t.nombre || t.id}</option>`).join('');
  // Conservar la selección si sigue disponible tras cambiar de empresa; si no, resetear.
  sel.value = tecs.some(t => t.id === prev) ? prev : '';
}

function tpFechaChange() {
  const ff = document.getElementById('tp-filtro-fecha')?.value;
  const custom = document.getElementById('tp-rango-custom');
  if (custom) custom.style.display = (ff === 'custom') ? 'inline-flex' : 'none';
  // "custom" espera a que el usuario elija fechas; el resto recarga de inmediato.
  if (ff !== 'custom') cargarTareasProg();
}

function tpLimpiarFiltros() {
  const set = (id, v) => { const e = document.getElementById(id); if (e) e.value = v; };
  set('tp-filtro-tecnico', ''); set('tp-filtro-estado', ''); set('tp-filtro-fecha', '');
  set('tp-filtro-desde', ''); set('tp-filtro-hasta', '');
  const custom = document.getElementById('tp-rango-custom');
  if (custom) custom.style.display = 'none';
  cargarTareasProg();
}

// Cambio del selector de empresa (compartido con recomendados): repobla técnicos
// (distintos por empresa) + recarga recomendados y la tabla de tareas.
async function tpEmpresaChange() {
  await cargarRecomendados();
  await cargarTecnicosConTareas();
  await cargarTareasProg();
}

async function cargarTareasProg() {
  const p = new URLSearchParams();
  const emp = document.getElementById('rec-filtro-empresa')?.value;
  if (emp) p.set('empresa_id', emp);
  const tec = document.getElementById('tp-filtro-tecnico')?.value;
  if (tec) p.set('tecnico_id', tec);
  const est = document.getElementById('tp-filtro-estado')?.value;
  if (est) p.set('estado', est);
  const ff = document.getElementById('tp-filtro-fecha')?.value;
  if (ff === 'custom') {
    const d = document.getElementById('tp-filtro-desde')?.value;
    const h = document.getElementById('tp-filtro-hasta')?.value;
    if (d) p.set('desde', d);
    if (h) p.set('hasta', h);
  } else if (ff) {
    p.set('fecha_filtro', ff);   // hoy | semana | mes | vencidas (server-side)
  }
  const tareas = await api(`/mantenimiento/tareas?${p}`) || [];
  const tbody = document.getElementById('tbl-tareas-prog-body');
  if (!tbody) return;
  const EST = { pendiente: 'var(--amber)', en_ejecucion: 'var(--cyan)', completada: 'var(--green)', cancelada: 'var(--text3)' };
  if (!tareas.length) {
    tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:18px">Sin tareas programadas</td></tr>';
    return;
  }
  tbody.innerHTML = tareas.map(t => `
    <tr>
      <td><span class="mono-tag">${t.placa || '—'}</span></td>
      <td>${t.tipo_activo || '—'}</td>
      <td>${t.tecnico || '—'}</td>
      <td style="font-size:12px">${t.fecha_programada ? _fecha(t.fecha_programada) : '—'}</td>
      <td style="font-size:12px">${t.plan_nombre || '—'}</td>
      <td>${_badge((t.estado || '').replace(/_/g,' '), EST[t.estado] || 'var(--text3)')}</td>
    </tr>`).join('');
}

// ══ FASE 3 — EJECUCIÓN (técnico) ════════════════════════════════════════════
const _SECC_ORDEN = ['diagnostico', 'hardware', 'software'];
const _SECC_TIT = { diagnostico: 'Diagnóstico', hardware: 'Mantenimiento hardware', software: 'Mantenimiento software' };
let _ejecTarea = null;

let _misLaterOpen = false;   // estado del grupo "Más adelante" (colapsable)

function _hoyISO() { return new Date().toISOString().slice(0, 10); }
function _diasEntre(iso, hoyISO) {
  return Math.round((new Date(hoyISO + 'T00:00:00') - new Date(String(iso).slice(0,10) + 'T00:00:00')) / 86400000);
}
function _finSemanaISO(hoyISO) {
  const d = new Date(hoyISO + 'T00:00:00');
  const dow = (d.getDay() + 6) % 7;       // Lun=0 … Dom=6
  d.setDate(d.getDate() + (6 - dow));      // domingo de esta semana
  return d.toISOString().slice(0, 10);
}

async function cargarMisTareas() {
  const data = await api('/mantenimiento/mis-tareas') || { resumen: { mes: {}, vencidos: 0 }, tareas: [] };
  const cont = document.getElementById('mis-tareas-dash');
  if (!cont) return;
  const R = data.resumen || { mes: {}, vencidos: 0 };
  const mes = R.mes || { pct: 0, completadas: 0, total: 0, pendientes: 0 };
  const tareas = data.tareas || [];

  // ── Header: anillo de progreso (mismo patrón donut de la app) + vencidos ──
  const C = 264;                                   // circunferencia r=42
  const off = C * (1 - (mes.pct || 0) / 100);
  const overdueCls = (R.vencidos > 0) ? '' : 'zero';
  const header = `
    <div class="mt-head">
      <svg width="92" height="92" viewBox="0 0 110 110">
        <circle cx="55" cy="55" r="42" fill="none" stroke="#152440" stroke-width="14"/>
        <circle cx="55" cy="55" r="42" fill="none" stroke="var(--cyan)" stroke-width="14"
                stroke-dasharray="${C}" stroke-dashoffset="${off}" stroke-linecap="round" transform="rotate(-90 55 55)"/>
        <text x="55" y="61" text-anchor="middle" font-size="22" font-weight="700" fill="#fff">${mes.pct || 0}%</text>
      </svg>
      <div class="mt-ring-txt">
        <span class="mt-ring-pct">Este mes</span>
        <span class="mt-ring-sub">${mes.completadas || 0} de ${mes.total || 0} completados · ${mes.pendientes || 0} pendientes</span>
      </div>
      <div class="mt-overdue ${overdueCls}">
        <div class="n">${R.vencidos || 0}</div>
        <div class="l">${R.vencidos === 1 ? 'vencido' : 'vencidos'}</div>
      </div>
    </div>
    <div style="display:flex;justify-content:flex-end;margin-bottom:10px">
      <button class="btn btn-ghost btn-sm" onclick="abrirAdhoc()"><i class="ti ti-plus"></i> Mantenimiento sin programar</button>
    </div>`;

  if (!tareas.length) {
    cont.innerHTML = header + '<div style="text-align:center;color:var(--text3);padding:26px">No tienes mantenimientos pendientes 🎉</div>';
    return;
  }

  // ── Agrupación por urgencia (cliente, desde fecha_programada vs hoy) ──
  const hoy = _hoyISO(), finSem = _finSemanaISO(hoy);
  const g = { venc: [], hoy: [], sem: [], later: [] };
  for (const t of tareas) {
    if (t.estado === 'en_ejecucion') { g.hoy.push(t); continue; }   // activo = más urgente
    const f = t.fecha_programada ? String(t.fecha_programada).slice(0,10) : null;
    if (!f) { g.later.push(t); }
    else if (f < hoy) { g.venc.push(t); }
    else if (f === hoy) { g.hoy.push(t); }
    else if (f <= finSem) { g.sem.push(t); }
    else { g.later.push(t); }
  }

  const grupos = [
    { key:'venc',  tit:'Vencidas',     cls:'venc', cardCls:'venc', prom:true,  items:g.venc },
    { key:'hoy',   tit:'Hoy',          cls:'hoy',  cardCls:'hoy',  prom:true,  items:g.hoy },
    { key:'sem',   tit:'Esta semana',  cls:'sem',  cardCls:'sem',  prom:false, items:g.sem },
    { key:'later', tit:'Más adelante', cls:'later',cardCls:'later',prom:false, items:g.later, collapsible:true },
  ];

  let html = header;
  for (const grp of grupos) {
    if (!grp.items.length) continue;
    const dim = grp.key === 'later' ? ' dim' : '';
    const collapsible = grp.collapsible;
    const open = !collapsible || _misLaterOpen;
    const head = collapsible
      ? `<div class="mt-group-head clickable" onclick="_misToggleLater()"><i class="ti ti-chevron-${open?'down':'right'}"></i> ${grp.tit} <span class="cnt">(${grp.items.length})</span></div>`
      : `<div class="mt-group-head" style="color:${grp.key==='venc'?'var(--red)':'var(--text2)'}">${grp.tit} <span class="cnt">(${grp.items.length})</span></div>`;
    const cards = open ? grp.items.map(t => _misCard(t, grp)).join('') : '';
    html += `<div class="mt-group${dim}">${head}${cards}</div>`;
  }
  cont.innerHTML = html;
}

function _misCard(t, grp) {
  const titulo = `${t.placa || '—'} · ${t.tipo_activo || ''} ${t.marca || ''}`.trim();
  const hoy = _hoyISO();
  const f = t.fecha_programada ? String(t.fecha_programada).slice(0,10) : null;
  let fechaTxt;
  if (t.estado === 'en_ejecucion') fechaTxt = '<span style="color:var(--cyan)">En ejecución</span>';
  else if (f && f < hoy) { const d = _diasEntre(f, hoy); fechaTxt = `<span style="color:var(--red)">Vencido hace ${d} día${d===1?'':'s'}</span>`; }
  else if (f) fechaTxt = `Programado: ${_fecha(f)}`;
  else fechaTxt = 'Sin fecha';

  const tenedor = t.activo_estado === 'asignado'
    ? `asignado a ${t.tenedor || '—'}`
    : (t.activo_estado === 'disponible' ? 'disponible' : (t.activo_estado || '—'));
  const age = t.ultimo_mantenimiento === 'Nunca' ? 'nunca mantenido' : (t.ultimo_mantenimiento || '').toLowerCase();

  // Botón principal por urgencia
  let mainBtn;
  if (t.estado === 'en_ejecucion') mainBtn = `<button class="btn btn-primary btn-sm" onclick="abrirEjecucion('${t.id}')">Continuar</button>`;
  else if (grp.prom) mainBtn = `<button class="btn btn-primary btn-sm" onclick="abrirEjecucion('${t.id}')">Iniciar</button>`;
  else mainBtn = `<button class="btn btn-ghost btn-sm" onclick="abrirEjecucion('${t.id}')">Ver</button>`;

  // "Cambiar fecha" solo para pendientes
  const reprog = t.estado === 'pendiente'
    ? `<button class="btn btn-ghost btn-sm" title="Cambiar fecha" onclick="reprogramarTarea('${t.id}','${f||''}')"><i class="ti ti-calendar"></i></button>`
    : '';

  return `<div class="mt-card ${grp.cardCls}">
    <div class="info">
      <div class="l1">${titulo}</div>
      <div class="l2">${fechaTxt} · ${tenedor} · <span title="Último mantenimiento del equipo">${age}</span></div>
    </div>
    <div class="acts">${reprog}${mainBtn}</div>
  </div>`;
}

function _misToggleLater() { _misLaterOpen = !_misLaterOpen; cargarMisTareas(); }

async function reprogramarTarea(tareaId, fechaActual) {
  const val = prompt('Nueva fecha (AAAA-MM-DD):', fechaActual || _hoyISO());
  if (val === null) return;
  const iso = val.trim();
  if (!/^\d{4}-\d{2}-\d{2}$/.test(iso)) { notif('Formato de fecha inválido (AAAA-MM-DD)', 'error'); return; }
  if (iso < _hoyISO() && !confirm('La fecha elegida está en el pasado. ¿Continuar de todos modos?')) return;
  const res = await apiRaw(`/mantenimiento/tareas/${tareaId}/reprogramar`, {
    method: 'POST', body: JSON.stringify({ fecha_programada: iso })
  });
  if (res.ok) { notif('Tarea reprogramada'); cargarMisTareas(); }
  else { const e = await res.json().catch(()=>({})); notif(e.detail || 'Error al reprogramar', 'error'); }
}

async function abrirEjecucion(tareaId) {
  const t = await api(`/mantenimiento/tareas/${tareaId}`);
  if (!t) { notif('No se pudo cargar la tarea', 'error'); return; }
  _ejecTarea = t;
  document.getElementById('ejec-tarea-id').value = t.id;
  const a = t.activo || {};
  document.getElementById('ejec-title').textContent = `Mantenimiento — ${a.placa || ''}`;
  document.getElementById('ejec-equipo-info').innerHTML =
    `<b>${a.placa || '—'}</b> · ${a.tipo_activo || ''} ${a.marca || ''} ${a.modelo || ''} · Serial: ${a.serial || '—'}<br>
     <span style="color:var(--text3)">Empresa: ${a.nombre_empresa || '—'} · Plan: ${t.plan_nombre || '—'}</span>`;
  const hint = document.getElementById('ejec-estado-hint');
  if (t.estado === 'en_ejecucion') {
    hint.style.display = ''; hint.innerHTML = '⚠ El equipo está <b>fuera de servicio</b> (mantenimiento preventivo) mientras ejecutas la tarea.';
  } else {
    hint.style.display = 'none';
  }
  document.getElementById('ejec-observaciones').value = t.observaciones || '';
  document.getElementById('ejec-acta-link').style.display = 'none';
  _ejecRenderChecklist(t);
  _ejecRenderFoot(t);
  const editable = t.estado === 'en_ejecucion';
  document.getElementById('ejec-observaciones').disabled = !editable;
  abrirModal('modal-ejec');
}

function _ejecRenderChecklist(t) {
  const cont = document.getElementById('ejec-checklist');
  const editable = t.estado === 'en_ejecucion';
  const items = t.checklist || [];
  let html = '';
  for (const sec of _SECC_ORDEN) {
    const its = items.filter(i => i.seccion === sec);
    if (!its.length) continue;
    html += `<div class="fsection">${_SECC_TIT[sec] || sec}</div>`;
    html += its.map(i => {
      if (i.tipo_item === 'dato') {
        return `<div class="frow"><div class="fgroup"><label>${i.texto}</label>
          <input class="finput ejec-item" data-id="${i.id}" data-tipo="dato" value="${(i.valor_dato||'').replace(/"/g,'&quot;')}" ${editable?'':'disabled'}></div></div>`;
      }
      const v = i.realizado === true ? 'si' : i.realizado === false ? 'no' : 'na';
      return `<div class="frow" style="align-items:center"><div class="fgroup" style="display:flex;justify-content:space-between;align-items:center;gap:10px">
        <label style="margin:0">${i.texto}</label>
        <select class="fselect ejec-item" data-id="${i.id}" data-tipo="check" style="max-width:110px" ${editable?'':'disabled'}>
          <option value="si"${v==='si'?' selected':''}>Sí</option>
          <option value="no"${v==='no'?' selected':''}>No</option>
          <option value="na"${v==='na'?' selected':''}>N/A</option>
        </select></div></div>`;
    }).join('');
  }
  cont.innerHTML = html || '<div style="color:var(--text3);font-size:12px">La tarea no tiene ítems de checklist.</div>';
}

function _ejecRenderFoot(t) {
  const foot = document.getElementById('ejec-foot');
  let btns = `<button class="btn btn-ghost" onclick="cerrarModal('modal-ejec')">Cerrar</button>`;
  if (t.estado === 'pendiente') {
    btns += `<button class="btn btn-primary" onclick="iniciarTarea()">Iniciar</button>`;
  } else if (t.estado === 'en_ejecucion') {
    btns += `<button class="btn btn-ghost" onclick="guardarAvance()">Guardar avance</button>
             <button class="btn btn-primary" onclick="finalizarTarea()">Finalizar y generar acta</button>`;
  }
  foot.innerHTML = btns;
}

function _ejecLeerChecklist() {
  return [...document.querySelectorAll('#ejec-checklist .ejec-item')].map(el => {
    const id = el.dataset.id;
    if (el.dataset.tipo === 'dato') return { id, valor_dato: el.value.trim() || null };
    const v = el.value;
    return { id, realizado: v === 'si' ? true : v === 'no' ? false : null };
  });
}

async function iniciarTarea() {
  const id = document.getElementById('ejec-tarea-id').value;
  const res = await apiRaw(`/mantenimiento/tareas/${id}/iniciar`, { method: 'POST' });
  if (!res.ok) { const e = await res.json().catch(()=>({})); notif(e.detail || 'Error al iniciar', 'error'); return; }
  notif('Mantenimiento iniciado — equipo fuera de servicio');
  await abrirEjecucion(id);   // recarga en modo ejecución
  cargarMisTareas();
}

async function guardarAvance() {
  const id = document.getElementById('ejec-tarea-id').value;
  const body = { items: _ejecLeerChecklist(), observaciones: document.getElementById('ejec-observaciones').value };
  const res = await apiRaw(`/mantenimiento/tareas/${id}/checklist`, { method: 'PUT', body: JSON.stringify(body) });
  if (res.ok) { notif('Avance guardado'); }
  else { const e = await res.json().catch(()=>({})); notif(e.detail || 'Error al guardar', 'error'); }
}

async function finalizarTarea() {
  const id = document.getElementById('ejec-tarea-id').value;
  if (!confirm('¿Finalizar el mantenimiento? El equipo volverá a su estado anterior y se generará el acta.')) return;
  const body = { items: _ejecLeerChecklist(), observaciones: document.getElementById('ejec-observaciones').value };
  const res = await apiRaw(`/mantenimiento/tareas/${id}/completar`, { method: 'POST', body: JSON.stringify(body) });
  if (!res.ok) { const e = await res.json().catch(()=>({})); notif(e.detail || 'Error al finalizar', 'error'); return; }
  const t = await res.json();
  notif('Mantenimiento completado — acta generada');
  if (t.orphans_cancelados > 0) {
    notif(`Se cancelaron ${t.orphans_cancelados} tarea(s) pendiente(s) de este equipo porque ya recibió mantenimiento`);
  }
  _ejecRenderFoot(t);
  document.getElementById('ejec-observaciones').disabled = true;
  document.querySelectorAll('#ejec-checklist .ejec-item').forEach(el => el.disabled = true);
  document.getElementById('ejec-estado-hint').style.display = 'none';
  const link = document.getElementById('ejec-acta-link');
  let extra = t.orphans_cancelados > 0
    ? `<div style="font-size:11px;color:var(--amber);margin-top:6px">Se cancelaron ${t.orphans_cancelados} tarea(s) pendiente(s) de este equipo.</div>` : '';
  if (t.url_acta_pdf) {
    link.style.display = '';
    link.innerHTML = `<button class="btn btn-ghost btn-sm" onclick="descargarActaMant('${t.id}')">📄 Ver acta generada</button>${extra}`;
  } else if (extra) {
    link.style.display = ''; link.innerHTML = extra;
  }
  cargarMisTareas();
}

// ── AD-HOC: mantenimiento sin programar ──
async function abrirAdhoc() {
  if (!hasPermiso('mantenimiento.ejecutar')) { notif('Sin permiso', 'error'); return; }
  document.getElementById('adhoc-search').value = '';
  await buscarAdhoc();
  abrirModal('modal-adhoc');
}

let _adhocTimer = null;
async function buscarAdhoc() {
  clearTimeout(_adhocTimer);
  _adhocTimer = setTimeout(async () => {
    const q = document.getElementById('adhoc-search').value.trim();
    const p = new URLSearchParams();
    if (q) p.set('q', q);
    const eq = await api(`/mantenimiento/adhoc/equipos?${p}`) || [];
    const tbody = document.getElementById('adhoc-results-body');
    if (!eq.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:var(--text3);padding:18px">Sin equipos elegibles</td></tr>';
      return;
    }
    tbody.innerHTML = eq.map(e => `
      <tr>
        <td><span class="mono-tag">${e.placa || '—'}</span></td>
        <td>${e.tipo_activo || '—'}</td>
        <td>${[e.marca, e.modelo].filter(Boolean).join(' ') || '—'}</td>
        <td style="font-size:11px">${e.estado}${e.tenedor ? ` · ${e.tenedor}` : ''}</td>
        <td><button class="btn btn-primary btn-sm" onclick="seleccionarAdhoc('${e.activo_id}')">Mantener</button></td>
      </tr>`).join('');
  }, 300);
}

async function seleccionarAdhoc(activoId) {
  const res = await apiRaw('/mantenimiento/tareas/adhoc', { method: 'POST', body: JSON.stringify({ activo_id: activoId }) });
  if (!res.ok) { const e = await res.json().catch(()=>({})); notif(e.detail || 'No se pudo crear el mantenimiento', 'error'); return; }
  const t = await res.json();
  cerrarModal('modal-adhoc');
  abrirEjecucion(t.id);   // abre la pantalla de ejecución (ya iniciada)
}

async function descargarActaMant(tareaId) {
  const res = await fetch(`${API}/mantenimiento/tareas/${tareaId}/acta`, { headers: { 'Authorization': `Bearer ${TOKEN}` } });
  if (!res.ok) { notif('No se pudo abrir el acta', 'error'); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  window.open(url, '_blank');
  setTimeout(() => URL.revokeObjectURL(url), 60000);
}

// ══ FASE 4a — CALENDARIO DEL PLANNER + REASIGNACIÓN ══════════════════════════
let _calInit = false;
let _calYear, _calMonth;          // month 0-based
let _calTareas = [];
let _calTecnicos = [];
let _calColors = {};              // tecnico_id → color
const _CAL_PALETTE = ['#06BFFF','#A78BFF','#FFB020','#00E5A0','#FF4D6D','#54A0FF','#F368E0','#26DE81','#FD9644','#45AAF2'];
const _CAL_MESES = ['Enero','Febrero','Marzo','Abril','Mayo','Junio','Julio','Agosto','Septiembre','Octubre','Noviembre','Diciembre'];

async function _initCalendario() {
  const hoy = new Date();
  _calYear = hoy.getFullYear(); _calMonth = hoy.getMonth();
  llenarSelectEmpresas('cal-filtro-empresa');
  const empSel = document.getElementById('cal-filtro-empresa');
  if (!empSel.querySelector('option[value=""]')) empSel.insertAdjacentHTML('afterbegin', '<option value="">Todas las empresas</option>');
  empSel.value = empresaActual || '';
  await _calCargarTecnicos();
  await cargarCalendario();
}

async function _calCargarTecnicos() {
  const p = new URLSearchParams();
  const emp = document.getElementById('cal-filtro-empresa')?.value;
  if (emp) p.set('empresa_id', emp);
  _calTecnicos = await api(`/mantenimiento/tecnicos?${p}`) || [];
  _calColors = {};
  _calTecnicos.forEach((t, i) => { _calColors[t.id] = _CAL_PALETTE[i % _CAL_PALETTE.length]; });
  // filtro de técnico
  const sel = document.getElementById('cal-filtro-tecnico');
  const prev = sel.value;
  sel.innerHTML = '<option value="">Todos los técnicos</option>' +
    _calTecnicos.map(t => `<option value="${t.id}">${t.nombre}</option>`).join('');
  sel.value = prev;
  // picker de reasignación
  const rsel = document.getElementById('calt-tecnico');
  if (rsel) rsel.innerHTML = '<option value="">Seleccionar...</option>' +
    _calTecnicos.map(t => `<option value="${t.id}">${t.nombre}</option>`).join('');
}

function _calBounds() {
  const desde = new Date(_calYear, _calMonth, 1);
  const hasta = new Date(_calYear, _calMonth + 1, 0);   // último día del mes
  const iso = d => `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
  return { desde: iso(desde), hasta: iso(hasta) };
}

async function cargarCalendario() {
  await _calCargarTecnicos();
  const { desde, hasta } = _calBounds();
  const p = new URLSearchParams({ desde, hasta });
  const emp = document.getElementById('cal-filtro-empresa')?.value;
  if (emp) p.set('empresa_id', emp);
  _calTareas = await api(`/mantenimiento/tareas?${p}`) || [];
  renderCalendario();
}

function calMes(delta) {
  _calMonth += delta;
  if (_calMonth < 0) { _calMonth = 11; _calYear--; }
  if (_calMonth > 11) { _calMonth = 0; _calYear++; }
  cargarCalendario();
}
function calHoy() { const h = new Date(); _calYear = h.getFullYear(); _calMonth = h.getMonth(); cargarCalendario(); }

function renderCalendario() {
  const grid = document.getElementById('cal-grid');
  if (!grid) return;
  document.getElementById('cal-mes-label').textContent = `${_CAL_MESES[_calMonth]} ${_calYear}`;

  const filtroTec = document.getElementById('cal-filtro-tecnico')?.value || '';
  const verCompletadas = document.getElementById('cal-show-completadas')?.checked;

  // tareas visibles: cancelada oculta; completada solo si toggle; filtro técnico
  const visibles = _calTareas.filter(t => {
    if (t.estado === 'cancelada') return false;
    if (t.estado === 'completada' && !verCompletadas) return false;
    if (filtroTec && t.tecnico_id !== filtroTec) return false;
    return t.fecha_programada;
  });
  // agrupar por día (YYYY-MM-DD)
  const porDia = {};
  visibles.forEach(t => { const k = String(t.fecha_programada).slice(0,10); (porDia[k] = porDia[k] || []).push(t); });

  // encabezados Lun–Dom (semana completa: 7 columnas) + celdas
  const dow = ['Lun','Mar','Mié','Jue','Vie','Sáb','Dom'];
  let html = dow.map(d => `<div class="cal-dow">${d}</div>`).join('');

  const primero = new Date(_calYear, _calMonth, 1);
  const ultimo = new Date(_calYear, _calMonth + 1, 0).getDate();
  const hoyISO = new Date().toISOString().slice(0,10);
  // blancos iniciales para alinear el día 1 a su columna (semana empieza en lunes)
  const firstWd = (primero.getDay() + 6) % 7;   // Lun=0 … Dom=6
  for (let i = 0; i < firstWd; i++) html += `<div class="cal-day empty"></div>`;

  let ultimoWd = firstWd;
  for (let d = 1; d <= ultimo; d++) {
    const wd = (new Date(_calYear, _calMonth, d).getDay() + 6) % 7;   // todos los días, incl. sáb/dom
    ultimoWd = wd;
    const iso = `${_calYear}-${String(_calMonth+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const chips = (porDia[iso] || []).map(t => {
      const col = _calColors[t.tecnico_id] || 'var(--text3)';
      const done = t.estado === 'completada' ? ' done' : '';
      return `<div class="cal-chip${done}" style="background:${col}" title="${t.placa} · ${t.tecnico || ''} · ${(t.estado||'').replace(/_/g,' ')}" onclick="abrirCalTarea('${t.id}')">${t.placa || '—'}</div>`;
    }).join('');
    const today = iso === hoyISO ? ' today' : '';
    html += `<div class="cal-day${today}"><div class="cal-day-num">${d}</div>${chips}</div>`;
  }
  // blancos finales para completar la última fila (7 columnas)
  for (let i = ultimoWd + 1; i < 7; i++) html += `<div class="cal-day empty"></div>`;
  grid.innerHTML = html;

  // leyenda (solo técnicos con tareas visibles este mes, o todos)
  const usados = new Set(visibles.map(t => t.tecnico_id));
  const leg = _calTecnicos.filter(t => usados.has(t.id));
  document.getElementById('cal-legend').innerHTML = (leg.length ? leg : _calTecnicos).map(t =>
    `<span class="lg"><span class="dot" style="background:${_calColors[t.id]}"></span>${t.nombre}</span>`).join('')
    || '<span style="font-size:12px;color:var(--text3)">Sin tareas este mes</span>';
}

function abrirCalTarea(tareaId) {
  const t = _calTareas.find(x => x.id === tareaId);
  if (!t) return;
  document.getElementById('calt-id').value = t.id;
  document.getElementById('calt-title').textContent = `Tarea — ${t.placa || ''}`;
  document.getElementById('calt-info').innerHTML =
    `<b>${t.placa || '—'}</b> · ${t.tipo_activo || ''} ${t.marca || ''}<br>
     Empresa: ${t.nombre_empresa || '—'}<br>
     Técnico: ${t.tecnico || '—'}<br>
     Fecha: ${t.fecha_programada ? _fecha(t.fecha_programada) : '—'}<br>
     Estado: ${_badge((t.estado||'').replace(/_/g,' '), t.estado==='completada'?'var(--green)':t.estado==='en_ejecucion'?'var(--cyan)':'var(--amber)')}<br>
     Plan: ${t.plan_nombre || '—'}`;
  // Reasignar/Reprogramar solo para pendientes
  const esPend = t.estado === 'pendiente';
  document.getElementById('calt-reasignar-wrap').style.display = esPend ? '' : 'none';
  document.getElementById('calt-reprog-wrap').style.display = esPend ? '' : 'none';
  const msg = document.getElementById('calt-msg');
  if (esPend) {
    document.getElementById('calt-tecnico').value = t.tecnico_id || '';
    document.getElementById('calt-fecha').value = t.fecha_programada ? String(t.fecha_programada).slice(0,10) : '';
    msg.style.display = 'none';
  } else {
    msg.style.display = ''; msg.textContent = 'Solo las tareas pendientes se pueden reasignar o reprogramar.';
  }
  abrirModal('modal-cal-tarea');
}

async function calReasignar() {
  const id = document.getElementById('calt-id').value;
  const tecnico_id = document.getElementById('calt-tecnico').value;
  if (!tecnico_id) { notif('Selecciona un técnico', 'error'); return; }
  const res = await apiRaw(`/mantenimiento/tareas/${id}/reasignar`, { method: 'POST', body: JSON.stringify({ tecnico_id }) });
  if (res.ok) { notif('Tarea reasignada'); cerrarModal('modal-cal-tarea'); cargarCalendario(); }
  else { const e = await res.json().catch(()=>({})); notif(e.detail || 'Error al reasignar', 'error'); }
}

async function calReprogramar() {
  const id = document.getElementById('calt-id').value;
  const fecha = document.getElementById('calt-fecha').value;
  if (!fecha) { notif('Elige una fecha', 'error'); return; }
  if (fecha < new Date().toISOString().slice(0,10) && !confirm('La fecha está en el pasado. ¿Continuar?')) return;
  const res = await apiRaw(`/mantenimiento/tareas/${id}/reprogramar`, { method: 'POST', body: JSON.stringify({ fecha_programada: fecha }) });
  if (res.ok) { notif('Tarea reprogramada'); cerrarModal('modal-cal-tarea'); cargarCalendario(); }
  else { const e = await res.json().catch(()=>({})); notif(e.detail || 'Error al reprogramar', 'error'); }
}

// ══════════════════════════════════════════════════════════
//  TABLEROS — analítica gerencial (solo lectura)
// ══════════════════════════════════════════════════════════
let _tablerosInit = false;
let _tableroSub = 'coordinacion';

function _initTableros() {
  llenarSelectEmpresas('tab-filtro-empresa');
  const sel = document.getElementById('tab-filtro-empresa');
  const empty = sel.querySelector('option[value=""]');
  if (empty) empty.textContent = 'Todas las empresas';
  sel.value = empresaActual || '';
  switchTablerosSub('coordinacion', document.querySelector('#tabs-tableros .tab'));
}

function switchTablerosSub(sub, el) {
  _tableroSub = sub;
  document.querySelectorAll('#tabs-tableros .tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  ['coordinacion', 'planificacion', 'parque'].forEach(s => {
    const p = document.getElementById('tablero-' + s);
    if (p) p.style.display = (s === sub) ? '' : 'none';
  });
  cargarTableroActual();
}

async function cargarTableroActual() {
  const sub = _tableroSub;
  const cont = document.getElementById('tablero-' + sub);
  if (!cont) return;
  const emp = document.getElementById('tab-filtro-empresa')?.value || '';
  const p = new URLSearchParams();
  if (emp) p.set('empresa_id', emp);
  cont.innerHTML = '<div class="tab-loading">Cargando tablero…</div>';
  const data = await api(`/mantenimiento/tableros/${sub}?${p}`);
  if (!data) { cont.innerHTML = '<div class="tab-empty">No se pudo cargar el tablero.</div>'; return; }
  if (sub === 'coordinacion') renderTabCoordinacion(cont, data);
  else if (sub === 'planificacion') renderTabPlanificacion(cont, data);
  else renderTabParque(cont, data);
}

// ── Helpers de gráficos (SVG/CSS hechos a mano, sin librería) ──
function _svgRing(pct, centerTxt) {
  const C = 264, off = C * (1 - (pct || 0) / 100);
  return `<svg width="120" height="120" viewBox="0 0 110 110">
    <circle cx="55" cy="55" r="42" fill="none" stroke="#152440" stroke-width="14"/>
    <circle cx="55" cy="55" r="42" fill="none" stroke="var(--cyan)" stroke-width="14"
      stroke-dasharray="${C}" stroke-dashoffset="${off}" stroke-linecap="round" transform="rotate(-90 55 55)"/>
    <text x="55" y="54" text-anchor="middle" font-size="24" font-weight="800" fill="#fff">${pct || 0}%</text>
    <text x="55" y="70" text-anchor="middle" font-size="9" fill="#6B9AB8">${centerTxt || ''}</text>
  </svg>`;
}

function _svgDonut(segments, centerTop, centerBot) {
  const C = 264, r = 42;
  const total = segments.reduce((s, x) => s + x.value, 0);
  let acc = 0, arcs = '';
  segments.forEach(sg => {
    if (sg.value <= 0) return;
    const len = C * sg.value / total;
    arcs += `<circle cx="55" cy="55" r="${r}" fill="none" stroke="${sg.color}" stroke-width="14"
      stroke-dasharray="${len} ${C - len}" stroke-dashoffset="${-acc}" transform="rotate(-90 55 55)"/>`;
    acc += len;
  });
  return `<svg width="120" height="120" viewBox="0 0 110 110">
    <circle cx="55" cy="55" r="${r}" fill="none" stroke="#152440" stroke-width="14"/>
    ${arcs}
    <text x="55" y="53" text-anchor="middle" font-size="22" font-weight="800" fill="#fff">${centerTop != null ? centerTop : total}</text>
    <text x="55" y="70" text-anchor="middle" font-size="9" fill="#6B9AB8">${centerBot || ''}</text>
  </svg>`;
}

function _donutLegend(items) {
  return `<div class="donut-legend">${items.map(i => `
    <div class="li"><span class="dot" style="background:${i.color}"></span>${i.label}<span class="lv">${i.value}</span></div>`).join('')}</div>`;
}

function _donutCard(title, segments, centerBot) {
  const total = segments.reduce((s, x) => s + x.value, 0);
  const body = total > 0
    ? `<div class="donut-wrap">${_svgDonut(segments, total, centerBot)}${_donutLegend(segments)}</div>`
    : `<div class="tab-empty">Sin datos aún</div>`;
  return `<div class="tab-card"><h4>${title}</h4>${body}</div>`;
}

function _barRows(items, color, opts) {
  opts = opts || {};
  if (!items || !items.length) return `<div class="tab-empty">${opts.empty || 'Sin datos aún'}</div>`;
  const scaleMax = opts.scaleMax || Math.max(...items.map(i => i.n), 1);
  const unit = opts.unit || '';
  return items.map(i => `<div class="bar-row">
    <span class="bl" title="${i.label}">${i.label}</span>
    <span class="bt"><span class="bf" style="width:${Math.round(100 * i.n / scaleMax)}%;background:${color}"></span></span>
    <span class="bv">${i.n}${unit}</span></div>`).join('');
}

function _svgTrend(points) {
  if (!points || !points.length) return `<div class="tab-empty">Sin datos aún</div>`;
  const W = 560, H = 130, pad = 26, n = points.length;
  const x = i => pad + (n === 1 ? 0 : i * (W - 2 * pad) / (n - 1));
  const y = v => H - pad - (v / 100) * (H - 2 * pad);
  const line = points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.pct).toFixed(1)}`).join(' ');
  const dots = points.map((p, i) => `<circle cx="${x(i).toFixed(1)}" cy="${y(p.pct).toFixed(1)}" r="3" fill="var(--cyan)"><title>${p.mes}: ${p.pct}%</title></circle>`).join('');
  const labels = points.map((p, i) => (i % 2 === 0) ? `<text x="${x(i).toFixed(1)}" y="${H - 8}" text-anchor="middle" font-size="8" fill="#344E66">${p.mes.slice(2)}</text>` : '').join('');
  const grid = [0, 50, 100].map(v => `<line x1="${pad}" y1="${y(v)}" x2="${W - pad}" y2="${y(v)}" stroke="#152440"/><text x="${pad - 4}" y="${y(v) + 3}" text-anchor="end" font-size="8" fill="#344E66">${v}</text>`).join('');
  return `<svg width="100%" viewBox="0 0 ${W} ${H}" style="max-height:170px">
    ${grid}
    <path d="${line}" fill="none" stroke="var(--cyan)" stroke-width="2"/>
    ${dots}${labels}
  </svg>`;
}

// ── Renderers por sub-tab ──
function renderTabCoordinacion(cont, d) {
  const ring = `<div class="tab-card"><h4>Cobertura del parque</h4>
    <div style="display:flex;align-items:center;gap:16px">
      ${_svgRing(d.cobertura_pct, 'al día')}
      <div style="font-size:12px;color:var(--text2);line-height:1.9">
        <div><strong style="color:var(--text);font-size:15px">${d.total_con_plan}</strong> equipos con plan</div>
        <div style="color:var(--green)">${d.al_dia + d.por_vencer} al día (últ. &lt; periodicidad)</div>
        <div style="color:var(--red)">${d.vencidos} vencidos o sin preventivo</div>
      </div>
    </div></div>`;

  const semaforo = `<div class="tab-card"><h4>Semáforo</h4>
    <div class="semaforo">
      <div class="sem-item" style="border-color:rgba(0,229,160,0.35)"><div class="n" style="color:var(--green)">${d.al_dia}</div><div class="l">Al día</div></div>
      <div class="sem-item" style="border-color:rgba(255,176,32,0.35)"><div class="n" style="color:var(--amber)">${d.por_vencer}</div><div class="l">Por vencer &le;60d</div></div>
      <div class="sem-item" style="border-color:rgba(255,77,109,0.35)"><div class="n" style="color:var(--red)">${d.vencidos}</div><div class="l">Vencidos / nunca</div></div>
    </div></div>`;

  const trend = `<div class="tab-card wide"><h4>Tendencia de cobertura (12 meses)</h4>
    ${_svgTrend(d.tendencia)}
    <div class="tc-cap">Sobre la flota mantenible de hoy: qué parte tenía un preventivo válido a cada fin de mes. La composición de flota se mantiene constante (no se versiona la historia de planes).</div></div>`;

  const porEmp = `<div class="tab-card"><h4>Cobertura por empresa</h4>
    ${_barRows((d.por_empresa || []).map(e => ({ label: `${e.empresa} (${e.equipos})`, n: e.pct })), 'var(--cyan)', { unit: '%', scaleMax: 100 })}</div>`;

  const ola = `<div class="tab-card"><h4>Próxima ola de vencimientos</h4>
    ${_barRows([
      { label: '≤ 30 días', n: d.proxima_ola.d30 },
      { label: '31 – 60 días', n: d.proxima_ola.d60 },
      { label: '61 – 90 días', n: d.proxima_ola.d90 },
    ], 'var(--amber)', { empty: 'Nada por vencer en 90 días' })}</div>`;

  cont.innerHTML = `<div class="tab-grid">${ring}${semaforo}${trend}${porEmp}${ola}</div>`;
}

function renderTabPlanificacion(cont, d) {
  const carga = `<div class="tab-card"><h4>Carga por técnico (pendientes)</h4>
    ${_barRows((d.carga || []).map(x => ({ label: x.tecnico, n: x.n })), 'var(--cyan)')}</div>`;
  const vencidas = `<div class="tab-card"><h4>Vencidas por técnico</h4>
    ${_barRows((d.vencidas || []).map(x => ({ label: x.tecnico, n: x.n })), 'var(--red)', { empty: 'Sin tareas vencidas 🎉' })}</div>`;
  const pipeline = _donutCard('Pipeline (por estado)', [
    { label: 'Pendiente', color: 'var(--amber)', value: d.pipeline.pendiente || 0 },
    { label: 'En ejecución', color: 'var(--cyan)', value: d.pipeline.en_ejecucion || 0 },
    { label: 'Completada', color: 'var(--green)', value: d.pipeline.completada || 0 },
    { label: 'Cancelada', color: '#344E66', value: d.pipeline.cancelada || 0 },
  ], 'tareas');
  const comp = `<div class="tab-card"><h4>Completados este mes</h4>
    ${_barRows((d.completados_mes || []).map(x => ({ label: x.tecnico, n: x.n })), 'var(--green)', { empty: 'Ninguno completado este mes aún' })}</div>`;
  const origen = _donutCard('Origen de tareas', [
    { label: 'Planificación', color: 'var(--cyan)', value: d.origen.planificacion || 0 },
    { label: 'Devolución', color: 'var(--purple)', value: d.origen.devolucion || 0 },
    { label: 'Ad-hoc', color: 'var(--amber)', value: d.origen.adhoc || 0 },
  ], 'tareas');
  cont.innerHTML = `<div class="tab-grid">${carga}${vencidas}${pipeline}${comp}${origen}</div>`;
}

function renderTabParque(cont, d) {
  const tipos = d.por_tipo || [];
  const stack = tipos.length
    ? tipos.map(t => {
        const tot = (t.al_dia + t.por_vencer + t.vencido) || 1;
        const seg = (v, c) => v > 0 ? `<span style="width:${100 * v / tot}%;background:${c}"></span>` : '';
        return `<div class="stack-row"><span class="bl" title="${t.tipo}">${t.tipo}</span>
          <span class="stack-track">${seg(t.al_dia, 'var(--green)')}${seg(t.por_vencer, 'var(--amber)')}${seg(t.vencido, 'var(--red)')}</span>
          <span class="bv">${t.al_dia + t.por_vencer + t.vencido}</span></div>`;
      }).join('') +
      `<div class="cal-legend" style="margin-top:10px"><span><span class="dot" style="background:var(--green)"></span>Al día</span><span><span class="dot" style="background:var(--amber)"></span>Por vencer</span><span><span class="dot" style="background:var(--red)"></span>Vencido/nunca</span></div>`
    : '<div class="tab-empty">Sin datos aún</div>';
  const porTipo = `<div class="tab-card wide"><h4>Equipos por tipo</h4>${stack}</div>`;

  const cobertura = _donutCard('Cobertura de planes', [
    { label: 'Con plan', color: 'var(--green)', value: d.cobertura_planes.con_plan || 0 },
    { label: 'Sin plan', color: '#344E66', value: d.cobertura_planes.sin_plan || 0 },
  ], 'equipos');

  const antig = `<div class="tab-card"><h4>Antigüedad del último preventivo</h4>
    ${_barRows((d.antiguedad || []).map(b => ({ label: b.bucket + ' meses', n: b.n })), 'var(--purple)')}</div>`;

  const top = (d.top_atrasados && d.top_atrasados.length)
    ? `<div class="top-list">${d.top_atrasados.map(x => `<div class="top-item">
        <span class="mono-tag">${x.placa || '—'}</span>
        <span style="color:var(--text2)">${x.tipo || ''}</span>
        <span class="ti-meses">${x.meses == null ? 'nunca' : x.meses + ' m'}</span></div>`).join('')}</div>`
    : '<div class="tab-empty">Sin datos aún</div>';
  const topCard = `<div class="tab-card"><h4>Top 10 más atrasados</h4>${top}</div>`;

  const filas = (d.por_empresa || []).map(e => `<tr><td>${e.empresa}</td><td>${e.equipos}</td><td style="color:${e.vencidos ? 'var(--red)' : 'var(--text)'}">${e.vencidos}</td><td>${e.cobertura_pct}%</td></tr>`).join('');
  const tabla = `<div class="tab-card wide"><h4>Resumen por empresa</h4>
    ${filas ? `<table class="tab-table"><thead><tr><th>Empresa</th><th>Equipos con plan</th><th>Vencidos</th><th>Cobertura</th></tr></thead><tbody>${filas}</tbody></table>` : '<div class="tab-empty">Sin datos aún</div>'}</div>`;

  cont.innerHTML = `<div class="tab-grid">${porTipo}${cobertura}${antig}${topCard}${tabla}</div>`;
}
