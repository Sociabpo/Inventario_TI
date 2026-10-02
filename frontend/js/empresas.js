async function cargarEmpresasTabla() {
  const data = await api('/empresas?solo_activas=false');
  empresasCache = data || [];
  const tbody = document.getElementById('tbl-empresas-body');
  if (!data?.length) { tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text3);padding:20px">Sin empresas</td></tr>'; return; }
  tbody.innerHTML = data.map(e => `
    <tr class="clickable" onclick="editarEmpresa('${e.id}')">
      <td><span class="mono-tag">${e.nit}</span></td>
      <td><div class="td-name">${e.nombre_empresa}</div>${(e.relacionadas && e.relacionadas.length) ? `<div class="td-sub" style="font-size:10px;color:#54A0FF">↔ ${e.relacionadas.map(r=>r.nombre_empresa).join(', ')}</div>` : ''}</td>
      <td><span class="mono-tag">${e.prefijo}</span></td>
      <td>${e.ciudad||'—'}</td>
      <td style="font-size:11px">${e.correo||'—'}</td>
      <td><span class="badge ${e.activo?'disponible':'baja'}">${e.activo?'Activa':'Inactiva'}</span></td>
    </tr>`).join('');
}

function buscarEmpresas() {
  const q = document.getElementById('search-empresas').value.toLowerCase();
  const rows = document.querySelectorAll('#tbl-empresas-body tr');
  rows.forEach(r => r.style.display = r.textContent.toLowerCase().includes(q) ? '' : 'none');
}

// ── DASHBOARD ─────────────────────────────────────────
async function cargarDashboard() {
  cargarDashboardResumen();   // alertas + paneles nuevos (no rompe lo existente)
  const p = empresaActual ? `?empresa_id=${empresaActual}` : '';
  const [activos, asig, usuarios] = await Promise.all([
    api(`/activos${p}`), api(`/asignaciones/activas${p}`),
    api(`/usuarios${p?p+'&estado=activo':'?estado=activo'}`)
  ]);
  if (activos) {
    const _mant=['mantenimiento_preventivo','mantenimiento_correctivo','en_reparacion','en_garantia'];
    const t=activos.length, a=activos.filter(x=>x.estado==='asignado').length,
          m=activos.filter(x=>_mant.includes(x.estado)).length,
          d=activos.filter(x=>x.estado==='disponible').length,
          b=activos.filter(x=>x.estado==='retirado').length;
    document.getElementById('kpi-total').textContent     = t;
    document.getElementById('kpi-asignados').textContent = a;
    document.getElementById('kpi-mant').textContent      = m;
    document.getElementById('kpi-pct').textContent       = t>0?`${Math.round(a/t*100)}% del inventario`:'del inventario';
    document.getElementById('badge-activos').textContent = t;
    document.getElementById('d-total').textContent       = t;
    document.getElementById('leg-a').textContent = a;
    document.getElementById('leg-d').textContent = d;
    document.getElementById('leg-m').textContent = m;
    document.getElementById('leg-b').textContent = b;
    // 5º KPI "Disponibles" — mismo dato que la leyenda del donut (sin regresión)
    const kd = document.getElementById('kpi-disponibles');
    if (kd) kd.textContent = d;
  }
  if (usuarios) document.getElementById('kpi-empleados').textContent = usuarios.length;
  if (asig) {
    const tbody = document.getElementById('tbl-dash-asig');
    tbody.innerHTML = asig.length ? asig.slice(0,6).map(a=>`
      <tr><td><span class="mono-tag">${a.placa_activo||'—'}</span></td>
      <td><div class="td-name">${a.nombre_usuario||'—'}</div><div class="td-sub">${a.documento_usuario||''}</div></td>
      <td><div class="td-sub">${a.nombre_empresa||'—'}</div></td>
      <td><span class="badge asignado">Activa</span></td>
      <td style="font-size:11px;color:var(--text3)">${fFecha(a.fecha_asignacion)}</td></tr>`).join('')
      : '<tr><td colspan="5" style="text-align:center;color:var(--text3);padding:16px">Sin asignaciones</td></tr>';
    document.getElementById('act-body').innerHTML = asig.length ? asig.slice(0,4).map(a=>`
      <div class="act-item"><div class="act-dot c"></div>
      <div><div class="act-text">Activo <strong>${a.placa_activo}</strong> asignado a <strong>${a.nombre_usuario}</strong> — ${a.nombre_empresa}</div>
      <div class="act-time">${fFecha(a.fecha_asignacion)}</div></div></div>`).join('')
      : '<div style="padding:16px;text-align:center;color:var(--text3)">Sin actividad reciente</div>';
  }
}

