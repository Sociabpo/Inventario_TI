let estadoFiltro = '';
let activosFiltrados = [];   // resultado tras aplicar filtros (listo para exportar)
let _obsManual = false;      // true si el usuario editó la fecha de obsolescencia a mano

// ── Obsolescencia automática en el formulario de activo ──
function _obsResetManual() {
  _obsManual = false;
  const h = document.getElementById('activo-obs-hint');
  if (h) { h.style.display = 'none'; h.textContent = ''; }
}
// El usuario escribió la fecha → su valor manda; no auto-recalcular en esta sesión del modal.
function _obsMarcarManual() {
  _obsManual = true;
  const h = document.getElementById('activo-obs-hint');
  if (h) h.style.display = 'none';
}
async function _obsRecalc() {
  if (_obsManual) return;
  const tipo = document.getElementById('activo-tipo')?.value || '';
  if (!tipo) return;
  const fc = document.getElementById('activo-fecha-compra')?.value || '';
  const q = new URLSearchParams({ tipo_activo: tipo });
  if (fc) q.set('fecha_compra', fc);
  const d = await api(`/activos/calcular-obsolescencia?${q.toString()}`);
  if (!d || d.fecha_obsolescencia == null) return;
  document.getElementById('activo-fecha-obs').value = String(d.fecha_obsolescencia).slice(0, 10);
  const h = document.getElementById('activo-obs-hint');
  if (h) { h.textContent = `Calculado automáticamente (${d.anios} años). Puedes ajustarlo.`; h.style.display = ''; }
}

// ── Garantía simple en el formulario de activo (mismo patrón que obsolescencia) ──
let _garManual = false;      // true si el usuario editó el fin de garantía a mano
function _garResetManual() {
  _garManual = false;
  const h = document.getElementById('activo-garantia-hint');
  if (h) { h.style.display = 'none'; h.textContent = ''; }
}
function _garMarcarManual() {
  _garManual = true;
  const h = document.getElementById('activo-garantia-hint');
  if (h) h.style.display = 'none';
}
async function _garRecalc() {
  if (_garManual) return;
  const meses = document.getElementById('activo-garantia-meses')?.value;
  if (meses === '' || meses == null) { document.getElementById('activo-garantia-fin').value = ''; return; }
  const fc = document.getElementById('activo-fecha-compra')?.value || '';
  const q = new URLSearchParams({ meses });
  if (fc) q.set('fecha_compra', fc);
  const d = await api(`/activos/calcular-garantia?${q.toString()}`);
  if (!d || d.garantia_fin == null) return;
  document.getElementById('activo-garantia-fin').value = String(d.garantia_fin).slice(0, 10);
  const h = document.getElementById('activo-garantia-hint');
  if (h) { h.textContent = `Calculado automáticamente (${d.meses} meses). Puedes ajustarlo.`; h.style.display = ''; }
}
async function cargarActivos() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  if (estadoFiltro)  p.set('estado', estadoFiltro);
  const data = await api(`/activos?${p}`);
  activosCache = data || [];
  poblarFiltrosActivos();
  aplicarFiltrosActivos();
}
function renderActivos(list) {
  const tbody = document.getElementById('tbl-activos-body');
  tbody.innerHTML = list.length ? list.map(a=>`
    <tr class="clickable" onclick="editarActivo('${a.id}')">
      <td><span class="mono-tag">${a.id_placa_activo}</span></td>
      <td><div class="td-name">${a.tipo_activo}</div><div class="td-sub">${a.marca||''} ${a.modelo||''}</div></td>
      <td><span style="font-family:var(--mono);font-size:11px">${a.serial||'—'}</span></td>
      <td><div style="font-size:11px">${a.procesador||'—'}</div><div class="td-sub">${a.memoria_ram||''}</div></td>
      <td><div class="td-sub">${a.nombre_empresa||'—'}</div></td>
      <td>${a.nombre_usuario?`<div class="td-name">${a.nombre_usuario}</div><div class="td-sub">${a.documento_usuario}</div>`:'<span style="color:var(--text3)">—</span>'}</td>
      <td><span class="badge ${badgeEstado(a.estado)}">${labelEstado(a.estado)}</span>${a.ubicacion && a.estado!=='asignado' ? `<div class="td-sub" style="font-size:10px">📍 ${a.ubicacion}</div>` : ''}${a.estado==='reservado' && a.reserva_alta ? `<div class="td-sub" style="font-size:10px;color:#54A0FF">📌 Reservado: ${a.reserva_alta}</div>` : ''}${loanBadge(a)}${rentalBadge(a)}${custodioBadge(a)}</td>
      <td style="white-space:nowrap">
        <button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();abrirEtiqueta('${a.id_placa_activo}','${a.tipo_activo}','${a.empresa_id}')" title="Imprimir etiqueta"><i class="ti ti-qrcode"></i></button>
        <button class="btn btn-ghost btn-sm" style="color:var(--purple);border-color:rgba(167,139,255,0.3)" onclick="event.stopPropagation();abrirHojaVida('${a.id}')"><i class="ti ti-id-badge"></i> Hoja de vida</button>
        ${hasPermiso('estados.cambiar') && !['retirado','reservado'].includes(a.estado) ? `<button class="btn btn-ghost btn-sm" onclick="event.stopPropagation();abrirCambioEstado('activo','${a.id}','${a.id_placa_activo}','${a.estado}','${a.id_usuario||''}','${a.empresa_id}')" title="Cambio de estado"><i class="ti ti-transfer"></i> Estado</button>` : ''}
        ${loanActions('activo', a, a.id_placa_activo)}
        ${custodioAction('activo', a)}
        ${a.estado==='asignado' && hasPermiso('activos.devolver') ? `<button class="btn btn-ghost btn-sm" style="color:var(--amber);border-color:rgba(255,176,32,0.3)" data-uid="${a.id_usuario||''}" data-placa="${a.id_placa_activo}" onclick="event.stopPropagation();devolverDesdeRecurso(this.dataset.uid,this.dataset.placa)">↩ Devolver</button>` : ''}
      </td>
    </tr>`).join('')
    : '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:20px">Sin activos</td></tr>';
}
function filtrarActivos(estado, el) {
  estadoFiltro = estado;
  document.querySelectorAll('#tabs-activos .tab').forEach(t=>t.classList.remove('active'));
  if(el) el.classList.add('active');
  cargarActivos();
}
function buscarActivos() { aplicarFiltrosActivos(); }

