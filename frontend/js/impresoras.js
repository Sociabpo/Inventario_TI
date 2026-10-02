// ── Impresoras (alquiladas) module ──────────────────────────────────────────────
// Inventario aparte (como servidores/redes). Obedece al selector GLOBAL de empresa.
// Sede reutiliza Catalogo categoria='sede' (per-empresa, opción=id catálogo, como redes).
// Ciudad = catálogo GLOBAL categoria='ciudad'. Proveedor = /api/proveedores?modulo=impresoras.

let impresorasCache = [];
let _impReemplazoOldId = null;   // id de la impresora vieja cuando el modal está en modo reemplazo

const IMP_ESTADO_META = {
  en_servicio:   { label: 'En servicio',   color: '#00E5A0' },
  inactiva:      { label: 'Inactiva',      color: '#8b949e' },
  en_reparacion: { label: 'En reparación', color: '#FFB020' },
};

function _impPuedeGestionar() { return hasPermiso('impresoras.gestionar'); }

function _escImp(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
async function _errImp(res, fallback) {
  if (!res) return fallback;
  try { const d = await res.json(); return d.detail || fallback; } catch (e) { return fallback; }
}

// ── Entrada + carga ─────────────────────────────────────────────────────────────

let _imprTab = 'inventario';   // pestaña activa dentro del módulo Impresoras

function initImpresorasView() {
  // Obedece al selector global de empresa (registrado en recargadores de core.js).
  // Recarga la pestaña activa (por defecto Inventario).
  if (_imprTab === 'reportes') cargarReportesImpr();
  else cargarImpresoras();
}

function switchImprTab(tab, el) {
  _imprTab = tab;
  document.querySelectorAll('#tabs-impresoras .tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  const inv = document.getElementById('impr-panel-inventario');
  const rep = document.getElementById('impr-panel-reportes');
  if (inv) inv.style.display = tab === 'inventario' ? '' : 'none';
  if (rep) rep.style.display = tab === 'reportes' ? '' : 'none';
  if (tab === 'reportes') cargarReportesImpr();
  else cargarImpresoras();
}

async function cargarImpresoras() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  const estado = document.getElementById('impr-filtro-estado')?.value || '';
  if (estado) p.set('estado', estado);
  const data = await api(`/impresoras?${p}`);
  impresorasCache = data || [];
  renderImpresoras(impresorasCache);
}

function filtrarImpresoras() {
  const q = (document.getElementById('impr-search')?.value || '').toLowerCase();
  const list = q ? impresorasCache.filter(i =>
    (i.serial || '').toLowerCase().includes(q) ||
    (i.modelo || '').toLowerCase().includes(q)) : impresorasCache;
  renderImpresoras(list);
}

function _impEstadoBadge(estado) {
  const m = IMP_ESTADO_META[estado] || { label: estado || '—', color: '#8b949e' };
  return `<span class="badge" style="background:${m.color}22;color:${m.color};border:1px solid ${m.color}55">${_escImp(m.label)}</span>`;
}

function renderImpresoras(list) {
  const tbody = document.getElementById('tbl-impresoras-body');
  if (!tbody) return;
  const gestionar = _impPuedeGestionar();
  if (!list.length) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align:center;color:var(--text3);padding:24px">Sin impresoras registradas${gestionar ? ' — crea la primera con “Nueva impresora”.' : '.'}</td></tr>`;
    return;
  }
  tbody.innerHTML = list.map(i => {
    const click = gestionar ? `class="clickable" onclick="abrirModalImpresora('${i.id}')"` : '';
    const tipoLbl = i.tipo === 'color' ? 'Color' : i.tipo === 'monocromatica' ? 'Monocromática' : '—';
    const esReempl = i.estado === 'reemplazada';
    // Historial: para todos (ver). Reemplazar: solo gestionar y si no está ya reemplazada.
    const acciones = `
      <button class="btn btn-ghost btn-sm" title="Ver historial de reemplazo" onclick="event.stopPropagation();verHistorialImpresora('${i.id}')"><i class="ti ti-history"></i></button>
      <button class="btn btn-ghost btn-sm" title="Reportes de daño" onclick="event.stopPropagation();verReportesDano('${i.id}')"><i class="ti ti-mail"></i></button>
      ${gestionar && !esReempl ? `<button class="btn btn-ghost btn-sm" title="Reportar daño" onclick="event.stopPropagation();abrirReporteDano('${i.id}')"><i class="ti ti-alert-triangle"></i></button>` : ''}
      ${gestionar && !esReempl ? `<button class="btn btn-ghost btn-sm" title="Reemplazar" onclick="event.stopPropagation();abrirReemplazoImpresora('${i.id}')"><i class="ti ti-refresh"></i></button>` : ''}`;
    return `
    <tr ${click}>
      <td><div class="td-name">${_escImp(i.modelo) || '—'}</div>
          <div class="td-sub" style="font-family:var(--mono);font-size:10px">${_escImp(i.serial) || '—'}</div></td>
      <td><div style="font-size:11px">${_escImp(i.ciudad) || '—'}</div>
          <div class="td-sub">${_escImp(i.sede) || '—'}</div></td>
      <td style="font-size:11px">${_escImp(i.dependencia) || '—'}</td>
      <td style="font-size:11px">${tipoLbl}</td>
      <td>${i.ip ? `<span class="mono-tag">${_escImp(i.ip)}</span>` : '—'}</td>
      <td>${_impEstadoBadge(i.estado)}</td>
      <td style="font-size:11px">${_escImp(i.correo_escaneo) || '—'}</td>
      <td style="font-size:11px">${_escImp(i.proveedor) || '—'}</td>
      <td style="font-size:11px;color:var(--text2)">${_escImp(i.empresa ? i.empresa.nombre : '')}</td>
      <td style="white-space:nowrap" onclick="event.stopPropagation()">${acciones}</td>
    </tr>`;
  }).join('');
}