// ── Dashboard: alertas + paneles accionables (endpoint consolidado) ──
async function cargarDashboardResumen() {
  const p = empresaActual ? `?empresa_id=${empresaActual}` : '';
  const d = await api(`/dashboard/resumen${p}`);
  if (!d) return;
  renderDashAlertas(d.alertas || {});
  renderDashReservados(d.reservados || [], d.reservados_total || 0);
  renderDashFueraServicio(d.fuera_servicio || [], d.fuera_servicio_total || 0, d.fuera_servicio_desglose || {});
  renderDashPrestamos(d.prestamos || [], d.prestamos_total || 0);
}

function renderDashAlertas(al) {
  const cont = document.getElementById('dash-alertas');
  if (!cont) return;
  const chips = [];
  if (al.prestamos_vencidos > 0)
    chips.push(`<span class="dash-alerta-chip red" onclick="irAPrestamos('vencido')">⏰ ${al.prestamos_vencidos} préstamos vencidos</span>`);
  if (al.prestamos_por_vencer > 0)
    chips.push(`<span class="dash-alerta-chip amber" onclick="irAPrestamos('prestamo')">⏳ ${al.prestamos_por_vencer} préstamos por vencer</span>`);
  if (al.reservas_activas > 0)
    chips.push(`<span class="dash-alerta-chip blue" onclick="dashIrSiPermiso('reservas.gestionar','reservas')">📌 ${al.reservas_activas} reservas activas</span>`);
  if (al.actas_sin_firmar > 0)
    chips.push(`<span class="dash-alerta-chip amber" onclick="dashIrSiPermiso('actas.ver','actas')">📄 ${al.actas_sin_firmar} actas sin firmar</span>`);
  if (!chips.length)
    chips.push(`<span class="dash-alerta-chip green">✓ Sin alertas pendientes</span>`);
  cont.innerHTML = chips.join('');
  cont.style.display = 'flex';
}

function renderDashReservados(list, total) {
  const body = document.getElementById('dash-reservados-body');
  const verTodos = document.getElementById('dash-reservados-vertodos');
  if (verTodos) verTodos.style.display = total > list.length ? '' : 'none';
  if (!list.length) { body.innerHTML = '<div class="dash-list-empty">No hay activos reservados</div>'; return; }
  body.innerHTML = list.map(r => {
    const dias = r.dias_para_vencer;
    const pill = dias == null ? ''
      : dias < 0 ? `<span class="prestamo-pill vencido">Vencida hace ${Math.abs(dias)}d</span>`
      : dias <= 3 ? `<span class="prestamo-pill proximo">Vence en ${dias}d</span>`
      : `<span class="prestamo-pill normal">${dias}d</span>`;
    return `<div class="dash-list-row clickable" onclick="dashVerRecurso('${r.tipo_recurso}','${r.recurso_id}')">
      <span class="mono-tag">${r.placa || '—'}</span>
      <div class="dash-row-main">
        <div class="td-name">${r.tipo || '—'} ${r.marca || ''}</div>
        <div class="td-sub">📌 Reservado: ${r.numero_alta || '—'}</div>
      </div>${pill}</div>`;
  }).join('');
}

