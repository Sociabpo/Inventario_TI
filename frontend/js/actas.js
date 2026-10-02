let actasCache = [], actasFiltradas = [];

async function cargarActas() {
  const p = empresaActual ? `?empresa_id=${empresaActual}` : '';
  const data = await api(`/actas${p}`);
  actasCache = data || [];
  poblarFiltrosActas();
  aplicarFiltrosActas();
}

function renderActas(list) {
  const tbody = document.getElementById('tbl-actas-body');
  tbody.innerHTML = list.length ? list.map(a=>`
    <tr>
      <td><span class="badge ${a.tipo==='entrega'?'asignado':'disponible'}">${a.tipo}</span></td>
      <td><span class="mono-tag">${a.placa_activo||'—'}</span></td>
      <td><div class="td-name">${a.empleado||'—'}</div><div class="td-sub">${a.documento||''}</div></td>
      <td><div class="td-sub">${a.empresa||'—'}</div></td>
      <td style="font-size:11px">${a.responsable_entrega||'—'}</td>
      <td style="font-size:11px;color:var(--text3)">${fFecha(a.fecha)}</td>
      <td>${a.firmada
        ? `<button class="btn btn-ghost btn-sm" onclick="descargarActa('${a.id}')">↓ PDF</button>`
        : a.tiene_pdf
          ? `<button class="btn btn-ghost btn-sm" onclick="descargarActa('${a.id}')">↓ PDF</button>`
          : `<button class="btn btn-ghost btn-sm" style="color:var(--amber)" onclick="generarPDF('${a.id}',this)">Generar PDF</button>`}
      </td>
      <td>
        ${_badgeFirma(a)}
        ${!a.firmada && a.tipo==='entrega' ? _bloqueVigencia(a) : ''}
      </td>
    </tr>`).join('')
    : '<tr><td colspan="8" style="text-align:center;color:var(--text3);padding:20px">Sin actas que coincidan</td></tr>';
}

// Indicador de acta anticipada + botón para configurar fecha de ingreso
function _bloqueVigencia(a) {
  if (!hasPermiso('actas.generar')) {
    return a.es_anticipada ? '<div style="font-size:9px;color:var(--amber);margin-top:3px">📅 Anticipada</div>' : '';
  }
  if (a.es_anticipada) {
    const falta = !a.fecha_inicio_vigencia;
    return `<div style="margin-top:4px">
      <span style="font-size:9px;color:var(--amber)">📅 Anticipada${a.fecha_inicio_vigencia ? ' · ' + fFecha(a.fecha_inicio_vigencia) : ''}</span>
      <button class="btn btn-ghost btn-sm" style="margin-left:6px;${falta ? 'color:var(--amber);border-color:rgba(255,176,32,0.3)' : ''}" onclick="abrirModalVigencia('${a.id}',${a.es_anticipada},'${(a.fecha_inicio_vigencia || '').slice(0,10)}')">📅 ${falta ? 'Configurar ingreso' : 'Editar ingreso'}</button>
    </div>`;
  }
  return `<div style="margin-top:4px"><button class="btn btn-ghost btn-sm" onclick="abrirModalVigencia('${a.id}',false,'')">📅 Configurar ingreso</button></div>`;
}

function buscarActas() { aplicarFiltrosActas(); }

// ── Modal vigencia / fecha de ingreso ─────────────────
function toggleVigenciaFields() {
  const checked = document.getElementById('vig-es-anticipada').checked;
  document.getElementById('vig-fecha-wrap').style.display = checked ? 'block' : 'none';
}

function abrirModalVigencia(actaId, esAnticipada, fechaActual) {
  document.getElementById('vig-acta-id').value = actaId;
  document.getElementById('vig-es-anticipada').checked = !!esAnticipada;
  document.getElementById('vig-fecha-inicio').value = fechaActual || '';
  toggleVigenciaFields();
  abrirModal('modal-vigencia');
}

