// ── Redes module ──────────────────────────────────────────────────────────────
// Dos vistas: nivel 1 (cuartos técnicos, card grid) y nivel 2 (detalle + racks).
// Inventario aparte (como servidores). Sede reutiliza el catálogo per-empresa
// Catalogo categoria='sede' vía llenarSelectCatalogoEmpresa (core.js).

let redesCuartosCache = [];
let _redesCuartoActual = null;   // id del cuarto abierto en nivel 2
let _redesCuartoDetalle = null;  // detalle completo del cuarto abierto
let _redesDispositivos = { byRack: {}, byId: {}, fuera: [] };  // dispositivos del cuarto abierto
let _dispUbic = 'rack';          // modo de ubicación en el modal de dispositivo

// ── Mapeo tipo → color/icono (ÚNICO lugar; ajústalo aquí) ───────────────────────
// Los tipos vienen del catálogo abierto tipo_activo, así que se mapea por palabra
// clave con respaldo gris para lo no reconocido.
const REDES_TIPO_ESTILO = [
  { re: /switch/i,             color: '#185FA5', icon: 'ti-switch-3' },      // azul
  { re: /firewall|fortigate/i, color: '#993C1D', icon: 'ti-flame' },        // coral
  { re: /router/i,             color: '#6C4AB6', icon: 'ti-router' },       // púrpura
  { re: /patch/i,              color: '#0E7C7B', icon: 'ti-plug' },         // teal
  { re: /ont/i,                color: '#0E7C7B', icon: 'ti-device-desktop' },// teal
  { re: /ups/i,                color: '#5F5E5A', icon: 'ti-battery-2' },    // gris
  { re: /access\s*point|\bap\b/i, color: '#185FA5', icon: 'ti-access-point' }, // azul
  { re: /servidor|server/i,    color: '#633806', icon: 'ti-server' },       // ámbar
];
const REDES_TIPO_FALLBACK = { color: '#5F5E5A', icon: 'ti-device-desktop' };  // gris
function redesTipoEstilo(tipo) {
  const t = tipo || '';
  for (const m of REDES_TIPO_ESTILO) { if (m.re.test(t)) return m; }
  return REDES_TIPO_FALLBACK;
}

const REDES_U_PX = 22;  // altura visual por unidad de rack (U)

// ── Init / entrada al módulo ───────────────────────────────────────────────────

function initRedesView() {
  // Redes obedece al selector GLOBAL de empresa (empresaActual), como el resto
  // de módulos. No tiene filtro propio. Al cambiar la empresa global, el hook
  // recargarVistaActual() vuelve a ejecutar volverACuartos() (ver core.js).
  volverACuartos();
}

function _puedeGestionar() { return hasPermiso('redes.gestionar'); }

// ── NIVEL 1: Cuartos técnicos ───────────────────────────────────────────────────

let redesFiltroSede = '';   // '' = todas las sedes (2º filtro, dentro de la empresa activa)

async function cargarCuartos() {
  // Filtra por el selector global (igual que activos/servidores). '' = todas en alcance.
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  const data = await api(`/redes/cuartos?${p}`);
  redesCuartosCache = data || [];
  redesFiltroSede = '';            // reset al (re)cargar (p.ej. cambio de empresa global)
  _poblarFiltroSede();             // repuebla opciones con las sedes de la empresa activa
  renderCuartos(_cuartosFiltrados());
}

// Cuartos visibles tras aplicar el filtro de sede (dentro de la empresa ya scoped en backend).
function _cuartosFiltrados() {
  if (!redesFiltroSede) return redesCuartosCache;
  return redesCuartosCache.filter(c => c.sede && c.sede.id === redesFiltroSede);
}

// Opciones del filtro = sedes que EFECTIVAMENTE tienen cuartos (derivadas del cache;
// sin opciones muertas, sin consulta extra). Reset a "Todas las sedes".
function _poblarFiltroSede() {
  const sel = document.getElementById('redes-filtro-sede');
  if (!sel) return;
  const map = new Map();
  redesCuartosCache.forEach(c => { if (c.sede && c.sede.id) map.set(c.sede.id, c.sede.nombre); });
  const sedes = [...map.entries()].sort((a, b) => (a[1] || '').localeCompare(b[1] || ''));
  sel.innerHTML = '<option value="">Todas las sedes</option>' +
    sedes.map(([id, nom]) => `<option value="${id}">${_esc(nom)}</option>`).join('');
  sel.value = redesFiltroSede;     // '' tras el reset
}

function filtrarCuartosPorSede(sedeId) {
  redesFiltroSede = sedeId || '';
  renderCuartos(_cuartosFiltrados());
}

