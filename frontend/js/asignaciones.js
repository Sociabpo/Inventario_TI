async function cargarAsignaciones() {
  const p = empresaActual ? `?empresa_id=${empresaActual}` : '';
  const data = await api(`/asignaciones/activas${p}`);
  const tbody = document.getElementById('tbl-asig-body');
  tbody.innerHTML = data?.length ? data.map(a=>`
    <tr>
      <td><span class="mono-tag">${a.placa_activo||'—'}</span></td>
      <td><div class="td-sub">${a.tipo_activo||'—'}</div></td>
      <td><div class="td-name">${a.nombre_usuario||'—'}</div><div class="td-sub">${a.documento_usuario||''}</div></td>
      <td><div class="td-sub">${a.nombre_empresa||'—'}</div></td>
      <td style="font-size:11px;color:var(--text2)">${a.asignado_por||'—'}</td>
      <td style="font-size:11px;color:var(--text3)">${fFecha(a.fecha_asignacion)}</td>
      <td>—</td>
    </tr>`).join('')
    : '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:20px">Sin asignaciones activas</td></tr>';
}

// Muestra/oculta el campo de fecha límite según el checkbox "Es préstamo temporal"
function toggleAsigPrestamo() {
  const chk  = document.getElementById('asig-es-prestamo');
  const wrap = document.getElementById('asig-fecha-limite-wrap');
  const inp  = document.getElementById('asig-fecha-limite');
  if (!chk || !wrap || !inp) return;
  wrap.style.display = chk.checked ? '' : 'none';
  if (chk.checked) {
    inp.min = _tomorrowISO();
    inp.required = true;
  } else {
    inp.required = false;
    inp.value = '';
  }
}

let timCedula, timPlaca;
function buscarEmpleadoAsig() {
  clearTimeout(timCedula);
  timCedula = setTimeout(async () => {
    const cedula = document.getElementById('asig-cedula').value.trim();
    const empresa = document.getElementById('asig-empresa').value;
    if (cedula.length < 4) { usuarioAsigId = ''; _empleadoMsg = null; actualizarInfoAsig(null); return; }
    if (!empresa) {
      usuarioAsigId = ''; _empleadoMsg = 'Selecciona primero la empresa para buscar el empleado.';
      actualizarInfoAsig(null); return;
    }
    // Busca en la empresa seleccionada + sus empresas relacionadas (hermanas)
    const data = await api(`/usuarios/buscar-para-asignacion?documento=${encodeURIComponent(cedula)}&empresa_id=${encodeURIComponent(empresa)}`);
    if (data?.length) { usuarioAsigId = data[0].id; _empleadoMsg = null; actualizarInfoAsig(data[0]); }
    else {
      usuarioAsigId = '';
      _empleadoMsg = 'No se encontró un empleado con esa cédula en la empresa seleccionada ni en sus empresas relacionadas.';
      actualizarInfoAsig(null);
    }
  }, 400);
}
const _estadosDisponibles = ['disponible'];
// Estados en los que un recurso puede asignarse (disponible o apartado en una reserva)
const _estadosAsignables = ['disponible', 'reservado'];

function _cerrarResultados(cont) {
  if (cont) { cont.classList.remove('open'); cont.innerHTML = ''; }
}

let _activoResultados = [];
function buscarActivoAsig() {
  clearTimeout(timPlaca);
  const cont = document.getElementById('asig-placa-results');
  const termino = document.getElementById('asig-placa').value.trim();
  if (termino.length < 2) { _cerrarResultados(cont); return; }
  timPlaca = setTimeout(async () => {
    const lista = await api(`/activos?q=${encodeURIComponent(termino)}`);
    _renderResultadosActivo(lista || []);
  }, 350);
}

function _renderResultadosActivo(lista) {
  const cont = document.getElementById('asig-placa-results');
  _activoResultados = lista.slice(0, 50);
  if (!_activoResultados.length) {
    cont.innerHTML = '<div class="asig-res-empty">Sin coincidencias</div>';
    cont.classList.add('open');
    return;
  }
  cont.innerHTML = _activoResultados.map((a, i) => {
    const yaAgregado = asigActivos.some(x => x.id === a.id);
    const asignable = _estadosAsignables.includes(a.estado);
    const bloqueado = yaAgregado || !asignable;
    const estadoTxt = yaAgregado ? '✓ ya agregado' : a.estado;
    const col = yaAgregado ? 'var(--amber)'
      : (a.estado === 'disponible' ? 'var(--green)' : (a.estado === 'reservado' ? '#54A0FF' : 'var(--red)'));
    const serial = a.serial ? ` · <span class="asig-res-serial">S/N ${a.serial}</span>` : '';
    return `<div class="asig-res-item ${bloqueado?'disabled':''}" ${bloqueado?'':`onclick="seleccionarActivoAsig(${i})"`}>
      <span class="asig-res-placa">${a.id_placa_activo}</span>
      <span class="asig-res-desc">${a.tipo_activo||''} ${a.marca||''} ${a.modelo||''}${serial}</span>
      <span class="asig-res-estado" style="color:${col}">${estadoTxt}</span>
    </div>`;
  }).join('');
  cont.classList.add('open');
}

