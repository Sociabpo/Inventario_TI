// ── Hoja de Vida del Activo (vista de solo lectura) ────────────────────────────
let hojaVidaData = null;
let hvActivo = null;

function _hvFecha(v) { return v ? (typeof fFecha === 'function' ? fFecha(v) : String(v).slice(0, 10)) : '—'; }
function _hvMoney(v) { return (v == null) ? '—' : '$' + Number(v).toLocaleString('es-CO'); }
function _hvEsc(s) { return (s == null ? '' : String(s)).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }
function _hvAniosMeses(meses) {
  meses = meses || 0;
  const a = Math.floor(meses / 12), m = meses % 12;
  const partes = [];
  if (a) partes.push(a + (a === 1 ? ' año' : ' años'));
  if (m) partes.push(m + (m === 1 ? ' mes' : ' meses'));
  return partes.length ? partes.join(' ') : '0 meses';
}

// ── MODAL (resumen rápido) ───────────────────────────────────────────────────
async function abrirHojaVida(activoId) {
  const cont = document.getElementById('hv-content');
  cont.innerHTML = '<div style="text-align:center;color:var(--text3);padding:40px">Cargando resumen...</div>';
  abrirModal('modal-hoja-vida');
  const data = await api(`/activos/${activoId}/hoja-de-vida`);
  if (!data) { cont.innerHTML = '<div style="text-align:center;color:var(--red);padding:40px">No se pudo cargar la hoja de vida</div>'; return; }
  hojaVidaData = data;
  hvActivo = data.activo;
  renderHojaVidaModal(data);
}

function renderHojaVidaModal(data) {
  const a = data.activo;
  document.getElementById('hv-modal-title').textContent = `Hoja de vida — ${a.id_placa_activo}`;
  const exp = document.getElementById('hv-btn-export');
  if (exp) exp.style.display = 'none';  // el modal es solo resumen; el detalle está en la vista
  document.getElementById('hv-content').innerHTML = `
    ${renderHVHeader(a, data.stats, data.usuario_actual, { alerta: false, infoMode: 'usuario' })}
    <div style="height:14px"></div>
    <div class="hv-section-title">Línea de tiempo</div>
    ${renderHVLineaTiempo(data.linea_de_tiempo)}
    <div style="height:18px"></div>
    <button class="btn btn-primary" style="width:100%" onclick="cerrarModal('modal-hoja-vida');irAExpedienteCompleto('${a.id}')">
      Ver expediente completo →
    </button>
  `;
}

// ── VISTA (expediente completo) ──────────────────────────────────────────────
function renderHojaVidaCompleta(data) {
  hojaVidaData = data;
  hvActivo = data.activo;
  const a = data.activo;
  document.getElementById('hv-view-content').innerHTML = `
    ${renderHVHeader(a, data.stats, data.usuario_actual, { alerta: true, infoMode: 'full' })}
    <div style="height:14px"></div>
    ${renderHVVidaUtil(data.vida_util, a)}
    <div class="hv-section-title">Línea de tiempo</div>
    ${renderHVLineaTiempo(data.linea_de_tiempo)}
    <div style="height:14px"></div>
    <div class="hv-section-title">Historial de responsables</div>
    ${renderHVResponsables(data.historial_responsables)}
    <div style="height:14px"></div>
    ${renderHVTabs(data)}
  `;
  switchHVTab('asignaciones', document.querySelector('#hv-tabs-nav .hv-tab'));
}

function irAExpedienteCompleto(activoId) {
  showView('hoja-vida-view', document.querySelector('[onclick*="hoja-vida-view"]'));
  setTimeout(() => cargarHojaVidaEnVista(activoId), 100);
}