function renderCuartos(list) {
  const grid = document.getElementById('redes-cuartos-grid');
  if (!grid) return;
  if (!list.length) {
    grid.innerHTML = `<div class="redes-empty">
      <i class="ti ti-server-2"></i>
      <p>Sin cuartos técnicos${_puedeGestionar() ? '. Crea el primero con “Nuevo cuarto técnico”.' : '.'}</p>
    </div>`;
    return;
  }
  grid.innerHTML = list.map(c => {
    const empresa = c.empresa ? c.empresa.nombre : '—';
    const sede    = c.sede ? c.sede.nombre : '—';
    const detalle = c.ubicacion_detalle ? ` · ${_esc(c.ubicacion_detalle)}` : '';
    return `
    <div class="redes-card" onclick="abrirCuarto('${c.id}')">
      <div class="redes-card-top">
        <div class="redes-card-ident"><i class="ti ti-server-2"></i> ${_esc(c.identificador)}</div>
        ${c.nombre ? `<div class="redes-card-nombre">${_esc(c.nombre)}</div>` : ''}
      </div>
      <div class="redes-card-meta">
        <div class="redes-card-row"><i class="ti ti-building"></i> ${_esc(empresa)}</div>
        <div class="redes-card-row"><i class="ti ti-map-pin"></i> ${_esc(sede)}${detalle}</div>
      </div>
      <div class="redes-card-foot">
        <span class="redes-chip"><i class="ti ti-server"></i> ${c.num_racks} rack${c.num_racks === 1 ? '' : 's'}</span>
        <span class="redes-chip"><i class="ti ti-device-desktop"></i> ${c.num_dispositivos} dispositivo${c.num_dispositivos === 1 ? '' : 's'}</span>
      </div>
    </div>`;
  }).join('');
}

function volverACuartos() {
  _redesCuartoActual = null;
  _redesCuartoDetalle = null;
  document.getElementById('redes-nivel2').style.display = 'none';
  document.getElementById('redes-nivel1').style.display = '';
  cargarCuartos();
}

// ── NIVEL 2: Detalle de un cuarto ────────────────────────────────────────────────

async function abrirCuarto(cuartoId) {
  const c = await api(`/redes/cuartos/${cuartoId}`);
  if (!c) { notif('No se pudo abrir el cuarto técnico', 'error'); return; }
  _redesCuartoActual = cuartoId;
  _redesCuartoDetalle = c;

  // Cargar dispositivos del cuarto (en rack + fuera de rack)
  const disp = await api(`/redes/cuartos/${cuartoId}/dispositivos`) || { en_rack: [], fuera_de_rack: [] };
  _redesDispositivos = { byRack: {}, byId: {}, fuera: disp.fuera_de_rack || [] };
  (disp.en_rack || []).forEach(d => {
    (_redesDispositivos.byRack[d.rack_id] = _redesDispositivos.byRack[d.rack_id] || []).push(d);
    _redesDispositivos.byId[d.id] = d;
  });
  (disp.fuera_de_rack || []).forEach(d => { _redesDispositivos.byId[d.id] = d; });

  document.getElementById('redes-nivel1').style.display = 'none';
  document.getElementById('redes-nivel2').style.display = '';

  const empresa = c.empresa ? c.empresa.nombre : '—';
  const sede    = c.sede ? c.sede.nombre : '—';

  document.getElementById('redes-bc-empresa').textContent = empresa;
  document.getElementById('redes-bc-sede').textContent    = sede;
  document.getElementById('redes-bc-ident').textContent   = c.identificador;

  document.getElementById('redes-det-titulo').textContent =
    c.identificador + (c.nombre ? ` — ${c.nombre}` : '');
  document.getElementById('redes-det-sub').textContent =
    `${empresa} · ${sede}${c.ubicacion_detalle ? ' · ' + c.ubicacion_detalle : ''}`;

  const racks = c.racks || [];
  document.getElementById('redes-det-body').innerHTML = `
    <div class="redes-det-stats">
      <div class="redes-stat"><div class="redes-stat-num">${racks.length}</div><div class="redes-stat-lbl">Racks</div></div>
      <div class="redes-stat"><div class="redes-stat-num">${c.num_dispositivos}</div><div class="redes-stat-lbl">Dispositivos</div></div>
    </div>
    ${c.descripcion ? `<div class="redes-det-desc">${_esc(c.descripcion)}</div>` : ''}`;

  renderRacks(racks);
  renderFuera(_redesDispositivos.fuera);
}

