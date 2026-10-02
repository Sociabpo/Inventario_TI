let mdevPaso = 1;
let mdevItems = [];
let mdevSelec = [];
let mdevAsigId = null;
let mdevActaId = null;
let mdevActaIds = [];   // todas las actas generadas (una por empresa)
let mdevTiposCubiertos = [];   // tipo_activo con plan de mantenimiento activo
let mdevMantHabilitado = false; // permiso mantenimiento.planes + hay tipos cubiertos

// Fija "Responsable que recibe" con el nombre del usuario del sistema actual (no editable).
// Espeja setResponsableAsig() del módulo de asignación (misma fuente: sessionStorage.usuario.nombre).
function setResponsableDevol() {
  const el = document.getElementById('mdev-responsable');
  if (!el) return;
  let nombre = '';
  try { nombre = (JSON.parse(sessionStorage.getItem('usuario') || '{}').nombre) || ''; } catch (e) {}
  el.value = nombre;
}

// Entrada desde tabla de ACTIVOS
async function abrirDevolucionDesdeActivo(activoId, placa, usuarioId) {
  if (!usuarioId) {
    notif('Este activo no tiene un empleado asignado','error'); return;
  }
  // Buscar asignación por placa (más confiable)
  const asig = await api('/asignaciones/activas');
  const asigActiva = asig?.find(a => a.placa_activo === placa);
  // Usar id_usuario del activo (ya lo tenemos) aunque no haya asignación en la tabla
  const resolvedUserId = usuarioId || asigActiva?.id_usuario || '';
  if (!resolvedUserId) {
    notif('No se encontró el empleado asignado a '+placa,'error'); return;
  }
  await _abrirModalDevolucion(asigActiva?.id || null, resolvedUserId, placa);
}

// Entrada desde tabla de ASIGNACIONES
async function abrirDevolucionDesdeAsignacion(asigId, placa, usuarioId) {
  await _abrirModalDevolucion(asigId, usuarioId, placa);
}

// Devolución RÁPIDA de accesorio (sin modal completo)
async function devolverAccesorioRapido(accId, placa, usuarioId) {
  if (!confirm(`¿Confirmar devolución del accesorio ${placa}?`)) return;
  const res = await apiRaw(`/accesorios/${accId}`, {
    method: 'PUT',
    body: JSON.stringify({ estado: 'disponible', id_usuario: null, ubicacion: 'Bodega CT' })
  });
  if (res.ok) {
    notif(`Accesorio ${placa} devuelto — estado: disponible CT`);
    cargarAccesorios(); cargarDashboard();
  } else {
    const err = await res.json();
    notif(err.detail||'Error al devolver accesorio','error');
  }
}