function poblarFiltrosActivos() {
  llenarSelectDistinct('filtro-activos-tipo',    activosCache, 'tipo_activo',    'Todos');
  llenarSelectDistinct('filtro-activos-marca',   activosCache, 'marca',          'Todas');
  llenarSelectDistinct('filtro-activos-empresa', activosCache, 'nombre_empresa', 'Todas');
}

function aplicarFiltrosActivos() {
  const q       = (document.getElementById('search-activos').value || '').toLowerCase().trim();
  const tipo    = document.getElementById('filtro-activos-tipo').value;
  const marca   = document.getElementById('filtro-activos-marca').value;
  const empresa = document.getElementById('filtro-activos-empresa').value;
  const asign   = document.getElementById('filtro-activos-asignacion').value;
  const prestamo = document.getElementById('filtro-activos-prestamo')?.value || '';
  const fDesde  = document.getElementById('filtro-activos-fcompra-desde').value;
  const fHasta  = document.getElementById('filtro-activos-fcompra-hasta').value;

  let lista = activosCache.slice();
  if (tipo)    lista = lista.filter(a => a.tipo_activo === tipo);
  if (marca)   lista = lista.filter(a => (a.marca || '') === marca);
  if (empresa) lista = lista.filter(a => (a.nombre_empresa || '') === empresa);
  if (asign === 'asignado') lista = lista.filter(a => !!a.id_usuario);
  if (asign === 'libre')    lista = lista.filter(a => !a.id_usuario);
  if (prestamo === 'prestamo') lista = lista.filter(a => a.es_prestamo);
  if (prestamo === 'vencido')  lista = lista.filter(a => a.prestamo_vencido);
  if (fDesde)  lista = lista.filter(a => a.fecha_compra && a.fecha_compra >= fDesde);
  if (fHasta)  lista = lista.filter(a => a.fecha_compra && a.fecha_compra <= fHasta);
  if (q) lista = lista.filter(a =>
    (a.id_placa_activo||'').toLowerCase().includes(q)||
    (a.serial||'').toLowerCase().includes(q)||
    (a.modelo||'').toLowerCase().includes(q)||
    (a.marca||'').toLowerCase().includes(q)||
    (a.nombre_usuario||'').toLowerCase().includes(q));

  activosFiltrados = lista;
  renderActivos(lista);
  actualizarCount('count-activos', lista.length, activosCache.length);
}