function renderRacks(racks) {
  const cont = document.getElementById('redes-racks-grid');
  if (!cont) return;
  if (!racks.length) {
    cont.innerHTML = `<div class="redes-empty">
      <i class="ti ti-server"></i>
      <p>Este cuarto no tiene racks${_puedeGestionar() ? '. Agrega uno con “Agregar rack”.' : '.'}</p>
    </div>`;
    return;
  }
  const gestionar = _puedeGestionar();
  cont.innerHTML = racks.map(r => {
    const devs = _redesDispositivos.byRack[r.id] || [];
    const cap = r.capacidad_u || 0;
    return `
    <div class="rack-card">
      <div class="rack-card-head">
        <div class="rack-card-title"><i class="ti ti-server"></i> ${_esc(r.nombre)}</div>
        ${gestionar ? `<button class="rack-edit-btn" title="Editar rack" onclick="abrirModalRack('${r.id}')"><i class="ti ti-pencil"></i></button>` : ''}
      </div>
      <div class="rack-card-sub">${cap}U · ${r.usadas_u || 0}U usadas · ${r.libres_u != null ? r.libres_u : (cap - (r.usadas_u || 0))}U libres</div>
      ${r.descripcion ? `<div class="rack-card-desc">${_esc(r.descripcion)}</div>` : ''}
      <div class="rack-body">${_rackBodyHTML(r, devs, true)}</div>
      ${_rackLegend(devs)}
      <button class="btn btn-ghost btn-sm rack-ver-btn" onclick="verRackCompleto('${r.id}')">Ver rack completo</button>
    </div>`;
  }).join('');
}

// Dibuja el cuerpo del rack: slots de U de arriba (capacidad) hacia abajo (1),
// con los dispositivos en su posición/tamaño y color por tipo. Colapsa tramos
// libres largos (>4U) en una banda "⋮ NU libres ⋮" cuando collapse=true.
function _rackBodyHTML(rack, devices, collapse) {
  const cap = rack.capacidad_u || 0;
  const byTop = {};            // U superior de cada dispositivo → dispositivo
  const occupied = new Set();  // todas las U ocupadas
  (devices || []).forEach(d => {
    if (d.posicion_u == null) return;
    const size = d.tamano_u || 1;
    const top = d.posicion_u + size - 1;
    byTop[top] = d;
    for (let k = d.posicion_u; k <= top; k++) occupied.add(k);
  });

  let html = '';
  let u = cap;
  while (u >= 1) {
    if (byTop[u]) {
      const d = byTop[u];
      html += _deviceSlotHTML(d, d.tamano_u || 1);
      u -= (d.tamano_u || 1);
    } else if (occupied.has(u)) {
      u -= 1;  // defensivo (no debería ocurrir sin solapes)
    } else {
      let runTop = u;
      while (u >= 1 && !occupied.has(u) && !byTop[u]) u -= 1;
      const runBot = u + 1;
      const runLen = runTop - runBot + 1;
      if (collapse && runLen > 4) {
        html += `<div class="rack-gap" style="height:${REDES_U_PX + 10}px">
          <span class="rack-gap-lbl">⋮ U${runTop}–U${runBot} · ${runLen}U libres ⋮</span></div>`;
      } else {
        for (let k = runTop; k >= runBot; k--) {
          html += `<div class="rack-slot rack-slot-free" style="height:${REDES_U_PX}px">
            <span class="rack-u-num">${k}</span><span class="rack-free-lbl">libre</span></div>`;
        }
      }
    }
  }
  return `<div class="rack-frame">${html}</div>`;
}

function _deviceSlotHTML(d, size) {
  const st = redesTipoEstilo(d.tipo_activo);
  const h = REDES_U_PX * size;
  const top = d.posicion_u + size - 1;
  const rango = size > 1 ? `${d.posicion_u}–${top}` : `${d.posicion_u}`;
  const label = d.consecutivo || '—';
  const meta = [d.tipo_activo, d.modelo, d.num_puertos ? `${d.num_puertos}p` : null, `${size}U`].filter(Boolean).join(' · ');
  const pencil = _puedeGestionar()
    ? `<button class="rack-dev-edit" title="Editar montaje" onclick="event.stopPropagation();abrirModalDispositivo('${d.id}')"><i class="ti ti-pencil"></i></button>` : '';
  return `<div class="rack-slot rack-dev" style="height:${h}px;background:${st.color}"
      title="${_esc(label)} — ${_esc(meta)}" onclick="abrirHojaVida('${d.activo_id}')">
      <span class="rack-u-num rack-u-num-dev">${rango}</span>
      <i class="ti ${st.icon} rack-dev-ic"></i>
      <span class="rack-dev-txt"><span class="rack-dev-name">${_esc(label)}</span><span class="rack-dev-meta">${_esc(meta)}</span></span>
      ${pencil}
    </div>`;
}