async function guardarVigencia() {
  const actaId       = document.getElementById('vig-acta-id').value;
  const esAnticipada = document.getElementById('vig-es-anticipada').checked;
  const fechaInicio  = document.getElementById('vig-fecha-inicio').value;
  if (esAnticipada && !fechaInicio) { notif('Ingresa la fecha de ingreso del empleado', 'error'); return; }
  const res = await apiRaw(`/actas/${actaId}/configurar-vigencia`, {
    method: 'POST',
    body: JSON.stringify({ es_anticipada: esAnticipada, fecha_inicio_vigencia: fechaInicio || null }),
  });
  if (res.ok) {
    notif('Configuración guardada — los recordatorios respetarán la fecha de ingreso');
    cerrarModal('modal-vigencia');
    cargarActas();
  } else {
    const err = await res.json().catch(() => ({}));
    notif(err.detail || 'Error al guardar', 'error');
  }
}

function poblarFiltrosActas() {
  llenarSelectDistinct('filtro-actas-empresa', actasCache, 'empresa', 'Todas');
}

function aplicarFiltrosActas() {
  const q       = (document.getElementById('search-actas')?.value || '').toLowerCase().trim();
  const tipo    = document.getElementById('filtro-actas-tipo').value;
  const empresa = document.getElementById('filtro-actas-empresa').value;
  const firma   = document.getElementById('filtro-actas-firma').value;
  const desde   = document.getElementById('filtro-actas-desde').value;
  const hasta   = document.getElementById('filtro-actas-hasta').value;

  let l = actasCache.slice();
  if (tipo)    l = l.filter(a => a.tipo === tipo);
  if (empresa) l = l.filter(a => (a.empresa || '') === empresa);
  if (firma === 'firmada')   l = l.filter(a => a.firmada);
  if (firma === 'pendiente') l = l.filter(a => !a.firmada);
  if (desde)   l = l.filter(a => a.fecha && String(a.fecha).slice(0,10) >= desde);
  if (hasta)   l = l.filter(a => a.fecha && String(a.fecha).slice(0,10) <= hasta);
  if (q) l = l.filter(a =>
    (a.empleado||'').toLowerCase().includes(q) ||
    (a.documento||'').toLowerCase().includes(q) ||
    (a.placa_activo||'').toLowerCase().includes(q) ||
    (a.responsable_entrega||'').toLowerCase().includes(q));

  actasFiltradas = l;
  renderActas(l);
  actualizarCount('count-actas', l.length, actasCache.length);
}

function limpiarFiltrosActas() {
  ['filtro-actas-tipo','filtro-actas-empresa','filtro-actas-firma','filtro-actas-desde','filtro-actas-hasta'].forEach(id => {
    const e = document.getElementById(id); if (e) e.value = '';
  });
  document.getElementById('search-actas').value = '';
  aplicarFiltrosActas();
}

function _badgeFirma(a) {
  if (a.tipo !== 'entrega' && a.tipo !== 'devolucion') return '—';
  if (a.firmada) {
    const fecha = a.fecha_firma ? fFecha(a.fecha_firma) : '';
    const label = a.tipo === 'devolucion' ? '✓ Recibido' : '✓ Firmada';
    return `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(0,229,160,0.1);border:1px solid rgba(0,229,160,0.35);border-radius:20px;padding:3px 10px;font-size:11px;color:#00E5A0;white-space:nowrap">
      ${label}${fecha ? ' · ' + fecha : ''}
    </span>`;
  }
  if (a.tiene_pdf) {
    const btnLabel = a.tipo === 'devolucion' ? '✍ Recibo' : '✍ Firma';
    return `<span style="display:inline-flex;align-items:center;gap:5px;background:rgba(255,176,32,0.08);border:1px solid rgba(255,176,32,0.3);border-radius:20px;padding:3px 10px;font-size:11px;color:var(--amber);white-space:nowrap">
      ⏳ Pendiente
    </span>
    <button class="btn btn-ghost btn-sm" style="color:var(--purple);border-color:rgba(167,139,255,0.3);margin-left:4px" onclick="generarLinkFirma('${a.id}',this)">${btnLabel}</button>`;
  }
  return `<span style="font-size:11px;color:var(--text3)">—</span>`;
}