// Función interna que abre el modal con los datos correctos
async function _abrirModalDevolucion(asigId, usuarioId, placaPresel) {
  mdevAsigId = asigId;
  mdevSelec  = [];
  mdevItems  = [];
  mdevActaId = null;
  mdevActaIds = [];
  mdevPaso   = 1;

  const itemsData = await api(`/asignaciones/usuario/${usuarioId}/items-asignados`);
  if (!itemsData) {
    notif('Error cargando ítems del empleado','error'); return;
  }

  // Si no llegó asigId, intentar obtenerlo de la asignación activa del activo preseleccionado
  let asigIdFinal = asigId;
  if (!asigIdFinal && placaPresel) {
    const asigs = await api('/asignaciones/activas');
    const encontrada = asigs?.find(a => a.placa_activo === placaPresel);
    asigIdFinal = encontrada?.id || null;
  }

  document.getElementById('mdev-title').textContent = `Devolución — ${itemsData.usuario?.nombre_completo || ''}`;
  document.getElementById('mdev-asig-id').value     = asigIdFinal || '';
  document.getElementById('mdev-usuario-id').value  = usuarioId || '';
  setResponsableDevol();   // "Responsable que recibe" = usuario del sistema actual (no editable)
  document.getElementById('mdev-emp-nombre').textContent = itemsData.usuario?.nombre_completo || '—';
  document.getElementById('mdev-emp-info').textContent   =
    `Cédula: ${itemsData.usuario?.documento || '—'} · ${itemsData.usuario?.cargo||''}`;

  // Combinar activos y accesorios
  mdevItems = [
    ...(itemsData.activos||[]).map(a  => ({...a, _tipo:'activo',   _placa:a.id_placa_activo,   _desc:`${a.tipo_activo} ${a.marca||''} ${a.modelo||''}`})),
    ...(itemsData.accesorios||[]).map(a=> ({...a, _tipo:'accesorio',_placa:a.id_placa_accesorio,_desc:`${a.tipo_accesorio} ${a.marca||''} ${a.modelo||''}`}))
  ];

  // Pre-seleccionar el ítem que originó la devolución
  const presel = mdevItems.find(i => i._placa === placaPresel);
  if (presel) mdevSelec = [presel];

  const custEl = document.getElementById('mdev-custodio-cedula');
  if (custEl) custEl.value = '';   // custodio opcional: limpiar al abrir

  // ── Mantenimiento preventivo (opcional): solo con permiso mantenimiento.planes ──
  mdevTiposCubiertos = [];
  mdevMantHabilitado = false;
  const mantBlock = document.getElementById('mdev-mant-block');
  if (mantBlock) mantBlock.style.display = 'none';
  if (typeof hasPermiso === 'function' && hasPermiso('mantenimiento.planes')) {
    const [tipos, tecs] = await Promise.all([
      api('/mantenimiento/tipos-cubiertos'),
      api('/mantenimiento/tecnicos'),
    ]);
    mdevTiposCubiertos = tipos || [];
    mdevMantHabilitado = mdevTiposCubiertos.length > 0;
    const selTec = document.getElementById('mdev-mant-tecnico');
    if (selTec) selTec.innerHTML = '<option value="">Seleccionar...</option>' +
      (tecs || []).map(t => `<option value="${t.id}">${t.nombre || t.email}</option>`).join('');
  }

  renderMdevLista();
  actualizarMdevContador();
  irMdevPaso(1);
  abrirModal('modal-devolucion');
}

function renderMdevLista() {
  const lista = document.getElementById('mdev-lista-items');
  if (!mdevItems.length) {
    lista.innerHTML = '<div style="text-align:center;color:var(--text3);padding:20px">Sin ítems asignados</div>';
    return;
  }
  // Separar por tipo
  const activos    = mdevItems.filter(i=>i._tipo==='activo');
  const accesorios = mdevItems.filter(i=>i._tipo==='accesorio');
  let html = '';
  if (activos.length) {
    html += '<div class="devol-seccion">🖥 Activos</div>';
    html += activos.map(item => renderMdevItem(item)).join('');
  }
  if (accesorios.length) {
    html += '<div class="devol-seccion">🖱 Accesorios</div>';
    html += accesorios.map(item => renderMdevItem(item)).join('');
  }
  lista.innerHTML = html;
}

function renderMdevItem(item) {
  const sel = mdevSelec.find(s=>s.id===item.id);
  return `<div class="devol-item ${sel?'selected':''}" id="mdevitem-${item.id}"
    onclick="toggleMdevItem('${item.id}')">
    <div class="di-check">${sel?'✓':''}</div>
    <span class="di-placa">${item._placa}</span>
    <div>
      <div class="di-desc">${item._desc.trim()}</div>
      <div class="di-sub">${item.serial||''}</div>
    </div>
  </div>`;
}

function toggleMdevItem(id) {
  const item = mdevItems.find(i=>i.id===id);
  if (!item) return;
  const idx = mdevSelec.findIndex(s=>s.id===id);
  if (idx > -1) mdevSelec.splice(idx,1);
  else mdevSelec.push(item);
  renderMdevLista();
  actualizarMdevContador();
}

function actualizarMdevContador() {
  document.getElementById('mdev-contador').textContent =
    `${mdevSelec.length} ítem(s) seleccionado(s) para devolver`;
}