function _rackLegend(devices) {
  const tipos = [...new Set((devices || []).map(d => d.tipo_activo).filter(Boolean))];
  if (!tipos.length) return '';
  return `<div class="rack-legend">` + tipos.map(t => {
    const st = redesTipoEstilo(t);
    return `<span class="rack-leg-item"><span class="rack-leg-dot" style="background:${st.color}"></span>${_esc(t)}</span>`;
  }).join('') + `</div>`;
}

function renderFuera(list) {
  const wrap = document.getElementById('redes-fuera-wrap');
  const grid = document.getElementById('redes-fuera-grid');
  if (!wrap || !grid) return;
  if (!list.length) { wrap.style.display = 'none'; return; }
  wrap.style.display = '';
  grid.innerHTML = list.map(d => {
    const st = redesTipoEstilo(d.tipo_activo);
    const mm = [d.marca, d.modelo].filter(Boolean).join(' ');
    const line = [mm, d.ip_gestion, d.ubicacion_fisica].filter(Boolean).map(_esc).join(' · ');
    const pencil = _puedeGestionar()
      ? `<button class="fuera-edit" title="Editar montaje" onclick="event.stopPropagation();abrirModalDispositivo('${d.id}')"><i class="ti ti-pencil"></i></button>` : '';
    return `
    <div class="fuera-card" onclick="abrirHojaVida('${d.activo_id}')">
      <div class="fuera-head">
        <span class="fuera-ic" style="background:${st.color}"><i class="ti ${st.icon}"></i></span>
        <span class="fuera-name">${_esc(d.consecutivo)}</span>
        ${pencil}
      </div>
      ${d.tipo_activo ? `<span class="fuera-pill" style="border-color:${st.color};color:${st.color}">${_esc(d.tipo_activo)}</span>` : ''}
      ${line ? `<div class="fuera-line">${line}</div>` : ''}
      ${d.conexion ? `<div class="fuera-conn"><i class="ti ti-plug-connected"></i> conectado a: ${_esc(d.conexion)}</div>` : ''}
    </div>`;
  }).join('');
}

// "Ver rack completo": el rack a tamaño completo (sin colapsar) + lista de dispositivos.
function verRackCompleto(rackId) {
  const rack = (_redesCuartoDetalle.racks || []).find(r => r.id === rackId);
  if (!rack) return;
  const devs = (_redesDispositivos.byRack[rackId] || []).slice()
    .sort((a, b) => (b.posicion_u || 0) - (a.posicion_u || 0));
  document.getElementById('modal-rack-full-title').textContent =
    `${rack.nombre} — ${rack.capacidad_u}U (${rack.usadas_u || 0}U usadas)`;
  const lista = devs.length
    ? devs.map(d => {
        const st = redesTipoEstilo(d.tipo_activo);
        const top = d.posicion_u + (d.tamano_u || 1) - 1;
        const rango = (d.tamano_u || 1) > 1 ? `U${d.posicion_u}–U${top}` : `U${d.posicion_u}`;
        const meta = [d.tipo_activo, d.marca, d.modelo].filter(Boolean).map(_esc).join(' · ');
        return `<div class="rackfull-row" onclick="cerrarModal('modal-rack-full');abrirHojaVida('${d.activo_id}')">
          <span class="rackfull-dot" style="background:${st.color}"></span>
          <span class="rackfull-pos">${rango}</span>
          <span class="rackfull-name">${_esc(d.consecutivo)}<span class="rackfull-meta">${meta}</span></span>
          ${d.ip_gestion ? `<span class="rackfull-ip">${_esc(d.ip_gestion)}</span>` : ''}
        </div>`;
      }).join('')
    : '<div class="redes-empty-sm">Rack vacío</div>';
  document.getElementById('modal-rack-full-body').innerHTML = `
    <div class="rackfull-layout">
      <div class="rackfull-viz"><div class="rack-body rack-body-full">${_rackBodyHTML(rack, _redesDispositivos.byRack[rackId] || [], false)}</div></div>
      <div class="rackfull-list">${lista}</div>
    </div>`;
  abrirModal('modal-rack-full');
}