// ── Dropdowns del modal ───────────────────────────────────────────────────────--

// Sede: Catalogo categoria='sede' de la empresa; opción = id del catálogo (como redes).
async function _poblarSedesImp(empresaId, sedeIdActual) {
  const sel = document.getElementById('impr-sede');
  const hint = document.getElementById('impr-sede-hint');
  if (!sel) return;
  if (!empresaId) {
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    if (hint) hint.style.display = 'none';
    return;
  }
  const data = await api(`/catalogos?categoria=sede&empresa_id=${empresaId}`) || [];
  sel.innerHTML = '<option value="">Seleccionar...</option>' +
    data.map(c => `<option value="${c.id}"${c.id === sedeIdActual ? ' selected' : ''}>${_escImp(c.valor)}</option>`).join('');
  if (hint) hint.style.display = data.length ? 'none' : '';
}

// Ciudad: catálogo GLOBAL categoria='ciudad'; opción = id del catálogo.
async function _poblarCiudadesImp(ciudadIdActual) {
  const sel = document.getElementById('impr-ciudad');
  const hint = document.getElementById('impr-ciudad-hint');
  if (!sel) return;
  const data = await api(`/catalogos?categoria=ciudad`) || [];
  sel.innerHTML = '<option value="">Seleccionar...</option>' +
    data.map(c => `<option value="${c.id}"${c.id === ciudadIdActual ? ' selected' : ''}>${_escImp(c.valor)}</option>`).join('');
  if (hint) hint.style.display = data.length ? 'none' : '';
}

// Proveedor: catálogo GLOBAL de proveedores flagged modulo='impresoras'.
async function _poblarProveedoresImp(provIdActual) {
  const sel = document.getElementById('impr-proveedor');
  const hint = document.getElementById('impr-proveedor-hint');
  if (!sel) return;
  const data = await api(`/proveedores?modulo=impresoras`) || [];
  sel.innerHTML = '<option value="">Seleccionar...</option>' +
    data.map(p => `<option value="${p.id}"${p.id === provIdActual ? ' selected' : ''}>${_escImp(p.nombre)}</option>`).join('');
  if (hint) hint.style.display = data.length ? 'none' : '';
}

function onCambioEmpresaImpresora() {
  const empresaId = document.getElementById('impr-empresa').value;
  _poblarSedesImp(empresaId, '');
}

// ── Crear / editar ──────────────────────────────────────────────────────────────

function abrirModalImpresora(imp = null) {
  if (!_impPuedeGestionar()) return;   // ver-only: sin modal
  // imp puede venir como id (desde onclick de la fila) o como objeto
  if (typeof imp === 'string') imp = impresorasCache.find(x => x.id === imp) || null;

  // Modo normal (crear/editar): reinicia cualquier estado de reemplazo.
  _impReemplazoOldId = null;
  document.getElementById('impr-motivo-wrap').style.display = 'none';
  document.getElementById('impr-estado-wrap').style.display = '';

  document.getElementById('impr-id').value = imp ? imp.id : '';
  document.getElementById('modal-impresora-title').textContent = imp ? 'Editar impresora' : 'Nueva impresora';

  const set = (id, v) => { const el = document.getElementById(id); if (el) el.value = (v == null ? '' : v); };
  set('impr-dependencia', imp ? imp.dependencia : '');
  set('impr-modelo',      imp ? imp.modelo : '');
  set('impr-tipo',        imp ? (imp.tipo || '') : '');
  set('impr-serial',      imp ? imp.serial : '');
  set('impr-ip',          imp ? imp.ip : '');
  set('impr-estado',      imp ? (imp.estado || 'en_servicio') : 'en_servicio');
  set('impr-correo',      imp ? imp.correo_escaneo : '');

  const selEmpresa = document.getElementById('impr-empresa');
  llenarSelectEmpresas('impr-empresa');
  if (imp) {
    selEmpresa.value = imp.empresa_id || '';
    selEmpresa.disabled = true;   // no se cambia la empresa al editar (sede depende de ella)
    _poblarSedesImp(imp.empresa_id, imp.sede_catalogo_id || '');
  } else {
    selEmpresa.disabled = false;
    const preset = empresaActual || '';
    selEmpresa.value = preset;
    _poblarSedesImp(preset, '');
  }
  _poblarCiudadesImp(imp ? (imp.ciudad_catalogo_id || '') : '');
  _poblarProveedoresImp(imp ? (imp.proveedor_id || '') : '');

  document.getElementById('impr-btn-eliminar').style.display = imp ? '' : 'none';
  abrirModal('modal-impresora');
}

