// ── Servidores module ─────────────────────────────────────────────────────────

let servidoresCache = [];
let servidoresFiltroAmbiente = '';
let servidoresVerBaja = false;   // false = solo vigentes; true = ver dados de baja
let catServidores = null;
let _bajaServidorId = null;      // servidor en curso del modal de baja

function _srvEsc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

// ── Catalogos ─────────────────────────────────────────────────────────────────

async function cargarCatalogosServidores() {
  if (catServidores) return catServidores;
  catServidores = await api('/servidores/catalogos');
  return catServidores;
}

function _llenarSelect(id, items, valKey, labelKey, blankLabel = '— Todos —') {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = `<option value="">${blankLabel}</option>` +
    items.map(i => `<option value="${i[valKey]}">${i[labelKey]}</option>`).join('');
}

async function _poblarSelects() {
  const c = catServidores;
  if (!c) return;
  _llenarSelect('srv-tipo',      c.tipos_servidor,   'id', 'nombre', '— Tipo —');
  _llenarSelect('srv-ambiente',  c.ambientes,         'id', 'nombre', '— Ambiente —');
  _llenarSelect('srv-criticidad',c.criticidades,      'id', 'nombre', '— Criticidad —');
  _llenarSelect('srv-estado',    c.estados_servidor,  'id', 'nombre', '— Estado —');
  _llenarSelect('srv-ubicacion', c.hosting || [],     'id', 'nombre', '— Ubicación (hosting) —');
  _llenarSelect('srv-so',        c.sistemas_operativos,'id','nombre', '— SO —');
}

// ── Stats KPIs ────────────────────────────────────────────────────────────────

async function cargarStatsServidores() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  const stats = await api(`/servidores/stats?${p}`);
  if (!stats) return;

  const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
  set('srv-kpi-total',    stats.total);
  set('srv-kpi-activos',  stats.activos);
  set('srv-kpi-inactivos',stats.inactivos);

  // Top herramienta por categoria
  const cats = stats.por_categoria_herr || {};
  const topCat = Object.entries(cats).sort((a,b) => b[1]-a[1])[0];
  set('srv-kpi-cobertura', topCat ? `${topCat[0]}: ${topCat[1]}` : '—');
}

// ── Lista ─────────────────────────────────────────────────────────────────────

async function cargarServidores() {
  const p = new URLSearchParams();
  if (empresaActual)              p.set('empresa_id',  empresaActual);
  if (servidoresFiltroAmbiente)   p.set('ambiente_id', servidoresFiltroAmbiente);
  if (servidoresVerBaja)          p.set('activo', 'false');   // ver dados de baja

  // Filtro avanzado (AND entre dimensiones). Se leen los controles del panel.
  const fval = id => (document.getElementById(id)?.value || '').trim();
  const tipo = fval('srv-f-tipo');       if (tipo) p.set('tipo_servidor_id', tipo);
  const crit = fval('srv-f-criticidad'); if (crit) p.set('criticidad_id', crit);
  const host = fval('srv-f-hosting');    if (host) p.set('ubicacion_catalogo_id', host);
  const so   = fval('srv-f-so');         if (so)   p.set('so_id', so);
  // Estado: si el usuario elige un estado concreto, manda el estado (puede mostrar dados de baja).
  const est  = fval('srv-f-estado');     if (est && !servidoresVerBaja) p.set('estado_id', est);

  const herr = _selectedMulti('srv-f-herramientas');
  if (herr.length) { herr.forEach(h => p.append('herramienta_ids', h)); p.set('herr_match', fval('srv-f-herr-match') || 'any'); }
  const svc = _selectedMulti('srv-f-servicios');
  if (svc.length) { svc.forEach(s => p.append('servicios', s)); p.set('svc_match', fval('srv-f-svc-match') || 'any'); }

  const data = await api(`/servidores?${p}`);
  servidoresCache = data || [];
  renderServidores(servidoresCache);
}

function _selectedMulti(id) {
  const el = document.getElementById(id);
  if (!el) return [];
  return [...el.selectedOptions].map(o => o.value).filter(v => v);
}