// ── Exportar PDF del cuarto (mismo patrón que descargarActaMant: fetch con token → blob → abrir) ──
async function exportarCuartoPDF(btn) {
  if (!_redesCuartoActual) return;
  const original = btn ? btn.innerHTML : null;
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="ti ti-loader"></i> Generando…'; }
  try {
    const res = await fetch(`${API}/redes/cuartos/${_redesCuartoActual}/export-pdf`,
                            { headers: { 'Authorization': `Bearer ${TOKEN}` } });
    if (!res.ok) { notif('No se pudo generar el PDF', 'error'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    window.open(url, '_blank');
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) {
    notif('Error de red al generar el PDF', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = original; }
  }
}

// ── Modal Dispositivo ────────────────────────────────────────────────────────────

function _v(id) { const el = document.getElementById(id); return el ? el.value : ''; }

let _activosMontables = [];   // cache del picker (modo montar)

async function abrirModalDispositivo(dispId = null) {
  const gestionar = _puedeGestionar();
  if (!_redesCuartoActual) { notif('Abre un cuarto técnico primero', 'error'); return; }
  const d = dispId ? _redesDispositivos.byId[dispId] : null;
  if (!d && !gestionar) return;   // montar requiere gestionar

  const cuarto = _redesCuartoDetalle;
  document.getElementById('disp-id').value = d ? d.id : '';
  document.getElementById('disp-cuarto-label').innerHTML =
    `<i class="ti ti-server-2"></i> ${_esc(cuarto.identificador)}${cuarto.nombre ? ' — ' + _esc(cuarto.nombre) : ''}`;
  document.getElementById('modal-disp-title').textContent =
    d ? (gestionar ? 'Editar montaje' : 'Detalle del dispositivo') : 'Montar dispositivo';

  const set = (id, val) => { const el = document.getElementById(id); if (el) el.value = (val == null ? '' : val); };
  set('disp-ip',               d ? d.ip_gestion : '');
  set('disp-puertos',          d ? d.num_puertos : '');
  set('disp-conexion',         d ? d.conexion : '');
  set('disp-datos',            d ? d.datos_adicionales : '');
  set('disp-posicion',         d ? d.posicion_u : '');
  set('disp-tamano',           d ? (d.tamano_u || 1) : 1);
  set('disp-ubicacion-fisica', d ? d.ubicacion_fisica : '');
  _poblarRacksDisp(d ? d.rack_id : '');

  if (d) {
    // ── EDITAR montaje ── (el activo no se cambia)
    document.getElementById('disp-activo-id').value = d.activo_id;
    document.getElementById('disp-picker-wrap').style.display = 'none';
    _renderActivoSel({ id_placa_activo: d.consecutivo, tipo_activo: d.tipo_activo, marca: d.marca, modelo: d.modelo }, false);
    document.getElementById('disp-montaje-fields').style.display = '';
    setDispUbicacion(d.en_rack ? 'rack' : 'fuera');
  } else {
    // ── MONTAR ── (paso 1: elegir activo)
    document.getElementById('disp-activo-id').value = '';
    document.getElementById('disp-activo-sel').style.display = 'none';
    document.getElementById('disp-picker-wrap').style.display = '';
    document.getElementById('disp-montaje-fields').style.display = 'none';
    set('disp-buscar', '');
    const hayRacks = (cuarto.racks || []).length > 0;
    setDispUbicacion(hayRacks ? 'rack' : 'fuera');
    cargarActivosMontables();
  }

  _setDispReadonly(!gestionar);
  document.getElementById('disp-btn-desmontar').style.display = (d && gestionar) ? '' : 'none';
  abrirModal('modal-dispositivo');
}

// ── Picker de activos montables (modo montar) ──
async function cargarActivosMontables() {
  const list = document.getElementById('disp-picker-list');
  if (list) list.innerHTML = '<div class="redes-empty-sm">Cargando…</div>';
  _activosMontables = await api(`/redes/activos-montables?cuarto_id=${_redesCuartoActual}`) || [];
  filtrarActivosMontables();
}

function filtrarActivosMontables() {
  const q = (_v('disp-buscar') || '').toLowerCase();
  const list = document.getElementById('disp-picker-list');
  if (!list) return;
  const items = _activosMontables.filter(a => !q ||
    (a.id_placa_activo || '').toLowerCase().includes(q) ||
    (a.marca || '').toLowerCase().includes(q) ||
    (a.modelo || '').toLowerCase().includes(q) ||
    (a.tipo_activo || '').toLowerCase().includes(q));
  if (!items.length) {
    list.innerHTML = `<div class="redes-empty-sm">${_activosMontables.length
      ? 'Sin coincidencias'
      : 'No hay activos disponibles de tipo red para montar en esta empresa'}</div>`;
    return;
  }
  list.innerHTML = items.map(a => {
    const st = redesTipoEstilo(a.tipo_activo);
    const mm = [a.marca, a.modelo].filter(Boolean).join(' ');
    return `<div class="disp-pick" onclick="seleccionarActivoMontable('${a.id}')">
      <span class="disp-pick-dot" style="background:${st.color}"></span>
      <span class="disp-pick-txt"><strong>${_esc(a.id_placa_activo)}</strong><span>${_esc([a.tipo_activo, mm].filter(Boolean).join(' · '))}</span></span>
      <i class="ti ti-chevron-right"></i>
    </div>`;
  }).join('');
}

function seleccionarActivoMontable(activoId) {
  const a = _activosMontables.find(x => x.id === activoId);
  if (!a) return;
  document.getElementById('disp-activo-id').value = a.id;
  document.getElementById('disp-picker-wrap').style.display = 'none';
  _renderActivoSel(a, true);
  document.getElementById('disp-montaje-fields').style.display = '';
}

function cambiarActivoMontable() {
  document.getElementById('disp-activo-id').value = '';
  document.getElementById('disp-activo-sel').style.display = 'none';
  document.getElementById('disp-picker-wrap').style.display = '';
  document.getElementById('disp-montaje-fields').style.display = 'none';
}

function _renderActivoSel(a, allowChange) {
  const el = document.getElementById('disp-activo-sel');
  if (!el) return;
  const st = redesTipoEstilo(a.tipo_activo);
  const mm = [a.marca, a.modelo].filter(Boolean).join(' ');
  el.style.display = '';
  el.innerHTML = `
    <span class="disp-sel-ic" style="background:${st.color}"><i class="ti ${st.icon}"></i></span>
    <span class="disp-sel-txt"><strong>${_esc(a.id_placa_activo)}</strong><span>${_esc([a.tipo_activo, mm].filter(Boolean).join(' · '))}</span></span>
    ${allowChange ? `<button class="btn btn-ghost btn-sm" onclick="cambiarActivoMontable()">Cambiar</button>` : ''}`;
}

function _poblarRacksDisp(sel) {
  const el = document.getElementById('disp-rack');
  if (!el) return;
  const racks = _redesCuartoDetalle.racks || [];
  el.innerHTML = '<option value="">Seleccionar...</option>' +
    racks.map(r => `<option value="${r.id}"${r.id === sel ? ' selected' : ''}>${_esc(r.nombre)} (${r.capacidad_u}U)</option>`).join('');
}

function setDispUbicacion(mode) {
  _dispUbic = mode;
  document.getElementById('disp-seg-rack').classList.toggle('active', mode === 'rack');
  document.getElementById('disp-seg-fuera').classList.toggle('active', mode === 'fuera');
  document.getElementById('disp-rack-fields').style.display  = mode === 'rack' ? '' : 'none';
  document.getElementById('disp-fuera-fields').style.display = mode === 'fuera' ? '' : 'none';
}

function _setDispReadonly(ro) {
  ['disp-buscar', 'disp-rack', 'disp-posicion', 'disp-tamano', 'disp-ubicacion-fisica',
   'disp-ip', 'disp-puertos', 'disp-conexion', 'disp-datos', 'disp-seg-rack', 'disp-seg-fuera']
    .forEach(id => { const el = document.getElementById(id); if (el) el.disabled = ro; });
  document.getElementById('disp-btn-guardar').style.display = ro ? 'none' : '';
}

async function guardarDispositivo() {
  const id       = _v('disp-id');
  const activoId = _v('disp-activo-id');
  if (!id && !activoId) { notif('Selecciona un activo para montar', 'error'); return; }

  const body = {
    ip_gestion:        _v('disp-ip').trim() || null,
    num_puertos:       _v('disp-puertos') === '' ? null : parseInt(_v('disp-puertos'), 10),
    conexion:          _v('disp-conexion').trim() || null,
    datos_adicionales: _v('disp-datos').trim() || null,
  };

  if (_dispUbic === 'rack') {
    const rackId = _v('disp-rack');
    const pos = parseInt(_v('disp-posicion'), 10);
    const tam = parseInt(_v('disp-tamano'), 10) || 1;
    if (!rackId) { notif('Selecciona un rack', 'error'); return; }
    if (!Number.isFinite(pos) || pos < 1) { notif('La posición (U) debe ser ≥ 1', 'error'); return; }
    if (!Number.isFinite(tam) || tam < 1) { notif('El tamaño (U) debe ser ≥ 1', 'error'); return; }
    const rack = (_redesCuartoDetalle.racks || []).find(r => r.id === rackId);
    if (rack && pos + tam - 1 > rack.capacidad_u) {
      notif(`No cabe: ocuparía hasta U${pos + tam - 1} y el rack tiene ${rack.capacidad_u}U`, 'error'); return;
    }
    const otros = (_redesDispositivos.byRack[rackId] || []).filter(x => x.id !== id);
    for (const o of otros) {
      if (o.posicion_u == null) continue;
      const oTop = o.posicion_u + (o.tamano_u || 1) - 1;
      if (pos <= oTop && o.posicion_u <= pos + tam - 1) {
        notif(`Se solapa con «${o.consecutivo}» (U${o.posicion_u}–U${oTop})`, 'error'); return;
      }
    }
    body.rack_id = rackId; body.posicion_u = pos; body.tamano_u = tam; body.ubicacion_fisica = null;
  } else {
    body.rack_id = null; body.posicion_u = null; body.tamano_u = null;
    body.ubicacion_fisica = _v('disp-ubicacion-fisica').trim() || null;
  }

  let res;
  if (id) {
    res = await apiRaw(`/redes/dispositivos/${id}`, { method: 'PUT', body: JSON.stringify(body) });
  } else {
    body.cuarto_tecnico_id = _redesCuartoActual;
    body.activo_id = activoId;
    res = await apiRaw('/redes/dispositivos', { method: 'POST', body: JSON.stringify(body) });
  }

  if (res && res.ok) {
    notif(id ? 'Montaje actualizado' : 'Dispositivo montado');
    cerrarModal('modal-dispositivo');
    abrirCuarto(_redesCuartoActual);
  } else {
    notif(await _err(res, 'No se pudo guardar el montaje'), 'error');
  }
}

async function desmontarDispositivo() {
  const id = _v('disp-id');
  if (!id) return;
  if (!confirm('¿Desmontar este dispositivo? El activo volverá a estado "disponible".')) return;
  const res = await apiRaw(`/redes/dispositivos/${id}`, { method: 'DELETE' });
  if (res && res.ok) {
    let body = null;
    try { body = await res.json(); } catch (e) {}
    if (body && body.warning) notif(body.warning, 'error');
    else notif('Dispositivo desmontado — activo disponible');
    cerrarModal('modal-dispositivo');
    abrirCuarto(_redesCuartoActual);
  } else {
    notif(await _err(res, 'No se pudo desmontar el dispositivo'), 'error');
  }
}

// ── Modal Cuarto técnico ─────────────────────────────────────────────────────────

function abrirModalCuarto(cuarto = null) {
  if (!_puedeGestionar()) return;
  document.getElementById('cuarto-id').value = cuarto ? cuarto.id : '';
  document.getElementById('modal-cuarto-title').textContent =
    cuarto ? 'Editar cuarto técnico' : 'Nuevo cuarto técnico';

  ['cuarto-identificador', 'cuarto-nombre', 'cuarto-ubicacion-detalle', 'cuarto-descripcion']
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ''; });

  const selEmpresa = document.getElementById('cuarto-empresa');
  llenarSelectEmpresas('cuarto-empresa');

  if (cuarto) {
    selEmpresa.value = cuarto.empresa_id || '';
    selEmpresa.disabled = true;   // la empresa no se cambia al editar (evita reasignar sede)
    document.getElementById('cuarto-identificador').value     = cuarto.identificador || '';
    document.getElementById('cuarto-nombre').value            = cuarto.nombre || '';
    document.getElementById('cuarto-ubicacion-detalle').value = cuarto.ubicacion_detalle || '';
    document.getElementById('cuarto-descripcion').value       = cuarto.descripcion || '';
    // Poblar sedes de esa empresa y seleccionar la actual (por id de catálogo)
    _poblarSedesCuarto(cuarto.empresa_id, cuarto.sede_catalogo_id);
  } else {
    selEmpresa.disabled = false;
    // Prellena con la empresa global activa (si hay una); si es "Todas", queda sin elegir.
    const preset = empresaActual || '';
    selEmpresa.value = preset;
    _poblarSedesCuarto(preset, '');
  }

  abrirModal('modal-cuarto');
}

