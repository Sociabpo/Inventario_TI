// ── Módulo Compras y Facturas ─────────────────────────────────────────────────

let comprasCache = { solicitudes: [], ordenes: [], facturas: [], contratos: [], recepciones: [] };
let comprasStats = {};
let proveedoresCache = [];
let comprasTab = 'solicitudes';

const EST_SOL = {
  borrador:              { txt: 'Borrador',        c: 'var(--text3)' },
  pendiente_aprobacion:  { txt: 'Pend. aprobación', c: 'var(--amber)' },
  aprobada:              { txt: 'Aprobada',        c: 'var(--green)' },
  rechazada:             { txt: 'Rechazada',       c: 'var(--red)' },
  en_proceso:            { txt: 'En proceso',      c: 'var(--cyan)' },
  recibida:              { txt: 'Recibida',        c: '#2dd4bf' },
  completada:            { txt: 'Completada',      c: 'var(--purple)' },
  cancelada:             { txt: 'Cancelada',       c: 'var(--text3)' },
};

function _badge(txt, color) {
  return `<span class="badge" style="background:${color}22;color:${color};border:1px solid ${color}55">${txt}</span>`;
}
function _money(v) {
  if (v == null) return '—';
  return '$' + Number(v).toLocaleString('es-CO');
}
function _fecha(v) { return v ? (typeof fFecha === 'function' ? fFecha(v) : String(v).slice(0, 10)) : '—'; }

// ── Carga principal ─────────────────────────────────────────────────────────
async function cargarCompras() {
  await cargarStatsCompras();
  await cargarProveedores();
  switchComprasTab(comprasTab, document.querySelector(`#tabs-compras .tab[data-tab="${comprasTab}"]`));
}

async function cargarStatsCompras() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  const s = await api(`/compras/stats?${p}`);
  if (!s) return;
  comprasStats = s;
  const chips = [
    { id: 'solicitudes_pendientes_aprobacion', label: 'Solicitudes por aprobar', warn: s.solicitudes_pendientes_aprobacion > 0 },
    { id: 'ordenes_pendientes_recepcion',      label: 'OC por recibir',          warn: s.ordenes_pendientes_recepcion > 0 },
    { id: 'facturas_por_vencer',               label: 'Facturas por vencer',     warn: s.facturas_por_vencer > 0 },
    { id: 'facturas_vencidas',                 label: 'Facturas vencidas',       danger: s.facturas_vencidas > 0 },
    { id: 'contratos_por_vencer',              label: 'Alquileres por vencer',   warn: s.contratos_por_vencer > 0 },
    { id: 'equipos_en_alquiler',               label: 'Equipos en alquiler',     val: s.equipos_en_alquiler },
    { id: 'total_compras_mes',                 label: 'Compras del mes',         money: true },
  ];
  const cont = document.getElementById('compras-stats');
  if (!cont) return;
  cont.innerHTML = chips.map(ch => {
    const valor = ch.money ? _money(s.total_compras_mes) : (s[ch.id] ?? 0);
    const col = ch.danger ? 'var(--red)' : (ch.warn ? 'var(--amber)' : 'var(--cyan)');
    return `<div class="compra-chip" style="border-color:${col}44">
      <div class="compra-chip-val" style="color:${col}">${valor}</div>
      <div class="compra-chip-lbl">${ch.label}</div>
    </div>`;
  }).join('');
}

async function cargarProveedores() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  proveedoresCache = await api(`/compras/proveedores?${p}`) || [];
}

function switchComprasTab(tab, el) {
  comprasTab = tab;
  document.querySelectorAll('#tabs-compras .tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  document.querySelectorAll('.compras-panel').forEach(p => p.style.display = 'none');
  const panel = document.getElementById(`compras-panel-${tab}`);
  if (panel) panel.style.display = '';
  ({
    solicitudes: cargarSolicitudes, ordenes: cargarOrdenes, facturas: cargarFacturas,
    recepciones: cargarRecepciones, contratos: cargarContratos,
  }[tab] || (() => {}))();
}

// ══ SOLICITUDES ══════════════════════════════════════════════════════════════
async function cargarSolicitudes() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  comprasCache.solicitudes = await api(`/compras/solicitudes?${p}`) || [];
  buscarSolicitudes();
}

function buscarSolicitudes() {
  const q = (document.getElementById('search-solicitudes')?.value || '').toLowerCase().trim();
  let list = comprasCache.solicitudes;
  if (q) list = list.filter(s =>
    (s.numero_solicitud || '').toLowerCase().includes(q) ||
    (s.titulo || '').toLowerCase().includes(q) ||
    (s.justificacion || '').toLowerCase().includes(q) ||
    (s.solicitante || '').toLowerCase().includes(q));
  renderSolicitudes(list);
}