function seleccionarActivoAsig(i) {
  const a = _activoResultados[i];
  if (!a) return;
  agregarActivoAsig(a);
}

function agregarActivoAsig(act) {
  if (asigActivos.some(x => x.id === act.id)) return;   // dedup
  asigActivos.push(act);
  document.getElementById('asig-placa').value = '';
  _cerrarResultados(document.getElementById('asig-placa-results'));
  renderAsigActivosLista();
  actualizarInfoAsig();
  if (act.estado === 'reservado') autoAgregarCoReservados('activo', act.id);
}

function quitarActivoAsig(id) {
  asigActivos = asigActivos.filter(a => a.id !== id);
  renderAsigActivosLista();
  actualizarInfoAsig();
}

function renderAsigActivosLista() {
  const lista = document.getElementById('asig-activos-lista');
  if (!lista) return;
  lista.innerHTML = asigActivos.map(a => `
    <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(6,191,255,0.12);border:1px solid rgba(6,191,255,0.3);border-radius:20px;padding:3px 10px;font-size:11px;color:var(--cyan)">
      <span class="mono-tag" style="font-size:9px">${a.id_placa_activo}</span>
      🖥 ${a.tipo_activo||''} ${a.marca||''}
      <button onclick="quitarActivoAsig('${a.id}')" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:13px;padding:0;line-height:1">×</button>
    </span>`).join('');
}

let _empleadoInfo = null, _activoInfo = null;
let _empleadoMsg = null;   // mensaje de feedback del lookup (no encontrado / falta empresa)
let asigActivos = [];    // activos seleccionados en el form de asignación (multi-select)
let asigAccesorios = []; // accesorios seleccionados en el form de asignación

function actualizarInfoAsig(emp, act) {
  if (emp !== undefined) _empleadoInfo = emp;
  if (act !== undefined) _activoInfo   = act;
  const div = document.getElementById('asig-info');
  const partes = [];
  let hayAviso = false;
  if (_empleadoInfo) {
    // Empleado de empresa relacionada (hermana) → badge ámbar; misma empresa → texto sutil
    const empName = _empleadoInfo.nombre_empresa || '';
    const empInfo = _empleadoInfo.es_empresa_relacionada
      ? ` <span style="background:rgba(255,176,32,0.15);color:var(--amber);border:1px solid rgba(255,176,32,0.35);border-radius:10px;padding:1px 8px;font-size:10px;font-weight:600">${empName} · empresa relacionada</span>`
      : ` · <span style="color:var(--text3)">${empName}</span>`;
    if (_empleadoInfo.es_empresa_relacionada) hayAviso = true;
    partes.push(`👤 ${_empleadoInfo.nombre_completo} — ${_empleadoInfo.cargo||''}${empInfo}`);
  } else if (_empleadoMsg) {
    hayAviso = true;
    partes.push(`<span style="color:var(--amber)">⚠ ${_empleadoMsg}</span>`);
  }
  if (asigActivos.length) {
    partes.push(`🖥 ${asigActivos.length} activo(s) seleccionado(s)`);
  }
  div.style.display = partes.length ? 'block' : 'none';
  div.innerHTML = partes.join('<br>');
  div.style.color = hayAviso ? 'var(--amber)' : 'var(--cyan)';
}

let _asigAccTimer = null;
let _accResultados = [];
function buscarAccesorioAsig() {
  clearTimeout(_asigAccTimer);
  const cont = document.getElementById('asig-acc-results');
  const termino = document.getElementById('asig-acc-placa').value.trim();
  if (termino.length < 2) { _cerrarResultados(cont); return; }
  _asigAccTimer = setTimeout(async () => {
    const lista = await api(`/accesorios?q=${encodeURIComponent(termino)}`);
    _renderResultadosAcc(lista || []);
  }, 350);
}