function onCambioEmpresaCuarto() {
  const empresaId = document.getElementById('cuarto-empresa').value;
  _poblarSedesCuarto(empresaId, '');
}

// Puebla el <select> de sede con el catálogo per-empresa (categoria='sede').
// El catálogo usa `valor` (string) como opción; aquí necesitamos el id del catálogo
// como valor de la opción, así que construimos el select manualmente pero reutilizando
// el mismo endpoint/mecanismo que llenarSelectCatalogoEmpresa.
async function _poblarSedesCuarto(empresaId, sedeIdActual) {
  const sel  = document.getElementById('cuarto-sede');
  const hint = document.getElementById('cuarto-sede-hint');
  if (!sel) return;
  if (!empresaId) {
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    if (hint) hint.style.display = 'none';
    return;
  }
  const data = await api(`/catalogos?categoria=sede&empresa_id=${empresaId}`) || [];
  sel.innerHTML = '<option value="">Seleccionar...</option>' +
    data.map(i => `<option value="${i.id}"${i.id === sedeIdActual ? ' selected' : ''}>${_esc(i.valor)}</option>`).join('');
  if (hint) hint.style.display = data.length ? 'none' : '';
}

async function guardarCuarto() {
  const id            = document.getElementById('cuarto-id').value;
  const empresa_id    = document.getElementById('cuarto-empresa').value;
  const sede_catalogo_id = document.getElementById('cuarto-sede').value;
  const identificador = document.getElementById('cuarto-identificador').value.trim();
  const nombre        = document.getElementById('cuarto-nombre').value.trim();
  const ubicacion_detalle = document.getElementById('cuarto-ubicacion-detalle').value.trim();
  const descripcion   = document.getElementById('cuarto-descripcion').value.trim();

  if (!empresa_id)        { notif('Selecciona una empresa', 'error'); return; }
  if (!sede_catalogo_id)  { notif('Selecciona una sede', 'error'); return; }
  if (!identificador)     { notif('El identificador es obligatorio', 'error'); return; }

  let res;
  if (id) {
    const body = { sede_catalogo_id, identificador, nombre: nombre || null,
                   descripcion: descripcion || null, ubicacion_detalle: ubicacion_detalle || null };
    res = await apiRaw(`/redes/cuartos/${id}`, { method: 'PUT', body: JSON.stringify(body) });
  } else {
    const body = { empresa_id, sede_catalogo_id, identificador, nombre: nombre || null,
                   descripcion: descripcion || null, ubicacion_detalle: ubicacion_detalle || null };
    res = await apiRaw('/redes/cuartos', { method: 'POST', body: JSON.stringify(body) });
  }

  if (res && res.ok) {
    notif(id ? 'Cuarto técnico actualizado' : 'Cuarto técnico creado');
    cerrarModal('modal-cuarto');
    if (_redesCuartoActual) { abrirCuarto(_redesCuartoActual); } else { cargarCuartos(); }
  } else {
    notif(await _err(res, 'No se pudo guardar el cuarto técnico'), 'error');
  }
}

