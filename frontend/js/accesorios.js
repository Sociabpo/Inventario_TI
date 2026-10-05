let estadoFiltroAcc = '';
let accFiltrados = [];   // resultado tras aplicar filtros (listo para exportar)
async function cargarAccesorios() {
  const p = new URLSearchParams();
  if (empresaActual)     p.set('empresa_id', empresaActual);
  if (estadoFiltroAcc)   p.set('estado', estadoFiltroAcc);
  const data = await api(`/accesorios${p.toString() ? '?' + p.toString() : ''}`);
  accCache = data || [];
  poblarFiltrosAccesorios();
  aplicarFiltrosAccesorios();
}
function filtrarAccesorios(estado, el) {
  estadoFiltroAcc = estado;
  document.querySelectorAll('#tabs-accesorios .tab').forEach(t => t.classList.remove('active'));
  if (el) el.classList.add('active');
  cargarAccesorios();
}
function renderAccesorios(list) {
  const tbody = document.getElementById('tbl-accesorios-body');
  tbody.innerHTML = list.length ? list.map(a=>`
    <tr class="clickable" onclick="editarAccesorio('${a.id}')">
      <td><span class="mono-tag">${a.id_placa_accesorio}</span></td>
      <td><span class="badge asignado" style="font-size:10px">${a.tipo_accesorio}</span></td>
      <td><div class="td-name">${a.marca||'—'}</div><div class="td-sub">${a.modelo||''}</div></td>
      <td><span style="font-family:var(--mono);font-size:11px">${a.serial||'—'}</span></td>
      <td><div class="td-sub">${a.nombre_empresa||'—'}</div></td>
      <td>${a.nombre_usuario?`<div class="td-name">${a.nombre_usuario}</div><div class="td-sub">${a.documento_usuario}</div>`:'<span style="color:var(--text3)">—</span>'}</td>
      <td><span class="badge ${badgeEstado(a.estado)}">${labelEstado(a.estado)}</span>${a.ubicacion && a.estado!=='asignado' ? `<div class="td-sub" style="font-size:10px">📍 ${a.ubicacion}</div>` : ''}${a.estado==='reservado' && a.reserva_alta ? `<div class="td-sub" style="font-size:10px;color:var(--info)">📌 Reservado: ${a.reserva_alta}</div>` : ''}${loanBadge(a)}${rentalBadge(a)}${custodioBadge(a)}</td>
      <td style="white-space:nowrap">
        <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();abrirEtiqueta('${a.id_placa_accesorio}','${a.tipo_accesorio}','${a.empresa_id}')" title="Imprimir etiqueta"><i class="ti ti-qrcode"></i></button>
        ${hasPermiso('estados.cambiar') && !['retirado','reservado'].includes(a.estado) ? `<button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();abrirCambioEstado('accesorio','${a.id}','${a.id_placa_accesorio}','${a.estado}','${a.id_usuario||''}','${a.empresa_id}')" title="Cambio de estado"><i class="ti ti-transfer"></i> Estado</button>` : ''}
        ${loanActions('accesorio', a, a.id_placa_accesorio)}
        ${custodioAction('accesorio', a)}
        ${a.estado==='asignado' && hasPermiso('accesorios.devolver') ? `<button class="btn btn-ghost btn-sm" style="color:var(--amber);border-color:rgba(255,176,32,0.3)" data-uid="${a.id_usuario||''}" data-placa="${a.id_placa_accesorio}" onclick="event.stopPropagation();devolverDesdeRecurso(this.dataset.uid,this.dataset.placa)">↩ Devolver</button>` : ''}
      </td>
    </tr>`).join('')
    : '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:20px">Sin accesorios</td></tr>';
}
function buscarAccesorios() { aplicarFiltrosAccesorios(); }

function poblarFiltrosAccesorios() {
  llenarSelectDistinct('filtro-accesorios-tipo',    accCache, 'tipo_accesorio', 'Todos');
  llenarSelectDistinct('filtro-accesorios-marca',   accCache, 'marca',          'Todas');
  llenarSelectDistinct('filtro-accesorios-empresa', accCache, 'nombre_empresa', 'Todas');
}

function aplicarFiltrosAccesorios() {
  const q       = (document.getElementById('search-accesorios').value || '').toLowerCase().trim();
  const tipo    = document.getElementById('filtro-accesorios-tipo').value;
  const marca   = document.getElementById('filtro-accesorios-marca').value;
  const empresa = document.getElementById('filtro-accesorios-empresa').value;
  const asign   = document.getElementById('filtro-accesorios-asignacion').value;
  const prestamo = document.getElementById('filtro-accesorios-prestamo')?.value || '';

  let lista = accCache.slice();
  if (tipo)    lista = lista.filter(a => a.tipo_accesorio === tipo);
  if (marca)   lista = lista.filter(a => (a.marca || '') === marca);
  if (empresa) lista = lista.filter(a => (a.nombre_empresa || '') === empresa);
  if (asign === 'asignado') lista = lista.filter(a => !!a.id_usuario);
  if (asign === 'libre')    lista = lista.filter(a => !a.id_usuario);
  if (prestamo === 'prestamo') lista = lista.filter(a => a.es_prestamo);
  if (prestamo === 'vencido')  lista = lista.filter(a => a.prestamo_vencido);
  if (q) lista = lista.filter(a =>
    (a.id_placa_accesorio||'').toLowerCase().includes(q)||
    (a.tipo_accesorio||'').toLowerCase().includes(q)||
    (a.marca||'').toLowerCase().includes(q)||
    (a.serial||'').toLowerCase().includes(q)||
    (a.nombre_usuario||'').toLowerCase().includes(q));

  accFiltrados = lista;
  renderAccesorios(lista);
  actualizarCount('count-accesorios', lista.length, accCache.length);
}

function limpiarFiltrosAccesorios() {
  ['filtro-accesorios-tipo','filtro-accesorios-marca','filtro-accesorios-empresa','filtro-accesorios-asignacion','filtro-accesorios-prestamo'].forEach(id => {
    const e = document.getElementById(id); if (e) e.value = '';
  });
  document.getElementById('search-accesorios').value = '';
  aplicarFiltrosAccesorios();
}

const COLUMNAS_EXPORT_ACCESORIOS = [
  {key:'id_placa_accesorio', label:'Placa'},
  {key:'tipo_accesorio',     label:'Tipo'},
  {key:'marca',              label:'Marca'},
  {key:'modelo',             label:'Modelo'},
  {key:'serial',             label:'Serial'},
  {key:'nombre_empresa',     label:'Empresa'},
  {key:'nombre_usuario',     label:'Asignado a'},
  {key:'documento_usuario',  label:'Documento'},
  {key:'estado',             label:'Estado'},
];
function exportarAccesorios(formato, btn) {
  exportarDatos(formato, 'Accesorios', COLUMNAS_EXPORT_ACCESORIOS, accFiltrados, btn);
}
// Pone el modal de accesorio en modo SOLO LECTURA (accesorios retirados): se puede
// consultar la información pero todos los campos quedan deshabilitados y se oculta
// el botón de guardar.
function _setAccesorioReadonly(readonly) {
  const modal = document.getElementById('modal-accesorio');
  if (!modal) return;
  modal.querySelectorAll('.finput, .fselect, .ftextarea').forEach(el => {
    el.disabled = readonly;
  });
  const banner = document.getElementById('acc-readonly-banner');
  if (banner) banner.style.display = readonly ? 'flex' : 'none';
  const btnGuardar = document.getElementById('btn-guardar-accesorio');
  if (btnGuardar) btnGuardar.style.display = readonly ? 'none' : '';
}
// Contexto de "crear inventario desde recepción" para accesorios. null = flujo normal.
let _recepcionContextAcc = null;

// ── Garantía simple en el formulario de accesorio (base = hoy; sin fecha_compra) ──
let _garManualAcc = false;
function _garResetManualAcc() {
  _garManualAcc = false;
  const h = document.getElementById('acc-garantia-hint');
  if (h) { h.style.display = 'none'; h.textContent = ''; }
}
function _garMarcarManualAcc() {
  _garManualAcc = true;
  const h = document.getElementById('acc-garantia-hint');
  if (h) h.style.display = 'none';
}
async function _garRecalcAcc() {
  if (_garManualAcc) return;
  const meses = document.getElementById('acc-garantia-meses')?.value;
  if (meses === '' || meses == null) { document.getElementById('acc-garantia-fin').value = ''; return; }
  const d = await api(`/activos/calcular-garantia?meses=${encodeURIComponent(meses)}`);
  if (!d || d.garantia_fin == null) return;
  document.getElementById('acc-garantia-fin').value = String(d.garantia_fin).slice(0, 10);
  const h = document.getElementById('acc-garantia-hint');
  if (h) { h.textContent = `Calculado automáticamente (${d.meses} meses). Puedes ajustarlo.`; h.style.display = ''; }
}

function abrirModalAccesorio() {
  _recepcionContextAcc = null;   // flujo normal
  limpiarModal(['acc-id','acc-marca','acc-modelo','acc-serial','acc-ubicacion','acc-obs','acc-garantia-meses','acc-garantia-fin']);
  _garResetManualAcc();
  llenarSelectCatalogo('acc-tipo', 'tipo_accesorio', '');
  document.getElementById('acc-estado').value = 'disponible';
  document.getElementById('modal-acc-title').textContent = 'Nuevo accesorio';
  document.getElementById('acc-etq-link').style.display = 'none';
  llenarSelectEmpresas('acc-empresa');
  if (empresaActual) document.getElementById('acc-empresa').value = empresaActual;
  llenarSelectUbicacion('acc-ubicacion', empresaActual || '', '', 'acc-ubicacion-hint');
  _setupEstadoSelect('acc-estado', 'acc-estado-nota', null);
  document.getElementById('acc-estado').disabled = false;   // editable al crear
  document.getElementById('acc-estado-hint').style.display = 'none';
  _setAccesorioReadonly(false);
  toggleUbicacion('acc-estado','acc-ubicacion-wrap');
  abrirModal('modal-accesorio');
}

// Al cambiar la empresa en el modal de accesorio, refresca el catálogo de ubicaciones
function onCambioEmpresaAccesorio() {
  const emp = document.getElementById('acc-empresa').value;
  llenarSelectUbicacion('acc-ubicacion', emp, '', 'acc-ubicacion-hint');
}

// Abre el modal de accesorio en "modo recepción": prellena y marca el contexto
// para que guardarAccesorio() llame al endpoint crear-unidad.
function abrirModalAccesorioDesdeRecepcion(item) {
  abrirModalAccesorio();                               // resetea todo (y _recepcionContextAcc=null)
  _recepcionContextAcc = { recepcion_item_id: item.recepcion_item_id,
                           recepcionId: item.recepcionId || null };
  document.getElementById('modal-acc-title').textContent =
    `Nuevo accesorio desde recepción (${(item.creados||0)+1}/${item.cantidad_recibida})`;
  if (item.empresa_id) {
    llenarSelectEmpresas('acc-empresa');
    document.getElementById('acc-empresa').value = item.empresa_id;
    llenarSelectUbicacion('acc-ubicacion', item.empresa_id, '', 'acc-ubicacion-hint');
  }
  if (item.tipo_sugerido) llenarSelectCatalogo('acc-tipo', 'tipo_accesorio', item.tipo_sugerido);
  if (item.modelo_sugerido) document.getElementById('acc-modelo').value = item.modelo_sugerido;
  if (item.serial_sugerido) document.getElementById('acc-serial').value = item.serial_sugerido;
  // Mostrar SOBRE el modal de "Crear inventario desde recepción" (que sigue abierto)
  document.getElementById('modal-accesorio').style.zIndex = '1100';
}
function editarAccesorio(id) {
  if (!hasPermiso('accesorios.editar')) return;
  const a = accCache.find(x=>x.id===id);
  if (!a) return;
  document.getElementById('acc-id').value     = a.id;
  document.getElementById('acc-marca').value  = a.marca||'';
  document.getElementById('acc-modelo').value = a.modelo||'';
  document.getElementById('acc-serial').value = a.serial||'';
  llenarSelectUbicacion('acc-ubicacion', a.empresa_id, a.ubicacion || '', 'acc-ubicacion-hint');
  document.getElementById('acc-obs').value    = a.observaciones||'';
  document.getElementById('acc-estado').value = a.estado;
  // Garantía: prefijar valores guardados; respetar el fin si ya existe
  document.getElementById('acc-garantia-meses').value = (a.garantia_meses != null ? a.garantia_meses : '');
  document.getElementById('acc-garantia-fin').value = a.garantia_fin ? String(a.garantia_fin).slice(0, 10) : '';
  _garResetManualAcc();
  _garManualAcc = !!a.garantia_fin;
  document.getElementById('modal-acc-title').textContent = `Editar — ${a.id_placa_accesorio}`;
  document.getElementById('acc-etq-link').style.display = '';
  llenarSelectEmpresas('acc-empresa');
  document.getElementById('acc-empresa').value = a.empresa_id;
  llenarSelectCatalogo('acc-tipo', 'tipo_accesorio', a.tipo_accesorio);
  _setupEstadoSelect('acc-estado', 'acc-estado-nota', a.estado);
  // En EDICIÓN el estado es de SOLO LECTURA: se cambia solo desde "Cambio de estado".
  document.getElementById('acc-estado').disabled = true;
  document.getElementById('acc-estado-nota').style.display = 'none';
  document.getElementById('acc-estado-hint').style.display = 'block';
  toggleUbicacion('acc-estado','acc-ubicacion-wrap');
  // Accesorio retirado → solo lectura: se puede consultar pero no modificar.
  _setAccesorioReadonly(a.estado === 'retirado');
  if (a.estado === 'retirado') {
    document.getElementById('acc-estado-hint').style.display = 'none';
  }
  abrirModal('modal-accesorio');
}
async function guardarAccesorio() {
  const id          = document.getElementById('acc-id').value;
  if ( id && !hasPermiso('accesorios.editar')) { notif('Sin permiso para editar accesorios','error'); return; }
  if (!id && !hasPermiso('accesorios.crear'))  { notif('Sin permiso para crear accesorios','error');  return; }
  const nuevoEstado = document.getElementById('acc-estado').value;

  if (id) {
    const cached = accCache.find(x => x.id === id);
    // Un accesorio retirado es de solo lectura: no se permite ninguna modificación.
    if (cached?.estado === 'retirado') {
      notif('El accesorio está retirado y no puede modificarse.', 'error');
      return;
    }
    if (cached?.estado === 'asignado' && nuevoEstado !== 'asignado') {
      notif('No se puede cambiar el estado de un accesorio asignado. Realice una devolución primero.', 'error');
      return;
    }
    if (cached?.estado !== 'asignado' && nuevoEstado === 'asignado') {
      notif('No se puede asignar manualmente. Use el módulo de Asignaciones.', 'error');
      return;
    }
  }

  const ubicacionVal = document.getElementById('acc-ubicacion').value.trim();
  if (nuevoEstado !== 'asignado' && !ubicacionVal) {
    notif('La ubicación es obligatoria cuando el estado no es "Asignado"', 'error');
    return;
  }

  const body = {
    empresa_id:     document.getElementById('acc-empresa').value,
    tipo_accesorio: document.getElementById('acc-tipo').value,
    marca:          document.getElementById('acc-marca').value||null,
    modelo:         document.getElementById('acc-modelo').value||null,
    serial:         document.getElementById('acc-serial').value||null,
    ubicacion:      ubicacionVal||null,
    observaciones:  document.getElementById('acc-obs').value||null,
    garantia_meses: document.getElementById('acc-garantia-meses').value !== '' ? parseInt(document.getElementById('acc-garantia-meses').value) : null,
    garantia_fin:   document.getElementById('acc-garantia-fin').value||null,
  };
  // El estado SOLO se envía al CREAR; al editar nunca se incluye.
  if (!id) body.estado = document.getElementById('acc-estado').value;
  if (!body.empresa_id||!body.tipo_accesorio) { notif('Empresa y tipo son obligatorios','error'); return; }
  // Modo recepción: crear UNA unidad vía el endpoint de recepción
  if (!id && _recepcionContextAcc) { return _guardarAccesorioDesdeRecepcion(body); }
  const res = await apiRaw(id?`/accesorios/${id}`:`/accesorios`, {
    method: id?'PUT':'POST', body: JSON.stringify(body)
  });
  if (res.ok) {
    if (id) {
      notif('Accesorio actualizado');
      cerrarModal('modal-accesorio'); cargarAccesorios();
    } else {
      const data = await res.json();
      notif('Accesorio creado');
      cerrarModal('modal-accesorio'); cargarAccesorios();
      if (data && data.id_placa_accesorio && confirm(`Accesorio ${data.id_placa_accesorio} creado. ¿Deseas imprimir la etiqueta?`)) {
        abrirEtiqueta(data.id_placa_accesorio, data.tipo_accesorio, data.empresa_id);
      }
    }
  } else {
    const err = await res.json();
    notif(err.detail||'Error al guardar','error');
  }
}

// Guarda una unidad de accesorio en modo recepción (POST crear-unidad).
async function _guardarAccesorioDesdeRecepcion(body) {
  const ctx = _recepcionContextAcc;
  const payload = { ...body, tipo_recurso: 'accesorio' };
  const res = await apiRaw(`/compras/recepciones/items/${ctx.recepcion_item_id}/crear-unidad`,
    { method: 'POST', body: JSON.stringify(payload) });
  if (res.ok) {
    const d = await res.json();
    const total = d.creados + d.pendientes;
    notif(`Accesorio ${d.recurso.placa} creado (${d.creados}/${total})`);
    _recepcionContextAcc = null;
    cerrarModal('modal-accesorio');
    if (ctx.recepcionId && typeof refrescarCrearInventario === 'function') refrescarCrearInventario(ctx.recepcionId);
    if (typeof cargarAccesorios === 'function') cargarAccesorios();
    if (d.recepcion_completa) {
      notif('Inventario completo', 'success');
      if (typeof cargarRecepciones === 'function') cargarRecepciones();
      if (typeof cargarOrdenes === 'function') cargarOrdenes();
      if (typeof cargarStatsCompras === 'function') cargarStatsCompras();
    }
  } else {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error al crear la unidad', 'error');
  }
}

// ── EMPLEADOS ─────────────────────────────────────────