async function guardarImpresora() {
  if (_impReemplazoOldId) return guardarReemplazo();   // el modal está en modo reemplazo
  const id = document.getElementById('impr-id').value;
  const empresa_id = document.getElementById('impr-empresa').value;
  const modelo = document.getElementById('impr-modelo').value.trim();
  if (!empresa_id) { notif('Selecciona una empresa', 'error'); return; }
  if (!modelo)     { notif('El modelo es obligatorio', 'error'); return; }

  const body = {
    sede_catalogo_id:   document.getElementById('impr-sede').value || null,
    ciudad_catalogo_id: document.getElementById('impr-ciudad').value || null,
    dependencia:        document.getElementById('impr-dependencia').value.trim() || null,
    modelo,
    tipo:               document.getElementById('impr-tipo').value || null,
    serial:             document.getElementById('impr-serial').value.trim() || null,
    ip:                 document.getElementById('impr-ip').value.trim() || null,
    estado:             document.getElementById('impr-estado').value || 'en_servicio',
    correo_escaneo:     document.getElementById('impr-correo').value.trim() || null,
    proveedor_id:       document.getElementById('impr-proveedor').value || null,
  };

  let res;
  if (id) {
    res = await apiRaw(`/impresoras/${id}`, { method: 'PUT', body: JSON.stringify(body) });
  } else {
    body.empresa_id = empresa_id;
    res = await apiRaw('/impresoras', { method: 'POST', body: JSON.stringify(body) });
  }

  if (res && res.ok) {
    notif(id ? 'Impresora actualizada' : 'Impresora creada');
    cerrarModal('modal-impresora');
    cargarImpresoras();
  } else {
    notif(await _errImp(res, 'No se pudo guardar la impresora'), 'error');
  }
}

async function eliminarImpresora() {
  const id = document.getElementById('impr-id').value;
  if (!id) return;
  if (!confirm('¿Eliminar esta impresora del inventario?')) return;
  const res = await apiRaw(`/impresoras/${id}`, { method: 'DELETE' });
  if (res && res.ok) {
    notif('Impresora eliminada');
    cerrarModal('modal-impresora');
    cargarImpresoras();
  } else {
    notif(await _errImp(res, 'No se pudo eliminar la impresora'), 'error');
  }
}

// ── Reemplazo (fase 2) ────────────────────────────────────────────────────────--

// Abre el modal-impresora en modo REEMPLAZO: prefill con la config de la vieja
// (todo editable) + muestra "Motivo del reemplazo". La empresa queda fija.
function abrirReemplazoImpresora(id) {
  if (!_impPuedeGestionar()) return;
  const imp = impresorasCache.find(x => x.id === id);
  if (!imp) return;
  if (imp.estado === 'reemplazada') { notif('Esta impresora ya fue reemplazada', 'error'); return; }

  _impReemplazoOldId = id;
  document.getElementById('impr-id').value = '';   // la NUEVA no tiene id todavía
  document.getElementById('modal-impresora-title').textContent = `Reemplazar impresora — nueva (reemplaza ${_escImp(imp.modelo) || imp.serial || ''})`;

  const set = (fid, v) => { const el = document.getElementById(fid); if (el) el.value = (v == null ? '' : v); };
  set('impr-dependencia', imp.dependencia);
  set('impr-modelo',      imp.modelo);
  set('impr-tipo',        imp.tipo || '');
  set('impr-serial',      imp.serial);
  set('impr-ip',          imp.ip);
  set('impr-correo',      imp.correo_escaneo);
  set('impr-motivo',      '');

  const selEmpresa = document.getElementById('impr-empresa');
  llenarSelectEmpresas('impr-empresa');
  selEmpresa.value = imp.empresa_id || '';
  selEmpresa.disabled = true;   // misma empresa (mismo punto físico)
  _poblarSedesImp(imp.empresa_id, imp.sede_catalogo_id || '');
  _poblarCiudadesImp(imp.ciudad_catalogo_id || '');
  _poblarProveedoresImp(imp.proveedor_id || '');

  // Estado no aplica (la nueva nace en_servicio); mostrar motivo, ocultar estado + eliminar.
  document.getElementById('impr-estado-wrap').style.display = 'none';
  document.getElementById('impr-motivo-wrap').style.display = '';
  document.getElementById('impr-btn-eliminar').style.display = 'none';
  abrirModal('modal-impresora');
}