// ── Búsqueda en la vista ─────────────────────────────────────────────────────
let _hvSearchTimer = null;
function hvBuscarActivo() {
  clearTimeout(_hvSearchTimer);
  const q = (document.getElementById('hv-search-input').value || '').trim();
  const cont = document.getElementById('hv-search-results');
  if (q.length < 2) { cont.innerHTML = ''; return; }
  _hvSearchTimer = setTimeout(async () => {
    const data = await api(`/activos/buscar-hoja-vida?q=${encodeURIComponent(q)}`) || [];
    if (!data.length) { cont.innerHTML = '<div style="font-size:12px;color:var(--text3);padding:6px">Sin coincidencias</div>'; return; }
    cont.innerHTML = data.map(r => `
      <div class="hv-search-item" onclick="cargarHojaVidaEnVista('${r.id}')">
        <span class="mono-tag">${r.id_placa_activo}</span>
        <span style="flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${_hvEsc([r.tipo_activo, r.marca, r.modelo].filter(Boolean).join(' '))}${r.serial ? ` · S/N ${_hvEsc(r.serial)}` : ''}</span>
        <span style="font-size:10px;color:var(--text3)">${r.nombre_usuario ? _hvEsc(r.nombre_usuario) : (typeof labelEstado === 'function' ? labelEstado(r.estado) : r.estado)}</span>
      </div>`).join('');
  }, 300);
}
function hvBuscarPrimero() {
  const items = document.querySelectorAll('#hv-search-results .hv-search-item');
  if (items.length) items[0].click();
}
async function cargarHojaVidaEnVista(activoId) {
  document.getElementById('hv-search-results').innerHTML = '';
  const cont = document.getElementById('hv-view-content');
  cont.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text3)">Cargando expediente...</div>';
  const data = await api(`/activos/${activoId}/hoja-de-vida`);
  if (!data) { cont.innerHTML = '<div style="text-align:center;padding:40px;color:var(--red)">No se pudo cargar el expediente</div>'; return; }
  renderHojaVidaCompleta(data);
}

// ── Device SVGs ────────────────────────────────────────────────────────────────
function getDeviceSVG(tipo) {
  const F = '#1c2128', S = '#30363d', A = '#267EE8';
  const t = (tipo || '').toLowerCase();
  if (['portatil', 'portátil', 'pc', 'aio'].some(x => t.includes(x)))
    return `<svg width="96" height="96" viewBox="0 0 96 96"><rect x="20" y="22" width="56" height="38" rx="3" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="26" y="28" width="44" height="26" rx="1" fill="#0d1117" stroke="${A}" stroke-width="1"/><path d="M14 66 H82 L76 60 H20 Z" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="40" y="62" width="16" height="2" rx="1" fill="${A}"/></svg>`;
  if (['monitor', 'televisor', 'video beam', 'beam'].some(x => t.includes(x)))
    return `<svg width="96" height="96" viewBox="0 0 96 96"><rect x="14" y="20" width="68" height="44" rx="3" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="20" y="26" width="56" height="32" rx="1" fill="#0d1117" stroke="${A}" stroke-width="1"/><rect x="42" y="64" width="12" height="8" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="32" y="72" width="32" height="4" rx="2" fill="${F}" stroke="${S}" stroke-width="2"/></svg>`;
  if (['celular', 'tablet', 'ipad'].some(x => t.includes(x)))
    return `<svg width="96" height="96" viewBox="0 0 96 96"><rect x="34" y="14" width="28" height="68" rx="5" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="38" y="22" width="20" height="48" rx="1" fill="#0d1117" stroke="${A}" stroke-width="1"/><circle cx="48" cy="76" r="2.5" fill="${A}"/></svg>`;
  if (['impresora', 'escaner', 'escáner'].some(x => t.includes(x)))
    return `<svg width="96" height="96" viewBox="0 0 96 96"><rect x="24" y="20" width="48" height="14" rx="2" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="18" y="34" width="60" height="30" rx="3" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="28" y="64" width="40" height="12" rx="2" fill="#0d1117" stroke="${A}" stroke-width="1"/><circle cx="66" cy="44" r="2.5" fill="${A}"/></svg>`;
  if (t.includes('servidor'))
    return `<svg width="96" height="96" viewBox="0 0 96 96"><rect x="26" y="18" width="44" height="16" rx="2" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="26" y="40" width="44" height="16" rx="2" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="26" y="62" width="44" height="16" rx="2" fill="${F}" stroke="${S}" stroke-width="2"/><circle cx="34" cy="26" r="2.5" fill="${A}"/><circle cx="34" cy="48" r="2.5" fill="${A}"/><circle cx="34" cy="70" r="2.5" fill="#00E5A0"/></svg>`;
  return `<svg width="96" height="96" viewBox="0 0 96 96"><rect x="22" y="24" width="52" height="40" rx="4" fill="${F}" stroke="${S}" stroke-width="2"/><rect x="28" y="30" width="40" height="28" rx="1" fill="#0d1117" stroke="${A}" stroke-width="1"/><rect x="38" y="68" width="20" height="4" rx="2" fill="${F}" stroke="${S}" stroke-width="2"/></svg>`;
}