async function generarLinkFirma(actaId, btn) {
  btn.textContent = 'Generando...';
  btn.disabled    = true;
  const res  = await apiRaw(`/actas/${actaId}/generar-token-firma`, { method: 'POST' });
  if (!res.ok) {
    notif('Error generando link de firma', 'error');
    btn.textContent = '✍ Firma';
    btn.disabled    = false;
    return;
  }
  const data = await res.json();
  // Mostrar modal con el link
  document.getElementById('firma-link-input').value = data.link;
  document.getElementById('firma-link-expira').textContent =
    `Válido por 72 horas — expira: ${new Date(data.expires_at).toLocaleString('es-CO')}`;
  abrirModal('modal-link-firma');
  btn.textContent = '✍ Firma';
  btn.disabled    = false;
}

function copiarLinkFirma() {
  const input = document.getElementById('firma-link-input');
  navigator.clipboard.writeText(input.value)
    .then(() => notif('Link copiado al portapapeles'))
    .catch(() => { input.select(); document.execCommand('copy'); notif('Link copiado'); });
}
async function generarPDF(id, btn) {
  btn.textContent='Generando...';
  await apiRaw(`/actas/${id}/generar-pdf`,{method:'POST'});
  btn.textContent='✓ Listo'; setTimeout(()=>cargarActas(),800);
}
async function descargarActa(id) {
  const res = await fetch(`${API}/actas/${id}/descargar`,{headers:{'Authorization':`Bearer ${TOKEN}`}});
  if (res.ok) {
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href=url; a.download=`acta_${id.slice(0,8)}.pdf`;
    a.click(); URL.revokeObjectURL(url);
  } else notif('Error al descargar PDF','error');
}
let _previewBlobUrl = null;
let _previewNombre  = '';
let _previewActaId  = '';

async function verUltimaActa(usuarioId, nombre) {
  const actas = await api(`/actas?usuario_id=${usuarioId}&tipo=entrega&limit=1`);
  if (!actas?.length) {
    notif(`${nombre} no tiene actas de entrega generadas`, 'error');
    return;
  }
  const acta = actas[0];
  if (!acta.firmada && !acta.tiene_pdf) {
    notif('Generando PDF...', 'info');
    const gen = await apiRaw(`/actas/${acta.id}/generar-pdf`, {method:'POST'});
    if (!gen.ok) { notif('Error al generar el PDF del acta','error'); return; }
  }
  abrirPreviewActa(acta.id, nombre, acta);
}

async function abrirPreviewActa(actaId, nombre, actaData = null) {
  if (_previewBlobUrl) { URL.revokeObjectURL(_previewBlobUrl); _previewBlobUrl = null; }

  _previewNombre = nombre;
  _previewActaId = actaId;

  document.getElementById('preview-titulo').textContent = `Acta de entrega — ${nombre}`;
  document.getElementById('preview-iframe').src = '';
  document.getElementById('preview-loading').style.display = 'flex';
  document.getElementById('preview-iframe').style.display  = 'none';

  // Banner de firma digital
  const bannerEl = document.getElementById('preview-firma-banner');
  if (bannerEl) {
    if (actaData?.firmada) {
      const label = actaData.tipo === 'devolucion' ? 'Devolución confirmada digitalmente' : 'Acta firmada digitalmente';
      bannerEl.textContent = `✓ ${label}${actaData.fecha_firma ? ' el ' + fFecha(actaData.fecha_firma) : ''}`;
      bannerEl.style.display = '';
    } else {
      bannerEl.style.display = 'none';
    }
  }

  abrirModal('modal-acta-preview');

  const res = await fetch(`${API}/actas/${actaId}/descargar`, {headers:{'Authorization':`Bearer ${TOKEN}`}});
  if (res.ok) {
    const blob = await res.blob();
    _previewBlobUrl = URL.createObjectURL(blob);
    document.getElementById('preview-iframe').src = _previewBlobUrl;
    document.getElementById('preview-loading').style.display = 'none';
    document.getElementById('preview-iframe').style.display  = 'block';
  } else {
    cerrarModal('modal-acta-preview');
    notif('Error al cargar el PDF','error');
  }
}