async function guardarReemplazo() {
  const oldId = _impReemplazoOldId;
  if (!oldId) return;
  const modelo = document.getElementById('impr-modelo').value.trim();
  const motivo = document.getElementById('impr-motivo').value.trim();
  if (!modelo) { notif('El modelo es obligatorio', 'error'); return; }
  if (!motivo) { notif('El motivo del reemplazo es obligatorio', 'error'); return; }

  const body = {
    sede_catalogo_id:   document.getElementById('impr-sede').value || null,
    ciudad_catalogo_id: document.getElementById('impr-ciudad').value || null,
    dependencia:        document.getElementById('impr-dependencia').value.trim() || null,
    modelo,
    tipo:               document.getElementById('impr-tipo').value || null,
    serial:             document.getElementById('impr-serial').value.trim() || null,
    ip:                 document.getElementById('impr-ip').value.trim() || null,
    correo_escaneo:     document.getElementById('impr-correo').value.trim() || null,
    proveedor_id:       document.getElementById('impr-proveedor').value || null,
    motivo,
  };
  const res = await apiRaw(`/impresoras/${oldId}/reemplazar`, { method: 'POST', body: JSON.stringify(body) });
  if (res && res.ok) {
    notif('Impresora reemplazada');
    _impReemplazoOldId = null;
    cerrarModal('modal-impresora');
    cargarImpresoras();
  } else {
    notif(await _errImp(res, 'No se pudo reemplazar la impresora'), 'error');
  }
}

// ── Historial de reemplazo ────────────────────────────────────────────────────--

function _impFecha(iso) {
  if (!iso) return '—';
  try { return new Date(iso).toLocaleDateString('es-CO'); } catch (e) { return iso.slice(0, 10); }
}

async function verHistorialImpresora(id) {
  const data = await api(`/impresoras/${id}/historial`);
  const body = document.getElementById('impr-hist-body');
  if (!body) return;
  const cad = (data && data.cadena) || [];
  if (!cad.length) { body.innerHTML = '<div style="color:var(--text3);padding:12px">Sin historial.</div>'; abrirModal('modal-impresora-historial'); return; }
  body.innerHTML = cad.map((n, idx) => `
    <div style="border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:${idx < cad.length - 1 ? '4px' : '0'};background:${n.es_actual ? 'rgba(0,229,160,0.06)' : 'var(--dark2)'}">
      <div style="display:flex;align-items:center;gap:8px;font-size:12px">
        ${n.es_actual ? '<span class="badge" style="background:#00E5A022;color:#00E5A0;border:1px solid #00E5A055">Actual</span>' : ''}
        <strong style="color:var(--text)">${_escImp(n.modelo) || '—'}</strong>
        <span style="font-family:var(--mono);font-size:10px;color:var(--text2)">${_escImp(n.serial) || '—'}</span>
        ${_impEstadoBadge(n.estado)}
      </div>
      <div style="font-size:10px;color:var(--text3);margin-top:3px">
        En servicio desde: ${_impFecha(n.created_at)}${n.reemplazado_at ? ` · Reemplazada: ${_impFecha(n.reemplazado_at)}` : ''}
      </div>
      ${n.motivo_reemplazo ? `<div style="font-size:11px;color:var(--text2);margin-top:3px">Motivo: ${_escImp(n.motivo_reemplazo)}</div>` : ''}
    </div>
    ${idx < cad.length - 1 ? '<div style="text-align:center;color:var(--text3);font-size:11px;margin:2px 0">↑ reemplazó a</div>' : ''}`
  ).join('');
  abrirModal('modal-impresora-historial');
}

// ── Fase 3: reporte de daño al proveedor ──────────────────────────────────────--

let _rdImpresora = null;   // impresora en curso del reporte
let _rdDest = [];          // destinatarios (correos)
let _rdImgs = [];          // capturas como data URLs (en memoria; no se guardan)
const _RD_MAX_IMGS = 10, _RD_MAX_BYTES = 5 * 1024 * 1024;