// ── Header (compartido: modal y vista) ───────────────────────────────────────
// Garantía SIMPLE del recurso (campo garantia_fin en el activo) — fuente primaria.
// Sin alertas, solo estado: vigente / vencida / sin dato.
function _hvGarantiaSimple(a) {
  if (!a || !a.garantia_fin) return { txt: 'Sin garantía registrada', color: 'var(--text2)' };
  const fin = new Date(String(a.garantia_fin).slice(0, 10) + 'T00:00:00');
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
  const fechaTxt = fin.toLocaleDateString('es-CO');
  if (fin >= hoy) {
    const dias = Math.round((fin - hoy) / 86400000);
    return { txt: `En garantía hasta ${fechaTxt} (${dias} días)`, color: 'var(--green)' };
  }
  return { txt: `Garantía vencida (${fechaTxt})`, color: 'var(--text3)' };
}

function renderHVHeader(a, stats, usuario, opts) {
  opts = opts || {};
  const showAlerta = opts.alerta !== false;
  const infoMode = opts.infoMode || 'full';

  let alerta = '';
  if (stats.edad_meses > 48)
    alerta = `<div class="hv-alert-banner"><i class="ti ti-alert-triangle"></i> Activo en obsolescencia (${_hvAniosMeses(stats.edad_meses)} de antigüedad)</div>`;

  // Garantía simple del recurso (campo garantia_fin) = fuente primaria de visualización.
  const garSimple = _hvGarantiaSimple(a);
  const obsoTxt = _hvAniosMeses(stats.edad_meses);

  const kpis = [
    { v: stats.edad_meses, l: 'Meses', c: '#A78BFF' },
    { v: stats.total_mantenimientos, l: 'Mantenim.', c: '#FFB020' },
    { v: stats.total_asignaciones, l: 'Asignaciones', c: '#267EE8' },
    { v: _hvMoney(stats.inversion_total), l: 'Inversión', c: '#00E5A0' },
  ].map(k => `<div class="hv-kpi"><div style="font-size:17px;font-weight:700;color:${k.c}">${k.v}</div><div style="font-size:10px;color:var(--text3);margin-top:2px">${k.l}</div><div class="hv-kpi-accent" style="width:100%;background:${k.c}"></div></div>`).join('');

  const infoBox = (label, val, color) => `<div style="background:var(--bg3);border:0.5px solid var(--border);border-radius:8px;padding:8px 10px"><div style="font-size:9px;color:var(--text3);text-transform:uppercase;letter-spacing:.5px">${label}</div><div style="font-size:12px;color:${color || 'var(--text)'};margin-top:2px;font-weight:500">${_hvEsc(val)}</div></div>`;

  let infoHtml;
  if (infoMode === 'usuario') {
    const sub = usuario ? [usuario.cargo, usuario.area].filter(Boolean).join(' · ') : 'Equipo en inventario (CT)';
    infoHtml = `<div style="background:var(--bg3);border:0.5px solid var(--border);border-radius:8px;padding:8px 10px;margin-top:10px">
      <div style="font-size:9px;color:var(--text3);text-transform:uppercase;letter-spacing:.5px">Usuario actual</div>
      <div style="font-size:13px;color:${usuario ? 'var(--cyan)' : 'var(--text2)'};margin-top:2px;font-weight:500">${_hvEsc(usuario ? usuario.nombre_completo : 'En inventario (CT)')}</div>
      ${sub ? `<div style="font-size:11px;color:var(--text3);margin-top:1px">${_hvEsc(sub)}</div>` : ''}
    </div>`;
  } else {
    infoHtml = `<div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-top:10px">
      ${infoBox('Responsable actual', usuario ? usuario.nombre_completo : 'En inventario (CT)', usuario ? 'var(--cyan)' : 'var(--text2)')}
      ${infoBox('Garantía', garSimple.txt, garSimple.color)}
      ${infoBox('Antigüedad', obsoTxt)}
    </div>`;
  }

  const empresaSede = [a.nombre_empresa, usuario && usuario.sede].filter(Boolean).join(' · ');

  return `
  <div style="display:grid;grid-template-columns:200px 1fr;gap:14px">
    <div class="hv-device-wrap">
      ${getDeviceSVG(a.tipo_activo)}
      <div class="hv-placa">${a.id_placa_activo}</div>
      <div style="font-size:11px;color:var(--text2);text-align:center">${_hvEsc(a.tipo_activo || '')}</div>
      <div style="font-size:11px;color:var(--text3);text-align:center">${_hvEsc([a.marca, a.modelo].filter(Boolean).join(' '))}</div>
      <div style="margin-top:6px"><span class="badge ${a.estado === 'asignado' ? 'asignado' : 'disponible'}">${(a.estado || '').replace(/_/g, ' ')}</span></div>
      ${a.es_alquiler ? `<div style="margin-top:5px"><span class="badge" style="background:#A78BFF22;color:#A78BFF;border:1px solid #A78BFF55">🔑 Alquilado</span></div>` : ''}
      ${empresaSede ? `<div style="font-size:10px;color:var(--text3);text-align:center;margin-top:6px">${_hvEsc(empresaSede)}</div>` : ''}
    </div>
    <div>
      ${showAlerta ? alerta : ''}
      <div class="hv-kpi4" style="margin-top:${showAlerta && alerta ? '10px' : '0'}">${kpis}</div>
      ${infoHtml}
    </div>
  </div>`;
}