function renderSolicitudes(list) {
  const tbody = document.getElementById('tbl-solicitudes-body');
  if (!tbody) return;
  if (!list.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:22px">Sin solicitudes</td></tr>'; return; }
  const puedeAprobar = hasPermiso('compras.aprobar');
  const puedeCrear = hasPermiso('compras.crear_solicitud');
  tbody.innerHTML = list.map(s => {
    const est = EST_SOL[s.estado] || { txt: s.estado, c: 'var(--text3)' };
    const verBtn = `<button class="btn btn-ghost btn-sm" onclick="verSolicitud('${s.id}')">👁 Ver</button>`;
    let acc = '';
    if (s.estado === 'borrador' && puedeCrear)
      acc = `<button class="btn btn-ghost btn-sm" style="color:var(--amber);border-color:rgba(255,176,32,.3)" onclick="enviarSolicitud('${s.id}')">Enviar a aprobación</button>`;
    else if (s.estado === 'pendiente_aprobacion' && puedeAprobar)
      acc = `<button class="btn btn-ghost btn-sm" style="color:var(--green);border-color:rgba(0,229,160,.3)" onclick="aprobarSolicitud('${s.id}')">Aprobar</button>
             <button class="btn btn-ghost btn-sm" style="color:var(--red);border-color:rgba(255,77,109,.3)" onclick="rechazarSolicitud('${s.id}')">Rechazar</button>`;
    else if (s.estado === 'aprobada' && puedeCrear)
      acc = `<button class="btn btn-ghost btn-sm" style="color:var(--cyan);border-color:rgba(var(--accent-rgb),.3)" onclick="abrirModalOrden('${s.id}')">Crear OC</button>`;
    // Cancelar disponible en borrador / pendiente_aprobacion
    if (['borrador', 'pendiente_aprobacion'].includes(s.estado) && puedeCrear)
      acc += ` <button class="btn btn-ghost btn-sm" style="color:var(--text3)" onclick="cancelarSolicitud('${s.id}')">Cancelar</button>`;
    return `<tr>
      <td><span class="mono-tag">${s.numero_solicitud || '—'}</span><div class="td-sub" style="font-size:10px">${_fecha(s.created_at)}</div></td>
      <td><div class="td-name">${s.titulo || '—'}</div><div class="td-sub" style="max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${s.justificacion || ''}</div></td>
      <td><div class="td-sub">${s.nombre_empresa || '—'}</div>${(s.sede || s.area) ? `<div class="td-sub" style="font-size:10px;color:var(--text3)">${[s.sede, s.area].filter(Boolean).join(' · ')}</div>` : ''}</td>
      <td><div class="td-sub">${s.solicitante || '—'}</div></td>
      <td style="text-align:center"><span class="mono-tag">${s.items_count}</span></td>
      <td>${_badge(est.txt, est.c)}</td>
      <td style="white-space:nowrap">${verBtn} ${acc}</td>
    </tr>`;
  }).join('');
}

// items dinámicos en el modal de solicitud (acepta un ítem para precargar en edición)
function _filaItemSolicitud(it) {
  const d = it || {};
  const sel = (a, b) => a === b ? ' selected' : '';
  const dsc = (d.descripcion || '').replace(/"/g, '&quot;');
  const val = (d.valor_unitario_estimado != null) ? d.valor_unitario_estimado : '';
  return `<div class="sol-item-row" style="display:grid;grid-template-columns:2fr 1fr 1fr .7fr 1fr auto;gap:6px;align-items:center;margin-bottom:6px">
    <input class="finput sol-it-desc" placeholder="Descripción" value="${dsc}">
    <select class="fselect sol-it-tipoitem"><option value="activo"${sel(d.tipo_item, 'activo')}>Activo</option><option value="accesorio"${sel(d.tipo_item, 'accesorio')}>Accesorio</option></select>
    <select class="fselect sol-it-adq"><option value="compra"${sel(d.tipo_adquisicion, 'compra')}>Compra</option><option value="alquiler"${sel(d.tipo_adquisicion, 'alquiler')}>Alquiler</option></select>
    <input class="finput sol-it-cant" type="number" min="1" value="${d.cantidad || 1}" placeholder="Cant">
    <input class="finput sol-it-val" type="number" min="0" step="0.01" value="${val}" placeholder="Valor unit.">
    <button type="button" class="btn btn-ghost btn-sm" style="color:var(--red)" onclick="this.closest('.sol-item-row').remove()">×</button>
  </div>`;
}
function agregarItemSolicitud() {
  document.getElementById('sol-items-container').insertAdjacentHTML('beforeend', _filaItemSolicitud());
}
// Carga los dropdowns de Sede/Área con el catálogo de la empresa seleccionada.
// Se llama al abrir/editar y cuando cambia la empresa (onchange).
function refrescarSedeAreaSolicitud(sedeActual, areaActual) {
  const empresaId = document.getElementById('sol-empresa').value;
  llenarSelectCatalogoEmpresa('sol-sede', 'sede', empresaId, sedeActual, 'sol-sede-hint');
  llenarSelectCatalogoEmpresa('sol-area', 'area', empresaId, areaActual, 'sol-area-hint');
}

function abrirModalSolicitud() {
  if (!hasPermiso('compras.crear_solicitud')) { notif('Sin permiso para crear solicitudes', 'error'); return; }
  document.getElementById('sol-id').value = '';
  document.getElementById('modal-sol-title').textContent = 'Nueva solicitud de compra';
  const empSel = document.getElementById('sol-empresa');
  empSel.disabled = false;
  llenarSelectEmpresas('sol-empresa');
  if (empresaActual) empSel.value = empresaActual;
  document.getElementById('sol-titulo').value = '';
  document.getElementById('sol-justificacion').value = '';
  document.getElementById('sol-observaciones').value = '';
  document.getElementById('sol-items-container').innerHTML = _filaItemSolicitud();
  refrescarSedeAreaSolicitud();
  abrirModal('modal-solicitud');
}
async function editarSolicitud(id) {
  const s = await api(`/compras/solicitudes/${id}`);
  if (!s) { notif('No se pudo cargar la solicitud', 'error'); return; }
  cerrarModal('modal-solicitud-detalle');
  document.getElementById('sol-id').value = s.id;
  document.getElementById('modal-sol-title').textContent = 'Editar solicitud';
  const empSel = document.getElementById('sol-empresa');
  llenarSelectEmpresas('sol-empresa');
  empSel.value = s.empresa_id;
  empSel.disabled = true;   // la empresa no se cambia al editar
  document.getElementById('sol-titulo').value = s.titulo || '';
  document.getElementById('sol-justificacion').value = s.justificacion || '';
  document.getElementById('sol-observaciones').value = s.observaciones || '';
  refrescarSedeAreaSolicitud(s.sede, s.area);   // prefill sede/area de la empresa
  document.getElementById('sol-items-container').innerHTML =
    (s.items && s.items.length ? s.items.map(it => _filaItemSolicitud(it)).join('') : _filaItemSolicitud());
  abrirModal('modal-solicitud');
}
async function guardarSolicitud() {
  const id = document.getElementById('sol-id').value;
  const empresa_id = document.getElementById('sol-empresa').value;
  const titulo = document.getElementById('sol-titulo').value.trim();
  const justificacion = document.getElementById('sol-justificacion').value.trim();
  const sede = document.getElementById('sol-sede').value;
  const area = document.getElementById('sol-area').value;
  if (!titulo) { notif('El título es obligatorio', 'error'); return; }
  if (!justificacion || (!id && !empresa_id)) { notif('Empresa y justificación son obligatorias', 'error'); return; }
  if (!sede) { notif('La sede es obligatoria', 'error'); return; }
  if (!area) { notif('El área es obligatoria', 'error'); return; }
  const items = [...document.querySelectorAll('#sol-items-container .sol-item-row')].map(r => ({
    descripcion: r.querySelector('.sol-it-desc').value.trim(),
    tipo_item: r.querySelector('.sol-it-tipoitem').value,
    tipo_adquisicion: r.querySelector('.sol-it-adq').value,
    cantidad: parseInt(r.querySelector('.sol-it-cant').value) || 1,
    valor_unitario_estimado: r.querySelector('.sol-it-val').value ? parseFloat(r.querySelector('.sol-it-val').value) : null,
  })).filter(i => i.descripcion);
  if (!items.length) { notif('Agrega al menos un ítem', 'error'); return; }
  const observaciones = document.getElementById('sol-observaciones').value || null;
  let res;
  if (id) {
    res = await apiRaw(`/compras/solicitudes/${id}`, { method: 'PUT', body: JSON.stringify({ titulo, justificacion, sede, area, observaciones, items }) });
  } else {
    res = await apiRaw('/compras/solicitudes', { method: 'POST', body: JSON.stringify({ empresa_id, titulo, justificacion, sede, area, observaciones, items }) });
  }
  if (res.ok) { notif(id ? 'Solicitud actualizada' : 'Solicitud creada'); cerrarModal('modal-solicitud'); cargarSolicitudes(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error al guardar', 'error'); }
}

async function cancelarSolicitud(id) {
  const motivo = prompt('Motivo de la cancelación:');
  if (motivo == null || !motivo.trim()) return;
  const res = await apiRaw(`/compras/solicitudes/${id}/cancelar`, { method: 'POST', body: JSON.stringify({ motivo_cancelacion: motivo.trim() }) });
  if (res.ok) { notif('Solicitud cancelada'); cerrarModal('modal-solicitud-detalle'); cargarSolicitudes(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

// Ver detalle de la solicitud (qué se está solicitando) + acciones contextuales
async function verSolicitud(id) {
  const s = await api(`/compras/solicitudes/${id}`);
  if (!s) { notif('No se pudo cargar la solicitud', 'error'); return; }
  const est = EST_SOL[s.estado] || { txt: s.estado, c: 'var(--text3)' };
  const items = s.items || [];
  const filas = items.map(it => `<tr>
      <td>${it.descripcion || ''}</td>
      <td style="text-transform:capitalize">${it.tipo_item || ''}</td>
      <td style="text-transform:capitalize">${it.tipo_adquisicion || ''}</td>
      <td style="text-align:center">${it.cantidad}</td>
      <td style="text-align:right">${_money(it.valor_unitario_estimado)}</td>
      <td style="text-align:right">${_money((it.valor_unitario_estimado || 0) * (it.cantidad || 1))}</td>
    </tr>`).join('') || '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:14px">Sin ítems</td></tr>';
  const total = items.reduce((a, it) => a + (it.valor_unitario_estimado || 0) * (it.cantidad || 1), 0);
  document.getElementById('sol-detalle-body').innerHTML = `
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px">
      <span class="mono-tag">${s.numero_solicitud || '—'}</span>
      <span style="font-size:15px;font-weight:700;color:var(--text)">${s.titulo || '—'}</span>
    </div>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">
      <div><div class="seb-label">Empresa</div><div style="font-size:13px">${s.nombre_empresa || '—'}</div></div>
      <div><div class="seb-label">Solicitante</div><div style="font-size:13px">${s.solicitante || '—'}</div></div>
      <div><div class="seb-label">Sede</div><div style="font-size:13px">${s.sede || '—'}</div></div>
      <div><div class="seb-label">Área</div><div style="font-size:13px">${s.area || '—'}</div></div>
      <div><div class="seb-label">Estado</div><div>${_badge(est.txt, est.c)}</div></div>
      <div><div class="seb-label">Fecha</div><div style="font-size:13px">${_fecha(s.created_at)}</div></div>
      ${s.aprobado_por ? `<div><div class="seb-label">Aprobado/revisado por</div><div style="font-size:13px">${s.aprobado_por}</div></div>` : ''}
      ${(s.ordenes && s.ordenes.length) ? `<div><div class="seb-label">Orden(es) de compra</div><div style="font-size:13px">${s.ordenes.map(o => `<span class="mono-tag">${o.numero_oc || o.id.slice(0,8)}</span>`).join(' ')}</div></div>` : ''}
    </div>
    <div style="margin-bottom:10px"><div class="seb-label">Justificación</div><div style="font-size:13px;color:var(--text)">${s.justificacion || '—'}</div></div>
    ${s.observaciones ? `<div style="margin-bottom:10px"><div class="seb-label">Observaciones</div><div style="font-size:13px">${s.observaciones}</div></div>` : ''}
    ${s.motivo_rechazo ? `<div style="margin-bottom:10px"><div class="seb-label" style="color:var(--red)">Motivo de rechazo</div><div style="font-size:13px;color:var(--red)">${s.motivo_rechazo}</div></div>` : ''}
    ${s.motivo_cancelacion ? `<div style="margin-bottom:10px"><div class="seb-label" style="color:var(--text3)">Motivo de cancelación</div><div style="font-size:13px;color:var(--text2)">${s.motivo_cancelacion}</div></div>` : ''}
    <div class="seb-label" style="margin-bottom:6px">Ítems solicitados (${items.length})</div>
    <table class="tbl"><thead><tr><th>Descripción</th><th>Tipo</th><th>Adquisición</th><th>Cant.</th><th style="text-align:right">Valor unit.</th><th style="text-align:right">Subtotal</th></tr></thead>
      <tbody>${filas}</tbody></table>
    <div style="text-align:right;margin-top:8px;font-size:12px;color:var(--text2)">Total estimado: <strong style="color:var(--cyan)">${_money(total)}</strong></div>
    ${_cotizacionesSectionHTML(s)}`;

  const puedeAprobar = hasPermiso('compras.aprobar');
  const puedeCrear = hasPermiso('compras.crear_solicitud');
  const editable = ['borrador', 'pendiente_aprobacion', 'aprobada'].includes(s.estado);
  let acc = '';
  if (editable && (puedeCrear || puedeAprobar))
    acc += `<button class="btn btn-ghost" onclick="editarSolicitud('${s.id}')">✎ Editar</button>`;
  if (s.estado === 'borrador' && puedeCrear) {
    if (s.tiene_ganadora)
      acc += `<button class="btn btn-primary" onclick="_accDetalle(enviarSolicitud,'${s.id}')">Enviar a aprobación</button>`;
    else
      acc += `<button class="btn btn-primary" disabled title="Agrega al menos una cotización y marca la ganadora antes de enviar" style="opacity:.5;cursor:not-allowed">Enviar a aprobación</button>`;
  }
  if (s.estado === 'pendiente_aprobacion' && puedeAprobar)
    acc += `<button class="btn btn-ghost" style="color:var(--red);border-color:rgba(255,77,109,.3)" onclick="_accDetalle(rechazarSolicitud,'${s.id}')">Rechazar</button>
            <button class="btn btn-primary" onclick="_accDetalle(aprobarSolicitud,'${s.id}')">Aprobar</button>`;
  if (s.estado === 'aprobada' && puedeCrear)
    acc += `<button class="btn btn-primary" onclick="cerrarModal('modal-solicitud-detalle');abrirModalOrden('${s.id}')">Crear OC</button>`;
  // Marcar completada manualmente (recursos creados fuera del módulo de compras)
  if (['recibida', 'en_proceso', 'aprobada'].includes(s.estado) && puedeCrear)
    acc += `<button class="btn btn-ghost" style="color:var(--purple);border-color:rgba(167,139,255,.3)" onclick="_accDetalle(completarSolicitud,'${s.id}')">Marcar como completada</button>`;
  if (['borrador', 'pendiente_aprobacion'].includes(s.estado) && puedeCrear)
    acc += `<button class="btn btn-ghost" style="color:var(--text3)" onclick="cancelarSolicitud('${s.id}')">Cancelar solicitud</button>`;
  document.getElementById('sol-detalle-acciones').innerHTML = acc;
  abrirModal('modal-solicitud-detalle');
}
function _accDetalle(fn, id) { cerrarModal('modal-solicitud-detalle'); fn(id); }

// ══ COTIZACIONES ═════════════════════════════════════════════════════════════
// Sección de cotizaciones dentro del detalle de la solicitud.
function _cotizacionesSectionHTML(s) {
  const cots = s.cotizaciones || [];
  const puedeCrear = hasPermiso('compras.crear_solicitud');
  const esBorrador = s.estado === 'borrador';
  const addBtn = (puedeCrear && esBorrador)
    ? `<button class="btn btn-ghost btn-sm" onclick="abrirModalCotizacion('${s.id}','${s.empresa_id}')">+ Agregar cotización</button>` : '';

  let filas;
  if (!cots.length) {
    filas = `<div style="font-size:12px;color:var(--text3);padding:10px 0">Sin cotizaciones. ${esBorrador ? 'Agrega al menos una y marca la ganadora antes de enviar a aprobación.' : ''}</div>`;
  } else {
    filas = cots.map(c => {
      const gan = c.es_ganadora
        ? `<span class="badge" style="background:var(--green)22;color:var(--green);border:1px solid var(--green)55">★ Ganadora</span>`
        : (puedeCrear && esBorrador ? `<button class="btn btn-ghost btn-sm" onclick="marcarGanadora('${c.id}','${s.id}')">Marcar ganadora</button>` : '');
      let ver;
      if (!c.tiene_archivo) {
        ver = '<span style="color:var(--text3);font-size:11px">sin adjunto</span>';
      } else {
        const nombreSafe = (c.archivo_nombre || 'archivo').replace(/'/g, '');
        const ext = (nombreSafe.split('.').pop() || '').toLowerCase();
        const previewable = ['pdf', 'png', 'jpg', 'jpeg'].includes(ext);
        const verBtn = previewable
          ? `<button class="btn btn-ghost btn-sm" onclick="verCotizacion('${c.id}','${nombreSafe}')">👁 Ver</button>`
          : `<span style="color:var(--text3);font-size:10px" title="No se puede previsualizar, descárgalo">no previsualizable</span>`;
        ver = `<div style="display:flex;gap:4px;align-items:center;flex-wrap:wrap">
          ${verBtn}
          <button class="btn btn-ghost btn-sm" onclick="descargarCotizacion('${c.id}','${nombreSafe}')">⬇ Descargar</button>
          <span class="td-sub" style="font-size:10px;color:var(--text3);width:100%">${nombreSafe}</span>
        </div>`;
      }
      const del = (puedeCrear && esBorrador)
        ? `<button class="btn btn-ghost btn-sm" style="color:var(--red)" onclick="eliminarCotizacion('${c.id}','${s.id}')">Eliminar</button>` : '';
      return `<tr>
        <td>${c.proveedor || '—'}${c.referencia ? `<div class="td-sub" style="font-size:10px;color:var(--text3)">Ref: ${c.referencia}</div>` : ''}</td>
        <td style="text-align:right">${_money(c.valor_total)}</td>
        <td style="font-size:11px;color:var(--text3)">${_fecha(c.fecha)}</td>
        <td>${ver}</td>
        <td style="white-space:nowrap;text-align:right">${gan} ${del}</td>
      </tr>`;
    }).join('');
    filas = `<table class="tbl"><thead><tr><th>Proveedor</th><th style="text-align:right">Valor</th><th>Fecha</th><th>Adjunto</th><th></th></tr></thead><tbody>${filas}</tbody></table>`;
  }
  return `<div class="fsection" style="display:flex;justify-content:space-between;align-items:center;margin-top:16px">Cotizaciones (${cots.length}) ${addBtn}</div>${filas}`;
}

async function abrirModalCotizacion(solicitudId, empresaId) {
  if (!hasPermiso('compras.crear_solicitud')) { notif('Sin permiso', 'error'); return; }
  document.getElementById('cot-solicitud-id').value = solicitudId;
  // Proveedores de la empresa de la solicitud (puede diferir de empresaActual)
  const provs = await api(`/compras/proveedores?empresa_id=${empresaId}`) || [];
  document.getElementById('cot-proveedor').innerHTML = '<option value="">Seleccionar proveedor...</option>' +
    provs.filter(p => p.activo !== false).map(p => `<option value="${p.id}">${p.nombre}${p.nit ? ' — ' + p.nit : ''}</option>`).join('');
  ['cot-referencia','cot-valor','cot-fecha','cot-observaciones'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('cot-archivo').value = '';
  const msg = document.getElementById('cot-msg'); msg.style.display = 'none';
  abrirModal('modal-cotizacion');
}

async function guardarCotizacion() {
  const solId = document.getElementById('cot-solicitud-id').value;
  const proveedorId = document.getElementById('cot-proveedor').value;
  const archivo = document.getElementById('cot-archivo').files[0];
  const msg = document.getElementById('cot-msg');
  const showErr = (t) => { msg.textContent = '⚠ ' + t; msg.style.cssText = 'display:block;font-size:12px;border-radius:8px;padding:8px 12px;margin-top:6px;background:rgba(255,176,32,0.1);border:1px solid rgba(255,176,32,0.3);color:var(--amber)'; };
  if (!proveedorId) { showErr('Selecciona un proveedor'); return; }
  if (!archivo) { showErr('Adjunta el archivo de la cotización'); return; }
  const ALLOWED = ['pdf','png','jpg','jpeg','eml','msg'];
  const ext = (archivo.name.split('.').pop() || '').toLowerCase();
  if (!ALLOWED.includes(ext)) { showErr(`Tipo no permitido (.${ext}). Permitidos: ${ALLOWED.join(', ')}`); return; }
  if (archivo.size > 10 * 1024 * 1024) { showErr('El archivo supera 10 MB'); return; }

  const fd = new FormData();
  fd.append('proveedor_id', proveedorId);
  const valor = document.getElementById('cot-valor').value;
  if (valor) fd.append('valor_total', valor);
  const ref = document.getElementById('cot-referencia').value.trim();
  if (ref) fd.append('referencia', ref);
  const fecha = document.getElementById('cot-fecha').value;
  if (fecha) fd.append('fecha', fecha);
  const obs = document.getElementById('cot-observaciones').value.trim();
  if (obs) fd.append('observaciones', obs);
  fd.append('archivo', archivo);

  // multipart: NO fijar Content-Type (el navegador pone el boundary)
  const res = await fetch(`${API}/compras/solicitudes/${solId}/cotizaciones`, {
    method: 'POST', headers: { 'Authorization': `Bearer ${TOKEN}` }, body: fd
  });
  if (res.ok) { notif('Cotización agregada'); cerrarModal('modal-cotizacion'); verSolicitud(solId); }
  else { const e = await res.json().catch(()=>({})); showErr(e.detail || 'Error al guardar la cotización'); }
}

async function marcarGanadora(cotId, solId) {
  const res = await apiRaw(`/compras/cotizaciones/${cotId}/ganadora`, { method: 'POST' });
  if (res.ok) { notif('Cotización marcada como ganadora'); verSolicitud(solId); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

async function eliminarCotizacion(cotId, solId) {
  if (!confirm('¿Eliminar esta cotización y su adjunto?')) return;
  const res = await apiRaw(`/compras/cotizaciones/${cotId}`, { method: 'DELETE' });
  if (res.ok) { notif('Cotización eliminada'); verSolicitud(solId); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

async function descargarCotizacion(cotId, nombre) {
  const res = await fetch(`${API}/compras/cotizaciones/${cotId}/archivo`, {
    headers: { 'Authorization': `Bearer ${TOKEN}` }
  });
  if (!res.ok) { notif('No se pudo abrir el adjunto', 'error'); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = nombre || 'cotizacion';
  a.click(); URL.revokeObjectURL(url);
}

// ── Visor de adjuntos (pdf/imagen) — carga con token → blob → object URL ──
const _COT_MIME = { pdf: 'application/pdf', png: 'image/png', jpg: 'image/jpeg', jpeg: 'image/jpeg' };
let _cotViewerUrl = null;

async function verCotizacion(cotId, nombre) {
  const ext = (String(nombre).split('.').pop() || '').toLowerCase();
  const mime = _COT_MIME[ext];
  if (!mime) { descargarCotizacion(cotId, nombre); return; }   // no previsualizable → descarga

  if (_cotViewerUrl) { URL.revokeObjectURL(_cotViewerUrl); _cotViewerUrl = null; }
  const loading = document.getElementById('cotv-loading');
  const errBox = document.getElementById('cotv-error');
  const iframe = document.getElementById('cotv-iframe');
  const img = document.getElementById('cotv-img');
  document.getElementById('cotv-titulo').textContent = nombre || 'Vista previa';
  loading.style.display = 'flex'; errBox.style.display = 'none';
  iframe.style.display = 'none'; iframe.src = '';
  img.style.display = 'none'; img.src = '';
  // Los botones de descarga (footer + fallback) apuntan a esta cotización
  document.getElementById('cotv-download').onclick = () => descargarCotizacion(cotId, nombre);
  document.getElementById('cotv-error-download').onclick = () => descargarCotizacion(cotId, nombre);
  abrirModal('modal-cot-viewer');

  try {
    const res = await fetch(`${API}/compras/cotizaciones/${cotId}/archivo`, {
      headers: { 'Authorization': `Bearer ${TOKEN}` }
    });
    if (!res.ok) throw new Error('HTTP ' + res.status);
    const buf = await res.arrayBuffer();
    const blob = new Blob([buf], { type: mime });   // MIME correcto garantizado (guard)
    _cotViewerUrl = URL.createObjectURL(blob);
    loading.style.display = 'none';
    if (ext === 'pdf') { iframe.src = _cotViewerUrl; iframe.style.display = 'block'; }
    else { img.src = _cotViewerUrl; img.style.display = 'block'; }
  } catch (e) {
    loading.style.display = 'none';
    errBox.style.display = 'flex';
  }
}

function cerrarCotViewer() {
  cerrarModal('modal-cot-viewer');
  const iframe = document.getElementById('cotv-iframe');
  const img = document.getElementById('cotv-img');
  if (iframe) iframe.src = '';
  if (img) img.src = '';
  if (_cotViewerUrl) { URL.revokeObjectURL(_cotViewerUrl); _cotViewerUrl = null; }
}
async function enviarSolicitud(id) {
  const res = await apiRaw(`/compras/solicitudes/${id}/enviar`, { method: 'PUT' });
  if (res.ok) { notif('Solicitud enviada a aprobación'); cargarSolicitudes(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}
async function aprobarSolicitud(id) {
  const res = await apiRaw(`/compras/solicitudes/${id}/aprobar`, { method: 'POST', body: JSON.stringify({}) });
  if (res.ok) { notif('Solicitud aprobada'); cargarSolicitudes(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}
async function rechazarSolicitud(id) {
  const motivo = prompt('Motivo del rechazo:');
  if (motivo == null || !motivo.trim()) return;
  const res = await apiRaw(`/compras/solicitudes/${id}/rechazar`, { method: 'POST', body: JSON.stringify({ motivo_rechazo: motivo.trim() }) });
  if (res.ok) { notif('Solicitud rechazada'); cargarSolicitudes(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}
async function completarSolicitud(id) {
  const res = await apiRaw(`/compras/solicitudes/${id}/completar`, { method: 'POST', body: JSON.stringify({}) });
  if (res.ok) { notif('Solicitud marcada como completada'); cargarSolicitudes(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

// ══ ORDENES DE COMPRA ════════════════════════════════════════════════════════
async function cargarOrdenes() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  comprasCache.ordenes = await api(`/compras/ordenes?${p}`) || [];
  renderOrdenes(comprasCache.ordenes);
}
function renderOrdenes(list) {
  const tbody = document.getElementById('tbl-ordenes-body');
  if (!tbody) return;
  if (!list.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:22px">Sin órdenes de compra</td></tr>'; return; }
  const EST = { emitida: 'var(--amber)', parcialmente_recibida: 'var(--cyan)', recibida: 'var(--green)', cancelada: 'var(--red)' };
  const puedeRec = hasPermiso('compras.recepcionar');
  const puedeEditarErp = hasPermiso('compras.crear_solicitud');
  tbody.innerHTML = list.map(o => {
    const tcol = o.tipo === 'alquiler' ? 'var(--purple)' : 'var(--cyan)';
    let acc = (puedeRec && ['emitida', 'parcialmente_recibida'].includes(o.estado))
      ? `<button class="btn btn-ghost btn-sm" style="color:var(--cyan);border-color:rgba(var(--accent-rgb),.3)" onclick="abrirModalRecepcion('${o.id}')">Recepcionar</button>` : '';
    if (puedeEditarErp)
      acc += ` <button class="btn btn-ghost btn-sm" title="Número de orden ERP" onclick="editarErpOrden('${o.id}')">${o.numero_orden_erp ? '✎ ERP' : '+ ERP'}</button>`;
    return `<tr>
      <td><span class="mono-tag">${o.numero_oc || '—'}</span>${o.numero_solicitud ? `<div class="td-sub" style="font-size:10px;color:var(--text3)">Origen: ${o.numero_solicitud}</div>` : ''}${o.numero_orden_erp ? `<div class="td-sub" style="font-size:10px;color:var(--text3)">Orden ERP: ${o.numero_orden_erp}</div>` : ''}</td>
      <td>${o.proveedor || '—'}</td>
      <td>${_badge(o.tipo, tcol)}</td>
      <td>${_money(o.valor_total)}</td>
      <td>${_badge(o.estado.replace(/_/g, ' '), EST[o.estado] || 'var(--text3)')}</td>
      <td style="font-size:11px;color:var(--text3)">${_fecha(o.fecha_entrega_esperada)}</td>
      <td>${acc || '<span style="color:var(--text3)">—</span>'}</td>
    </tr>`;
  }).join('');
}
async function editarErpOrden(id) {
  const actual = (comprasCache.ordenes.find(o => o.id === id) || {}).numero_orden_erp || '';
  const valor = prompt('Número de orden ERP (dejar vacío para quitarlo):', actual);
  if (valor === null) return;   // cancelado
  const res = await apiRaw(`/compras/ordenes/${id}`, { method: 'PUT', body: JSON.stringify({ numero_orden_erp: valor.trim() || null }) });
  if (res.ok) { notif('Número de orden ERP actualizado'); cargarOrdenes(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}
function _llenarProveedoresSelect(selId, soloTipo) {
  const sel = document.getElementById(selId);
  if (!sel) return;
  const list = proveedoresCache.filter(p => p.activo !== false && (!soloTipo || p.tipo === soloTipo));
  sel.innerHTML = '<option value="">Seleccionar proveedor...</option>' +
    list.map(p => `<option value="${p.id}">${p.nombre}${p.nit ? ' — ' + p.nit : ''}</option>`).join('');
}
async function abrirModalOrden(solicitudId) {
  if (!hasPermiso('compras.crear_solicitud')) { notif('Sin permiso', 'error'); return; }
  const sol = await api(`/compras/solicitudes/${solicitudId}`);
  if (!sol) { notif('No se pudo cargar la solicitud', 'error'); return; }
  document.getElementById('oc-solicitud-id').value = solicitudId;
  // Cotización ganadora (para prellenar proveedor + valor; siguen editables)
  const ganadora = (sol.cotizaciones || []).find(c => c.es_ganadora) || null;
  document.getElementById('oc-solicitud-info').textContent =
    `Solicitud de ${sol.solicitante || ''} — ${sol.items_count} ítem(s)` +
    (ganadora ? ` · Ganadora: ${ganadora.proveedor || ''}${ganadora.valor_total != null ? ' (' + _money(ganadora.valor_total) + ')' : ''}` : '');
  await cargarProveedores();
  _llenarProveedoresSelect('oc-proveedor');
  document.getElementById('oc-erp').value = '';
  document.getElementById('oc-tipo').value = 'compra';
  document.getElementById('oc-fecha-emision').value = new Date().toISOString().slice(0, 10);
  document.getElementById('oc-fecha-entrega').value = '';
  document.getElementById('oc-valor').value = '';
  // Prefill desde la ganadora (editable)
  if (ganadora) {
    if (ganadora.proveedor_id) document.getElementById('oc-proveedor').value = ganadora.proveedor_id;
    if (ganadora.valor_total != null) document.getElementById('oc-valor').value = ganadora.valor_total;
  }
  document.getElementById('oc-observaciones').value = '';
  document.getElementById('oc-fecha-inicio').value = '';
  document.getElementById('oc-fecha-fin').value = '';
  document.getElementById('oc-valor-mensual').value = '';
  toggleCamposAlquilerOC();
  abrirModal('modal-orden');
}
function toggleCamposAlquilerOC() {
  const esAlq = document.getElementById('oc-tipo').value === 'alquiler';
  document.getElementById('oc-campos-alquiler').style.display = esAlq ? '' : 'none';
}
async function guardarOrden() {
  const body = {
    solicitud_id: document.getElementById('oc-solicitud-id').value,
    proveedor_id: document.getElementById('oc-proveedor').value,
    numero_orden_erp: document.getElementById('oc-erp').value.trim() || null,
    tipo: document.getElementById('oc-tipo').value,
    fecha_emision: document.getElementById('oc-fecha-emision').value,
    fecha_entrega_esperada: document.getElementById('oc-fecha-entrega').value || null,
    valor_total: document.getElementById('oc-valor').value ? parseFloat(document.getElementById('oc-valor').value) : null,
    observaciones: document.getElementById('oc-observaciones').value || null,
    fecha_inicio_alquiler: document.getElementById('oc-fecha-inicio').value || null,
    fecha_fin_alquiler: document.getElementById('oc-fecha-fin').value || null,
    valor_mensual_alquiler: document.getElementById('oc-valor-mensual').value ? parseFloat(document.getElementById('oc-valor-mensual').value) : null,
  };
  if (!body.proveedor_id || !body.fecha_emision) { notif('Proveedor y fecha de emisión son obligatorios', 'error'); return; }
  const res = await apiRaw('/compras/ordenes', { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) { notif('Orden de compra creada'); cerrarModal('modal-orden'); cargarOrdenes(); cargarSolicitudes(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

// ══ FACTURAS ═════════════════════════════════════════════════════════════════
async function cargarFacturas() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  comprasCache.facturas = await api(`/compras/facturas?${p}`) || [];
  renderFacturas(comprasCache.facturas);
}
function renderFacturas(list) {
  const tbody = document.getElementById('tbl-facturas-body');
  if (!tbody) return;
  if (!list.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:22px">Sin facturas</td></tr>'; return; }
  const EST = { pendiente: 'var(--amber)', pagada: 'var(--green)', vencida: 'var(--red)', anulada: 'var(--text3)' };
  const puedeGest = hasPermiso('compras.gestionar_facturas');
  tbody.innerHTML = list.map(f => {
    const venceCol = f.vencida ? 'color:var(--red);font-weight:600' : '';
    const acc = (puedeGest && f.estado === 'pendiente')
      ? `<button class="btn btn-ghost btn-sm" style="color:var(--green);border-color:rgba(0,229,160,.3)" onclick="marcarPagada('${f.id}')">Marcar pagada</button>` : '';
    return `<tr>
      <td><span class="mono-tag">${f.numero_factura}</span></td>
      <td>${f.proveedor || '—'}</td>
      <td style="font-size:11px;color:var(--text3)">${f.numero_oc || '—'}</td>
      <td>${_money(f.valor_total)}</td>
      <td style="font-size:11px;${venceCol}">${_fecha(f.fecha_vencimiento)}${f.vencida ? ' ⚠' : ''}</td>
      <td>${_badge(f.estado, EST[f.estado] || 'var(--text3)')}</td>
      <td>${acc || '<span style="color:var(--text3)">—</span>'}</td>
    </tr>`;
  }).join('');
}
async function abrirModalFactura(ordenId) {
  if (!hasPermiso('compras.gestionar_facturas')) { notif('Sin permiso', 'error'); return; }
  // poblar selector de OC (las que no estén canceladas)
  await cargarOrdenes();
  const sel = document.getElementById('fac-orden');
  sel.innerHTML = '<option value="">Seleccionar OC...</option>' +
    comprasCache.ordenes.filter(o => o.estado !== 'cancelada')
      .map(o => `<option value="${o.id}">${o.numero_oc || o.id.slice(0, 8)} — ${o.proveedor || ''}</option>`).join('');
  if (ordenId) sel.value = ordenId;
  ['fac-numero', 'fac-fecha', 'fac-vencimiento', 'fac-subtotal', 'fac-iva', 'fac-total', 'fac-observaciones'].forEach(id => document.getElementById(id).value = '');
  document.getElementById('fac-fecha').value = new Date().toISOString().slice(0, 10);
  abrirModal('modal-factura');
}
async function guardarFactura() {
  const body = {
    orden_compra_id: document.getElementById('fac-orden').value,
    numero_factura: document.getElementById('fac-numero').value.trim(),
    fecha_factura: document.getElementById('fac-fecha').value,
    fecha_vencimiento: document.getElementById('fac-vencimiento').value || null,
    subtotal: document.getElementById('fac-subtotal').value ? parseFloat(document.getElementById('fac-subtotal').value) : null,
    iva: document.getElementById('fac-iva').value ? parseFloat(document.getElementById('fac-iva').value) : null,
    valor_total: document.getElementById('fac-total').value ? parseFloat(document.getElementById('fac-total').value) : null,
    observaciones: document.getElementById('fac-observaciones').value || null,
  };
  if (!body.orden_compra_id || !body.numero_factura || !body.fecha_factura || body.valor_total == null) {
    notif('OC, número, fecha y valor total son obligatorios', 'error'); return;
  }
  const res = await apiRaw('/compras/facturas', { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) { notif('Factura registrada'); cerrarModal('modal-factura'); cargarFacturas(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}
async function marcarPagada(id) {
  const res = await apiRaw(`/compras/facturas/${id}`, { method: 'PUT', body: JSON.stringify({ estado: 'pagada' }) });
  if (res.ok) { notif('Factura marcada como pagada'); cargarFacturas(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

// ══ RECEPCIONES ══════════════════════════════════════════════════════════════
async function cargarRecepciones() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  comprasCache.recepciones = await api(`/compras/recepciones?${p}`) || [];
  renderRecepciones(comprasCache.recepciones);
}
function renderRecepciones(list) {
  const tbody = document.getElementById('tbl-recepciones-body');
  if (!tbody) return;
  if (!list.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:22px">Sin recepciones</td></tr>'; return; }
  const EST = { pendiente: 'var(--text3)', recibida_parcial: 'var(--cyan)', recibida_completa: 'var(--green)', con_novedad: 'var(--amber)' };
  const puedeInv = hasPermiso('compras.crear_inventario');
  tbody.innerHTML = list.map(r => {
    let acc = '';
    if (puedeInv) {
      if (r.unidades_totales > 0 && r.inventario_completo) {
        // Todo el inventario creado → botón deshabilitado en estado de éxito
        acc = `<button class="btn btn-ghost btn-sm" disabled title="Todas las unidades fueron creadas en inventario" style="color:var(--green);border-color:rgba(0,229,160,.35);opacity:.85;cursor:default"><i class="ti ti-circle-check"></i> Inventario completo</button>`;
      } else if (r.unidades_totales > 0) {
        const lbl = `Crear inventario (${r.unidades_creadas}/${r.unidades_totales})`;
        acc = `<button class="btn btn-ghost btn-sm" style="color:var(--purple);border-color:rgba(167,139,255,.3)" onclick="abrirModalCrearInventario('${r.id}')">${lbl}</button>`;
      } else {
        // Sin ítems elegibles (nada recibido OK con cantidad > 0) → nada que crear
        acc = `<span style="color:var(--text3);font-size:11px">Sin ítems para inventario</span>`;
      }
    }
    return `<tr>
      <td style="font-size:11px;color:var(--text3)">${_fecha(r.fecha_recepcion)}</td>
      <td><span class="mono-tag">${r.numero_oc || '—'}</span></td>
      <td>${r.proveedor || '—'}</td>
      <td style="text-align:center"><span class="mono-tag">${r.items_count}</span></td>
      <td>${_badge((r.estado || '').replace(/_/g, ' '), EST[r.estado] || 'var(--text3)')}</td>
      <td>${acc || '<span style="color:var(--text3)">—</span>'}</td>
    </tr>`;
  }).join('');
}
async function abrirModalRecepcion(ordenId) {
  if (!hasPermiso('compras.recepcionar')) { notif('Sin permiso', 'error'); return; }
  const orden = await api(`/compras/ordenes/${ordenId}`);
  if (!orden) { notif('No se pudo cargar la OC', 'error'); return; }
  const sol = await api(`/compras/solicitudes/${orden.solicitud_id}`);
  const items = sol ? sol.items : [];
  document.getElementById('rec-orden-id').value = ordenId;
  document.getElementById('rec-orden-info').textContent = `${orden.numero_oc || ordenId.slice(0, 8)} — ${orden.proveedor || ''}`;
  document.getElementById('rec-fecha').value = new Date().toISOString().slice(0, 10);
  document.getElementById('rec-observaciones').value = '';
  document.getElementById('rec-novedades').value = '';
  document.getElementById('rec-items-container').innerHTML = items.map(it => `
    <div class="rec-item-row" data-si="${it.id}" style="display:grid;grid-template-columns:2fr .7fr .7fr 1fr 1.2fr 1fr;gap:6px;align-items:center;margin-bottom:6px">
      <input class="finput rec-it-desc" value="${(it.descripcion || '').replace(/"/g, '&quot;')}" readonly>
      <input class="finput rec-it-esp" type="number" value="${it.cantidad}" readonly title="Esperado">
      <input class="finput rec-it-rec" type="number" min="0" value="${it.cantidad}" title="Recibido">
      <select class="fselect rec-it-estado">
        <option value="ok">OK</option><option value="dañado">Dañado</option>
        <option value="incompleto">Incompleto</option><option value="no_recibido">No recibido</option>
      </select>
      <input class="finput rec-it-serial" placeholder="Serial (opc.)">
      <input class="finput rec-it-obs" placeholder="Observación (opc.)">
    </div>`).join('') || '<div style="color:var(--text3);font-size:12px">La solicitud no tiene ítems; agrega manualmente desde la OC.</div>';
  abrirModal('modal-recepcion');
}
async function guardarRecepcion() {
  const items = [...document.querySelectorAll('#rec-items-container .rec-item-row')].map(r => ({
    solicitud_item_id: r.dataset.si || null,
    descripcion: r.querySelector('.rec-it-desc').value.trim(),
    cantidad_esperada: parseInt(r.querySelector('.rec-it-esp').value) || 0,
    cantidad_recibida: parseInt(r.querySelector('.rec-it-rec').value) || 0,
    estado: r.querySelector('.rec-it-estado').value,
    serial: r.querySelector('.rec-it-serial').value || null,
    observacion: r.querySelector('.rec-it-obs').value || null,
  })).filter(i => i.descripcion);
  const body = {
    orden_compra_id: document.getElementById('rec-orden-id').value,
    fecha_recepcion: document.getElementById('rec-fecha').value,
    items,
    observaciones: document.getElementById('rec-observaciones').value || null,
    novedades: document.getElementById('rec-novedades').value || null,
  };
  if (!body.orden_compra_id || !body.fecha_recepcion || !items.length) { notif('OC, fecha e ítems son obligatorios', 'error'); return; }
  const res = await apiRaw('/compras/recepciones', { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) { notif('Recepción registrada'); cerrarModal('modal-recepcion'); cargarRecepciones(); cargarOrdenes(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

// Flujo de "Crear inventario": lista los ítems recibidos con su progreso y, por
// cada uno, abre el modal COMPLETO de activo/accesorio (prellenado) para crear
// cada unidad individualmente hasta completar la cantidad recibida.
let _ciItems = [];          // items-para-inventario de la recepción abierta
let _ciRecepcionId = null;

async function abrirModalCrearInventario(recepcionId) {
  if (!hasPermiso('compras.crear_inventario')) { notif('Sin permiso', 'error'); return; }
  _ciRecepcionId = recepcionId;
  document.getElementById('ci-recepcion-id').value = recepcionId;
  await _ciCargar(recepcionId);
  abrirModal('modal-crear-inventario');
}

// Recarga la lista de progreso (llamada por activos/accesorios.js tras crear una unidad)
async function refrescarCrearInventario(recepcionId) {
  await _ciCargar(recepcionId || _ciRecepcionId);
}

// Cierra el modal y refresca la lista de recepciones para que el botón
// "Crear inventario" refleje el estado actualizado (p. ej. "Inventario completo").
function cerrarModalCrearInventario() {
  cerrarModal('modal-crear-inventario');
  if (typeof cargarRecepciones === 'function') cargarRecepciones();
}

async function _ciCargar(recepcionId) {
  // Preservar el tipo seleccionado por el usuario (override) entre recargas
  const prevSel = {};
  _ciItems.forEach(i => { if (i.tipo_sel) prevSel[i.recepcion_item_id] = i.tipo_sel; });
  const items = await api(`/compras/recepciones/${recepcionId}/items-para-inventario`);
  _ciItems = (items || []).map(i => ({
    ...i,
    // tipo_sel = elección actual; por defecto el original (tipo_item), o el override previo
    tipo_sel: prevSel[i.recepcion_item_id] || i.tipo_item || 'activo',
  }));
  _ciRender();
}

function _ciRender() {
  const cont = document.getElementById('ci-items-container');
  if (!cont) return;
  if (!_ciItems.length) {
    cont.innerHTML = '<div style="color:var(--text3);font-size:12px;padding:8px">No hay ítems recibidos OK pendientes de crear en inventario.</div>';
    document.getElementById('ci-progreso').textContent = '';
    return;
  }
  const totU = _ciItems.reduce((s, i) => s + i.cantidad_recibida, 0);
  const totC = _ciItems.reduce((s, i) => s + Math.min(i.creados, i.cantidad_recibida), 0);
  document.getElementById('ci-progreso').textContent = `${totC} de ${totU} unidades creadas`;

  // Banner de inventario completo (todos los ítems al 100%)
  const todoCompleto = _ciItems.every(i => i.completo);
  const banner = todoCompleto
    ? `<div style="display:flex;align-items:center;gap:8px;background:rgba(0,229,160,.08);border:1px solid rgba(0,229,160,.35);color:var(--green);border-radius:8px;padding:10px 12px;margin-bottom:10px;font-size:12px;font-weight:600">
        <i class="ti ti-circle-check"></i> Inventario completo — todos los recursos fueron creados
      </div>`
    : '';

  cont.innerHTML = banner + _ciItems.map((it, idx) => {
    const sel = it.tipo_sel || it.tipo_item || 'activo';
    const esAcc = sel === 'accesorio';
    const original = it.tipo_item_original || it.tipo_item;
    const overrideHint = (sel !== original)
      ? `<div style="font-size:10px;color:var(--amber);margin-top:3px">⚠ Tipo original: ${original} (lo estás creando como ${sel})</div>`
      : '';
    const pct = it.cantidad_recibida ? Math.round(it.creados / it.cantidad_recibida * 100) : 0;

    let right;
    if (it.completo) {
      right = `<button class="btn btn-ghost btn-sm" disabled style="opacity:.6">✓ Completo</button>`;
    } else {
      // Selector de tipo (override) + botón de crear, según el tipo seleccionado
      right = `<div style="display:flex;align-items:center;gap:6px;flex-shrink:0">
        <select class="fselect" style="width:auto;font-size:11px;padding:5px 6px" onchange="ciSetTipo(${idx}, this.value)" title="Tipo a crear">
          <option value="activo"${sel === 'activo' ? ' selected' : ''}>Activo</option>
          <option value="accesorio"${sel === 'accesorio' ? ' selected' : ''}>Accesorio</option>
        </select>
        <button class="btn btn-primary btn-sm" onclick="ciCrearUnidad(${idx})">+ Crear ${esAcc ? 'accesorio' : 'activo'} (${it.pendientes} pendiente${it.pendientes === 1 ? '' : 's'})</button>
      </div>`;
    }

    return `<div class="ci-item-row" style="border:1px solid var(--border);border-radius:8px;padding:10px 12px;margin-bottom:8px;display:flex;align-items:center;gap:12px">
      <div style="flex:1;min-width:0">
        <div style="font-size:12px;color:var(--text);font-weight:600">${it.descripcion}</div>
        <div style="font-size:11px;color:var(--text3)">${esAcc ? '🖱 Accesorio' : '🖥 Activo'} · Creados: ${it.creados}/${it.cantidad_recibida}</div>
        ${overrideHint}
        <div style="height:4px;background:var(--border);border-radius:3px;margin-top:5px;overflow:hidden"><div style="height:100%;width:${pct}%;background:${it.completo ? 'var(--green)' : 'var(--cyan)'}"></div></div>
      </div>
      ${right}
    </div>`;
  }).join('');
}

// Cambia el tipo seleccionado (override) para un ítem y re-renderiza
function ciSetTipo(idx, val) {
  if (_ciItems[idx]) { _ciItems[idx].tipo_sel = val; _ciRender(); }
}

// Abre el modal completo de activo/accesorio prellenado para este ítem,
// según el tipo SELECCIONADO (override) — no el original almacenado.
function ciCrearUnidad(idx) {
  const it = _ciItems[idx];
  if (!it || it.completo) return;
  const tipoSel = it.tipo_sel || it.tipo_item || 'activo';
  const prefill = {
    recepcion_item_id: it.recepcion_item_id,
    recepcionId: _ciRecepcionId,
    empresa_id: it.empresa_id,
    modelo_sugerido: it.modelo_sugerido,
    serial_sugerido: it.serial_sugerido,
    fecha_compra: it.fecha_compra,
    costo_unitario: it.costo_unitario,
    creados: it.creados,
    cantidad_recibida: it.cantidad_recibida,
  };
  if (tipoSel === 'accesorio') {
    if (typeof abrirModalAccesorioDesdeRecepcion === 'function') abrirModalAccesorioDesdeRecepcion(prefill);
    else notif('Módulo de accesorios no disponible', 'error');
  } else {
    if (typeof abrirModalActivoDesdeRecepcion === 'function') abrirModalActivoDesdeRecepcion(prefill);
    else notif('Módulo de activos no disponible', 'error');
  }
}

// ══ CONTRATOS DE ALQUILER ════════════════════════════════════════════════════
async function cargarContratos() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  comprasCache.contratos = await api(`/compras/contratos-alquiler?${p}`) || [];
  renderContratos(comprasCache.contratos);
}
function renderContratos(list) {
  const tbody = document.getElementById('tbl-contratos-body');
  if (!tbody) return;
  if (!list.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:22px">Sin contratos de alquiler</td></tr>'; return; }
  const EST = { activo: 'var(--green)', vencido: 'var(--amber)', terminado_anticipado: 'var(--text3)' };
  const puede = hasPermiso('compras.gestionar_facturas');
  tbody.innerHTML = list.map(c => {
    const finCol = c.proximo_a_vencer ? 'color:var(--amber);font-weight:600' : 'color:var(--text3)';
    const eqs = c.equipos || [];
    const placas = eqs.map(e => `<span class="mono-tag" style="font-size:9px">${e.placa}</span>`).join(' ');
    const itemCell = eqs.length
      ? `<div style="font-size:11px;color:var(--text2);margin-bottom:2px">${eqs.length} equipo(s)${c.numero_oc ? ` · OC ${c.numero_oc}` : ''}</div>${placas}`
      : `<span style="color:var(--text3)">Sin equipos${c.numero_oc ? ` · OC ${c.numero_oc}` : ''}</span>`;
    const acc = (puede && c.estado === 'activo')
      ? `<button class="btn btn-ghost btn-sm" style="color:var(--red);border-color:rgba(255,77,109,.3)" onclick="terminarContrato('${c.id}')">Terminar</button>` : '';
    return `<tr>
      <td>${itemCell}</td>
      <td>${c.proveedor || '—'}</td>
      <td style="font-size:11px;color:var(--text3)">${_fecha(c.fecha_inicio)}</td>
      <td style="font-size:11px;${finCol}">${_fecha(c.fecha_fin)}${c.proximo_a_vencer ? ' ⚠' : ''}</td>
      <td>${_money(c.valor_mensual)}</td>
      <td>${_badge((c.estado || '').replace(/_/g, ' '), EST[c.estado] || 'var(--text3)')}</td>
      <td>${acc || '<span style="color:var(--text3)">—</span>'}</td>
    </tr>`;
  }).join('');
}
function terminarContrato(id) {
  document.getElementById('ct-id').value = id;
  document.getElementById('ct-fecha').value = new Date().toISOString().slice(0, 10);
  document.getElementById('ct-observaciones').value = '';
  // Lista de equipos que se retirarán (devuelto a proveedor)
  const c = (comprasCache.contratos || []).find(x => x.id === id);
  const cont = document.getElementById('ct-equipos');
  if (cont) {
    const eqs = (c && c.equipos) || [];
    cont.innerHTML = eqs.length
      ? `<div style="font-size:11px;color:var(--text3);margin-bottom:4px">Al terminar, estos ${eqs.length} equipo(s) pasarán a <b>retirado</b> (devuelto a proveedor):</div>`
        + eqs.map(e => `<div style="font-size:12px"><span class="mono-tag" style="font-size:9px">${e.placa}</span> ${e.descripcion || ''}</div>`).join('')
      : '<div style="font-size:12px;color:var(--text3)">Este contrato no tiene equipos.</div>';
  }
  abrirModal('modal-contrato-terminar');
}
async function guardarTerminarContrato() {
  const id = document.getElementById('ct-id').value;
  const body = {
    fecha_devolucion_real: document.getElementById('ct-fecha').value,
    observaciones_devolucion: document.getElementById('ct-observaciones').value || null,
  };
  if (!body.fecha_devolucion_real) { notif('La fecha de devolución es obligatoria', 'error'); return; }
  const res = await apiRaw(`/compras/contratos-alquiler/${id}/terminar`, { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) { notif('Contrato terminado'); cerrarModal('modal-contrato-terminar'); cargarContratos(); cargarStatsCompras(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

// ══ PROVEEDORES (modal auxiliar — necesario para crear OC/garantías) ═════════
function abrirModalProveedor() {
  if (!hasPermiso('compras.ver')) { notif('Sin permiso', 'error'); return; }
  // Proveedores GLOBALES: sin empresa.
  ['prov-nombre', 'prov-nit', 'prov-contacto', 'prov-telefono', 'prov-correo', 'prov-ciudad'].forEach(id => document.getElementById(id).value = '');
  llenarSelectCatalogo('prov-tipo', 'tipo_proveedor', 'vendedor');
  abrirModal('modal-proveedor');
}
async function guardarProveedor() {
  const body = {
    nombre: document.getElementById('prov-nombre').value.trim(),
    nit: document.getElementById('prov-nit').value || null,
    tipo: document.getElementById('prov-tipo').value,
    contacto_nombre: document.getElementById('prov-contacto').value || null,
    telefono: document.getElementById('prov-telefono').value || null,
    correo: document.getElementById('prov-correo').value || null,
    ciudad: document.getElementById('prov-ciudad').value || null,
  };
  if (!body.nombre) { notif('El nombre es obligatorio', 'error'); return; }
  const res = await apiRaw('/compras/proveedores', { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) { notif('Proveedor creado'); cerrarModal('modal-proveedor'); await cargarProveedores(); }
  else { const e = await res.json(); notif(e.detail || 'Error', 'error'); }
}

// Acción del botón "+ Nueva solicitud" del encabezado (si llegara a mostrarse)
function accionNuevaCompra() {
  const map = { solicitudes: abrirModalSolicitud, facturas: () => abrirModalFactura() };
  (map[comprasTab] || abrirModalSolicitud)();
}