function abrirReporteDano(id) {
  if (!_impPuedeGestionar()) return;
  const imp = impresorasCache.find(x => x.id === id);
  if (!imp) return;
  if (imp.estado === 'reemplazada') { notif('Esta impresora ya fue reemplazada', 'error'); return; }
  _rdImpresora = imp;
  _rdImgs = [];
  _rdDest = imp.proveedor_correo ? [imp.proveedor_correo] : [];

  document.getElementById('impr-rd-id').value = imp.id;
  document.getElementById('impr-rd-printer').innerHTML =
    `<i class="ti ti-printer"></i> ${_escImp(imp.modelo) || '—'} · <span style="font-family:var(--mono);font-size:11px">${_escImp(imp.serial) || 's/serial'}</span> · ${_escImp(imp.ciudad) || ''} ${imp.sede ? '· ' + _escImp(imp.sede) : ''}`;
  document.getElementById('impr-rd-descripcion').value = '';
  document.getElementById('impr-rd-dest-input').value = '';
  document.getElementById('impr-rd-asunto').value = '';
  document.getElementById('impr-rd-cuerpo').value = '';
  document.getElementById('impr-rd-preview-wrap').style.display = 'none';
  _rdRenderChips();
  _rdRenderThumbs();

  document.addEventListener('paste', _rdOnPaste);   // captura Ctrl+V mientras el modal está abierto
  abrirModal('modal-reporte-dano');
}

function rdCerrar() {
  document.removeEventListener('paste', _rdOnPaste);
  cerrarModal('modal-reporte-dano');
}

function _rdValidEmail(e) { return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e); }

function rdAgregarDest() {
  const inp = document.getElementById('impr-rd-dest-input');
  const e = (inp.value || '').trim();
  if (!e) return;
  if (!_rdValidEmail(e)) { notif('Correo inválido', 'error'); return; }
  if (!_rdDest.some(x => x.toLowerCase() === e.toLowerCase())) _rdDest.push(e);
  inp.value = '';
  _rdRenderChips();
}

function rdQuitarDest(idx) { _rdDest.splice(idx, 1); _rdRenderChips(); }

function _rdRenderChips() {
  const c = document.getElementById('impr-rd-dest-chips');
  if (!c) return;
  c.innerHTML = _rdDest.length
    ? _rdDest.map((e, idx) => `<span class="badge asignado" style="display:inline-flex;align-items:center;gap:5px">${_escImp(e)}<span style="cursor:pointer;font-weight:700" onclick="rdQuitarDest(${idx})">×</span></span>`).join('')
    : '<span style="font-size:11px;color:var(--amber)">Sin destinatarios — agrega al menos uno</span>';
}

function _rdOnPaste(e) {
  const items = (e.clipboardData && e.clipboardData.items) || [];
  let found = false;
  for (const it of items) {
    if (it.type && it.type.indexOf('image/') === 0) {
      const f = it.getAsFile();
      if (!f) continue;
      if (_rdImgs.length >= _RD_MAX_IMGS) { notif(`Máximo ${_RD_MAX_IMGS} imágenes`, 'error'); break; }
      if (f.size > _RD_MAX_BYTES) { notif('Cada imagen debe pesar máx 5 MB', 'error'); continue; }
      found = true;
      const r = new FileReader();
      r.onload = () => { _rdImgs.push(r.result); _rdRenderThumbs(); };
      r.readAsDataURL(f);
    }
  }
  if (found) e.preventDefault();
}

function rdQuitarImg(idx) { _rdImgs.splice(idx, 1); _rdRenderThumbs(); }

function _rdRenderThumbs() {
  const t = document.getElementById('impr-rd-thumbs');
  if (!t) return;
  t.innerHTML = _rdImgs.map((src, idx) => `
    <div style="position:relative">
      <img src="${src}" style="width:72px;height:72px;object-fit:cover;border:1px solid var(--border);border-radius:8px">
      <span onclick="rdQuitarImg(${idx})" title="Quitar" style="position:absolute;top:-6px;right:-6px;background:var(--red);color:#fff;width:18px;height:18px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:12px;cursor:pointer">×</span>
    </div>`).join('');
}