function limpiarFiltrosActivos() {
  ['filtro-activos-tipo','filtro-activos-marca','filtro-activos-empresa','filtro-activos-asignacion',
   'filtro-activos-prestamo','filtro-activos-fcompra-desde','filtro-activos-fcompra-hasta'].forEach(id => {
    const e = document.getElementById(id); if (e) e.value = '';
  });
  document.getElementById('search-activos').value = '';
  aplicarFiltrosActivos();
}

const COLUMNAS_EXPORT_ACTIVOS = [
  {key:'id_placa_activo',   label:'Placa'},
  {key:'tipo_activo',       label:'Tipo'},
  {key:'marca',             label:'Marca'},
  {key:'modelo',            label:'Modelo'},
  {key:'serial',            label:'Serial'},
  {key:'procesador',        label:'Procesador'},
  {key:'memoria_ram',       label:'RAM'},
  {key:'disco_1',           label:'Disco'},
  {key:'nombre_empresa',    label:'Empresa'},
  {key:'nombre_usuario',    label:'Asignado a'},
  {key:'documento_usuario', label:'Documento'},
  {key:'estado',            label:'Estado'},
  {key:'fecha_compra',      label:'Fecha compra'},
];
function exportarActivos(formato, btn) {
  exportarDatos(formato, 'Activos', COLUMNAS_EXPORT_ACTIVOS, activosFiltrados, btn);
}

// Pone el modal de activo en modo SOLO LECTURA (activos retirados): se puede
// consultar la información pero todos los campos quedan deshabilitados y se
// oculta el botón de guardar.
function _setActivoReadonly(readonly) {
  const modal = document.getElementById('modal-activo');
  if (!modal) return;
  modal.querySelectorAll('.finput, .fselect, .ftextarea').forEach(el => {
    el.disabled = readonly;
  });
  const banner = document.getElementById('activo-readonly-banner');
  if (banner) banner.style.display = readonly ? 'flex' : 'none';
  const btnGuardar = document.getElementById('btn-guardar-activo');
  if (btnGuardar) btnGuardar.style.display = readonly ? 'none' : '';
}

// Modales activo
function _setupEstadoSelect(selectId, notaId, estadoActual) {
  const sel  = document.getElementById(selectId);
  const nota = document.getElementById(notaId);
  if (estadoActual === 'asignado') {
    sel.disabled = true;
    nota.textContent = '⚠ Estado bloqueado — el ítem está asignado a un usuario. Para cambiar el estado realice una devolución.';
    nota.style.display = 'block';
  } else {
    sel.disabled = false;
    nota.style.display = 'none';
    Array.from(sel.options).forEach(o => { o.disabled = o.value === 'asignado'; });
  }
}