// ── Vida útil del activo (reemplaza el panel de salud) ───────────────────────
function renderHVVidaUtil(vu, a) {
  if (!vu) return '';
  const restantes = vu.dias_restantes;
  const restanteTxt = restantes >= 0
    ? `Quedan <strong style="color:var(--text2)">${restantes} días</strong> de vida útil estimada`
    : `Superó la vida útil estimada por <strong style="color:var(--red)">${Math.abs(restantes)} días</strong>`;
  const origenTxt = vu.origen === 'fecha_obsolescencia'
    ? 'Según fecha de obsolescencia registrada'
    : `Estimación estándar (${vu['años_estimados']} años para ${_hvEsc(a.tipo_activo || '')})`;
  return `
  <div style="background:var(--bg3);border:0.5px solid var(--border);border-radius:10px;padding:14px;margin-bottom:12px">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px">
      <div style="font-size:9px;text-transform:uppercase;letter-spacing:1px;color:var(--text4);font-weight:500">
        <i class="ti ti-battery-3"></i> Vida útil del activo
      </div>
      <span class="badge" style="background:${vu.color}22;color:${vu.color};border:1px solid ${vu.color}55">${_hvEsc(vu.estado_vida)}</span>
    </div>
    <div style="display:flex;align-items:center;gap:14px">
      <div style="flex:1">
        <div style="height:10px;background:var(--bg);border-radius:5px;overflow:hidden;position:relative">
          <div style="height:100%;width:${vu.porcentaje}%;background:${vu.color};border-radius:5px;transition:width 0.4s"></div>
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:6px">
          <span style="font-size:10px;color:var(--text3)">${_hvFecha(vu.fecha_inicio)}</span>
          <span style="font-size:10px;color:var(--text3)">${_hvFecha(vu.fecha_fin)}</span>
        </div>
      </div>
      <div style="text-align:center;min-width:80px">
        <div style="font-size:22px;font-weight:500;color:${vu.color}">${vu.porcentaje}%</div>
        <div style="font-size:9px;color:var(--text4)">transcurrido</div>
      </div>
    </div>
    <div style="margin-top:8px;font-size:11px;color:var(--text3);display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
      <span>${restanteTxt}</span>
      <span style="color:var(--text4)">${origenTxt}</span>
    </div>
  </div>`;
}

