// ── Mis Pendientes ────────────────────────────────────────────────────────────
// Tablero de navegación: muestra los bloques de pendientes que el ROL del usuario
// puede gestionar (filtrado server-side) + enlaza al módulo para resolverlos.
// Obedece al selector GLOBAL de empresa (registrado en el recargadores map de core.js).

async function _fetchPendientes() {
  const p = new URLSearchParams();
  if (empresaActual) p.set('empresa_id', empresaActual);
  return await api(`/pendientes/mis-pendientes?${p}`);
}

// Actualiza solo el badge del nav (llamado al iniciar y tras cambios).
async function actualizarBadgePendientes() {
  const data = await _fetchPendientes();
  _setBadgePendientes(data ? data.total : 0);
}

function _setBadgePendientes(total) {
  const b = document.getElementById('nav-pendientes-badge');
  if (!b) return;
  if (total > 0) { b.textContent = total; b.style.display = ''; }
  else { b.style.display = 'none'; }
}

async function cargarPendientes() {
  const header = document.getElementById('pendientes-header');
  const grid   = document.getElementById('pendientes-grid');
  if (!grid) return;
  grid.innerHTML = '<div style="text-align:center;color:var(--text3);padding:30px">Cargando pendientes...</div>';
  if (header) header.innerHTML = '';

  const data = await _fetchPendientes();
  const bloques = (data && data.bloques) || [];
  const total = data ? data.total : 0;
  _setBadgePendientes(total);

  if (!bloques.length) {
    if (header) header.innerHTML = '';
    grid.innerHTML = `
      <div class="pend-empty">
        <div class="pend-empty-ic"><i class="ti ti-circle-check"></i></div>
        <div class="pend-empty-t">¡Sin pendientes!</div>
        <div class="pend-empty-s">No tienes nada por gestionar en este momento.</div>
      </div>`;
    return;
  }

  if (header) {
    header.innerHTML = `
      <div class="pend-total">
        <span class="pend-total-num">${total}</span>
        <span class="pend-total-lbl">pendiente${total === 1 ? '' : 's'} en total</span>
      </div>`;
  }

  grid.innerHTML = bloques.map(b =>
    b.tipo === 'agrupado' ? _cardAgrupado(b) : _cardDetalle(b)
  ).join('');
}

function _cardDetalle(b) {
  const items = (b.items || []).map(it => `
    <li class="pend-item${it.urgente ? ' pend-item-urgente' : ''}" onclick="irAPendiente('${b.modulo}')">
      <span class="pend-item-t">${_pEsc(it.titulo)}</span>
      ${it.detalle ? `<span class="pend-item-d">${_pEsc(it.detalle)}</span>` : ''}
    </li>`).join('');
  const restantes = b.count - (b.items || []).length;
  return `
  <div class="pend-card">
    <div class="pend-card-head">
      <span class="pend-card-title"><i class="ti ${b.icon || 'ti-alert-circle'}"></i> ${_pEsc(b.label)}</span>
      <span class="pend-count">${b.count}</span>
    </div>
    <ul class="pend-list">${items}</ul>
    ${restantes > 0 ? `<div class="pend-more">+${restantes} más</div>` : ''}
    <button class="pend-link" onclick="irAPendiente('${b.modulo}')">Ver todas <i class="ti ti-arrow-up-right"></i></button>
  </div>`;
}

function _cardAgrupado(b) {
  const d = b.desglose || {};
  const chip = (n, lbl, cls) => `<div class="pend-chip ${cls}"><span class="pend-chip-n">${n || 0}</span><span class="pend-chip-l">${lbl}</span></div>`;
  return `
  <div class="pend-card pend-card-agrupado">
    <div class="pend-card-head">
      <span class="pend-card-title"><i class="ti ${b.icon || 'ti-tool'}"></i> ${_pEsc(b.label)}</span>
      <span class="pend-count">${b.count}</span>
    </div>
    <div class="pend-chips">
      ${chip(d.vencidos, 'Vencidos', 'urg')}
      ${chip(d.semana, 'Esta semana', 'warn')}
      ${chip(d.proximos, 'Próximos', 'ok')}
    </div>
    <button class="pend-link" onclick="irAPendiente('${b.modulo}')">Ir al módulo <i class="ti ti-arrow-up-right"></i></button>
  </div>`;
}

function irAPendiente(modulo) {
  // Navega al módulo relevante (el filtro de aterrizaje es best-effort por módulo).
  if (typeof showView === 'function') showView(modulo, null);
}

function _pEsc(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
