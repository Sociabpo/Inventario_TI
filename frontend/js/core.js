const API = 'http://localhost:8000/api';
let TOKEN = '';
let empresaActual = '';
let activosCache = [], accCache = [], usuariosCache = [], empresasCache = [];
let usuarioAsigId = '', activoAsigId = '';
let vistaActual = 'dashboard';

// ── Estados de recursos (activos/accesorios) ──────────────
const ESTADOS_RECURSO = {
  disponible:               'Disponible',
  asignado:                 'Asignado',
  mantenimiento_preventivo: 'Mantenimiento Preventivo',
  mantenimiento_correctivo: 'Mantenimiento Correctivo',
  en_reparacion:            'En Reparación',
  en_garantia:              'En Garantía',
  retirado:                 'Retirado',
  reservado:                'Reservado',
};
const ESTADOS_DISPONIBLES = ['disponible'];
function labelEstado(e) { return ESTADOS_RECURSO[e] || (e || '').replace(/_/g, ' '); }
// Muestra/oculta el campo Ubicación según el estado (oculto solo cuando es "asignado")
function toggleUbicacion(selEstadoId, wrapId) {
  const el = document.getElementById(selEstadoId), w = document.getElementById(wrapId);
  if (!el || !w) return;
  w.style.display = el.value === 'asignado' ? 'none' : '';
}

window.RBAC = { roles: [], roles_todas: [], permisos: new Set(), is_super_admin: false };
function hasPermiso(codigo) {
  return window.RBAC.is_super_admin || window.RBAC.permisos.has(codigo);
}
// True si el usuario tiene AL MENOS UNO de los permisos (lista o string separado por comas)
function hasAnyPermiso(codigos) {
  const arr = Array.isArray(codigos) ? codigos : String(codigos).split(',');
  return arr.some(c => hasPermiso(c.trim()));
}