function rdGenerarPreview() {
  const imp = _rdImpresora;
  if (!imp) return;
  const desc = document.getElementById('impr-rd-descripcion').value.trim();
  if (!desc) { notif('Describe el daño antes de generar el preview', 'error'); return; }
  const empresa = imp.empresa ? imp.empresa.nombre : '';
  const asunto = `Reporte de daño — ${imp.modelo || 'impresora'}${imp.serial ? ' (' + imp.serial + ')' : ''}${empresa ? ' — ' + empresa : ''}`;
  // Cuerpo corporativo, email-safe: tablas + estilos inline (Outlook/Gmail/móvil).
  // Identidad fija "Servicios TIC / Socia BPO" (NO se muestra la empresa específica al proveedor).
  // Mismas variables de imp + desc; todos los valores escapados con _escImp().
  const fila = (l, v) => v
    ? `<tr>` +
        `<td style="padding:8px 12px;border-bottom:1px solid #e4e9f0;font-weight:bold;color:#0b2b4a;width:140px;font-family:Arial,Helvetica,sans-serif;font-size:13px">${_escImp(l)}</td>` +
        `<td style="padding:8px 12px;border-bottom:1px solid #e4e9f0;color:#333333;font-family:Arial,Helvetica,sans-serif;font-size:13px">${_escImp(v)}</td>` +
      `</tr>`
    : '';
  const descHtml = _escImp(desc).replace(/\n/g, '<br>');
  const cuerpo =
`<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#eef2f7;margin:0;padding:24px 0;font-family:Arial,Helvetica,sans-serif">
  <tr><td align="center">
    <table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px;max-width:600px;background-color:#ffffff;border:1px solid #dfe5ec">
      <tr><td style="background-color:#0b2b4a;padding:20px 28px">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
          <td align="left" style="vertical-align:middle">
            <div style="color:#ffffff;font-size:19px;font-weight:bold;font-family:Arial,Helvetica,sans-serif;line-height:1.2">Servicios TIC</div>
            <div style="color:#7fa8d0;font-size:11px;letter-spacing:2px;font-family:Arial,Helvetica,sans-serif;padding-top:2px">SOCIA BPO</div>
          </td>
          <td align="right" style="vertical-align:middle">
            <span style="background-color:#c0392b;color:#ffffff;font-size:12px;font-weight:bold;padding:7px 14px;border-radius:3px;font-family:Arial,Helvetica,sans-serif;white-space:nowrap">REPORTE DE DAÑO</span>
          </td>
        </tr></table>
      </td></tr>
      <tr><td style="height:3px;background-color:#c0392b;font-size:0;line-height:0">&nbsp;</td></tr>
      <tr><td style="padding:28px">
        <p style="margin:0 0 14px 0;color:#333333;font-size:14px;font-family:Arial,Helvetica,sans-serif">Estimado proveedor,</p>
        <p style="margin:0 0 20px 0;color:#333333;font-size:14px;line-height:1.5;font-family:Arial,Helvetica,sans-serif">Por medio del presente reportamos un daño en la siguiente impresora alquilada, con el fin de gestionar su revisión y atención oportuna.</p>
        <p style="margin:0 0 8px 0;color:#0b2b4a;font-size:12px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;font-family:Arial,Helvetica,sans-serif">Detalles del equipo</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="border:1px solid #e4e9f0;border-collapse:collapse;margin:0 0 22px 0">
          ${fila('Modelo', imp.modelo)}${fila('Serial', imp.serial)}${fila('Tipo', imp.tipo)}${fila('Ciudad', imp.ciudad)}${fila('Sede', imp.sede)}${fila('Dependencia', imp.dependencia)}${fila('Dirección IP', imp.ip)}
        </table>
        <p style="margin:0 0 8px 0;color:#c0392b;font-size:12px;font-weight:bold;text-transform:uppercase;letter-spacing:1px;font-family:Arial,Helvetica,sans-serif">Descripción de la incidencia</p>
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 22px 0"><tr>
          <td style="border-left:4px solid #c0392b;background-color:#fdf3f1;padding:14px 16px;color:#333333;font-size:14px;line-height:1.5;font-family:Arial,Helvetica,sans-serif">${descHtml}</td>
        </tr></table>
        <p style="margin:0;color:#333333;font-size:14px;line-height:1.5;font-family:Arial,Helvetica,sans-serif">Agradecemos de antemano su gestión oportuna para la atención de este caso. Quedamos atentos a su respuesta.</p>
      </td></tr>
      <tr><td style="background-color:#f4f7fa;border-top:1px solid #e4e9f0;padding:20px 28px">
        <p style="margin:0 0 2px 0;color:#333333;font-size:13px;font-family:Arial,Helvetica,sans-serif">Atentamente,</p>
        <p style="margin:0;color:#0b2b4a;font-size:14px;font-weight:bold;font-family:Arial,Helvetica,sans-serif">Servicios TIC</p>
        <p style="margin:2px 0 0 0;color:#5a6b7d;font-size:12px;font-family:Arial,Helvetica,sans-serif">Gestión de Infraestructura Tecnológica · Socia BPO</p>
      </td></tr>
    </table>
  </td></tr>
</table>`;
  document.getElementById('impr-rd-asunto').value = asunto;
  document.getElementById('impr-rd-cuerpo').value = cuerpo;
  document.getElementById('impr-rd-preview-wrap').style.display = '';
}