// ── Línea de tiempo ────────────────────────────────────────────────────────────
function renderHVLineaTiempo(eventos) {
  if (!eventos || !eventos.length) return '<div style="color:var(--text3);font-size:12px">Sin eventos</div>';
  const segs = eventos.map((e, i) => {
    const last = i === eventos.length - 1;
    const dur = e.duracion_dias != null ? `<span style="display:inline-block;margin-top:4px;font-size:9px;background:${e.color}22;color:${e.color};border-radius:10px;padding:1px 7px">${e.duracion_dias} días</span>` : '';
    return `<div class="hv-tl-seg" style="${e.es_actual ? 'border-right:2px solid #00E5A0;border-radius:0 6px 6px 0' : ''}">
      <div style="display:flex;align-items:center">
        <div class="hv-tl-dot" style="background:${e.color}"></div>
        ${last ? '' : `<div class="hv-tl-bar" style="background:${e.color};opacity:.35"></div>`}
      </div>
      <div style="padding:8px 8px 0 2px">
        <div style="font-size:9px;color:var(--text3)">${_hvFecha(e.fecha)}</div>
        <div style="font-size:11px;color:var(--text);font-weight:500;margin-top:2px"><i class="ti ti-${e.icono}" style="color:${e.color}"></i> ${_hvEsc(e.titulo)}</div>
        <div style="font-size:10px;color:var(--text3);margin-top:1px">${_hvEsc(e.descripcion || '')}</div>
        ${dur}
      </div>
    </div>`;
  }).join('');
  return `<div class="hv-tl-track">${segs}</div>`;
}

// ── Responsables ───────────────────────────────────────────────────────────────
function renderHVResponsables(resp) {
  if (!resp || !resp.length) return '<div style="color:var(--text3);font-size:12px">Sin responsables</div>';
  const cards = resp.map((r, i) => `
    ${i ? '<div style="align-self:center;color:var(--text3);padding:0 4px;font-size:14px">→</div>' : ''}
    <div class="hv-resp-card ${r.es_actual ? 'current' : ''}">
      <div class="hv-resp-av" style="background:${r.color_avatar}22;color:${r.color_avatar};border:1px solid ${r.color_avatar}55">${_hvEsc(r.iniciales)}</div>
      <div style="font-size:11px;color:var(--text);font-weight:500;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${_hvEsc(r.nombre)}</div>
      <div style="font-size:9px;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${_hvEsc(r.rol)}</div>
      <div style="font-size:9px;color:var(--text3);margin-top:3px">${_hvFecha(r.fecha_inicio)}</div>
      <div style="font-size:9px;color:${r.color_avatar}">${_hvEsc(r.duracion_label)}</div>
    </div>`).join('');
  return `<div class="hv-resp-track">${cards}</div>`;
}

// ── Tabs ───────────────────────────────────────────────────────────────────────
function renderHVTabs(data) {
  const tabs = [
    ['asignaciones', 'Asignaciones'], ['especificaciones', 'Especificaciones'],
    ['mantenimientos', 'Mantenimientos'], ['preventivos', 'Mant. preventivos'],
    ['documentos', 'Documentos'], ['auditoria', 'Auditoría'],
  ];
  const nav = tabs.map((t, i) => `<div class="hv-tab ${i === 0 ? 'active' : ''}" data-hvtab="${t[0]}" onclick="switchHVTab('${t[0]}',this)">${t[1]}</div>`).join('');
  return `<div class="hv-tabs-nav" id="hv-tabs-nav">${nav}</div><div class="hv-tab-body" id="hv-tab-body"></div>`;
}

