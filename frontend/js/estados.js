// ── Cambio de estado / bajas ─────────────────────────────────────────────────
// Estados de mantenimiento REACTIVO que ofrecen "finalizar" desde la ficha.
// El preventivo NO está aquí: lo gestiona el módulo de Mantenimiento (su propia
// pantalla de ejecución lo finaliza), así la ficha no interfiere con esas tareas.
const ESTADOS_MANT_SET = ['mantenimiento_correctivo', 'en_reparacion', 'en_garantia'];
// Las ubicaciones ahora vienen del catálogo per-empresa (no listas fijas).
// La señal de reparación externa (proveedor/fabricante) es un control explícito,
// independiente de la ubicación, que deriva estado=en_reparacion en el backend.

let _ce = null;  // contexto del cambio en curso

// ── Abrir cambio de estado ───────────────────────────────
function abrirCambioEstado(tipoRecurso, recursoId, placa, estadoActual, idUsuario, empresaId) {
  if (!hasPermiso('estados.cambiar')) { notif('Sin permiso para cambiar estados', 'error'); return; }
  if (estadoActual === 'retirado') { notif('Un recurso retirado no puede cambiar de estado', 'error'); return; }
  // Si ya está en mantenimiento → ofrecer finalizar
  if (ESTADOS_MANT_SET.includes(estadoActual)) {
    abrirFinalizarMantenimiento(tipoRecurso, recursoId, placa, empresaId);
    return;
  }
  _ce = { tipoRecurso, recursoId, placa, estadoActual, idUsuario: idUsuario || '', empresaId: empresaId || '', destino: null };
  document.getElementById('ce-placa').textContent = placa;
  document.getElementById('ce-fields').innerHTML = '';
  document.getElementById('ce-guardar').style.display = 'none';
  document.querySelectorAll('#modal-cambio-estado .ce-destino-btn').forEach(b => b.classList.remove('active'));
  abrirModal('modal-cambio-estado');
}

function onSelectDestino(destino) {
  if (destino === 'retirado') {
    cerrarModal('modal-cambio-estado');
    abrirFormularioBaja(_ce.tipoRecurso, _ce.recursoId, _ce.placa, _ce.estadoActual);
    return;
  }
  _ce.destino = destino;
  document.querySelectorAll('#modal-cambio-estado .ce-destino-btn').forEach(b =>
    b.classList.toggle('active', b.dataset.destino === destino));
  document.getElementById('ce-guardar').style.display = '';
  const cont = document.getElementById('ce-fields');
  const esAccesorio = _ce.tipoRecurso === 'accesorio';

  if (destino === 'disponible') {
    cont.innerHTML = `
      <div class="fgroup"><label>Ubicación *</label>
        <select class="fselect" id="ce-ubicacion"><option value="">Seleccionar...</option></select>
        <small id="ce-ubicacion-hint" style="display:none;color:var(--amber);font-size:10px;margin-top:4px">Esta empresa no tiene ubicaciones en el catálogo. Agrégalas en Administración → Catálogos.</small></div>`;
    llenarSelectUbicacion('ce-ubicacion', _ce.empresaId, '', 'ce-ubicacion-hint');
  } else { // mantenimiento
    // Señal de reparación externa (decoupled de la ubicación): proveedor/fabricante → en_reparacion
    const repExterna = esAccesorio ? '' : `
      <div class="fgroup"><label>¿Reparación externa?</label>
        <select class="fselect" id="ce-reparacion-externa">
          <option value="">No (mantenimiento interno)</option>
          <option value="proveedor">Sí — Donde proveedor</option>
          <option value="fabricante">Sí — Donde fabricante</option>
        </select></div>`;
    cont.innerHTML = `
      <div class="frow cols2">
        <div class="fgroup"><label>Tipo *</label>
          <select class="fselect" id="ce-tipo-mant"><option value="correctivo">Correctivo</option></select></div>
        <div class="fgroup"><label>Ubicación *</label>
          <select class="fselect" id="ce-ubicacion"><option value="">Seleccionar...</option></select>
          <small id="ce-ubicacion-hint" style="display:none;color:var(--amber);font-size:10px;margin-top:4px">Esta empresa no tiene ubicaciones en el catálogo. Agrégalas en Administración → Catálogos.</small></div>
      </div>
      ${repExterna}
      <div class="fgroup">
        <label style="display:flex;align-items:center;gap:8px;cursor:pointer">
          <input type="checkbox" id="ce-cubierto-gar" onchange="_ceToggleGarantia()"> ¿Cubierto por garantía?
        </label>
      </div>
      <div id="ce-gar-block" style="display:none">
        <div class="fgroup"><label>Cubre</label>
          <select class="fselect" id="ce-cubre-gar"><option value="proveedor">Proveedor</option><option value="fabricante">Fabricante</option></select></div>
      </div>
      <div class="frow cols2">
        <div class="fgroup"><label>Tiempo estimado (días)</label><input class="finput" id="ce-tiempo" type="number" min="0"></div>
        <div class="fgroup"><label>Responsable</label><input class="finput" id="ce-responsable"></div>
      </div>
      <div class="fgroup"><label>Descripción</label><textarea class="ftextarea" id="ce-descripcion" placeholder="Detalle del mantenimiento"></textarea></div>`;
    llenarSelectUbicacion('ce-ubicacion', _ce.empresaId, '', 'ce-ubicacion-hint');
  }
}
function _ceToggleGarantia() {
  document.getElementById('ce-gar-block').style.display = document.getElementById('ce-cubierto-gar').checked ? 'block' : 'none';
}