async function rdEnviar() {
  const imp = _rdImpresora;
  if (!imp) return;
  const descripcion = document.getElementById('impr-rd-descripcion').value.trim();
  const asunto = document.getElementById('impr-rd-asunto').value.trim();
  const cuerpo = document.getElementById('impr-rd-cuerpo').value.trim();
  if (!_rdDest.length) { notif('Agrega al menos un destinatario', 'error'); return; }
  if (!asunto || !cuerpo) { notif('Genera el preview (asunto y cuerpo) antes de enviar', 'error'); return; }

  const btn = document.getElementById('impr-rd-enviar');
  const orig = btn.innerHTML;
  btn.disabled = true; btn.innerHTML = '<i class="ti ti-loader"></i> Enviando…';
  try {
    const res = await apiRaw(`/impresoras/${imp.id}/reporte-dano`, {
      method: 'POST',
      body: JSON.stringify({ descripcion_dano: descripcion, asunto, cuerpo, destinatarios: _rdDest, imagenes: _rdImgs }),
    });
    if (res && res.ok) {
      notif('Reporte de daño enviado');
      rdCerrar();
      cargarImpresoras();
    } else {
      notif(await _errImp(res, 'No se pudo enviar el reporte'), 'error');
    }
  } catch (e) {
    notif('Error de red al enviar el reporte', 'error');
  } finally {
    btn.disabled = false; btn.innerHTML = orig;
  }
}

async function verReportesDano(id) {
  const data = await api(`/impresoras/${id}/reportes-dano`);
  const body = document.getElementById('impr-rd-hist-body');
  if (!body) return;
  const reps = (data && data.reportes) || [];
  body.innerHTML = reps.length ? reps.map(r => `
    <div style="border:1px solid var(--border);border-radius:10px;padding:10px 12px;margin-bottom:8px;background:var(--dark2)">
      <div style="font-size:12px;font-weight:600;color:var(--text)">${_escImp(r.asunto) || '—'}</div>
      <div style="font-size:10px;color:var(--text3);margin-top:2px">${_impFecha(r.created_at)} · por ${_escImp(r.generado_por_email) || '—'} · ${r.num_imagenes} imagen(es)</div>
      <div style="font-size:11px;color:var(--text2);margin-top:4px">Para: ${(r.destinatarios || []).map(_escImp).join(', ') || '—'}</div>
      ${r.descripcion_dano ? `<div style="font-size:11px;color:var(--text2);margin-top:4px">Daño: ${_escImp(r.descripcion_dano)}</div>` : ''}
    </div>`).join('') : '<div style="color:var(--text3);padding:12px">Sin reportes de daño para esta impresora.</div>';
  abrirModal('modal-reportes-dano');
}

// ── Sección "Reportes de daño" (nivel módulo: filtros + ranking + export) ─────--

let _repCache = [];

function _repFiltros() {
  const p = new URLSearchParams();
  const mes = document.getElementById('rep-filtro-mes')?.value || '';
  const emp = document.getElementById('rep-filtro-empresa')?.value || '';
  const sede = document.getElementById('rep-filtro-sede')?.value || '';
  if (mes) p.set('mes', mes);
  // Empresa: filtro propio de la sección; si está vacío, respeta el selector global.
  if (emp) p.set('empresa_id', emp);
  else if (empresaActual) p.set('empresa_id', empresaActual);
  if (sede) p.set('sede_id', sede);
  return p;
}

function onRepEmpresaChange() {
  // Al cambiar empresa, las sedes disponibles cambian → recargar (el backend recalcula sedes).
  const sede = document.getElementById('rep-filtro-sede');
  if (sede) sede.value = '';
  cargarReportesImpr();
}