function _renderResultadosAcc(lista) {
  const cont = document.getElementById('asig-acc-results');
  _accResultados = lista.slice(0, 50);
  if (!_accResultados.length) {
    cont.innerHTML = '<div class="asig-res-empty">Sin coincidencias</div>';
    cont.classList.add('open');
    return;
  }
  cont.innerHTML = _accResultados.map((a, i) => {
    const yaAgregado = asigAccesorios.some(x => x.id === a.id);
    const asignable = _estadosAsignables.includes(a.estado);
    const bloqueado = yaAgregado || !asignable;
    const estadoTxt = yaAgregado ? '✓ ya agregado' : a.estado;
    const col = yaAgregado ? 'var(--amber)'
      : (a.estado === 'disponible' ? 'var(--green)' : (a.estado === 'reservado' ? '#54A0FF' : 'var(--red)'));
    const serial = a.serial ? ` · <span class="asig-res-serial">S/N ${a.serial}</span>` : '';
    return `<div class="asig-res-item ${bloqueado?'disabled':''}" ${bloqueado?'':`onclick="seleccionarAccesorioAsig(${i})"`}>
      <span class="asig-res-placa">${a.id_placa_accesorio}</span>
      <span class="asig-res-desc">${a.tipo_accesorio||''} ${a.marca||''} ${a.modelo||''}${serial}</span>
      <span class="asig-res-estado" style="color:${col}">${estadoTxt}</span>
    </div>`;
  }).join('');
  cont.classList.add('open');
}

function seleccionarAccesorioAsig(i) {
  const a = _accResultados[i];
  if (!a) return;
  agregarAccesorioAsig(a);
}

function agregarAccesorioAsig(acc) {
  asigAccesorios.push(acc);
  document.getElementById('asig-acc-placa').value = '';
  _cerrarResultados(document.getElementById('asig-acc-results'));
  renderAsigAccLista();
  if (acc.estado === 'reservado') autoAgregarCoReservados('accesorio', acc.id);
}

// Al agregar un recurso reservado, trae el resto de su reserva y los precarga.
// No asigna nada; solo rellena la lista pendiente (el usuario puede quitarlos).
async function autoAgregarCoReservados(tipoRecurso, recursoId) {
  const data = await api(`/reservas/co-reservados/${tipoRecurso}/${recursoId}`);
  if (!data || !data.reserva_id || !(data.items || []).length) return;

  const agregados = [];
  for (const it of data.items) {
    if (it.tipo_recurso === 'activo') {
      if (asigActivos.some(x => x.id === it.recurso_id)) continue;   // ya está
      asigActivos.push({
        id: it.recurso_id, id_placa_activo: it.placa, tipo_activo: it.tipo,
        marca: it.marca, modelo: it.modelo, estado: it.estado_recurso,
      });
      agregados.push(`${it.tipo || 'Activo'} ${it.placa}`);
    } else {
      if (asigAccesorios.some(x => x.id === it.recurso_id)) continue;   // ya está
      asigAccesorios.push({
        id: it.recurso_id, id_placa_accesorio: it.placa, tipo_accesorio: it.tipo,
        marca: it.marca, modelo: it.modelo, estado: it.estado_recurso,
      });
      agregados.push(`${it.tipo || 'Accesorio'} ${it.placa}`);
    }
  }
  if (agregados.length) {
    renderAsigActivosLista();
    renderAsigAccLista();
    actualizarInfoAsig();
    notif(`Se agregaron ${agregados.length} recurso(s) de la misma reserva (${data.numero_alta}): ${agregados.join(', ')}`);
  }
}

function quitarAccesorioAsig(id) {
  asigAccesorios = asigAccesorios.filter(a => a.id !== id);
  renderAsigAccLista();
}

function renderAsigAccLista() {
  const lista = document.getElementById('asig-acc-lista');
  lista.innerHTML = asigAccesorios.map(a => `
    <span style="display:inline-flex;align-items:center;gap:5px;background:rgba(167,139,255,0.12);border:1px solid rgba(167,139,255,0.3);border-radius:20px;padding:3px 10px;font-size:11px;color:var(--purple)">
      <span class="mono-tag" style="font-size:9px">${a.id_placa_accesorio}</span>
      ${a.tipo_accesorio} ${a.marca||''}
      <button onclick="quitarAccesorioAsig('${a.id}')" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:13px;padding:0;line-height:1">×</button>
    </span>`).join('');
}