// Pobla los controles del filtro avanzado: dropdowns desde los catálogos;
// herramientas/servicios desde el vocabulario REAL (empresa-scoped, dinámico).
async function poblarFiltrosServidores() {
  const c = await cargarCatalogosServidores();
  if (c) {
    _llenarSelect('srv-f-tipo',       c.tipos_servidor,      'id', 'nombre', 'Tipo: todos');
    _llenarSelect('srv-f-ambiente',   c.ambientes,           'id', 'nombre', 'Ambiente: todos');
    _llenarSelect('srv-f-criticidad', c.criticidades,        'id', 'nombre', 'Criticidad: todas');
    _llenarSelect('srv-f-estado',     c.estados_servidor,    'id', 'nombre', 'Estado: todos');
    _llenarSelect('srv-f-hosting',    c.hosting || [],       'id', 'nombre', 'Hosting: todos');
    _llenarSelect('srv-f-so',         c.sistemas_operativos, 'id', 'nombre', 'SO: todos');
    const amb = document.getElementById('srv-f-ambiente');
    if (amb) amb.value = servidoresFiltroAmbiente || '';
  }
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  const f = await api(`/servidores/filtros?${p}`) || {};
  const herr = document.getElementById('srv-f-herramientas');
  if (herr) herr.innerHTML = (f.herramientas || []).length
    ? f.herramientas.map(h => `<option value="${h.id}">${_srvEsc(h.nombre)}</option>`).join('')
    : '<option disabled>— sin herramientas en uso —</option>';
  const svc = document.getElementById('srv-f-servicios');
  if (svc) svc.innerHTML = (f.servicios || []).length
    ? f.servicios.map(s => `<option value="${_srvEsc(s)}">${_srvEsc(s)}</option>`).join('')
    : '<option disabled>— sin servicios registrados —</option>';
}

function toggleFiltrosServidores(btn) {
  const panel = document.getElementById('srv-filtros-panel');
  if (!panel) return;
  const show = panel.style.display === 'none';
  panel.style.display = show ? '' : 'none';
  if (btn) btn.classList.toggle('active', show);
}

function aplicarFiltrosServidores() {
  // Ambiente se refleja en la variable que comparten panel y pestañas.
  servidoresFiltroAmbiente = document.getElementById('srv-f-ambiente')?.value || '';
  const tabs = document.querySelectorAll('#tabs-servidores .tab');
  tabs.forEach(t => t.classList.remove('active'));
  if (!servidoresFiltroAmbiente && tabs.length) tabs[0].classList.add('active');
  cargarServidores();
}

function limpiarFiltrosServidores() {
  ['srv-f-tipo','srv-f-ambiente','srv-f-criticidad','srv-f-estado','srv-f-hosting','srv-f-so']
    .forEach(id => { const e = document.getElementById(id); if (e) e.value = ''; });
  ['srv-f-herramientas','srv-f-servicios']
    .forEach(id => { const e = document.getElementById(id); if (e) [...e.options].forEach(o => o.selected = false); });
  const hm = document.getElementById('srv-f-herr-match'); if (hm) hm.value = 'any';
  const sm = document.getElementById('srv-f-svc-match');  if (sm) sm.value = 'any';
  const search = document.getElementById('search-servidores'); if (search) search.value = '';
  servidoresFiltroAmbiente = '';
  const tabs = document.querySelectorAll('#tabs-servidores .tab');
  tabs.forEach(t => t.classList.remove('active'));
  if (tabs.length) tabs[0].classList.add('active');
  cargarServidores();
}

function _colorDot(color) {
  return `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color||'#888'};margin-right:5px"></span>`;
}