const TIPO_GRUPOS = {
  'PC':         ['grp-pc'],
  'Portatil':   ['grp-pc'],
  'AIO':        ['grp-pc'],
  'Monitor':    ['grp-pantalla'],
  'Televisor':  ['grp-pantalla'],
  'Video Beam': ['grp-pantalla'],
  'Celular':    ['grp-movil'],
  'Ipad':       ['grp-movil'],
  'Tablet':     ['grp-movil'],
  'Impresora':  ['grp-impresora'],
  'Escaner':    ['grp-impresora'],
  'Camara':     ['grp-camara'],
  'DVR':        ['grp-camara'],
  'Diadema':    ['grp-diadema'],
  'Telefono':   ['grp-telefono'],
  'UPS':        ['grp-ups'],
};
function actualizarCamposActivo() {
  const tipo = document.getElementById('activo-tipo')?.value || '';
  document.querySelectorAll('[id^="grp-"]').forEach(g => {
    g.style.display = 'none';
    g.querySelectorAll('input,select,textarea').forEach(i => {
      if (i.type==='checkbox'||i.type==='radio') i.checked=false;
      else i.value='';
    });
  });
  const grupos = TIPO_GRUPOS[tipo] || [];
  grupos.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = 'block';
  });
  const canalesWrap = document.getElementById('activo-canales-dvr')?.closest('.fgroup');
  if (canalesWrap) canalesWrap.style.display = tipo === 'DVR' ? 'block' : 'none';
  _obsRecalc();   // recalcular fecha de obsolescencia al cambiar el tipo (si no fue manual)
}
// Contexto de "crear inventario desde recepción". null = flujo normal.
// { recepcion_item_id, recepcionId } cuando el modal se abre desde una recepción.
let _recepcionContext = null;

function abrirModalActivo() {
  _recepcionContext = null;   // flujo normal: nunca en modo recepción
  limpiarModal(['activo-id','activo-marca','activo-modelo','activo-serial','activo-parte','activo-codigo-contable','activo-ubicacion',
    'activo-fecha-compra','activo-fecha-obs','activo-costo','activo-observaciones','activo-garantia-meses','activo-garantia-fin']);
  document.getElementById('activo-estado').value = 'disponible';
  llenarSelectCatalogo('activo-tipo', 'tipo_activo', '');
  document.getElementById('modal-activo-title').textContent = 'Nuevo activo';
  document.getElementById('activo-hv-link').style.display = 'none';
  document.getElementById('activo-etq-link').style.display = 'none';
  toggleUbicacion('activo-estado','activo-ubicacion-wrap');
  llenarSelectEmpresas('activo-empresa');
  if (empresaActual) document.getElementById('activo-empresa').value = empresaActual;
  llenarSelectUbicacion('activo-ubicacion', empresaActual || '', '', 'activo-ubicacion-hint');
  _setupEstadoSelect('activo-estado', 'activo-estado-nota', null);
  document.getElementById('activo-estado').disabled = false;   // editable al crear
  document.getElementById('activo-estado-hint').style.display = 'none';
  _setActivoReadonly(false);
  _obsResetManual();   // activo nuevo → permitir auto-cálculo
  _garResetManual();   // garantía: permitir auto-cálculo
  actualizarCamposActivo();
  abrirModal('modal-activo');
}

// Al cambiar la empresa en el modal de activo, refresca el catálogo de ubicaciones
function onCambioEmpresaActivo() {
  const emp = document.getElementById('activo-empresa').value;
  llenarSelectUbicacion('activo-ubicacion', emp, '', 'activo-ubicacion-hint');
}