async function crearAsignacion() {
  if (!hasPermiso('asignaciones.crear')) { notif('Sin permiso para crear asignaciones','error'); return; }
  const empresa     = document.getElementById('asig-empresa').value;
  const responsable = document.getElementById('asig-responsable').value.trim();
  const obs         = document.getElementById('asig-obs').value.trim();
  const empNombre   = document.getElementById('asig-cedula').value;
  const msgDiv      = document.getElementById('asig-msg');

  if (!empresa || !usuarioAsigId || !responsable) {
    msgDiv.textContent = '⚠ Completa empresa, empleado y responsable de entrega';
    msgDiv.style.cssText = 'display:block;background:rgba(255,176,32,0.1);border:1px solid rgba(255,176,32,0.3);color:var(--amber)';
    return;
  }
  if (asigActivos.length === 0 && asigAccesorios.length === 0) {
    msgDiv.textContent = '⚠ Selecciona al menos un activo o un accesorio para asignar';
    msgDiv.style.cssText = 'display:block;background:rgba(255,176,32,0.1);border:1px solid rgba(255,176,32,0.3);color:var(--amber)';
    return;
  }

  // Préstamo temporal (opcional)
  const esPrestamo  = document.getElementById('asig-es-prestamo')?.checked || false;
  const fechaLimite = document.getElementById('asig-fecha-limite')?.value || null;
  if (esPrestamo) {
    if (!fechaLimite) {
      msgDiv.textContent = '⚠ Indica la fecha límite de devolución del préstamo';
      msgDiv.style.cssText = 'display:block;background:rgba(255,176,32,0.1);border:1px solid rgba(255,176,32,0.3);color:var(--amber)';
      return;
    }
    if (fechaLimite <= new Date().toISOString().slice(0, 10)) {
      msgDiv.textContent = '⚠ La fecha límite debe ser posterior a hoy';
      msgDiv.style.cssText = 'display:block;background:rgba(255,176,32,0.1);border:1px solid rgba(255,176,32,0.3);color:var(--amber)';
      return;
    }
  }

  // Capturar el resumen ANTES de limpiar el formulario
  const resumen = {
    empleado:     _empleadoInfo?.nombre_completo || empNombre,
    empleadoMeta: _empleadoInfo
      ? [_empleadoInfo.cargo, _empleadoInfo.nombre_empresa].filter(Boolean).join(' · ')
      : '',
    activos:      asigActivos.map(a => ({
                    placa: a.id_placa_activo,
                    desc:  [a.tipo_activo, a.marca, a.modelo].filter(Boolean).join(' '),
                  })),
    accesorios:   asigAccesorios.map(a => ({
                    placa: a.id_placa_accesorio,
                    desc:  [a.tipo_accesorio, a.marca, a.modelo].filter(Boolean).join(' '),
                  })),
  };

  let res, actaId;

  if (asigActivos.length) {
    // Activos (con o sin accesorios) → endpoint de asignaciones (multi-activo)
    res = await apiRaw('/asignaciones', { method:'POST', body: JSON.stringify({
      empresa_id: empresa,
      activos_ids: asigActivos.map(a => a.id),
      id_usuario: usuarioAsigId,
      accesorios_ids: asigAccesorios.map(a => a.id),
      responsable_entrega: responsable,
      responsable_recibe: empNombre,
      observaciones: obs||null,
      es_prestamo: esPrestamo,
      fecha_limite_devolucion: esPrestamo ? fechaLimite : null
    })});
    if (res.ok) {
      const data = await res.json();
      actaId = data.acta_id;
      await apiRaw(`/actas/${actaId}/generar-pdf`, {method:'POST'});
    }
  } else {
    // Solo accesorios → endpoint asignar-lote (el acta PDF ya se genera ahí)
    res = await apiRaw('/accesorios/asignar-lote', { method:'POST', body: JSON.stringify({
      empresa_id: empresa,
      id_usuario: usuarioAsigId,
      accesorios_ids: asigAccesorios.map(a => a.id),
      responsable_entrega: responsable,
      responsable_recibe: _empleadoInfo?.nombre_completo || empNombre,
      observaciones: obs||null,
      es_prestamo: esPrestamo,
      fecha_limite_devolucion: esPrestamo ? fechaLimite : null
    })});
    if (res.ok) {
      const data = await res.json();
      actaId = data.acta_id;
    }
  }

  if (res.ok) {
    msgDiv.style.display = 'none';
    limpiarAsig(); cargarAsignaciones(); cargarAccesorios(); cargarDashboard();
    mostrarResumenAsignacion(actaId, resumen);
  } else {
    const err = await res.json();
    msgDiv.textContent = `❌ ${err.detail||'Error al crear asignación'}`;
    msgDiv.style.cssText = 'display:block;background:rgba(255,77,109,0.1);border:1px solid rgba(255,77,109,0.3);color:var(--red)';
  }
}