async function guardarCambioEstado() {
  if (!_ce || !_ce.destino) return;
  const ubic = document.getElementById('ce-ubicacion')?.value || '';
  if (!ubic) { notif('Selecciona la ubicación', 'error'); return; }
  const body = {
    tipo_recurso: _ce.tipoRecurso, recurso_id: _ce.recursoId,
    estado_nuevo: _ce.destino, ubicacion: ubic,
  };
  if (_ce.destino === 'mantenimiento') {
    body.tipo_mantenimiento = document.getElementById('ce-tipo-mant').value;
    // Reparación externa (explícita) → el backend deriva en_reparacion. NO depende de la ubicación.
    body.reparacion_externa = document.getElementById('ce-reparacion-externa')?.value || null;
    body.cubierto_garantia = document.getElementById('ce-cubierto-gar').checked;
    if (body.cubierto_garantia) body.cubre_garantia = document.getElementById('ce-cubre-gar').value;
    body.tiempo_estimado_dias = parseInt(document.getElementById('ce-tiempo').value) || null;
    body.responsable_mant = document.getElementById('ce-responsable').value || null;
    body.descripcion = document.getElementById('ce-descripcion').value || null;
  }
  const res = await apiRaw('/estados/cambiar', { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) {
    const d = await res.json();
    notif('Estado actualizado');
    cerrarModal('modal-cambio-estado');
    if (d.genero_acta) notif('Se generó un acta de devolución pendiente de firma', 'success');
    _recargarRecursos(_ce.tipoRecurso);
  } else {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error al cambiar estado', 'error');
  }
}

// ── Finalizar mantenimiento ──────────────────────────────
async function abrirFinalizarMantenimiento(tipoRecurso, recursoId, placa, empresaId) {
  _ce = { tipoRecurso, recursoId, placa, empresaId: empresaId || '', caseA: false };
  document.getElementById('fm-placa').textContent = placa;
  document.getElementById('fm-resultado').value = 'exitoso';
  document.getElementById('fm-costo').value = '';
  document.getElementById('fm-destino').value = 'disponible';
  llenarSelectUbicacion('fm-ubicacion', empresaId || '', '', 'fm-ubicacion-hint');
  // Consultar si el equipo fue devuelto o sigue asignado
  const info = await api(`/estados/mantenimiento-activo/${tipoRecurso}/${recursoId}`) || {};
  // CASO A = NO fue devuelto (genero_acta=false) y hay usuario a restaurar
  _ce.caseA = (info.genero_acta === false) && !!info.usuario_previo;
  const infoBox = document.getElementById('fm-caso-a-info');
  const destinoWrap = document.getElementById('fm-destino-wrap');
  if (_ce.caseA) {
    document.getElementById('fm-usuario-nombre').textContent = info.usuario_previo_nombre || 'su usuario';
    infoBox.style.display = '';
    destinoWrap.style.display = 'none';
    document.getElementById('fm-ubic-wrap').style.display = 'none';
  } else {
    infoBox.style.display = 'none';
    destinoWrap.style.display = '';
    _fmToggleDestino();
  }
  abrirModal('modal-finalizar-mant');
}
function _fmToggleDestino() {
  const retirar = document.getElementById('fm-destino').value === 'retirar';
  document.getElementById('fm-ubic-wrap').style.display = retirar ? 'none' : '';
}
async function guardarFinalizarMantenimiento() {
  const resultado = document.getElementById('fm-resultado').value;
  const body = {
    tipo_recurso: _ce.tipoRecurso, recurso_id: _ce.recursoId,
    resultado,
    costo_real: parseFloat(document.getElementById('fm-costo').value) || null,
  };
  if (!_ce.caseA) {   // CASO B: el equipo fue devuelto → requiere destino
    const destino = document.getElementById('fm-destino').value;
    body.destino = destino;
    body.ubicacion = destino === 'disponible' ? document.getElementById('fm-ubicacion').value : null;
  }
  const res = await apiRaw('/estados/finalizar-mantenimiento', { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) {
    const d = await res.json();
    cerrarModal('modal-finalizar-mant');
    if (d.instruccion === 'solicitar_baja') {
      notif('Registra la solicitud de baja', 'info');
      abrirFormularioBaja(_ce.tipoRecurso, _ce.recursoId, _ce.placa, 'disponible');
    } else if (d.volvio_a_asignado) {
      notif(`Mantenimiento finalizado. El equipo volvió a estado asignado con ${d.usuario_nombre || 'su usuario'}.`);
      _recargarRecursos(_ce.tipoRecurso);
    } else {
      notif('Mantenimiento finalizado. Equipo disponible.');
      _recargarRecursos(_ce.tipoRecurso);
    }
  } else {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error', 'error');
  }
}

// ── Formulario de baja ───────────────────────────────────
function abrirFormularioBaja(tipoRecurso, recursoId, placa, estadoActual) {
  if (estadoActual === 'asignado') {
    notif('Registra la devolución del equipo antes de darlo de baja', 'error');
    return;
  }
  // empresa_id del recurso: necesario para excluir la empresa actual del traslado
  let empresaId = '';
  const cache = tipoRecurso === 'activo' ? (typeof activosCache !== 'undefined' ? activosCache : [])
                                         : (typeof accCache !== 'undefined' ? accCache : []);
  const rec = (cache || []).find(x => x.id === recursoId);
  if (rec) empresaId = rec.empresa_id || '';

  _ce = { tipoRecurso, recursoId, placa, empresaId };
  document.getElementById('baja-placa').textContent = placa;

  // Gating por alquiler: un equipo en alquiler SOLO puede darse de baja como
  // "devuelto_proveedor"; un equipo propio NO puede usar ese motivo.
  const esAlquiler = !!(rec && rec.es_alquiler);
  const sel = document.getElementById('baja-motivo');
  [...sel.options].forEach(o => {
    const soloAlq = o.dataset.soloAlquiler === '1';
    o.hidden = esAlquiler ? !soloAlq : soloAlq;    // rental → solo devuelto_proveedor; propio → todo menos ese
  });
  sel.value = esAlquiler ? 'devuelto_proveedor' : 'retiro_operacion';

  document.getElementById('baja-justificacion').value = '';
  document.getElementById('baja-estado-fisico').value = '';
  document.getElementById('baja-numero-denuncia').value = '';
  _bajaToggleMotivo();
  abrirModal('modal-baja');
}
function _bajaToggleMotivo() {
  const m = document.getElementById('baja-motivo').value;
  document.getElementById('baja-venta-wrap').style.display = m === 'vendido' ? '' : 'none';
  document.getElementById('baja-donado-wrap').style.display = m === 'donado' ? '' : 'none';
  document.getElementById('baja-destruido-wrap').style.display = m === 'destruido' ? '' : 'none';
  document.getElementById('baja-hurto-wrap').style.display = m === 'hurto' ? '' : 'none';
  document.getElementById('baja-traslado-wrap').style.display = m === 'traslado' ? '' : 'none';
  if (m === 'traslado') _poblarEmpresaDestino();
}
// Llena el select de empresa destino con todas las empresas EXCEPTO la actual del recurso.
function _poblarEmpresaDestino() {
  const sel = document.getElementById('baja-empresa-destino');
  if (!sel) return;
  const actual = _ce ? _ce.empresaId : '';
  const val = sel.value;
  sel.innerHTML = '<option value="">Seleccionar...</option>';
  (typeof empresasCache !== 'undefined' ? empresasCache : []).forEach(e => {
    if (e.id === actual) return;   // no se puede trasladar a la misma empresa
    const o = document.createElement('option');
    o.value = e.id; o.textContent = `${e.nombre_empresa} (${e.prefijo})`;
    sel.appendChild(o);
  });
  if (val) sel.value = val;
}
async function guardarBaja() {
  const just = document.getElementById('baja-justificacion').value.trim();
  if (!just) { notif('La justificación es obligatoria', 'error'); return; }
  const motivo = document.getElementById('baja-motivo').value;
  const empresaDestino = document.getElementById('baja-empresa-destino').value || null;
  if (motivo === 'traslado' && !empresaDestino) {
    notif('Debes indicar la empresa destino del traslado', 'error');
    return;
  }
  const body = {
    tipo_recurso: _ce.tipoRecurso, recurso_id: _ce.recursoId, motivo,
    justificacion: just, estado_fisico: document.getElementById('baja-estado-fisico').value || null,
    valor_venta: parseFloat(document.getElementById('baja-valor-venta').value) || null,
    comprador: document.getElementById('baja-comprador').value || null,
    entidad_receptora: document.getElementById('baja-entidad').value || null,
    metodo_destruccion: document.getElementById('baja-metodo').value || null,
    numero_denuncia: motivo === 'hurto' ? (document.getElementById('baja-numero-denuncia').value || null) : null,
    empresa_destino_id: motivo === 'traslado' ? empresaDestino : null,
  };
  const res = await apiRaw('/estados/solicitar-baja', { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) {
    const d = await res.json();
    notif(`Solicitud de baja ${d.numero_baja} creada. Pendiente de aprobación.`);
    cerrarModal('modal-baja');
    _recargarRecursos(_ce.tipoRecurso);
  } else {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error al solicitar baja', 'error');
  }
}

function _recargarRecursos(tipo) {
  if (tipo === 'activo' && typeof cargarActivos === 'function') cargarActivos();
  if (tipo === 'accesorio' && typeof cargarAccesorios === 'function') cargarAccesorios();
  if (typeof cargarDashboard === 'function') cargarDashboard();
}

// ── Vista de Bajas pendientes ────────────────────────────
let bajasCache = [];
async function cargarBajas() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  bajasCache = await api(`/estados/bajas?${p}`) || [];
  renderBajas(bajasCache);
}
const _MOTIVO_LBL = { donado: 'Donación', vendido: 'Venta', destruido: 'Destrucción', retiro_operacion: 'Retiro de operación', hurto: 'Hurto', traslado: 'Traslado', devuelto_proveedor: 'Devuelto a proveedor' };
const _APROB_BADGE = { pendiente: 'mantenimiento', aprobada: 'asignado', rechazada: 'baja' };
function renderBajas(list) {
  const tbody = document.getElementById('tbl-bajas-body');
  if (!tbody) return;
  const puedeAprobar = hasPermiso('estados.aprobar_baja');
  if (!list.length) { tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:22px">Sin solicitudes de baja</td></tr>'; return; }
  tbody.innerHTML = list.map(b => {
    let acc = '';
    if (b.estado_aprobacion === 'pendiente' && puedeAprobar) {
      acc = `<button class="btn btn-ghost btn-sm" style="color:var(--green);border-color:rgba(0,229,160,.3)" onclick="aprobarBaja('${b.id}')">Aprobar</button>
             <button class="btn btn-ghost btn-sm" style="color:var(--red);border-color:rgba(255,77,109,.3)" onclick="rechazarBaja('${b.id}')">Rechazar</button>`;
    } else if (b.url_pdf) {
      acc = `<button class="btn btn-ghost btn-sm" onclick="descargarBajaPdf('${b.id}','${b.numero_baja}')"><i class="ti ti-download"></i> PDF</button>`;
    }
    return `<tr>
      <td><span class="mono-tag">${b.numero_baja}</span></td>
      <td><span class="mono-tag">${b.placa || '—'}</span><div class="td-sub">${b.tipo_activo || ''}</div></td>
      <td>${_MOTIVO_LBL[b.motivo] || b.motivo}${b.motivo === 'traslado' && b.empresa_destino_nombre ? `<div class="td-sub" style="font-size:10px;color:#54A0FF">→ ${b.empresa_destino_nombre}</div>` : ''}${b.motivo === 'hurto' && b.numero_denuncia ? `<div class="td-sub" style="font-size:10px;color:var(--text3)">Denuncia: ${b.numero_denuncia}</div>` : ''}</td>
      <td style="max-width:220px;font-size:11px;color:var(--text3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${b.justificacion || ''}</td>
      <td style="font-size:11px">${b.solicitado_por || '—'}</td>
      <td><span class="badge ${_APROB_BADGE[b.estado_aprobacion] || 'disponible'}">${b.estado_aprobacion}</span></td>
      <td style="white-space:nowrap">${acc || '<span style="color:var(--text3)">—</span>'}</td>
    </tr>`;
  }).join('');
}
async function descargarBajaPdf(id, numeroBaja) {
  const res = await fetch(`${API}/estados/bajas/${id}/pdf`, { headers: { 'Authorization': `Bearer ${TOKEN}` } });
  if (res.ok) {
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `${numeroBaja || 'baja'}.pdf`;
    a.click(); URL.revokeObjectURL(url);
  } else {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error al descargar el PDF', 'error');
  }
}
async function aprobarBaja(id) {
  const obs = prompt('Observaciones (opcional):') || '';
  const res = await apiRaw(`/estados/bajas/${id}/aprobar`, { method: 'POST', body: JSON.stringify({ observaciones_aprobador: obs || null }) });
  if (res.ok) { notif('Baja aprobada — recurso retirado'); cargarBajas(); }
  else { const e = await res.json().catch(() => ({})); notif(e.detail || 'Error', 'error'); }
}
async function rechazarBaja(id) {
  const obs = prompt('Motivo del rechazo:');
  if (obs == null || !obs.trim()) return;
  const res = await apiRaw(`/estados/bajas/${id}/rechazar`, { method: 'POST', body: JSON.stringify({ observaciones_aprobador: obs.trim() }) });
  if (res.ok) { notif('Baja rechazada'); cargarBajas(); }
  else { const e = await res.json().catch(() => ({})); notif(e.detail || 'Error', 'error'); }
}