function renderDashFueraServicio(list, total, desg) {
  const body = document.getElementById('dash-fuera-body');
  const head = document.getElementById('dash-fuera-desglose');
  const verTodos = document.getElementById('dash-fuera-vertodos');
  if (verTodos) verTodos.style.display = total > list.length ? '' : 'none';
  if (head) head.textContent = `Mantenimiento: ${desg.mantenimiento || 0} · Reparación: ${desg.en_reparacion || 0} · Garantía: ${desg.en_garantia || 0}`;
  if (!list.length) { body.innerHTML = '<div class="dash-list-empty">Todos los equipos operativos</div>'; return; }
  body.innerHTML = list.map(r => `
    <div class="dash-list-row clickable" onclick="dashVerRecurso('${r.tipo_recurso}','${r.recurso_id}')">
      <span class="mono-tag">${r.placa || '—'}</span>
      <div class="dash-row-main">
        <div class="td-name">${r.tipo || '—'}</div>
        <div class="td-sub">${r.descripcion || r.ubicacion || ''}</div>
      </div>
      <span class="badge ${badgeEstado(r.estado)}">${labelEstado(r.estado)}</span>
    </div>`).join('');
}

function renderDashPrestamos(list, total) {
  const body = document.getElementById('dash-prestamos-body');
  const verTodos = document.getElementById('dash-prestamos-vertodos');
  if (verTodos) verTodos.style.display = total > list.length ? '' : 'none';
  if (!list.length) { body.innerHTML = '<div class="dash-list-empty">No hay préstamos con fecha límite</div>'; return; }
  body.innerHTML = list.map(r => {
    const dias = r.dias_para_vencer;
    const pill = dias < 0 ? `<span class="prestamo-pill vencido">Vencido hace ${Math.abs(dias)}d</span>`
      : dias <= 3 ? `<span class="prestamo-pill proximo">Vence en ${dias}d</span>`
      : `<span class="prestamo-pill normal">${dias}d restantes</span>`;
    const fecha = r.fecha_limite_devolucion ? (typeof fFechaCorta === 'function' ? fFechaCorta(r.fecha_limite_devolucion) : r.fecha_limite_devolucion) : '—';
    return `<div class="dash-list-row">
      <span class="mono-tag">${r.placa || '—'}</span>
      <div class="dash-row-main">
        <div class="td-name">${r.empleado_nombre || '—'}</div>
        <div class="td-sub">${r.tipo || ''} · Límite: ${fecha}</div>
      </div>
      ${pill}
      <button class="btn btn-ghost btn-sm" onclick="dashVerRecurso('${r.tipo_recurso}','${r.recurso_id}')">Ver</button>
    </div>`;
  }).join('');
}

// ── Navegación accionable desde el dashboard ──
function dashIrSiPermiso(permiso, vista) {
  if (typeof hasPermiso === 'function' && !hasPermiso(permiso)) return;  // graceful: no navega
  showView(vista, null);
}
function dashVerRecurso(tipo, id) {
  const vista = tipo === 'accesorio' ? 'accesorios' : 'activos';
  const permiso = tipo === 'accesorio' ? 'accesorios.ver' : 'activos.ver';
  if (typeof hasPermiso === 'function' && !hasPermiso(permiso)) return;
  showView(vista, null);
}
function dashVerReservados() {
  if (typeof hasPermiso === 'function' && !hasPermiso('activos.ver')) return;
  showView('activos', null);
  if (typeof filtrarActivos === 'function') filtrarActivos('reservado', null);
}
function dashVerFueraServicio() {
  if (typeof hasPermiso === 'function' && !hasPermiso('activos.ver')) return;
  showView('activos', null);
  if (typeof filtrarActivos === 'function') filtrarActivos('mantenimiento_preventivo', null);
}

// ── ACTIVOS ───────────────────────────────────────────