// Nombres amigables de roles (slug → etiqueta). Si no hay match, se formatea el slug.
const ROLE_LABELS = {
  super_admin:      'Super Administrador',
  superadmin:       'Super Administrador',
  admin:            'Administrador',
  analista_activos: 'Analista de Activos',
  soporte_ti:       'Soporte TI',
  auditoria:        'Auditoría',
  rrhh:             'Recursos Humanos',
  visualizador:     'Visualizador',
};
// Prioridad para elegir el rol "principal" cuando hay varios.
const ROLE_PRIORIDAD = ['super_admin', 'admin', 'analista_activos', 'soporte_ti', 'auditoria', 'rrhh', 'visualizador'];
function _rolLabel(slug) {
  return ROLE_LABELS[slug] || String(slug || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}
// Etiqueta de rol para el footer, a partir del RBAC real (no del campo legado).
function rolDisplayLabel() {
  if (window.RBAC.is_super_admin) return 'Super Administrador';
  const roles = [...new Set(window.RBAC.roles_todas || [])];
  if (!roles.length) return '—';
  const principal = ROLE_PRIORIDAD.find(r => roles.includes(r)) || roles.slice().sort()[0];
  const extra = roles.length - 1;
  return extra > 0 ? `${_rolLabel(principal)} +${extra}` : _rolLabel(principal);
}
function actualizarFooterRol() {
  const el = document.getElementById('user-role');
  if (el) el.textContent = rolDisplayLabel();
}

async function cargarRBAC() {
  const data = await api('/rbac/me/permisos');
  if (!data) return; // fail closed
  window.RBAC.roles         = data.roles || [];
  window.RBAC.roles_todas   = data.roles_todas || [];
  window.RBAC.permisos      = new Set(data.permisos || []);
  window.RBAC.is_super_admin = !!data.is_super_admin;
  actualizarFooterRol();   // mostrar el rol REAL en el footer
  // Filtrado por permisos + grupos colapsables (nav.js). Se ejecuta aquí, una vez
  // que RBAC está disponible, para evitar el parpadeo de ítems antes de ocultarlos.
  if (typeof inicializarNav === 'function') {
    inicializarNav();
  } else {
    document.querySelectorAll('.nav-item[data-permiso]').forEach(item => {
      item.style.display = hasPermiso(item.dataset.permiso) ? '' : 'none';
    });
  }
}

// ── Catálogos (listas desplegables gestionables) ─────────
let catalogosCache = {};

async function cargarCatalogos() {
  const empresa = empresaActual || '';
  const cats = ['tipo_activo', 'tipo_accesorio', 'tipo_mantenimiento', 'tipo_proveedor'];
  const perEmpresa = ['area', 'cargo', 'sede', 'ubicacion'];
  const promesas = cats.map(c =>
    api(`/catalogos?categoria=${c}`).then(d => ({ cat: c, data: d || [] }))
  );
  if (empresa) {
    perEmpresa.forEach(c =>
      promesas.push(api(`/catalogos?categoria=${c}&empresa_id=${empresa}`)
        .then(d => ({ cat: c, data: d || [] })))
    );
  }
  const resultados = await Promise.all(promesas);
  catalogosCache = {};
  resultados.forEach(r => { catalogosCache[r.cat] = r.data; });
}

function getCatalogo(categoria) {
  return catalogosCache[categoria] || [];
}

// Llena un <select> de UBICACIÓN con el catálogo de UNA empresa específica
// (puede diferir de empresaActual — p. ej. el selector de empresa del modal de activo).
// Muestra el hint de vacío si la empresa no tiene ubicaciones en su catálogo.
async function llenarSelectUbicacion(selectId, empresaId, valorActual, hintId) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const hint = hintId ? document.getElementById(hintId) : null;
  if (!empresaId) {
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    if (hint) hint.style.display = 'none';
    return;
  }
  const data = await api(`/catalogos?categoria=ubicacion&empresa_id=${empresaId}`) || [];
  let opts = '<option value="">Seleccionar...</option>' +
    data.map(i => `<option value="${i.valor}"${i.valor === valorActual ? ' selected' : ''}>${i.valor}</option>`).join('');
  if (valorActual && !data.some(i => i.valor === valorActual)) {
    opts += `<option value="${valorActual}" selected>${valorActual} (inactivo)</option>`;
  }
  sel.innerHTML = opts;
  if (hint) hint.style.display = data.length ? 'none' : '';
}

// Llena un <select> con un catálogo per-empresa arbitrario (sede, area, ubicacion…)
// de UNA empresa específica (puede diferir de empresaActual — p. ej. el selector de
// empresa de un modal). Muestra el hint de vacío si la empresa no tiene entradas.
async function llenarSelectCatalogoEmpresa(selectId, categoria, empresaId, valorActual, hintId) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const hint = hintId ? document.getElementById(hintId) : null;
  if (!empresaId) {
    sel.innerHTML = '<option value="">Seleccionar...</option>';
    if (hint) hint.style.display = 'none';
    return;
  }
  const data = await api(`/catalogos?categoria=${encodeURIComponent(categoria)}&empresa_id=${empresaId}`) || [];
  let opts = '<option value="">Seleccionar...</option>' +
    data.map(i => `<option value="${i.valor}"${i.valor === valorActual ? ' selected' : ''}>${i.valor}</option>`).join('');
  if (valorActual && !data.some(i => i.valor === valorActual)) {
    opts += `<option value="${valorActual}" selected>${valorActual} (inactivo)</option>`;
  }
  sel.innerHTML = opts;
  if (hint) hint.style.display = data.length ? 'none' : '';
}

function llenarSelectCatalogo(selectId, categoria, valorActual) {
  const sel = document.getElementById(selectId);
  if (!sel) return;
  const items = getCatalogo(categoria);
  let opts = '<option value="">Seleccionar...</option>' +
    items.map(i => `<option value="${i.valor}"${i.valor === valorActual ? ' selected' : ''}>${i.valor}</option>`).join('');
  // Conservar el valor actual aunque ya no esté activo en el catálogo (evita perderlo al editar)
  if (valorActual && !items.some(i => i.valor === valorActual)) {
    opts += `<option value="${valorActual}" selected>${valorActual} (inactivo)</option>`;
  }
  sel.innerHTML = opts;
}