async function cargarReportesImpr() {
  // Poblar el selector de empresa de la sección (una vez) desde el cache global.
  const selEmp = document.getElementById('rep-filtro-empresa');
  if (selEmp && selEmp.options.length <= 1 && Array.isArray(empresasCache)) {
    selEmp.innerHTML = '<option value="">Todas las empresas</option>' +
      empresasCache.map(e => `<option value="${e.id}">${_escImp(e.nombre_empresa)}</option>`).join('');
  }
  const rankEl = document.getElementById('rep-ranking');
  const body = document.getElementById('rep-list-body');
  if (rankEl) rankEl.innerHTML = '<div style="color:var(--text3);font-size:12px">Cargando…</div>';
  if (body) body.innerHTML = '';

  const data = await api(`/impresoras-reportes?${_repFiltros()}`);
  if (!data) { if (rankEl) rankEl.innerHTML = '<div style="color:var(--red)">No se pudo cargar</div>'; return; }
  _repCache = data.reportes || [];

  // Rellenar opciones de sede (desde el backend, según mes+empresa)
  const selSede = document.getElementById('rep-filtro-sede');
  if (selSede) {
    const actual = selSede.value;
    selSede.innerHTML = '<option value="">Todas las sedes</option>' +
      (data.sedes || []).map(s => `<option value="${s.id}">${_escImp(s.nombre)}</option>`).join('');
    if (actual && (data.sedes || []).some(s => s.id === actual)) selSede.value = actual;
  }

  // Ranking (barras horizontales)
  const rk = data.ranking || [];
  if (rankEl) {
    if (!rk.length) { rankEl.innerHTML = '<div style="color:var(--text3);font-size:12px">Sin reportes en el filtro actual.</div>'; }
    else {
      const max = rk[0].count || 1;
      rankEl.innerHTML = rk.map(r => `
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
          <div style="width:230px;font-size:11px;color:var(--text2);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${_escImp(r.modelo) || '—'}${r.serial ? ' · ' + _escImp(r.serial) : ''}${r.sede ? ` <span style="color:var(--text3)">(${_escImp(r.sede)})</span>` : ''}</div>
          <div style="flex:1;background:var(--dark3);border-radius:4px;height:14px;overflow:hidden"><div style="height:14px;width:${Math.round(r.count / max * 100)}%;background:var(--cyan)"></div></div>
          <div style="width:28px;text-align:right;font-weight:700;font-size:12px;color:var(--text)">${r.count}</div>
        </div>`).join('');
    }
  }

  // Lista
  if (body) {
    body.innerHTML = _repCache.length ? _repCache.map(r => `
      <tr class="clickable" onclick="verDetalleReporteImpr('${r.id}')">
        <td style="font-size:11px">${_impFecha(r.fecha)}</td>
        <td><div class="td-name">${_escImp(r.modelo) || '—'}</div><div class="td-sub" style="font-family:var(--mono);font-size:10px">${_escImp(r.serial) || '—'}</div></td>
        <td style="font-size:11px">${_escImp(r.sede) || '—'}</td>
        <td style="font-size:11px">${_escImp(r.empresa) || '—'}</td>
        <td style="font-size:11px;color:var(--text2)">${_escImp(r.snippet) || '—'}</td>
        <td style="font-size:11px">${_escImp(r.generado_por) || '—'}</td>
        <td>${r.enviado ? '<span class="badge" style="background:#00E5A022;color:#00E5A0;border:1px solid #00E5A055">Sí</span>' : '—'}</td>
      </tr>`).join('') : '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:24px">Sin reportes para los filtros aplicados.</td></tr>';
  }
}

async function verDetalleReporteImpr(id) {
  const d = await api(`/impresoras-reportes/${id}`);
  const body = document.getElementById('rep-detalle-body');
  if (!d || !body) return;
  const row = (l, v) => `<div style="display:flex;gap:8px;margin-bottom:6px"><div style="width:120px;font-size:11px;color:var(--text3)">${l}</div><div style="flex:1;font-size:12px;color:var(--text)">${v}</div></div>`;
  body.innerHTML =
    row('Fecha', _impFecha(d.fecha)) +
    row('Impresora', `${_escImp(d.modelo) || '—'}${d.serial ? ' · ' + _escImp(d.serial) : ''}`) +
    row('Sede', _escImp(d.sede) || '—') +
    row('Empresa', _escImp(d.empresa) || '—') +
    row('Asunto', _escImp(d.asunto) || '—') +
    row('Descripción', _escImp(d.descripcion_dano) || '—') +
    row('Destinatarios', (d.destinatarios || []).map(_escImp).join(', ') || '—') +
    row('En copia', (d.cc || []).map(_escImp).join(', ') || '—') +
    row('Reportó', _escImp(d.generado_por) || '—') +
    row('Imágenes', String(d.num_imagenes ?? 0));
  abrirModal('modal-rep-detalle');
}

async function exportarReportesImpr(fmt, btn) {
  const ep = fmt === 'excel' ? 'export-excel' : 'export-pdf';
  const orig = btn ? btn.innerHTML : null;
  if (btn) { btn.disabled = true; btn.innerHTML = '<i class="ti ti-loader"></i>…'; }
  try {
    const res = await fetch(`${API}/impresoras-reportes/${ep}?${_repFiltros()}`,
                            { headers: { 'Authorization': `Bearer ${TOKEN}` } });
    if (!res.ok) { notif('No se pudo exportar', 'error'); return; }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    if (fmt === 'pdf') { window.open(url, '_blank'); }
    else {
      const a = document.createElement('a');
      a.href = url; a.download = 'reportes_impresoras.xlsx'; a.click();
    }
    setTimeout(() => URL.revokeObjectURL(url), 60000);
  } catch (e) {
    notif('Error de red al exportar', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.innerHTML = orig; }
  }
}