// ── Modal Rack ───────────────────────────────────────────────────────────────────

function abrirModalRack(rackId = null) {
  if (!_puedeGestionar()) return;
  if (!_redesCuartoActual) { notif('Abre un cuarto técnico primero', 'error'); return; }
  const rack = rackId && _redesCuartoDetalle
    ? (_redesCuartoDetalle.racks || []).find(r => r.id === rackId)
    : null;
  document.getElementById('rack-id').value = rack ? rack.id : '';
  document.getElementById('modal-rack-title').textContent = rack ? 'Editar rack' : 'Nuevo rack';
  document.getElementById('rack-nombre').value      = rack ? (rack.nombre || '') : '';
  document.getElementById('rack-capacidad').value   = rack ? (rack.capacidad_u || 42) : 42;
  document.getElementById('rack-orden').value       = rack && rack.orden != null ? rack.orden : '';
  document.getElementById('rack-descripcion').value = rack ? (rack.descripcion || '') : '';
  abrirModal('modal-rack');
}

async function guardarRack() {
  const id          = document.getElementById('rack-id').value;
  const nombre      = document.getElementById('rack-nombre').value.trim();
  const capacidad_u = parseInt(document.getElementById('rack-capacidad').value, 10);
  const ordenRaw    = document.getElementById('rack-orden').value.trim();
  const descripcion = document.getElementById('rack-descripcion').value.trim();

  if (!nombre)                              { notif('El nombre del rack es obligatorio', 'error'); return; }
  if (!Number.isFinite(capacidad_u) || capacidad_u <= 0) { notif('La capacidad (U) debe ser mayor que 0', 'error'); return; }

  const body = {
    nombre,
    capacidad_u,
    descripcion: descripcion || null,
    orden: ordenRaw === '' ? null : parseInt(ordenRaw, 10),
  };

  let res;
  if (id) {
    res = await apiRaw(`/redes/racks/${id}`, { method: 'PUT', body: JSON.stringify(body) });
  } else {
    res = await apiRaw(`/redes/cuartos/${_redesCuartoActual}/racks`, { method: 'POST', body: JSON.stringify(body) });
  }

  if (res && res.ok) {
    notif(id ? 'Rack actualizado' : 'Rack agregado');
    cerrarModal('modal-rack');
    abrirCuarto(_redesCuartoActual);
  } else {
    notif(await _err(res, 'No se pudo guardar el rack'), 'error');
  }
}

// ── Helpers ────────────────────────────────────────────────────────────────────

function _esc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
async function _err(res, fallback) {
  if (!res) return fallback;
  try { const d = await res.json(); return d.detail || fallback; } catch (e) { return fallback; }
}