function renderServidores(list) {
  const tbody = document.getElementById('tbl-servidores-body');
  if (!tbody) return;
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text3);padding:24px">Sin servidores registrados</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(s => `
    <tr class="clickable" onclick="abrirDetalleServidor('${s.id}')">
      <td>
        <div class="td-name">${s.nombre}</div>
        <div class="td-sub" style="font-family:var(--mono);font-size:10px">${s.hostname}</div>
      </td>
      <td>${s.ip_lan ? `<span class="mono-tag">${s.ip_lan}</span>` : '<span style="color:var(--text3)">—</span>'}</td>
      <td>${s.tipo_nombre ? `<span class="badge badge-outline">${s.tipo_nombre}</span>` : '—'}</td>
      <td>${s.ambiente_nombre ? `${_colorDot(s.ambiente_color)}<span style="font-size:11px">${s.ambiente_nombre}</span>` : '—'}</td>
      <td>${s.criticidad_nombre ? `<span class="badge" style="background:${s.criticidad_color}22;color:${s.criticidad_color};border:1px solid ${s.criticidad_color}44">${s.criticidad_nombre}</span>` : '—'}</td>
      <td>${s.so_nombre ? `<div style="font-size:11px">${s.so_nombre}</div><div class="td-sub">${s.so_familia||''}</div>` : '—'}</td>
      <td>${s.estado_nombre ? `${_colorDot(s.estado_color)}<span style="font-size:11px">${s.estado_nombre}</span>` : '—'}</td>
      <td>
        <span style="font-size:11px;color:var(--text2)">${s.num_herramientas} herr.</span>
        ${s.nombre_empresa ? `<div class="td-sub">${s.nombre_empresa}</div>` : ''}
      </td>
    </tr>`).join('');
}

function filtrarServidores(ambienteId, el) {
  servidoresFiltroAmbiente = ambienteId;
  document.querySelectorAll('#tabs-servidores .tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  const sel = document.getElementById('srv-f-ambiente'); if (sel) sel.value = ambienteId || '';
  cargarServidores();
}

function buscarServidores() {
  const q = (document.getElementById('search-servidores')?.value || '').toLowerCase();
  renderServidores(q ? servidoresCache.filter(s =>
    (s.nombre||'').toLowerCase().includes(q) ||
    (s.hostname||'').toLowerCase().includes(q) ||
    (s.ip_lan||'').toLowerCase().includes(q) ||
    (s.ip_salida||'').toLowerCase().includes(q) ||
    (s.id_servicio||'').toLowerCase().includes(q) ||
    (s.so_nombre||'').toLowerCase().includes(q)
  ) : servidoresCache);
}

// ── Modal crear/editar ────────────────────────────────────────────────────────

let _servidorEditId = null;

async function abrirModalServidor(servidor = null) {
  // Puede recibir un id (string, desde el onclick del detalle) o un objeto ya cargado.
  // Si es id, se OBTIENE la data guardada del servidor (fetch) — patrón de impresoras/redes.
  if (typeof servidor === 'string') {
    servidor = await api(`/servidores/${servidor}`);
    if (!servidor) { notif('No se pudo cargar el servidor', 'error'); return; }
  }
  _servidorEditId = servidor ? servidor.id : null;
  const titulo = document.getElementById('modal-srv-titulo');
  if (titulo) titulo.textContent = servidor ? 'Editar Servidor' : 'Nuevo Servidor';

  // Poblar las opciones de los <select> ANTES de asignar sus valores: si se asignan
  // antes de que existan las opciones (o se repuebla después), el value se pierde.
  await cargarCatalogosServidores();
  await _poblarSelects();

  const fields = ['srv-nombre','srv-hostname','srv-id-servicio','srv-kawak-id',
                  'srv-glpi-id','srv-procesador','srv-ram','srv-disco',
                  'srv-ip-lan','srv-ip-salida','srv-observaciones','srv-pendientes'];
  fields.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

  const selects = ['srv-tipo','srv-ambiente','srv-criticidad','srv-estado','srv-ubicacion','srv-so'];
  selects.forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

  if (servidor) {
    const map = {
      'srv-nombre':      servidor.nombre,
      'srv-hostname':    servidor.hostname,
      'srv-id-servicio': servidor.id_servicio||'',
      'srv-kawak-id':    servidor.kawak_id||'',
      'srv-glpi-id':     servidor.glpi_id||'',
      'srv-procesador':  servidor.procesador||'',
      'srv-ram':         servidor.memoria_ram||'',
      'srv-disco':       servidor.disco||'',
      'srv-ip-lan':      servidor.ip_lan||'',
      'srv-ip-salida':   servidor.ip_salida||'',
      'srv-observaciones': servidor.observaciones||'',
      'srv-pendientes':  servidor.pendientes||'',
    };
    Object.entries(map).forEach(([id, val]) => { const el = document.getElementById(id); if (el) el.value = val; });

    const selMap = {
      'srv-tipo':       servidor.tipo_servidor_id,
      'srv-ambiente':   servidor.ambiente_id,
      'srv-criticidad': servidor.criticidad_id,
      'srv-estado':     servidor.estado_id,
      'srv-ubicacion':  servidor.ubicacion_catalogo_id,
      'srv-so':         servidor.so_id,
    };
    Object.entries(selMap).forEach(([id, val]) => { const el = document.getElementById(id); if (el && val) el.value = val; });
  }

  // Aplicabilidad por empresa. Nuevo servidor => "específicas" con la dueña pre-marcada
  // (default acordado: sin visibilidad demasiado amplia). Edición => refleja lo guardado.
  const ownerId = servidor ? servidor.empresa_id : empresaActual;
  const aplicaTodas = servidor ? !!servidor.aplica_todas : false;
  const aplicables = servidor
    ? (servidor.empresas_aplicables || []).map(e => e.id)
    : (ownerId ? [ownerId] : []);
  const rTodas = document.getElementById('srv-aplic-todas');
  const rEsp   = document.getElementById('srv-aplic-especificas');
  if (rTodas && rEsp) { rTodas.checked = aplicaTodas; rEsp.checked = !aplicaTodas; }
  _srvRenderAplicChecklist(ownerId, aplicables);
  _srvToggleAplic();

  abrirModal('modal-servidor');
}

function _srvToggleAplic() {
  const todas = document.getElementById('srv-aplic-todas')?.checked;
  const wrap = document.getElementById('srv-aplic-checklist-wrap');
  if (wrap) wrap.style.display = todas ? 'none' : '';
}

// Checklist de empresas. La dueña (ownerId) queda marcada + deshabilitada (INVARIANTE:
// un servidor siempre aplica a su empresa dueña). checkedIds = empresas ya seleccionadas.
function _srvRenderAplicChecklist(ownerId, checkedIds) {
  const cont = document.getElementById('srv-aplic-checklist');
  if (!cont) return;
  const checked = new Set(checkedIds || []);
  if (ownerId) checked.add(ownerId);
  cont.innerHTML = (empresasCache || []).map(e => {
    const isOwner = e.id === ownerId;
    const on = checked.has(e.id);
    return `<label style="display:inline-flex;align-items:center;gap:5px;font-size:12px;cursor:${isOwner ? 'not-allowed' : 'pointer'};opacity:${isOwner ? 0.75 : 1}">` +
      `<input type="checkbox" class="srv-aplic-emp" value="${e.id}" ${on ? 'checked' : ''} ${isOwner ? 'checked disabled' : ''}>` +
      `${_srvEsc(e.nombre_empresa)}${isOwner ? ' (dueña)' : ''}</label>`;
  }).join('') || '<span style="font-size:11px;color:var(--text3)">Sin empresas disponibles</span>';
}

async function guardarServidor() {
  const nombre   = document.getElementById('srv-nombre')?.value.trim();
  const hostname = document.getElementById('srv-hostname')?.value.trim();
  if (!nombre || !hostname) { notif('Nombre y hostname son obligatorios', 'error'); return; }

  const body = {
    nombre,
    hostname,
    id_servicio:      document.getElementById('srv-id-servicio')?.value.trim() || null,
    kawak_id:         document.getElementById('srv-kawak-id')?.value.trim() || null,
    glpi_id:          document.getElementById('srv-glpi-id')?.value.trim() || null,
    tipo_servidor_id: document.getElementById('srv-tipo')?.value || null,
    ambiente_id:      document.getElementById('srv-ambiente')?.value || null,
    criticidad_id:    document.getElementById('srv-criticidad')?.value || null,
    estado_id:        document.getElementById('srv-estado')?.value || null,
    ubicacion_catalogo_id: document.getElementById('srv-ubicacion')?.value || null,
    so_id:            document.getElementById('srv-so')?.value || null,
    procesador:       document.getElementById('srv-procesador')?.value.trim() || null,
    memoria_ram:      document.getElementById('srv-ram')?.value.trim() || null,
    disco:            document.getElementById('srv-disco')?.value.trim() || null,
    ip_lan:           document.getElementById('srv-ip-lan')?.value.trim() || null,
    ip_salida:        document.getElementById('srv-ip-salida')?.value.trim() || null,
    observaciones:    document.getElementById('srv-observaciones')?.value.trim() || null,
    pendientes:       document.getElementById('srv-pendientes')?.value.trim() || null,
  };

  // Aplicabilidad. El backend fuerza la invariante (owner-in-set); aquí enviamos la selección.
  const aplicaTodas = document.getElementById('srv-aplic-todas')?.checked || false;
  const checkedEmp = [...document.querySelectorAll('.srv-aplic-emp:checked')].map(c => c.value);
  body.aplica_todas = aplicaTodas;
  body.empresa_ids = aplicaTodas ? [] : checkedEmp;
  if (!aplicaTodas && !checkedEmp.length) {
    notif('Selecciona al menos una empresa (o elige "Aplica a todas")', 'error'); return;
  }

  let ok;
  if (_servidorEditId) {
    ok = await apiRaw(`/servidores/${_servidorEditId}`, { method: 'PUT', body: JSON.stringify(body) });
  } else {
    body.empresa_id = empresaActual || checkedEmp[0] || null;
    if (!body.empresa_id) { notif('Selecciona la empresa dueña (o una empresa específica) antes de guardar', 'error'); return; }
    body.herramienta_ids = [];
    ok = await apiRaw('/servidores', { method: 'POST', body: JSON.stringify(body) });
  }

  if (ok && ok.ok) {
    notif(_servidorEditId ? 'Servidor actualizado' : 'Servidor registrado');
    cerrarModal('modal-servidor');
    cargarServidores();
    cargarStatsServidores();
  } else {
    const err = ok ? await ok.json().catch(() => ({})) : {};
    notif(err.detail || 'Error al guardar servidor', 'error');
  }
}

// ── Modal detalle (tabs) ──────────────────────────────────────────────────────

let _detalleServidor = null;

async function abrirDetalleServidor(id) {
  const data = await api(`/servidores/${id}`);
  if (!data) return;
  _detalleServidor = data;
  _renderDetalleGeneral(data);
  _renderDetalleHerramientas(data.herramientas || []);
  _renderDetalleServicios(data.servicios || []);
  _renderDetalleHistorial([]);
  _switchTabDetalle('general');
  abrirModal('modal-detalle-servidor');
}

function _switchTabDetalle(tab) {
  document.querySelectorAll('#modal-detalle-servidor .tab-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.tab === tab);
  });
  document.querySelectorAll('#modal-detalle-servidor [data-panel]').forEach(p => {
    p.style.display = p.dataset.panel === tab ? '' : 'none';
  });
  if (tab === 'historial' && _detalleServidor) _cargarHistorial(_detalleServidor.id);
}

function _renderDetalleGeneral(s) {
  const el = document.getElementById('detalle-srv-general');
  if (!el) return;
  const fila = (lbl, val) => `<tr><td style="color:var(--text3);font-size:11px;padding:4px 8px;width:140px">${lbl}</td><td style="font-size:12px;padding:4px 8px">${val||'—'}</td></tr>`;
  el.innerHTML = `
    <div style="display:flex;gap:12px;align-items:flex-start;flex-wrap:wrap">
      <div style="flex:1;min-width:240px">
        <div style="font-size:11px;color:var(--text3);margin-bottom:6px;font-weight:600;text-transform:uppercase">Identificación</div>
        <table style="width:100%;border-collapse:collapse">
          ${fila('Nombre',     s.nombre)}
          ${fila('Hostname',   `<span style="font-family:var(--mono);font-size:11px">${s.hostname}</span>`)}
          ${fila('IP LAN',     s.ip_lan ? `<span style="font-family:var(--mono)">${s.ip_lan}</span>` : null)}
          ${fila('IP Salida',  s.ip_salida ? `<span style="font-family:var(--mono)">${s.ip_salida}</span>` : null)}
          ${fila('ID Servicio',s.id_servicio)}
          ${fila('Kawak ID',   s.kawak_id)}
          ${fila('GLPI ID',    s.glpi_id)}
          ${fila('Empresa',    s.nombre_empresa)}
        </table>
      </div>
      <div style="flex:1;min-width:240px">
        <div style="font-size:11px;color:var(--text3);margin-bottom:6px;font-weight:600;text-transform:uppercase">Clasificación</div>
        <table style="width:100%;border-collapse:collapse">
          ${fila('Tipo',       s.tipo_nombre)}
          ${fila('Ambiente',   s.ambiente_nombre ? `${_colorDot(s.ambiente_color)}${s.ambiente_nombre}` : null)}
          ${fila('Criticidad', s.criticidad_nombre ? `<span style="color:${s.criticidad_color}">${s.criticidad_nombre}</span>` : null)}
          ${fila('Estado',     s.estado_nombre ? `${_colorDot(s.estado_color)}${s.estado_nombre}` : null)}
          ${fila('Ubicación',  s.ubicacion_nombre)}
          ${fila('Aplica a',   s.aplica_todas
              ? '<span class="badge asignado">Todas las empresas</span>'
              : (s.empresas_aplicables || []).map(e => e.nombre).filter(Boolean)
                  .map(n => `<span class="badge badge-outline" style="margin:1px 2px">${_srvEsc(n)}</span>`).join(''))}
        </table>
      </div>
      <div style="flex:1;min-width:240px">
        <div style="font-size:11px;color:var(--text3);margin-bottom:6px;font-weight:600;text-transform:uppercase">Hardware / SO</div>
        <table style="width:100%;border-collapse:collapse">
          ${fila('SO',         s.so_nombre)}
          ${fila('Familia SO', s.so_familia)}
          ${fila('Procesador', s.procesador)}
          ${fila('RAM',        s.memoria_ram)}
          ${fila('Disco',      s.disco)}
        </table>
      </div>
    </div>
    ${s.observaciones ? `<div style="margin-top:12px;padding:8px 10px;background:var(--bg3);border-radius:6px;font-size:12px"><b>Observaciones:</b> ${s.observaciones}</div>` : ''}
    ${s.pendientes    ? `<div style="margin-top:6px;padding:8px 10px;background:#fff3cd22;border:1px solid #f39c1244;border-radius:6px;font-size:12px"><b>Pendientes:</b> ${s.pendientes}</div>` : ''}
    <div style="margin-top:16px;display:flex;gap:8px">
      ${hasPermiso('servidores.editar') ? `<button class="btn btn-sm" onclick="abrirModalServidor('${s.id}');cerrarModal('modal-detalle-servidor')">Editar</button>` : ''}
      ${hasPermiso('servidores.eliminar') && s.activo !== false ? `<button class="btn btn-sm btn-ghost" style="color:var(--danger)" onclick="darDeBajaServidor('${s.id}')">Dar de baja</button>` : ''}
      ${s.activo === false ? `<span class="badge baja" style="align-self:center">Dado de baja${s.motivo_baja ? ' — '+_srvEsc(s.motivo_baja) : ''}</span>` : ''}
    </div>`;
}

function _renderDetalleHerramientas(herramientas) {
  const el = document.getElementById('detalle-srv-herramientas');
  if (!el) return;

  const ESTADO_COLOR = {
    instalado: '#27ae60', configurado: '#3498db', pendiente: '#f39c12',
    obsoleto: '#e74c3c', removido: '#95a5a6'
  };

  const canEdit = hasPermiso('servidores.editar');
  const rows = herramientas.map(h => `
    <tr>
      <td><b>${h.nombre}</b></td>
      <td><span class="badge badge-outline" style="font-size:10px">${h.categoria}</span></td>
      <td><span style="color:${ESTADO_COLOR[h.estado]||'#888'};font-size:11px">${h.estado}</span></td>
      <td style="font-family:var(--mono);font-size:11px">${h.version||'—'}</td>
      <td style="font-size:11px">${h.fecha_instalacion||'—'}</td>
      <td>${canEdit ? `<button class="btn btn-ghost btn-sm" style="color:var(--danger)" onclick="removerHerramientaServidor('${h.id}')">✕</button>` : ''}</td>
    </tr>`).join('');

  const optsHerr = (catServidores?.herramientas || [])
    .map(h => `<option value="${h.id}">${h.nombre} (${h.categoria})</option>`)
    .join('');

  el.innerHTML = `
    ${canEdit ? `
    <div style="margin-bottom:8px;display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap">
      <select id="new-herr-id" style="flex:1;min-width:180px">
        <option value="">— Seleccionar herramienta —</option>
        ${optsHerr}
      </select>
      <select id="new-herr-estado" style="width:130px">
        <option value="pendiente">Pendiente</option>
        <option value="instalado">Instalado</option>
        <option value="configurado">Configurado</option>
      </select>
      <input id="new-herr-version" placeholder="Versión" style="width:90px" class="finput">
      <button class="btn btn-sm" onclick="agregarHerramientaServidor()">+ Asignar</button>
      <button class="btn btn-ghost btn-sm" style="color:var(--cyan);border-color:rgba(var(--accent-rgb),0.3)"
              onclick="document.getElementById('nueva-herr-form').style.display=document.getElementById('nueva-herr-form').style.display==='none'?'':'none'">
        ＋ Nueva herramienta
      </button>
    </div>
    <div id="nueva-herr-form" style="display:none;margin-bottom:12px;padding:10px 12px;background:rgba(var(--accent-rgb),0.05);border:1px solid rgba(var(--accent-rgb),0.2);border-radius:8px">
      <div style="font-size:10px;color:var(--text3);text-transform:uppercase;letter-spacing:1px;font-weight:600;margin-bottom:8px">Agregar al catálogo</div>
      <div style="display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap">
        <input id="nueva-herr-nombre" placeholder="Nombre *" style="flex:1;min-width:140px" class="finput">
        <select id="nueva-herr-cat" style="width:150px" class="fselect">
          <option value="Monitoreo">Monitoreo</option>
          <option value="SIEM">SIEM</option>
          <option value="EDR/AV">EDR/AV</option>
          <option value="RMM">RMM</option>
          <option value="Vulnerabilidades">Vulnerabilidades</option>
          <option value="Backup">Backup</option>
          <option value="Gestión de Configuración">Gestión de Configuración</option>
          <option value="APM">APM</option>
          <option value="General">General</option>
        </select>
        <input id="nueva-herr-desc" placeholder="Descripción (opcional)" style="flex:2;min-width:160px" class="finput">
        <button class="btn btn-sm" onclick="crearHerramientaCatalogo()">Guardar</button>
        <button class="btn btn-ghost btn-sm" onclick="document.getElementById('nueva-herr-form').style.display='none'">Cancelar</button>
      </div>
    </div>` : ''}
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Herramienta</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Categoría</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Estado</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Versión</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Instalado</th>
        <th style="padding:4px 8px"></th>
      </tr></thead>
      <tbody>${rows || '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:16px">Sin herramientas asignadas</td></tr>'}</tbody>
    </table>`;
}

function _renderDetalleServicios(servicios) {
  const el = document.getElementById('detalle-srv-servicios');
  if (!el) return;
  const canEdit = hasPermiso('servidores.editar');
  const rows = servicios.map(sv => `
    <tr>
      <td><b>${sv.nombre_servicio}</b></td>
      <td style="font-size:11px">${sv.descripcion||'—'}</td>
      <td style="font-family:var(--mono);font-size:11px">${sv.puerto||'—'}</td>
      <td style="font-size:11px">${sv.protocolo||'—'}</td>
      <td><span style="color:${sv.activo?'#27ae60':'#95a5a6'};font-size:11px">${sv.activo?'Activo':'Inactivo'}</span></td>
      <td>${canEdit ? `<button class="btn btn-ghost btn-sm" style="color:var(--danger)" onclick="eliminarServicioServidor('${sv.id}')">✕</button>` : ''}</td>
    </tr>`).join('');

  el.innerHTML = `
    ${canEdit ? `
    <div style="margin-bottom:10px;display:flex;gap:8px;align-items:flex-end;flex-wrap:wrap">
      <input id="new-svc-nombre" placeholder="Nombre del servicio *" style="flex:1;min-width:150px">
      <input id="new-svc-puerto" placeholder="Puerto" style="width:80px" type="number">
      <input id="new-svc-protocolo" placeholder="TCP/UDP" style="width:80px">
      <input id="new-svc-desc" placeholder="Descripción" style="flex:1;min-width:150px">
      <button class="btn btn-sm" onclick="agregarServicioServidor()">Agregar</button>
    </div>` : ''}
    <table style="width:100%;border-collapse:collapse;font-size:12px">
      <thead><tr>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Servicio</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Descripción</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Puerto</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Protocolo</th>
        <th style="text-align:left;padding:4px 8px;color:var(--text3);font-size:11px">Estado</th>
        <th style="padding:4px 8px"></th>
      </tr></thead>
      <tbody>${rows || '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:16px">Sin servicios registrados</td></tr>'}</tbody>
    </table>`;
}

function _renderDetalleHistorial(registros) {
  const el = document.getElementById('detalle-srv-historial');
  if (!el) return;
  if (!registros.length) {
    el.innerHTML = '<p style="text-align:center;color:var(--text3);padding:20px">Sin registros</p>';
    return;
  }
  el.innerHTML = `<table style="width:100%;border-collapse:collapse;font-size:11px">
    <thead><tr>
      <th style="text-align:left;padding:4px 8px;color:var(--text3)">Fecha</th>
      <th style="text-align:left;padding:4px 8px;color:var(--text3)">Tipo</th>
      <th style="text-align:left;padding:4px 8px;color:var(--text3)">Campo</th>
      <th style="text-align:left;padding:4px 8px;color:var(--text3)">Anterior</th>
      <th style="text-align:left;padding:4px 8px;color:var(--text3)">Nuevo</th>
      <th style="text-align:left;padding:4px 8px;color:var(--text3)">Usuario</th>
    </tr></thead>
    <tbody>${registros.map(r => `
      <tr>
        <td style="padding:4px 8px;color:var(--text3)">${r.created_at ? r.created_at.slice(0,16).replace('T',' ') : '—'}</td>
        <td style="padding:4px 8px"><span class="badge badge-outline" style="font-size:9px">${r.tipo_cambio}</span></td>
        <td style="padding:4px 8px">${r.campo_modificado||'—'}</td>
        <td style="padding:4px 8px;color:var(--danger)">${r.valor_anterior||'—'}</td>
        <td style="padding:4px 8px;color:#27ae60">${r.valor_nuevo||'—'}</td>
        <td style="padding:4px 8px">${r.usuario||'—'}</td>
      </tr>`).join('')}
    </tbody></table>`;
}

async function _cargarHistorial(servidorId) {
  const data = await api(`/servidores/${servidorId}/historial`);
  _renderDetalleHistorial(data || []);
}

// ── Acciones herramientas / servicios ─────────────────────────────────────────

async function agregarHerramientaServidor() {
  const sid   = _detalleServidor?.id;
  const hid   = document.getElementById('new-herr-id')?.value;
  const estado = document.getElementById('new-herr-estado')?.value || 'pendiente';
  const version = document.getElementById('new-herr-version')?.value.trim() || null;
  if (!sid || !hid) { notif('Selecciona una herramienta', 'error'); return; }

  const ok = await apiRaw(`/servidores/${sid}/herramientas`, {
    method: 'POST',
    body: JSON.stringify({ herramienta_id: hid, estado, version }),
  });
  if (ok?.ok) {
    notif('Herramienta agregada');
    const data = await api(`/servidores/${sid}`);
    if (data) { _detalleServidor = data; _renderDetalleHerramientas(data.herramientas || []); }
  } else {
    const err = ok ? await ok.json().catch(() => ({})) : {};
    notif(err.detail || 'Error al agregar herramienta', 'error');
  }
}

async function removerHerramientaServidor(shId) {
  const sid = _detalleServidor?.id;
  if (!sid) return;
  const ok = await apiRaw(`/servidores/${sid}/herramientas/${shId}`, { method: 'DELETE' });
  if (ok?.ok || ok?.status === 204) {
    notif('Herramienta removida');
    const data = await api(`/servidores/${sid}`);
    if (data) { _detalleServidor = data; _renderDetalleHerramientas(data.herramientas || []); }
  } else {
    notif('Error al remover herramienta', 'error');
  }
}

async function agregarServicioServidor() {
  const sid    = _detalleServidor?.id;
  const nombre = document.getElementById('new-svc-nombre')?.value.trim();
  if (!sid || !nombre) { notif('El nombre del servicio es obligatorio', 'error'); return; }

  const body = {
    nombre_servicio: nombre,
    puerto:    parseInt(document.getElementById('new-svc-puerto')?.value) || null,
    protocolo: document.getElementById('new-svc-protocolo')?.value.trim() || null,
    descripcion: document.getElementById('new-svc-desc')?.value.trim() || null,
    activo: true,
  };
  const ok = await apiRaw(`/servidores/${sid}/servicios`, { method: 'POST', body: JSON.stringify(body) });
  if (ok?.ok) {
    notif('Servicio agregado');
    const data = await api(`/servidores/${sid}`);
    if (data) { _detalleServidor = data; _renderDetalleServicios(data.servicios || []); }
  } else {
    const err = ok ? await ok.json().catch(() => ({})) : {};
    notif(err.detail || 'Error al agregar servicio', 'error');
  }
}

async function eliminarServicioServidor(svId) {
  const sid = _detalleServidor?.id;
  if (!sid) return;
  const ok = await apiRaw(`/servidores/${sid}/servicios/${svId}`, { method: 'DELETE' });
  if (ok?.ok || ok?.status === 204) {
    notif('Servicio eliminado');
    const data = await api(`/servidores/${sid}`);
    if (data) { _detalleServidor = data; _renderDetalleServicios(data.servicios || []); }
  } else {
    notif('Error al eliminar servicio', 'error');
  }
}

async function crearHerramientaCatalogo() {
  const nombre = document.getElementById('nueva-herr-nombre')?.value.trim();
  if (!nombre) { notif('El nombre es obligatorio', 'error'); return; }
  const body = {
    nombre,
    categoria:   document.getElementById('nueva-herr-cat')?.value || 'General',
    descripcion: document.getElementById('nueva-herr-desc')?.value.trim() || null,
  };
  const ok = await apiRaw('/servidores/herramientas-catalogo', { method: 'POST', body: JSON.stringify(body) });
  if (ok?.ok) {
    notif(`Herramienta '${nombre}' agregada al catálogo`);
    // Forzar recarga del catálogo para que aparezca en el select
    catServidores = null;
    await cargarCatalogosServidores();
    // Volver a renderizar el tab con la lista actual de herramientas del servidor
    if (_detalleServidor) {
      _renderDetalleHerramientas(_detalleServidor.herramientas || []);
    }
    document.getElementById('nueva-herr-form').style.display = 'none';
  } else {
    const err = ok ? await ok.json().catch(() => ({})) : {};
    notif(err.detail || 'Error al crear herramienta', 'error');
  }
}

// ── Dar de baja (con motivo) ────────────────────────────────────────────────--

function darDeBajaServidor(id) {
  if (!hasPermiso('servidores.eliminar')) return;
  _bajaServidorId = id;
  const inp = document.getElementById('srv-baja-motivo');
  if (inp) inp.value = '';
  abrirModal('modal-baja-servidor');
}

async function confirmarBajaServidor() {
  if (!_bajaServidorId) return;
  const motivo = (document.getElementById('srv-baja-motivo')?.value || '').trim();
  if (!motivo) { notif('El motivo de la baja es obligatorio', 'error'); return; }
  const res = await apiRaw(`/servidores/${_bajaServidorId}/dar-de-baja`, {
    method: 'POST', body: JSON.stringify({ motivo }),
  });
  if (res && res.ok) {
    notif('Servidor dado de baja');
    _bajaServidorId = null;
    cerrarModal('modal-baja-servidor');
    cerrarModal('modal-detalle-servidor');
    cargarServidores();
    cargarStatsServidores();
  } else {
    const e = res ? await res.json().catch(() => ({})) : {};
    notif(e.detail || 'No se pudo dar de baja el servidor', 'error');
  }
}

// Alterna entre ver vigentes y ver dados de baja en la lista principal.
function toggleVerBajaServidores(btn) {
  servidoresVerBaja = !servidoresVerBaja;
  if (btn) {
    btn.classList.toggle('active', servidoresVerBaja);
    btn.textContent = servidoresVerBaja ? 'Ver vigentes' : 'Dados de baja';
  }
  const nuevo = document.getElementById('srv-btn-nuevo');
  if (nuevo) nuevo.style.display = servidoresVerBaja ? 'none' : '';
  cargarServidores();
}
