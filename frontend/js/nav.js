// ── Navegación lateral: grupos colapsables + filtrado por permisos ───────────

function toggleNavGroup(groupId) {
  const group = document.querySelector(`.nav-group[data-group="${groupId}"]`);
  if (!group) return;
  group.classList.toggle('collapsed');
  guardarEstadoNav();
}

function toggleNavSubgroup(subId) {
  const sub = document.querySelector(`.nav-subgroup[data-subgroup="${subId}"]`);
  if (!sub) return;
  sub.classList.toggle('collapsed');
  guardarEstadoNav();
}

// Recuerda abierto/cerrado en localStorage (app real servida desde el servidor)
function guardarEstadoNav() {
  const estado = {};
  document.querySelectorAll('.nav-group[data-group]').forEach(g => {
    estado[g.dataset.group] = g.classList.contains('collapsed');
  });
  document.querySelectorAll('.nav-subgroup[data-subgroup]').forEach(s => {
    estado['sub:' + s.dataset.subgroup] = s.classList.contains('collapsed');
  });
  try { localStorage.setItem('nav_estado', JSON.stringify(estado)); } catch (e) {}
}

function restaurarEstadoNav() {
  let estado = {};
  try { estado = JSON.parse(localStorage.getItem('nav_estado') || '{}'); } catch (e) {}
  Object.keys(estado).forEach(key => {
    if (key.startsWith('sub:')) {
      const el = document.querySelector(`.nav-subgroup[data-subgroup="${key.slice(4)}"]`);
      if (el && estado[key]) el.classList.add('collapsed');
    } else {
      const el = document.querySelector(`.nav-group[data-group="${key}"]`);
      if (el && estado[key]) el.classList.add('collapsed');
    }
  });
}

// Visibilidad de un ítem de nav según su permiso:
//  - data-permiso        → hasPermiso (uno)
//  - data-permiso-any    → hasAnyPermiso (cualquiera de la lista, separada por comas)
//  - sin permiso         → siempre visible (Dashboard, Historial…)
function _navItemVisible(item) {
  if (item.dataset.permisoAny) return hasAnyPermiso(item.dataset.permisoAny);
  if (item.dataset.permiso)    return hasPermiso(item.dataset.permiso);
  return true;
}

// Filtrado POR GRUPO: oculta un grupo entero si ninguno de sus ítems es visible
function filtrarGruposNav() {
  document.querySelectorAll('.nav-group[data-group]').forEach(group => {
    // ítems con permiso (single o any): se muestran/ocultan según el permiso
    const items = group.querySelectorAll('.nav-item[data-permiso], .nav-item[data-permiso-any]');
    let algunoVisible = false;
    items.forEach(item => {
      const visible = _navItemVisible(item);
      item.style.display = visible ? '' : 'none';
      if (visible) algunoVisible = true;
    });
    // ítems sin permiso (p. ej. Dashboard, Historial) siempre cuentan como visibles,
    // EXCEPTO el botón padre del subgrupo (.nav-parent), que no es un destino navegable
    const itemsSinPermiso = group.querySelectorAll(
      '.nav-item:not([data-permiso]):not([data-permiso-any]):not(.nav-parent)');
    if (itemsSinPermiso.length) algunoVisible = true;
    group.style.display = algunoVisible ? '' : 'none';
  });
  // subgrupos: oculta el padre "Inventario" si ni Activos ni Accesorios son visibles
  document.querySelectorAll('.nav-subgroup[data-subgroup]').forEach(sub => {
    const children = sub.querySelectorAll('.nav-child[data-permiso]');
    let algunoVisible = false;
    children.forEach(c => { if (!c.dataset.permiso || hasPermiso(c.dataset.permiso)) algunoVisible = true; });
    sub.style.display = algunoVisible ? '' : 'none';
  });
}

// Si la vista activa está dentro de un grupo/subgrupo colapsado, lo expande al cargar
function expandirGrupoActivo() {
  const activo = document.querySelector('.nav-item.active');
  if (!activo) return;
  const grupo = activo.closest('.nav-group');
  if (grupo) grupo.classList.remove('collapsed');
  const sub = activo.closest('.nav-subgroup');
  if (sub) sub.classList.remove('collapsed');
}

// Oculta botones de acción gated por permiso (data-permiso-btn)
function filtrarBotonesPorPermiso() {
  document.querySelectorAll('[data-permiso-btn]').forEach(btn => {
    btn.style.display = hasPermiso(btn.dataset.permisoBtn) ? '' : 'none';
  });
}

// Punto único de inicialización tras cargar RBAC
function inicializarNav() {
  filtrarGruposNav();
  filtrarBotonesPorPermiso();
  restaurarEstadoNav();
  expandirGrupoActivo();
}