// Abre el modal de activo en "modo recepción": prellena desde el ítem recibido y
// marca el contexto para que guardarActivo() llame al endpoint crear-unidad.
function abrirModalActivoDesdeRecepcion(item) {
  abrirModalActivo();                                  // resetea todo (y _recepcionContext=null)
  _recepcionContext = { recepcion_item_id: item.recepcion_item_id,
                        recepcionId: item.recepcionId || null };
  document.getElementById('modal-activo-title').textContent =
    `Nuevo activo desde recepción (${(item.creados||0)+1}/${item.cantidad_recibida})`;
  // empresa
  if (item.empresa_id) {
    llenarSelectEmpresas('activo-empresa');
    document.getElementById('activo-empresa').value = item.empresa_id;
    llenarSelectUbicacion('activo-ubicacion', item.empresa_id, '', 'activo-ubicacion-hint');
  }
  // tipo: si la descripción coincide con un tipo del catálogo, se preselecciona; si no, queda libre
  if (item.tipo_sugerido) llenarSelectCatalogo('activo-tipo', 'tipo_activo', item.tipo_sugerido);
  if (item.modelo_sugerido) document.getElementById('activo-modelo').value = item.modelo_sugerido;
  if (item.serial_sugerido) document.getElementById('activo-serial').value = item.serial_sugerido;
  if (item.fecha_compra) document.getElementById('activo-fecha-compra').value = String(item.fecha_compra).slice(0,10);
  if (item.costo_unitario != null) document.getElementById('activo-costo').value = item.costo_unitario;
  actualizarCamposActivo();   // recalcula obsolescencia con el tipo/fecha prellenados
  // Mostrar SOBRE el modal de "Crear inventario desde recepción" (que sigue abierto)
  document.getElementById('modal-activo').style.zIndex = '1100';
}
function editarActivo(id) {
  if (!hasPermiso('activos.editar')) return;
  const a = activosCache.find(x=>x.id===id);
  if (!a) return;
  document.getElementById('activo-id').value              = a.id;
  document.getElementById('activo-marca').value           = a.marca||'';
  document.getElementById('activo-modelo').value          = a.modelo||'';
  document.getElementById('activo-serial').value          = a.serial||'';
  document.getElementById('activo-parte').value           = a.numero_parte||'';
  document.getElementById('activo-codigo-contable').value = a.codigo_contable||'';
  llenarSelectUbicacion('activo-ubicacion', a.empresa_id, a.ubicacion || '', 'activo-ubicacion-hint');
  // Nota: procesador/ram/disco viven en grp-pc (grupo dinámico). Se poblan MÁS ABAJO,
  // después de actualizarCamposActivo(), que limpia todos los grp-* — si se setean antes,
  // la limpieza los borra. Ver el bloque de campos por tipo.
  document.getElementById('activo-costo').value           = a.costo||'';
  document.getElementById('activo-observaciones').value   = a.observaciones||'';
  document.getElementById('activo-estado').value          = a.estado;
  if (a.fecha_compra) document.getElementById('activo-fecha-compra').value = a.fecha_compra;
  if (a.fecha_obsolescencia) document.getElementById('activo-fecha-obs').value = a.fecha_obsolescencia;
  // En edición: si ya tiene fecha de obsolescencia, se respeta (no se recalcula).
  // Si está vacía, se permite el auto-cálculo al cambiar el tipo.
  _obsResetManual();
  _obsManual = !!a.fecha_obsolescencia;
  // Garantía: prefijar valores guardados; respetar el fin si ya existe
  document.getElementById('activo-garantia-meses').value = (a.garantia_meses != null ? a.garantia_meses : '');
  document.getElementById('activo-garantia-fin').value = a.garantia_fin ? String(a.garantia_fin).slice(0, 10) : '';
  _garResetManual();
  _garManual = !!a.garantia_fin;
  document.getElementById('modal-activo-title').textContent = `Editar — ${a.id_placa_activo}`;
  document.getElementById('activo-hv-link').style.display = '';
  document.getElementById('activo-etq-link').style.display = '';
  llenarSelectEmpresas('activo-empresa');
  document.getElementById('activo-empresa').value = a.empresa_id;
  llenarSelectCatalogo('activo-tipo', 'tipo_activo', a.tipo_activo);
  actualizarCamposActivo();
  // Campos de grupos dinámicos (grp-*): poblar DESPUÉS del wipe de actualizarCamposActivo().
  document.getElementById('activo-procesador').value    = a.procesador||'';
  document.getElementById('activo-ram').value           = a.memoria_ram||'';
  document.getElementById('activo-disco1').value        = a.disco_1||'';
  document.getElementById('activo-disco2').value        = a.disco_2||'';
  document.getElementById('activo-resolucion').value    = a.resolucion||'';
  document.getElementById('activo-conexion').value      = a.tipo_conexion||'';
  document.getElementById('activo-tamano').value        = a.tamano_pantalla||'';
  document.getElementById('activo-imei').value          = a.imei||'';
  document.getElementById('activo-numtel').value        = a.numero_telefono||'';
  document.getElementById('activo-capacidad').value     = a.capacidad_almacenamiento||'';
  document.getElementById('activo-color').value         = a.color||'';
  document.getElementById('activo-tipo-impresora').value= a.tipo_impresora||'';
  document.getElementById('activo-ip').value            = a.ip_dispositivo||'';
  document.getElementById('activo-tipo-camara').value   = a.tipo_camara||'';
  document.getElementById('activo-canales-dvr').value   = a.canales_dvr||'';
  document.getElementById('activo-microfono').value     = a.con_microfono===true?'true':a.con_microfono===false?'false':'';
  document.getElementById('activo-extension').value     = a.extension||'';
  document.getElementById('activo-linea').value         = a.linea_telefono||'';
  document.getElementById('activo-tipo-telefono').value = a.tipo_telefono||'';
  document.getElementById('activo-capacidad-ups').value = a.capacidad_ups||'';
  document.getElementById('activo-respaldo-ups').value  = a.tiempo_respaldo_ups||'';
  _setupEstadoSelect('activo-estado', 'activo-estado-nota', a.estado);
  // En EDICIÓN el estado es de SOLO LECTURA: se cambia solo desde "Cambio de estado".
  document.getElementById('activo-estado').disabled = true;
  document.getElementById('activo-estado-nota').style.display = 'none';
  document.getElementById('activo-estado-hint').style.display = 'block';
  toggleUbicacion('activo-estado','activo-ubicacion-wrap');
  // Activo retirado → solo lectura: se puede consultar pero no modificar.
  _setActivoReadonly(a.estado === 'retirado');
  if (a.estado === 'retirado') {
    document.getElementById('activo-estado-hint').style.display = 'none';
  }
  abrirModal('modal-activo');
}
async function guardarActivo() {
  const id          = document.getElementById('activo-id').value;
  if ( id && !hasPermiso('activos.editar')) { notif('Sin permiso para editar activos','error'); return; }
  if (!id && !hasPermiso('activos.crear'))  { notif('Sin permiso para crear activos','error');  return; }
  const nuevoEstado = document.getElementById('activo-estado').value;

  if (id) {
    const cached = activosCache.find(x => x.id === id);
    // Un activo retirado es de solo lectura: no se permite ninguna modificación.
    if (cached?.estado === 'retirado') {
      notif('El activo está retirado y no puede modificarse.', 'error');
      return;
    }
    // Se puede editar un activo asignado; lo único bloqueado es CAMBIAR su estado.
    if (cached?.estado === 'asignado' && nuevoEstado !== 'asignado') {
      notif('No se puede cambiar el estado de un activo asignado. Realice una devolución primero.', 'error');
      return;
    }
    if (cached?.estado !== 'asignado' && nuevoEstado === 'asignado') {
      notif('No se puede asignar manualmente. Use el módulo de Asignaciones.', 'error');
      return;
    }
  }

  const ubicacionVal = document.getElementById('activo-ubicacion').value.trim();
  if (nuevoEstado !== 'asignado' && !ubicacionVal) {
    notif('La ubicación es obligatoria cuando el estado no es "Asignado"', 'error');
    return;
  }

  const body = {
    empresa_id:     document.getElementById('activo-empresa').value,
    tipo_activo:    document.getElementById('activo-tipo').value,
    marca:          document.getElementById('activo-marca').value||null,
    modelo:         document.getElementById('activo-modelo').value||null,
    serial:         document.getElementById('activo-serial').value||null,
    numero_parte:   document.getElementById('activo-parte').value||null,
    codigo_contable: document.getElementById('activo-codigo-contable').value||null,
    ubicacion:      ubicacionVal||null,
    procesador:     document.getElementById('activo-procesador').value||null,
    memoria_ram:    document.getElementById('activo-ram').value||null,
    disco_1:        document.getElementById('activo-disco1').value||null,
    disco_2:                  document.getElementById('activo-disco2').value||null,
    resolucion:               document.getElementById('activo-resolucion')?.value||null,
    tipo_conexion:            document.getElementById('activo-conexion')?.value||null,
    tamano_pantalla:          document.getElementById('activo-tamano')?.value||null,
    imei:                     document.getElementById('activo-imei')?.value||null,
    numero_telefono:          document.getElementById('activo-numtel')?.value||null,
    capacidad_almacenamiento: document.getElementById('activo-capacidad')?.value||null,
    color:                    document.getElementById('activo-color')?.value||null,
    tipo_impresora:           document.getElementById('activo-tipo-impresora')?.value||null,
    ip_dispositivo:           document.getElementById('activo-ip')?.value||null,
    tipo_camara:              document.getElementById('activo-tipo-camara')?.value||null,
    canales_dvr:              document.getElementById('activo-canales-dvr')?.value ? parseInt(document.getElementById('activo-canales-dvr').value) : null,
    con_microfono:            document.getElementById('activo-microfono')?.value===''?null:document.getElementById('activo-microfono')?.value==='true',
    extension:                document.getElementById('activo-extension')?.value||null,
    linea_telefono:           document.getElementById('activo-linea')?.value||null,
    tipo_telefono:            document.getElementById('activo-tipo-telefono')?.value||null,
    capacidad_ups:            document.getElementById('activo-capacidad-ups')?.value||null,
    tiempo_respaldo_ups:      document.getElementById('activo-respaldo-ups')?.value||null,
    fecha_compra:   document.getElementById('activo-fecha-compra').value||null,
    fecha_obsolescencia: document.getElementById('activo-fecha-obs').value||null,
    costo:          document.getElementById('activo-costo').value||null,
    observaciones:  document.getElementById('activo-observaciones').value||null,
    garantia_meses: document.getElementById('activo-garantia-meses').value !== '' ? parseInt(document.getElementById('activo-garantia-meses').value) : null,
    garantia_fin:   document.getElementById('activo-garantia-fin').value||null,
  };
  // El estado SOLO se envía al CREAR. Al editar nunca se incluye: los cambios de
  // estado se realizan exclusivamente desde el botón "Cambio de estado".
  if (!id) body.estado = nuevoEstado;
  if (!body.empresa_id||!body.tipo_activo) { notif('Empresa y tipo son obligatorios','error'); return; }
  // Modo recepción: crear UNA unidad vía el endpoint de recepción (no el create normal)
  if (!id && _recepcionContext) { return _guardarActivoDesdeRecepcion(body); }
  const res = await apiRaw(id?`/activos/${id}`:`/activos`, {
    method: id?'PUT':'POST', body: JSON.stringify(id?{...body}:body)
  });
  if (res.ok) {
    if (id) {
      notif('Activo actualizado');
      cerrarModal('modal-activo'); cargarActivos(); cargarDashboard();
    } else {
      const data = await res.json();
      notif('Activo creado correctamente');
      cerrarModal('modal-activo'); cargarActivos(); cargarDashboard(); cargarEmpresas();
      if (data && data.id_placa_activo && confirm(`Activo ${data.id_placa_activo} creado. ¿Deseas imprimir la etiqueta?`)) {
        abrirEtiqueta(data.id_placa_activo, data.tipo_activo, data.empresa_id);
      }
    }
  } else {
    const err = await res.json();
    notif(err.detail||'Error al guardar','error');
  }
}

// Guarda una unidad en modo recepción (POST crear-unidad). Mantiene el modal
// reabrible para crear la siguiente unidad del mismo ítem.
async function _guardarActivoDesdeRecepcion(body) {
  const ctx = _recepcionContext;
  const payload = { ...body, tipo_recurso: 'activo' };
  const res = await apiRaw(`/compras/recepciones/items/${ctx.recepcion_item_id}/crear-unidad`,
    { method: 'POST', body: JSON.stringify(payload) });
  if (res.ok) {
    const d = await res.json();
    const total = d.creados + d.pendientes;
    notif(`Activo ${d.recurso.placa} creado (${d.creados}/${total})`);
    _recepcionContext = null;
    cerrarModal('modal-activo');
    if (ctx.recepcionId && typeof refrescarCrearInventario === 'function') refrescarCrearInventario(ctx.recepcionId);
    if (typeof cargarActivos === 'function') cargarActivos();
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

// ── ACCESORIOS ────────────────────────────────────────