// ── INIT ──────────────────────────────────────────────
window.addEventListener('DOMContentLoaded', async () => {
  TOKEN = sessionStorage.getItem('token');
  if (!TOKEN) { window.location.href = 'index.html'; return; }
  const u = JSON.parse(sessionStorage.getItem('usuario') || '{}');
  document.getElementById('user-name').textContent = u.nombre || 'Usuario';
  // El rol se establece desde RBAC (rol real), NO desde el campo legado u.rol.
  document.getElementById('user-role').textContent  = '…';
  await cargarRBAC();
  await cargarEmpresas();
  await cargarCatalogos();
  await cargarDashboard();
  if (typeof actualizarBadgePendientes === 'function') actualizarBadgePendientes();
});

// ── API ───────────────────────────────────────────────
async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json', ...(opts.headers||{}) }
  });
  if (res.status === 401) { window.location.href = 'index.html'; return null; }
  return res.ok ? res.json() : null;
}
async function apiRaw(path, opts = {}) {
  return fetch(`${API}${path}`, {
    ...opts,
    headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json', ...(opts.headers||{}) }
  });
}

// ── NOTIFICACIONES ────────────────────────────────────
function notif(msg, type='success') {
  const c = document.getElementById('notif-container');
  const el = document.createElement('div');
  el.className = `notif-item ${type}`;
  el.textContent = (type==='success'?'✓ ':'❌ ') + msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── NAVEGACIÓN ────────────────────────────────────────
const VIEWS = {
  dashboard:    {title:'Dashboard',    sub:'— Resumen general',         btn:'Nuevo activo'},
  pendientes:   {title:'Mis Pendientes', sub:'— Lo que tu rol puede gestionar', btn:'—'},
  activos:      {title:'Activos',      sub:'— Inventario tecnológico',  btn:'Nuevo activo'},
  accesorios:   {title:'Accesorios',   sub:'— Periféricos',             btn:'Nuevo accesorio'},
  'hoja-vida-view': {title:'Hoja de vida', sub:'— Expediente del activo', btn:'—'},
  asignaciones: {title:'Asignaciones', sub:'— Control de asignaciones', btn:'Nueva asignación'},
  reservas:     {title:'Reservas',     sub:'— Recursos apartados para ingresos', btn:'—'},
  usuarios:     {title:'Empleados',    sub:'— Directorio de personal',  btn:'Nuevo empleado'},
  empresas:     {title:'Empresas',     sub:'— Gestión multiempresa',    btn:'Nueva empresa'},
  compras:      {title:'Compras',      sub:'— Gestión de compras y facturas', btn:'Nueva solicitud'},
  mantenimiento:   {title:'Mantenimiento',   sub:'— Mantenimiento preventivo · planes', btn:'—'},
  bajas:           {title:'Bajas',            sub:'— Solicitudes de retiro',   btn:'—'},
  actas:           {title:'Actas PDF',       sub:'— Documentos generados',    btn:'—'},
  historial:       {title:'Historial',       sub:'— Trazabilidad completa',   btn:'—'},
  redes:           {title:'Redes',            sub:'— Cuartos técnicos · racks',btn:'—'},
  impresoras:      {title:'Impresoras',       sub:'— Impresoras alquiladas',  btn:'—'},
  administracion:  {title:'Administración',  sub:'— Control de accesos',      btn:'—'},
};

function showView(name, el) {
  document.querySelectorAll('[id^="view-"]').forEach(v => v.style.display = 'none');
  const v = document.getElementById('view-' + name);
  if (v) v.style.display = '';
  document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
  if (el) el.classList.add('active');
  const cfg = VIEWS[name] || VIEWS.dashboard;
  document.getElementById('topbar-title').textContent    = cfg.title;
  document.getElementById('topbar-sub').textContent      = cfg.sub;
  document.getElementById('btn-nuevo-label').textContent = cfg.btn;
  // El botón "+ Nuevo" del encabezado se retiró de Activos, Accesorios, Asignaciones,
  // Empleados y Empresas: cada módulo conserva su propio botón en la barra de búsqueda.
  // (Servidores vuelve a mostrarlo en su propia extensión de showView.)
  document.getElementById('btn-nuevo').style.display = 'none';
  vistaActual = name;
  if (name==='activos')         cargarActivos();
  if (name==='accesorios')      cargarAccesorios();
  if (name==='asignaciones')    { cargarAsignaciones(); llenarSelectEmpresas('asig-empresa'); if (empresaActual) document.getElementById('asig-empresa').value = empresaActual; setResponsableAsig(); }
  if (name==='reservas')        cargarReservas();
  if (name==='usuarios')        cargarUsuarios();
  if (name==='empresas')        cargarEmpresasTabla();
  if (name==='bajas')           cargarBajas();
  if (name==='actas')           cargarActas();
  if (name==='compras')         cargarCompras();
  if (name==='mantenimiento')   initMantView();
  if (name==='administracion')  cargarAdminView();
  if (name==='redes')           initRedesView();
  if (name==='impresoras')      initImpresorasView();
  if (name==='pendientes')      cargarPendientes();
  if (name==='hoja-vida-view') {
    const inp = document.getElementById('hv-search-input');
    if (inp && !inp.value) document.getElementById('hv-search-results').innerHTML = '';
  }
}

function accionNuevo() {
  const acciones = {
    activos: abrirModalActivo, accesorios: abrirModalAccesorio,
    usuarios: abrirModalUsuario, empresas: abrirModalEmpresa,
  };
  if (acciones[vistaActual]) acciones[vistaActual]();
}

// ── EMPRESA SELECTOR ─────────────────────────────────
// Paleta de colores para empresas
const EMPRESA_COLORS = [
  '#06BFFF','#00E5A0','#FFB020','#A78BFF','#FF6B6B',
  '#00D4B4','#FF9F43','#54A0FF','#5F27CD','#EE5A24',
  '#C44569','#40739E','#8C7AE6','#0ABDE3','#10AC84'
];
const empresaColorMap = {};

function getEmpresaColor(empresaId) {
  if (!empresaColorMap[empresaId]) {
    const idx = Object.keys(empresaColorMap).length % EMPRESA_COLORS.length;
    empresaColorMap[empresaId] = EMPRESA_COLORS[idx];
  }
  return empresaColorMap[empresaId];
}

async function cargarEmpresas() {
  const data = await api('/rbac/empresas-disponibles');
  if (!data) return;
  empresasCache = data;
  data.forEach((e, i) => { empresaColorMap[e.id] = EMPRESA_COLORS[i % EMPRESA_COLORS.length]; });

  const list = document.getElementById('emp-options-list');
  const selector = document.getElementById('empresa-selector');

  if (data.length === 0) {
    list.innerHTML = '<div class="emp-divider"></div><div style="padding:12px 16px;color:var(--text3);font-size:12px;">Sin empresas asignadas</div>';
    return;
  }

  list.innerHTML = '<div class="emp-divider"></div>' + data.map(e => `
    <div class="emp-option" id="emp-opt-${e.id}"
      onclick="seleccionarEmpresa('${e.id}','${e.nombre_empresa}','${e.prefijo}')">
      <div class="emp-opt-dot" style="background:${getEmpresaColor(e.id)}"></div>
      <div class="emp-opt-info">
        <div class="emp-opt-name">${e.nombre_empresa}</div>
        <div class="emp-opt-nit">${e.nit || ''}</div>
      </div>
      <span class="emp-opt-prefijo">${e.prefijo}</span>
    </div>`).join('');

  if (data.length === 1) {
    // Single company: auto-select and hide the switcher — user has no choice to make
    if (selector) selector.style.display = 'none';
    seleccionarEmpresa(data[0].id, data[0].nombre_empresa, data[0].prefijo);
    return;
  }

  // Multiple companies: show selector normally
  if (selector) selector.style.display = '';

  // If empresaActual is set to a company no longer accessible, reset to first allowed
  const allowedIds = data.map(e => e.id);
  if (empresaActual && !allowedIds.includes(empresaActual)) {
    seleccionarEmpresa(data[0].id, data[0].nombre_empresa, data[0].prefijo);
  }
}

function llenarSelectEmpresas(id) {
  const sel = document.getElementById(id);
  if (!sel) return;
  const val = sel.value;
  sel.innerHTML = '<option value="">Seleccionar...</option>';
  empresasCache.forEach(e => {
    const o = document.createElement('option');
    o.value = e.id; o.textContent = `${e.nombre_empresa} (${e.prefijo})`;
    sel.appendChild(o);
  });
  if (val) sel.value = val;
}

// ── Filtros avanzados (helpers compartidos) ───────────────
function toggleFiltros(mod) {
  const panel = document.getElementById('filtros-' + mod);
  const btn   = document.getElementById('btn-filtros-' + mod);
  if (!panel) return;
  const open = panel.classList.toggle('open');
  if (btn) btn.classList.toggle('active', open);
}

// Llena un <select> con los valores distintos de un campo en una lista (conserva la selección actual).
function llenarSelectDistinct(selId, lista, campo, labelTodos = 'Todos') {
  const sel = document.getElementById(selId);
  if (!sel) return;
  const actual = sel.value;
  const valores = [...new Set(lista.map(x => x[campo]).filter(v => v != null && v !== ''))]
    .sort((a, b) => String(a).localeCompare(String(b), 'es'));
  sel.innerHTML = `<option value="">${labelTodos}</option>` +
    valores.map(v => `<option value="${String(v).replace(/"/g, '&quot;')}">${v}</option>`).join('');
  if (valores.map(String).includes(actual)) sel.value = actual;
}

function actualizarCount(id, shown, total) {
  const el = document.getElementById(id);
  if (el) el.textContent = `Mostrando ${shown} de ${total}`;
}

// Exporta un dataset (ya filtrado) a Excel o PDF vía el backend.
// formato: 'excel' | 'pdf' ; columnas: [{key,label}] ; filas: [obj]
async function exportarDatos(formato, titulo, columnas, filas, btn) {
  if (!filas || !filas.length) { notif('No hay datos para exportar', 'error'); return; }
  const original = btn ? btn.textContent : null;
  if (btn) { btn.disabled = true; btn.textContent = 'Generando...'; }
  try {
    const res = await fetch(`${API}/export/${formato}`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ titulo, columnas, filas }),
    });
    if (!res.ok) { notif('Error al exportar', 'error'); return; }
    const blob = await res.blob();
    const ext  = formato === 'excel' ? 'xlsx' : 'pdf';
    const url  = URL.createObjectURL(blob);
    const fecha = new Date().toISOString().slice(0, 10);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${titulo.replace(/[^\w\-]+/g, '_')}_${fecha}.${ext}`;
    a.click();
    URL.revokeObjectURL(url);
    notif(`Exportado a ${ext.toUpperCase()}`);
  } catch (e) {
    notif('Error de red al exportar', 'error');
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = original; }
  }
}

function seleccionarEmpresa(id, nombre, prefijo) {
  empresaActual = id;
  const color = id ? getEmpresaColor(id) : null;

  // Actualizar selector
  const sel = document.getElementById('empresa-selector');
  const dot = document.getElementById('emp-dot');
  const nameDisplay = document.getElementById('emp-name-display');
  dot.style.background = color || 'var(--text3)';
  dot.style.color = color || 'var(--text3)';
  dot.classList.toggle('active', !!id);
  nameDisplay.textContent = nombre;
  nameDisplay.style.color = color || 'var(--text)';

  // Marcar opción activa
  document.querySelectorAll('.emp-option').forEach(o => o.classList.remove('selected'));
  if (id) {
    const opt = document.getElementById(`emp-opt-${id}`);
    if (opt) opt.classList.add('selected');
  }

  // Banner
  const banner = document.getElementById('empresa-banner');
  if (id) {
    banner.classList.add('visible');
    banner.style.background = `linear-gradient(135deg, ${color}08, transparent)`;
    banner.style.borderBottomColor = `${color}30`;
    document.getElementById('banner-dot').style.background = color;
    document.getElementById('banner-dot').style.boxShadow = `0 0 10px ${color}`;
    document.getElementById('banner-name').textContent = nombre;
    document.getElementById('banner-name').style.color = color;
    document.getElementById('banner-prefijo').textContent = prefijo;
    // Actualizar stats del banner
    cargarStatsBanner(id, color);
  } else {
    banner.classList.remove('visible');
  }

  // Sidebar badge
  const seb = document.getElementById('seb');
  if (id) {
    seb.classList.add('visible');
    seb.style.background = `${color}10`;
    seb.style.borderColor = `${color}30`;
    document.getElementById('seb-name').textContent = nombre;
    document.getElementById('seb-name').style.color = color;
  } else {
    seb.classList.remove('visible');
  }

  // Topbar color accent
  document.querySelector('.topbar').style.borderBottomColor = id ? `${color}40` : '';

  cerrarEmpresaDropdown();
  cargarCatalogos();
  recargarVistaActual();
}

async function cargarStatsBanner(empresaId, color) {
  const [activos, usuarios, asig] = await Promise.all([
    api(`/activos?empresa_id=${empresaId}`),
    api(`/usuarios?empresa_id=${empresaId}`),
    api(`/asignaciones/activas?empresa_id=${empresaId}`)
  ]);
  const banActivos = document.getElementById('ban-activos');
  const banEmp     = document.getElementById('ban-empleados');
  const banAsig    = document.getElementById('ban-asig');
  if (banActivos) { banActivos.textContent = activos?.length||0; banActivos.style.color = color; }
  if (banEmp)     { banEmp.textContent     = usuarios?.length||0; banEmp.style.color = color; }
  if (banAsig)    { banAsig.textContent    = asig?.length||0; banAsig.style.color = color; }
}

function toggleEmpresaDropdown() {
  const sel      = document.getElementById('empresa-selector');
  const dropdown = document.getElementById('emp-dropdown');
  const ov       = document.getElementById('dropdown-overlay');
  const isOpen   = dropdown.classList.contains('open');

  if (isOpen) {
    cerrarEmpresaDropdown();
  } else {
    // Posicionar el dropdown justo debajo del selector
    const rect = sel.getBoundingClientRect();
    dropdown.style.top   = (rect.bottom + 8) + 'px';
    dropdown.style.left  = rect.left + 'px';
    dropdown.style.width = rect.width + 'px';
    dropdown.classList.add('open');
    sel.classList.add('open');
    ov.classList.add('open');
  }
}
function cerrarEmpresaDropdown() {
  document.getElementById('empresa-selector').classList.remove('open');
  document.getElementById('emp-dropdown').classList.remove('open');
  document.getElementById('dropdown-overlay').classList.remove('open');
}

function recargarVistaActual() {
  const recargadores = {
    dashboard:      cargarDashboard,
    pendientes:     cargarPendientes,
    activos:        cargarActivos,
    accesorios:     cargarAccesorios,
    asignaciones:   cargarAsignaciones,
    reservas:       cargarReservas,
    usuarios:       cargarUsuarios,
    empresas:       cargarEmpresasTabla,
    actas:          cargarActas,
    compras:        cargarCompras,
    administracion: recargarAdminView,
    redes:          volverACuartos,
    impresoras:     cargarImpresoras,
    servidores:     cargarServidores,
    mantenimiento:  initMantView,
  };
  if (recargadores[vistaActual]) recargadores[vistaActual]();
}