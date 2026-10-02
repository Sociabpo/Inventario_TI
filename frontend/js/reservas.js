// ── Reservas de activos/accesorios ───────────────────────────────────────────
let reservaItems = [];     // {tipo_recurso, recurso_id, placa, tipo, marca, modelo}
let reservasCache = [];

// ── Modal de nueva reserva ────────────────────────────────
function abrirModalReserva() {
  if (!hasPermiso('reservas.gestionar')) { notif('Sin permiso para gestionar reservas', 'error'); return; }
  if (!empresaActual) { notif('Selecciona una empresa primero', 'error'); return; }
  reservaItems = [];
  document.getElementById('reserva-alta').value = '';
  document.getElementById('reserva-desc').value = '';
  const fl = document.getElementById('reserva-fecha-limite');
  const manana = new Date(); manana.setDate(manana.getDate() + 1);
  fl.min = manana.toISOString().slice(0, 10);
  fl.value = '';
  document.getElementById('reserva-tipo-recurso').value = 'activo';
  document.getElementById('reserva-buscar-input').value = '';
  document.getElementById('reserva-buscar-results').innerHTML = '';
  renderReservaItems();
  abrirModal('modal-reserva');
}

// ── Buscar recursos disponibles de la empresa activa ──────
async function buscarRecursoReserva() {
  const tipo = document.getElementById('reserva-tipo-recurso').value;   // activo | accesorio
  const q = document.getElementById('reserva-buscar-input').value.trim();
  const path = tipo === 'activo' ? 'activos' : 'accesorios';
  const p = new URLSearchParams();
  p.set('estado', 'disponible');
  if (empresaActual) p.set('empresa_id', empresaActual);
  if (q) p.set('q', q);
  const data = await api(`/${path}?${p}`) || [];
  const cont = document.getElementById('reserva-buscar-results');
  if (!data.length) {
    cont.innerHTML = '<div style="padding:9px 10px;color:var(--text3);font-size:12px">Sin recursos disponibles</div>';
    return;
  }
  cont.innerHTML = data.slice(0, 25).map(r => {
    const placa = tipo === 'activo' ? r.id_placa_activo : r.id_placa_accesorio;
    const t = tipo === 'activo' ? r.tipo_activo : r.tipo_accesorio;
    const ya = reservaItems.some(i => i.recurso_id === r.id);
    const marca = (r.marca || '').replace(/'/g, '');
    const modelo = (r.modelo || '').replace(/'/g, '');
    return `<div style="display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-bottom:0.5px solid var(--border)">
      <div><span class="mono-tag">${placa}</span> <span style="font-size:12px">${t} ${r.marca || ''} ${r.modelo || ''}</span></div>
      <button class="btn btn-ghost btn-sm" ${ya ? 'disabled' : ''}
        onclick="agregarItemReserva('${tipo}','${r.id}','${placa}','${t}','${marca}','${modelo}')">${ya ? '✓ Agregado' : '+ Agregar'}</button>
    </div>`;
  }).join('');
}

function agregarItemReserva(tipo, recursoId, placa, t, marca, modelo) {
  if (reservaItems.some(i => i.recurso_id === recursoId)) return;
  reservaItems.push({ tipo_recurso: tipo, recurso_id: recursoId, placa, tipo: t, marca, modelo });
  renderReservaItems();
  buscarRecursoReserva();   // refresca para deshabilitar el ya agregado
}

function quitarItemReserva(idx) {
  reservaItems.splice(idx, 1);
  renderReservaItems();
  buscarRecursoReserva();
}

function renderReservaItems() {
  const cont = document.getElementById('reserva-items-list');
  document.getElementById('reserva-items-count').textContent = reservaItems.length;
  if (!reservaItems.length) {
    cont.innerHTML = '<div style="padding:10px;color:var(--text3);font-size:12px">Aún no has agregado recursos</div>';
    return;
  }
  cont.innerHTML = reservaItems.map((i, idx) => `
    <div style="display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:var(--bg3);border-radius:6px;margin-bottom:4px">
      <div>
        <span class="badge ${i.tipo_recurso === 'activo' ? 'asignado' : 'disponible'}" style="font-size:9px">${i.tipo_recurso}</span>
        <span class="mono-tag">${i.placa}</span>
        <span style="font-size:11px;color:var(--text3)">${i.tipo} ${i.marca || ''} ${i.modelo || ''}</span>
      </div>
      <button class="btn btn-ghost btn-sm" style="color:var(--red)" onclick="quitarItemReserva(${idx})" title="Quitar">×</button>
    </div>`).join('');
}

async function guardarReserva() {
  const numero_alta = document.getElementById('reserva-alta').value.trim();
  const descripcion = document.getElementById('reserva-desc').value.trim();
  const fecha_limite = document.getElementById('reserva-fecha-limite').value;
  if (!numero_alta) { notif('El número de alta es obligatorio', 'error'); return; }
  if (!fecha_limite) { notif('La fecha límite es obligatoria', 'error'); return; }
  if (!reservaItems.length) { notif('Agrega al menos un recurso', 'error'); return; }
  const body = {
    numero_alta,
    descripcion: descripcion || null,
    empresa_id: empresaActual,
    fecha_limite,
    items: reservaItems.map(i => ({ tipo_recurso: i.tipo_recurso, recurso_id: i.recurso_id })),
  };
  const res = await apiRaw('/reservas', { method: 'POST', body: JSON.stringify(body) });
  if (res.ok) {
    notif('Reserva creada correctamente');
    cerrarModal('modal-reserva');
    if (vistaActual === 'activos' && typeof cargarActivos === 'function') cargarActivos();
    if (vistaActual === 'accesorios' && typeof cargarAccesorios === 'function') cargarAccesorios();
    if (vistaActual === 'reservas') cargarReservas();
  } else {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error al crear la reserva', 'error');
  }
}

// ── Vista de reservas ─────────────────────────────────────
async function cargarReservas() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  const estadoF = document.getElementById('reservas-filtro-estado')?.value;
  if (estadoF) p.set('estado', estadoF);
  const q = document.getElementById('reservas-search')?.value.trim();
  if (q) p.set('q', q);
  reservasCache = await api(`/reservas?${p}`) || [];
  aplicarFiltrosReservas();
}

function buscarReservas() { cargarReservas(); }

// Filtros client-side sobre la fecha límite (la búsqueda y el estado van al backend)
function aplicarFiltrosReservas() {
  const desde = document.getElementById('reservas-filtro-desde')?.value;
  const hasta = document.getElementById('reservas-filtro-hasta')?.value;
  const vence = document.getElementById('reservas-filtro-vence')?.value;
  let lista = reservasCache.slice();
  if (desde) lista = lista.filter(r => r.fecha_limite && r.fecha_limite >= desde);
  if (hasta) lista = lista.filter(r => r.fecha_limite && r.fecha_limite <= hasta);
  if (vence === 'pronto')   lista = lista.filter(r => r.estado === 'activa' && r.dias_restantes != null && r.dias_restantes >= 0 && r.dias_restantes <= 2);
  if (vence === 'vencidas') lista = lista.filter(r => r.dias_restantes != null && r.dias_restantes < 0);
  renderReservas(lista);
  const cnt = document.getElementById('count-reservas');
  if (cnt) cnt.textContent = `Mostrando ${lista.length} de ${reservasCache.length}`;
}

function limpiarFiltrosReservas() {
  ['reservas-filtro-desde', 'reservas-filtro-hasta'].forEach(id => { const e = document.getElementById(id); if (e) e.value = ''; });
  const ve = document.getElementById('reservas-filtro-vence'); if (ve) ve.value = '';
  const es = document.getElementById('reservas-filtro-estado'); if (es) es.value = '';
  const sr = document.getElementById('reservas-search'); if (sr) sr.value = '';
  cargarReservas();
}

function renderReservas(list) {
  const tbody = document.getElementById('tbl-reservas-body');
  if (!tbody) return;
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="7" style="text-align:center;color:var(--text3);padding:22px">Sin reservas</td></tr>';
    return;
  }
  const badge = { activa: 'asignado', completada: 'disponible', cancelada: 'baja', vencida: 'mantenimiento' };
  tbody.innerHTML = list.map(r => {
    const venceProximo = r.estado === 'activa' && r.dias_restantes != null && r.dias_restantes <= 2;
    const filaStyle = venceProximo ? 'style="background:rgba(255,176,32,0.06)"' : '';
    const altaEsc = (r.numero_alta || '').replace(/'/g, '');
    const acciones = r.estado === 'activa'
      ? `<button class="btn btn-ghost btn-sm" onclick="abrirEditarReserva('${r.id}','${altaEsc}','${r.fecha_limite || ''}','${(r.descripcion || '').replace(/'/g, '')}')" title="Editar fecha límite"><i class="ti ti-edit"></i> Editar</button>
         <button class="btn btn-ghost btn-sm" style="color:var(--red);border-color:rgba(255,77,109,.3)" onclick="cancelarReserva('${r.id}','${altaEsc}')">Cancelar</button>`
      : '<span style="color:var(--text3)">—</span>';
    const dias = r.estado === 'activa'
      ? (r.dias_restantes < 0 ? 'Vencida' : `${r.dias_restantes} día(s)`)
      : '';
    const recursos = (r.items || []).map(i =>
      `<span class="mono-tag" title="${i.tipo || ''} ${i.marca || ''} ${i.modelo || ''} · ${i.estado}">${i.placa}</span>`).join(' ');
    return `<tr ${filaStyle}>
      <td><span class="mono-tag">${r.numero_alta}</span></td>
      <td style="font-size:11px;color:var(--text3);max-width:200px">${r.descripcion || '—'}</td>
      <td><div class="td-sub">${r.nombre_empresa || '—'}</div></td>
      <td>${r.fecha_limite || '—'}${venceProximo ? ` <span style="font-size:10px;color:var(--amber)">⚠ ${dias}</span>` : ''}</td>
      <td>${r.items_reservados}/${r.total_items} reservados<div style="margin-top:3px;display:flex;flex-wrap:wrap;gap:3px">${recursos}</div></td>
      <td><span class="badge ${badge[r.estado] || 'disponible'}">${r.estado}</span></td>
      <td style="white-space:nowrap">${acciones}</td>
    </tr>`;
  }).join('');
}

// ── Editar fecha límite / descripción ─────────────────────
function abrirEditarReserva(id, alta, fechaLimite, descripcion) {
  if (!hasPermiso('reservas.gestionar')) { notif('Sin permiso para gestionar reservas', 'error'); return; }
  document.getElementById('editar-reserva-id').value = id;
  document.getElementById('editar-reserva-alta').textContent = alta;
  const fl = document.getElementById('editar-reserva-fecha');
  const manana = new Date(); manana.setDate(manana.getDate() + 1);
  fl.min = manana.toISOString().slice(0, 10);
  fl.value = fechaLimite || '';
  document.getElementById('editar-reserva-desc').value = descripcion || '';
  abrirModal('modal-editar-reserva');
}

async function guardarEditarReserva() {
  const id = document.getElementById('editar-reserva-id').value;
  const fecha_limite = document.getElementById('editar-reserva-fecha').value;
  const descripcion = document.getElementById('editar-reserva-desc').value.trim();
  if (!fecha_limite) { notif('La fecha límite es obligatoria', 'error'); return; }
  const res = await apiRaw(`/reservas/${id}`, {
    method: 'PUT', body: JSON.stringify({ fecha_limite, descripcion: descripcion || null }),
  });
  if (res.ok) {
    notif('Reserva actualizada');
    cerrarModal('modal-editar-reserva');
    cargarReservas();
  } else {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error al actualizar la reserva', 'error');
  }
}

async function cancelarReserva(id, alta) {
  if (!confirm(`¿Cancelar la reserva ${alta}? Los recursos aún reservados volverán a estado disponible.`)) return;
  const res = await apiRaw(`/reservas/${id}/cancelar`, { method: 'POST' });
  if (res.ok) {
    notif('Reserva cancelada, recursos liberados');
    cargarReservas();
  } else {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error al cancelar la reserva', 'error');
  }
}