// ── Modal de resumen tras crear la asignación ──────────────
let _asigExitoActaId = '';
let _asigExitoEmpleado = '';
async function mostrarResumenAsignacion(actaId, resumen) {
  _asigExitoActaId   = actaId || '';
  _asigExitoEmpleado = resumen.empleado || '';

  document.getElementById('asig-exito-empleado').textContent      = resumen.empleado || '—';
  document.getElementById('asig-exito-empleado-meta').textContent = resumen.empleadoMeta || '';

  const items = [];
  (resumen.activos || []).forEach(a => {
    items.push(`<div class="asig-exito-item"><span class="mono-tag">${a.placa}</span><span>🖥 ${a.desc}</span></div>`);
  });
  resumen.accesorios.forEach(a => {
    items.push(`<div class="asig-exito-item"><span class="mono-tag">${a.placa}</span><span>🖱 ${a.desc}</span></div>`);
  });
  document.getElementById('asig-exito-items').innerHTML =
    items.length ? items.join('') : '<div style="font-size:12px;color:var(--text3)">Sin ítems</div>';

  const linkInput = document.getElementById('asig-exito-link');
  const expira    = document.getElementById('asig-exito-expira');
  linkInput.value = 'Generando link...';
  expira.textContent = '';
  abrirModal('modal-asig-exito');

  if (!actaId) {
    linkInput.value = '';
    expira.textContent = 'No se pudo generar el link de firma — genéralo desde el módulo de Actas.';
    return;
  }

  const r = await apiRaw(`/actas/${actaId}/generar-token-firma`, {method:'POST'});
  if (r.ok) {
    const d = await r.json();
    linkInput.value = d.link;
    expira.textContent = `Válido por 72 horas — expira: ${new Date(d.expires_at).toLocaleString('es-CO')}`;
  } else {
    linkInput.value = '';
    expira.textContent = 'No se pudo generar el link de firma — genéralo desde el módulo de Actas.';
  }
}

function copiarAsigExitoLink() {
  const input = document.getElementById('asig-exito-link');
  if (!input.value || input.value === 'Generando link...') return;
  navigator.clipboard.writeText(input.value)
    .then(() => notif('Link copiado al portapapeles'))
    .catch(() => { input.select(); document.execCommand('copy'); notif('Link copiado'); });
}

function verActaAsigExito() {
  if (!_asigExitoActaId) { notif('El acta aún no está disponible', 'error'); return; }
  if (typeof abrirPreviewActa !== 'function') { notif('Vista previa no disponible', 'error'); return; }
  // Mostrar la vista previa SOBRE el modal del link (sin cerrarlo)
  const preview = document.getElementById('modal-acta-preview');
  if (preview) preview.style.zIndex = '1100';
  abrirPreviewActa(_asigExitoActaId, _asigExitoEmpleado);
}

// Fija "Responsable entrega" con el nombre del usuario del sistema actual (no editable)
function setResponsableAsig() {
  const el = document.getElementById('asig-responsable');
  if (!el) return;
  let nombre = '';
  try { nombre = (JSON.parse(sessionStorage.getItem('usuario') || '{}').nombre) || ''; } catch (e) {}
  el.value = nombre;
}

function limpiarAsig() {
  ['asig-cedula','asig-placa','asig-obs','asig-acc-placa'].forEach(id => document.getElementById(id).value='');
  const chkP = document.getElementById('asig-es-prestamo');
  if (chkP) { chkP.checked = false; toggleAsigPrestamo(); }
  setResponsableAsig();
  usuarioAsigId=''; activoAsigId=''; _empleadoInfo=null; _activoInfo=null; _empleadoMsg=null;
  asigActivos = [];
  asigAccesorios = [];
  renderAsigActivosLista();
  renderAsigAccLista();
  _cerrarResultados(document.getElementById('asig-placa-results'));
  _cerrarResultados(document.getElementById('asig-acc-results'));
  document.getElementById('asig-info').style.display='none';
}

// Cerrar los dropdowns de resultados al hacer clic fuera
document.addEventListener('click', (e) => {
  if (!e.target.closest('#asig-placa-wrap')) _cerrarResultados(document.getElementById('asig-placa-results'));
  if (!e.target.closest('#asig-acc-wrap'))   _cerrarResultados(document.getElementById('asig-acc-results'));
});