function irMdevPaso(paso) {
  mdevPaso = paso;
  document.querySelectorAll('.devol-step').forEach(s=>s.classList.remove('active'));
  document.getElementById(`mdev-paso${paso}`).classList.add('active');
  // Actualizar dots
  for (let i=1;i<=3;i++) {
    const dot = document.getElementById(`dot-${i}`);
    dot.className = 'devol-step-dot' + (i<paso?' done':i===paso?' active':'');
    dot.textContent = i<paso ? '✓' : i;
  }
  for (let i=1;i<=2;i++) {
    document.getElementById(`line-${i}`).className = 'devol-step-line'+(i<paso?' done':'');
  }
  // Botones footer
  const btnBack   = document.getElementById('mdev-btn-back');
  const btnNext   = document.getElementById('mdev-btn-next');
  const btnCancel = document.getElementById('mdev-btn-cancelar');
  btnBack.style.display   = paso>1 && paso<3 ? '' : 'none';
  btnCancel.style.display = paso<3 ? '' : 'none';
  if (paso===1) { btnNext.textContent = 'Siguiente →'; btnNext.style.display=''; }
  if (paso===2) { btnNext.textContent = '✓ Confirmar devolución'; btnNext.style.display=''; }
  if (paso===3) { btnNext.style.display='none'; }
}

function mdevAnterior() { if(mdevPaso>1) irMdevPaso(mdevPaso-1); }

// Bloque de mantenimiento en el Paso 2: checkbox por activo con plan, más un
// hint 'sin plan' para los que no lo tienen. Se muestra solo si hay permiso +
// al menos un activo seleccionado cuyo tipo tenga plan de mantenimiento activo.
function renderMdevMantBlock() {
  const block = document.getElementById('mdev-mant-block');
  if (!block) return;
  const activosSel = mdevSelec.filter(i => i._tipo === 'activo');
  const cubiertos  = activosSel.filter(a => mdevTiposCubiertos.includes(a.tipo_activo));
  if (!mdevMantHabilitado || !cubiertos.length) { block.style.display = 'none'; return; }

  const lista = document.getElementById('mdev-mant-lista');
  lista.innerHTML = activosSel.map(a => {
    const tienePlan = mdevTiposCubiertos.includes(a.tipo_activo);
    if (tienePlan) {
      return `<label class="devol-mant-item" style="display:flex;align-items:center;gap:8px;padding:6px 8px;cursor:pointer">
        <input type="checkbox" class="mdev-mant-chk" value="${a.id}">
        <span class="mono-tag">${a._placa}</span>
        <span style="flex:1;font-size:12px;color:var(--text)">${a._desc.trim()}</span>
      </label>`;
    }
    return `<div style="display:flex;align-items:center;gap:8px;padding:6px 8px;opacity:.55">
        <span style="width:13px;text-align:center">—</span>
        <span class="mono-tag">${a._placa}</span>
        <span style="flex:1;font-size:12px;color:var(--text2)">${a._desc.trim()}</span>
        <small style="font-size:10px;color:var(--text3)">sin plan de mantenimiento</small>
      </div>`;
  }).join('');

  const fechaEl = document.getElementById('mdev-mant-fecha');
  if (fechaEl && !fechaEl.value) fechaEl.value = new Date().toISOString().slice(0, 10);
  block.style.display = '';
}