function switchHVTab(tab, el) {
  document.querySelectorAll('#hv-tabs-nav .hv-tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  const d = hojaVidaData;
  const body = document.getElementById('hv-tab-body');
  if (!d || !body) return;
  const map = {
    asignaciones: () => renderHVTabAsignaciones(d.asignaciones),
    especificaciones: () => renderHVTabEspecificaciones(d.activo),
    mantenimientos: () => renderHVTabMantenimientos(d.mantenimientos),
    preventivos: () => renderHVTabPreventivos(d.mantenimientos_preventivos),
    documentos: () => renderHVTabDocumentos(d.actas),
    auditoria: () => renderHVTabAuditoria(d.auditoria),
  };
  body.innerHTML = (map[tab] || (() => ''))();
}

function renderHVTabAsignaciones(asigs) {
  if (!asigs || !asigs.length) return '<div style="color:var(--text3);font-size:12px">Este activo nunca ha sido asignado.</div>';
  return asigs.map(a => {
    const u = a.usuario || {};
    const ini = (u.nombre_completo || '?').slice(0, 2).toUpperCase();
    const actual = a.estado === 'activa';
    const actas = (a.actas || []).map(ac =>
      `<button class="btn btn-ghost btn-sm" onclick="descargarActa('${ac.id}')"><i class="ti ti-file-text"></i> ${_hvEsc(ac.numero || ac.tipo)}</button>`).join(' ');
    return `<div class="hv-asig-card ${actual ? 'current' : ''}">
      <div class="hv-resp-av" style="background:rgba(var(--accent-rgb),0.13);color:var(--cyan);border:1px solid rgba(var(--accent-rgb),0.33)">${_hvEsc(ini)}</div>
      <div style="flex:1">
        <div style="font-size:12px;color:var(--text);font-weight:500">${_hvEsc(u.nombre_completo || '—')}${actual ? ' <span class="badge asignado" style="font-size:9px">Actual</span>' : ''}</div>
        <div style="font-size:10px;color:var(--text3)">${_hvEsc([u.cargo, u.empresa].filter(Boolean).join(' · '))}</div>
        <div style="font-size:10px;color:var(--text3)">${_hvFecha(a.fecha_asignacion)} → ${a.fecha_devolucion ? _hvFecha(a.fecha_devolucion) : 'Actual'} ${actas}</div>
      </div>
      <div style="text-align:right;font-size:11px;color:var(--cyan)">${a.duracion_dias != null ? a.duracion_dias + ' días' : ''}</div>
    </div>`;
  }).join('');
}

function renderHVTabEspecificaciones(a) {
  const campos = [
    ['Marca', a.marca], ['Modelo', a.modelo], ['Serial', a.serial], ['No. Parte', a.numero_parte],
    ['Código Contable', a.codigo_contable], ['Procesador', a.procesador], ['RAM', a.memoria_ram],
    ['Disco 1', a.disco_1], ['Disco 2', a.disco_2], ['Resolución', a.resolucion],
    ['Conexión', a.tipo_conexion], ['Tamaño pantalla', a.tamano_pantalla], ['IMEI', a.imei],
    ['No. teléfono', a.numero_telefono], ['Capacidad', a.capacidad_almacenamiento], ['Color', a.color],
    ['Tipo impresora', a.tipo_impresora], ['IP', a.ip_dispositivo], ['Tipo cámara', a.tipo_camara],
    ['Canales DVR', a.canales_dvr], ['Extensión', a.extension], ['Línea', a.linea_telefono],
    ['Tipo teléfono', a.tipo_telefono], ['Capacidad UPS', a.capacidad_ups], ['Respaldo UPS', a.tiempo_respaldo_ups],
    ['Fecha compra', a.fecha_compra ? _hvFecha(a.fecha_compra) : null], ['Costo', a.costo != null ? _hvMoney(a.costo) : null],
    ['Observaciones', a.observaciones],
  ].filter(([, v]) => v != null && v !== '');
  if (!campos.length) return '<div style="color:var(--text3);font-size:12px">Sin especificaciones registradas.</div>';
  return `<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:8px">${campos.map(([l, v]) =>
    `<div style="background:var(--bg);border:0.5px solid var(--border);border-radius:7px;padding:8px 10px"><div style="font-size:9px;color:var(--text3);text-transform:uppercase">${l}</div><div style="font-size:12px;color:var(--text);margin-top:2px">${_hvEsc(v)}</div></div>`).join('')}</div>`;
}

function renderHVTabMantenimientos(items) {
  if (!items || !items.length) return '<div style="color:var(--text3);font-size:12px">Sin mantenimientos ni upgrades registrados.</div>';
  return items.map(m => `
    <div class="hv-acta-row">
      <i class="ti ti-tool" style="color:#FFB020;font-size:16px"></i>
      <div style="flex:1">
        <div style="font-size:12px;color:var(--text)">${_hvEsc(m.observaciones || m.tipo_cambio)}</div>
        <div style="font-size:10px;color:var(--text3)">${_hvFecha(m.created_at)} · ${_hvEsc(m.responsable || '—')} · <span style="text-transform:capitalize">${_hvEsc(m.tipo_cambio)}</span></div>
      </div>
    </div>`).join('');
}

function renderHVTabPreventivos(items) {
  if (!items || !items.length) return '<div style="color:var(--text3);font-size:12px">Sin mantenimientos preventivos registrados.</div>';
  return items.map(m => `
    <div class="hv-acta-row">
      <i class="ti ti-shield-check" style="color:#00E5A0;font-size:16px"></i>
      <div style="flex:1">
        <div style="font-size:12px;color:var(--text)">${_hvEsc(m.plan || 'Plan')} · ${_hvEsc(m.resumen || '')}</div>
        <div style="font-size:10px;color:var(--text3)">${_hvFecha(m.fecha)} · Técnico: ${_hvEsc(m.tecnico || '—')}${m.observaciones ? ' · ' + _hvEsc(m.observaciones) : ''}</div>
      </div>
      ${m.tiene_acta ? `<button class="btn btn-ghost btn-sm" onclick="descargarActaMant('${m.id}')">📄 Acta</button>` : ''}
    </div>`).join('');
}

function renderHVTabDocumentos(actas) {
  if (!actas || !actas.length) return '<div style="color:var(--text3);font-size:12px">No hay actas asociadas a este activo.</div>';
  return actas.map(ac => `
    <div class="hv-acta-row">
      <span class="badge ${ac.tipo === 'entrega' ? 'asignado' : 'disponible'}" style="font-size:10px">${_hvEsc(ac.tipo)}</span>
      <div style="flex:1">
        <div style="font-size:12px;color:var(--text)"><span class="mono-tag">${_hvEsc(ac.numero || '—')}</span></div>
        <div style="font-size:10px;color:var(--text3)">${_hvFecha(ac.fecha_entrega)} · ${_hvEsc(ac.usuario_nombre || '')}</div>
      </div>
      ${ac.firmada ? '<span class="badge" style="background:rgba(0,229,160,.1);color:#00E5A0;border:1px solid rgba(0,229,160,.35);font-size:10px">✓ Firmada</span>' : '<span style="font-size:10px;color:var(--text3)">Pendiente</span>'}
      ${ac.url_pdf ? `<button class="btn btn-ghost btn-sm" onclick="descargarActa('${ac.id}')"><i class="ti ti-download"></i> PDF</button>` : ''}
    </div>`).join('');
}

function renderHVTabAuditoria(aud) {
  if (!aud || !aud.length) return '<div style="color:var(--text3);font-size:12px">Sin movimientos registrados.</div>';
  return aud.map(m => `
    <div class="hv-acta-row">
      <i class="ti ti-history" style="color:var(--text3);font-size:15px"></i>
      <div style="flex:1">
        <div style="font-size:12px;color:var(--text);text-transform:capitalize">${_hvEsc((m.tipo_movimiento || '').replace(/_/g, ' '))}</div>
        <div style="font-size:10px;color:var(--text3)">${_hvFecha(m.fecha)} · ${_hvEsc(m.responsable || '—')}${m.observaciones ? ' · ' + _hvEsc(m.observaciones) : ''}</div>
      </div>
    </div>`).join('');
}