function descargarPreviewActa() {
  if (!_previewBlobUrl) return;
  const a = document.createElement('a');
  a.href = _previewBlobUrl;
  a.download = `acta_${_previewNombre.replace(/ /g,'_')}_${_previewActaId.slice(0,8)}.pdf`;
  a.click();
}

// ── HISTORIAL ─────────────────────────────────────────
async function consultarHistorial() {
  const placa  = document.getElementById('hist-placa').value.trim().toUpperCase();
  const cedula = document.getElementById('hist-cedula').value.trim();
  const div    = document.getElementById('hist-result');
  if (!placa && !cedula) {
    div.innerHTML = '<div style="color:var(--amber);padding:10px">Ingresa una placa o cédula</div>';
    return;
  }

  if (placa) {
    const activo = await api(`/activos/placa/${placa}`);
    if (activo) {
      const hist = await api(`/asignaciones/historial/activo/${activo.id}`);
      if (!hist) return;
      div.innerHTML = _renderHistorialMovimientos(
        `${hist.activo.placa} · ${hist.activo.tipo} ${hist.activo.marca||''} ${hist.activo.modelo||''}`,
        hist.activo.estado_actual, 'Activo', hist.movimientos
      );
      return;
    }

    const acc = await api(`/accesorios/placa/${placa}`);
    if (acc) {
      const hist = await api(`/asignaciones/historial/accesorio/${acc.id}`);
      if (!hist) return;
      div.innerHTML = _renderHistorialMovimientos(
        `${hist.accesorio.placa} · ${hist.accesorio.tipo} ${hist.accesorio.marca||''} ${hist.accesorio.modelo||''}`,
        hist.accesorio.estado_actual, 'Accesorio', hist.movimientos
      );
      return;
    }

    div.innerHTML = '<div class="panel" style="padding:20px;text-align:center;color:var(--red)">Placa no encontrada (ni activo ni accesorio)</div>';
    return;
  }

  if (cedula) {
    const usuarios = await api(`/usuarios/buscar?cedula=${encodeURIComponent(cedula)}`);
    if (!usuarios || !usuarios.length) {
      div.innerHTML = '<div class="panel" style="padding:20px;text-align:center;color:var(--red)">Empleado no encontrado</div>';
      return;
    }
    // Preferir coincidencia exacta, si no tomar el primero
    const usuario = usuarios.find(u => u.documento === cedula) || usuarios[0];
    const hist = await api(`/asignaciones/historial/usuario/${usuario.id}`);
    if (!hist) return;
    div.innerHTML = _renderHistorialUsuario(hist);
  }
}

function _renderHistorialMovimientos(titulo, estadoActual, tipo, movimientos) {
  const badgeColor = tipo === 'Accesorio' ? 'mantenimiento' : 'asignado';
  return `<div class="panel">
    <div class="panel-head">
      <span class="panel-title">Historial — ${titulo}</span>
      <span class="badge ${badgeColor}" style="font-size:10px">${tipo}</span>
      <span class="badge ${badgeEstado(estadoActual)}">${estadoActual.replace(/_/g,' ')}</span>
    </div>
    ${movimientos.length
      ? `<table class="tbl"><thead><tr><th>Movimiento</th><th>Fecha</th><th>Responsable</th><th>Observaciones</th></tr></thead>
         <tbody>${movimientos.map(m=>`<tr>
           <td><span class="badge asignado">${m.tipo.replace(/_/g,' ')}</span></td>
           <td style="font-size:11px;font-family:var(--mono)">${fFecha(m.fecha)}</td>
           <td style="font-size:11px">${m.responsable||'—'}</td>
           <td style="font-size:11px;color:var(--text2)">${m.observaciones||'—'}</td>
         </tr>`).join('')}</tbody></table>`
      : '<div style="padding:16px;text-align:center;color:var(--text3);font-size:12px">Sin movimientos registrados</div>'}
  </div>`;
}