async function mdevSiguiente() {
  if (mdevPaso===1) {
    if (!mdevSelec.length) { notif('Selecciona al menos un ítem para devolver','error'); return; }
    const res = document.getElementById('mdev-resumen-items');
    res.innerHTML = mdevSelec.map(i=>`
      <div class="devol-resumen-item">
        <span class="mono-tag">${i._placa}</span>
        <span style="flex:1;font-size:12px;color:var(--text)">${i._desc.trim()}</span>
        <span class="badge ${i._tipo==='activo'?'asignado':'mantenimiento'}">${i._tipo}</span>
      </div>`).join('');
    renderMdevMantBlock();
    irMdevPaso(2);

  } else if (mdevPaso===2) {
    const responsable  = document.getElementById('mdev-responsable').value.trim();
    const estadoFisico = document.getElementById('mdev-estado-fisico').value;
    const obs          = document.getElementById('mdev-obs').value.trim();
    const custodioCedula = (document.getElementById('mdev-custodio-cedula')?.value || '').trim();
    if (!responsable) { notif('Ingresa el nombre del responsable que recibe','error'); return; }

    const usuarioId     = document.getElementById('mdev-usuario-id').value;
    const activosSel    = mdevSelec.filter(i=>i._tipo==='activo');
    const accesoriosSel = mdevSelec.filter(i=>i._tipo==='accesorio');
    const obsCompleta   = `${obs ? obs+' | ' : ''}Estado físico: ${estadoFisico}`;
    const empNombre     = document.getElementById('mdev-emp-nombre').textContent;

    // ── Mantenimiento preventivo opcional: solo si hay ≥1 activo marcado ──
    let mantenimiento = null;
    const block = document.getElementById('mdev-mant-block');
    if (block && block.style.display !== 'none') {
      const marcados = Array.from(document.querySelectorAll('.mdev-mant-chk:checked')).map(c => c.value);
      if (marcados.length) {
        const tecId = document.getElementById('mdev-mant-tecnico').value;
        if (!tecId) { notif('Selecciona el técnico para el mantenimiento programado','error'); return; }
        mantenimiento = {
          tecnico_id: tecId,
          fecha: document.getElementById('mdev-mant-fecha').value || null,
          activos_ids: marcados,
        };
      }
    }

    // ── Una sola llamada consolidada ──────────────────────────────
    // El backend agrupa por empresa y crea UNA acta por empresa con TODOS
    // los recursos (activos + accesorios). Maneja recursos con Asignación
    // activa y recursos importados sin asignación de forma indistinta.
    const res = await apiRaw('/asignaciones/devolver-lote', {
      method: 'POST',
      body: JSON.stringify({
        activos_ids: activosSel.map(a => a.id),
        accesorios_ids: accesoriosSel.map(a => a.id),
        responsable_entrega: responsable,
        responsable_recibe: empNombre,
        observaciones: obsCompleta,
        custodio_documento: custodioCedula || null,
        mantenimiento
      })
    });

    if (!res.ok) {
      const err = await res.json().catch(()=>({}));
      notif(`No se pudo registrar la devolución: ${err.detail || 'verifica los recursos seleccionados.'}`,'error');
      return;
    }

    const data  = await res.json();
    const actas = data.actas || [];

    // Generar el PDF de cada acta (normalmente 1; varias si hay empresas mixtas)
    mdevActaIds = [];
    for (const acta of actas) {
      if (acta.acta_id) {
        await apiRaw(`/actas/${acta.acta_id}/generar-pdf`, {method:'POST'});
        mdevActaIds.push(acta.acta_id);
      }
    }
    mdevActaId = mdevActaIds[0] || null;

    const totalItems = activosSel.length + accesoriosSel.length;
    const actaTxt = actas.length === 1 ? '1 acta' : `${actas.length} actas (una por empresa)`;
    const mantCreadas = data.mantenimiento?.total_creadas || 0;
    const mantTxt = mantCreadas ? ` · ${mantCreadas} tarea(s) de mantenimiento creada(s)` : '';
    document.getElementById('mdev-acta-info').textContent =
      `Devolución registrada: ${totalItems} ítem(s) en ${actaTxt}${mantTxt}.`;
    const omitidos = data.mantenimiento?.omitidos || [];
    if (omitidos.length) {
      notif(`Mantenimiento: ${omitidos.length} equipo(s) omitido(s) — ${omitidos.map(o=>`${o.placa||o.activo_id}: ${o.motivo}`).join('; ')}`,'error');
    }
    if (!mdevActaIds.length) document.getElementById('mdev-btn-pdf').style.display = 'none';
    irMdevPaso(3);
    cargarActivos(); cargarAccesorios(); cargarDashboard(); cargarUsuarios();
    if (vistaActual==='asignaciones') cargarAsignaciones();
  }
}

async function descargarActaDev() {
  // Descarga TODAS las actas generadas (una por empresa). Compatibilidad:
  // si no hay arreglo, cae al id único.
  const ids = (mdevActaIds && mdevActaIds.length) ? mdevActaIds : (mdevActaId ? [mdevActaId] : []);
  if (!ids.length) return;
  for (const id of ids) {
    const res = await fetch(`${API}/actas/${id}/descargar`, {
      headers:{'Authorization':`Bearer ${TOKEN}`}
    });
    if (res.ok) {
      const blob = await res.blob();
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href=url; a.download=`acta_devolucion_${id.slice(0,8)}.pdf`;
      a.click(); URL.revokeObjectURL(url);
    }
  }
}

// ── ASIGNACIÓN DESDE EMPLEADO ─────────────────────────