function _renderHistorialUsuario(hist) {
  const u = hist.usuario;
  const actas = hist.actas || [];
  return `<div class="panel">
    <div class="panel-head">
      <span class="panel-title">Historial — ${u.nombre}</span>
      <span class="badge disponible-ct" style="font-size:10px">${u.documento}</span>
      <span style="font-size:11px;color:var(--text2)">${u.cargo||''} · ${u.empresa||''}</span>
    </div>
    ${actas.length ? actas.map(a => {
      const esEntrega  = a.tipo === 'entrega';
      const colorBadge = esEntrega ? 'asignado' : 'mantenimiento';
      const label      = esEntrega ? '↓ Entrega' : '↑ Devolución';
      const items      = a.items || [];
      return `<div style="border-left:3px solid var(--${esEntrega?'green':'amber'});margin:8px 0;padding:8px 12px;background:var(--surface2);border-radius:0 6px 6px 0">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">
          <span class="badge ${colorBadge}" style="font-size:10px">${label}</span>
          <span style="font-size:11px;font-family:var(--mono);color:var(--text2)">${fFecha(a.fecha)}</span>
          <span style="font-size:11px;color:var(--text3)">Entregó: ${a.responsable_entrega||'—'} · Recibió: ${a.responsable_recibe||'—'}</span>
        </div>
        ${items.length
          ? `<div style="display:flex;flex-wrap:wrap;gap:4px">${items.map(i=>
              `<span style="font-size:10px;background:var(--surface3);padding:2px 7px;border-radius:4px;font-family:var(--mono)">
                ${i.placa} <span style="color:var(--text3)">${i.descripcion}</span>
              </span>`).join('')}</div>`
          : '<span style="font-size:11px;color:var(--text3)">Sin ítems registrados</span>'}
        ${a.observaciones ? `<div style="font-size:10px;color:var(--text3);margin-top:4px">${a.observaciones}</div>` : ''}
      </div>`;
    }).join('')
    : '<div style="padding:16px;text-align:center;color:var(--text3);font-size:12px">Sin actas registradas</div>'}
  </div>`;
}

// ── HELPERS ───────────────────────────────────────────
function abrirModal(id)  { document.getElementById(id).classList.add('open'); }
function cerrarModal(id) { const el = document.getElementById(id); el.classList.remove('open'); el.style.zIndex = ''; }
function limpiarModal(ids) { ids.forEach(id => { const el=document.getElementById(id); if(el) el.value=''; }); }
function badgeEstado(e)  {
  return {
    disponible:'disponible',
    asignado:'asignado',
    mantenimiento_preventivo:'mantenimiento',
    mantenimiento_correctivo:'mantenimiento',
    en_reparacion:'mantenimiento',
    en_garantia:'disponible',
    retirado:'baja',
    reservado:'reservado',
    // legado / otros badges
    mantenimiento:'mantenimiento',
    baja:'baja',
    activo:'activo',
    inactivo:'inactivo',
  }[e]||'disponible';
}
function fFecha(iso) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleDateString('es-CO',{day:'2-digit',month:'2-digit',year:'numeric'})+' '+d.toLocaleTimeString('es-CO',{hour:'2-digit',minute:'2-digit'});
}
function logout() { sessionStorage.clear(); window.location.href='index.html'; }



// ── ASIGNACIÓN RÁPIDA DESDE ACTIVO/ACCESORIO ─────────