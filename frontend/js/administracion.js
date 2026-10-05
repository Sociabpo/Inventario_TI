let admUsersCache     = [];
let admRolesCache     = [];
let admEmpresasDisp   = [];
let admAccesoUserId   = null;
let admAccesoUserName = null;

async function cargarAdminView() {
  if (hasPermiso('usuarios.crear')) {
    document.getElementById('btn-nuevo-usr-adm').style.display = '';
  }
  // Mostrar la pestaña de Importación solo si el usuario tiene el permiso
  const impTab = document.getElementById('adm-tab-importacion');
  if (impTab) impTab.style.display = hasPermiso('importacion.ejecutar') ? '' : 'none';
  await Promise.all([cargarUsuariosSistema(), cargarRolesRef()]);
}

// Recargador para el cambio de empresa GLOBAL (recargadores map de core.js).
// A diferencia de cargarAdminView (loader de entrada, que carga Usuarios), este
// refresca SOLO la pestaña/sección activa EN SITIO, sin sacar al usuario de donde está.
function recargarAdminView() {
  const panel = document.querySelector('.adm-panel.active');
  const tab = panel ? panel.id.replace('adm-panel-', '') : null;
  if (tab === 'catalogos') {
    // Re-ejecuta la sección de catálogo activa (per-empresa recarga para la nueva
    // empresa; global/proveedores re-consulta sin daño). No cambia de sección.
    const cfg = CATEGORIAS_CONFIG.find(c => c.key === catActivaKey);
    if (cfg && cfg.special === 'proveedores') cargarProveedoresMaster();
    else cargarItemsCat(catActivaKey);
  } else if (tab === 'usuarios' || !tab) {
    cargarUsuariosSistema();
  }
  // roles / importacion: sin datos per-empresa → no-op
}

// ── Sub-tabs ──────────────────────────────────────────
function switchAdmTab(tab, el) {
  document.querySelectorAll('.adm-tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.adm-panel').forEach(p => p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById(`adm-panel-${tab}`).classList.add('active');
  if (tab === 'catalogos') cargarAdminCatalogos();
  if (tab === 'importacion') initImportacion();
}

// ── TAB 1: Usuarios del sistema ───────────────────────
async function cargarUsuariosSistema() {
  const data = await api('/rbac/usuarios');
  admUsersCache = data || [];
  renderUsuariosSistema(admUsersCache);
}

function renderUsuariosSistema(list) {
  const tbody = document.getElementById('tbl-adm-usuarios-body');
  if (!list.length) {
    tbody.innerHTML = '<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:20px">Sin usuarios del sistema</td></tr>';
    return;
  }
  tbody.innerHTML = list.map(u => {
    const tags = u.accesos?.length
      ? u.accesos.map(a => `<span class="acceso-tag ${a.rol_nombre}">${a.rol_nombre}${a.empresa_nombre ? ' · ' + a.empresa_nombre : ' · Todas'}</span>`).join(' ')
      : '<span style="color:var(--text3);font-size:11px">Sin accesos</span>';
    const editBtn = hasPermiso('usuarios.editar')
      ? `<button class="btn btn-ghost btn-sm" onclick="abrirModalEditarUsuario('${u.id}')">Editar</button>`
      : '';
    const pwdBtn = window.RBAC.is_super_admin
      ? `<button class="btn btn-ghost btn-sm" style="color:var(--amber);border-color:rgba(255,176,32,0.3)" onclick="abrirModalPassword('${u.id}','${u.nombre.replace(/'/g, "\\'")}')">🔒 Pwd</button>`
      : '';
    return `<tr>
      <td><div class="td-name">${u.nombre}</div><div class="td-sub">${u.email}</div></td>
      <td><span class="badge ${u.activo ? 'asignado' : 'baja'}">${u.activo ? 'activo' : 'inactivo'}</span></td>
      <td style="display:flex;flex-wrap:wrap;gap:4px;align-items:center">${tags}</td>
      <td>
        <div style="display:flex;gap:6px;flex-wrap:wrap">
          ${editBtn}
          <button class="btn btn-ghost btn-sm" style="color:var(--cyan);border-color:rgba(var(--accent-rgb),0.3)" onclick="abrirModalAccesos('${u.id}','${u.nombre.replace(/'/g, "\\'")}')">🔑 Accesos</button>
          ${pwdBtn}
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ── Modal nuevo usuario ───────────────────────────────
function abrirModalNuevoUsuario() {
  if (!hasPermiso('usuarios.crear')) { notif('Sin permiso para crear usuarios','error'); return; }
  document.getElementById('adm-usr-nombre').value   = '';
  document.getElementById('adm-usr-email').value    = '';
  document.getElementById('adm-usr-password').value = '';
  llenarSelectEmpresas('adm-usr-empresa');
  abrirModal('modal-adm-usuario');
}

async function guardarNuevoUsuario() {
  const nombre    = document.getElementById('adm-usr-nombre').value.trim();
  const email     = document.getElementById('adm-usr-email').value.trim();
  const password  = document.getElementById('adm-usr-password').value;
  const empresa_id = document.getElementById('adm-usr-empresa').value || null;

  if (!nombre || !email || !password) { notif('Nombre, email y contraseña son obligatorios','error'); return; }
  if (password.length < 6)            { notif('La contraseña debe tener al menos 6 caracteres','error'); return; }

  const res = await apiRaw('/rbac/usuarios', {
    method: 'POST',
    body: JSON.stringify({ nombre, email, password, empresa_id }),
  });
  if (res.ok) {
    const data = await res.json();
    notif('Usuario creado — ahora configura sus accesos');
    cerrarModal('modal-adm-usuario');
    await cargarUsuariosSistema();
    abrirModalAccesos(data.id, nombre);
  } else {
    const err = await res.json();
    notif(err.detail || 'Error al crear usuario','error');
  }
}

// ── Modal editar usuario ──────────────────────────────
function abrirModalEditarUsuario(userId) {
  if (!hasPermiso('usuarios.editar')) { notif('Sin permiso para editar usuarios','error'); return; }
  const u = admUsersCache.find(x => x.id === userId);
  if (!u) return;
  document.getElementById('adm-edit-id').value     = u.id;
  document.getElementById('adm-edit-nombre').value = u.nombre;
  document.getElementById('adm-edit-email').value  = u.email;
  document.getElementById('adm-edit-activo').value = String(u.activo);
  document.getElementById('adm-edit-pwd-wrap').style.display = window.RBAC.is_super_admin ? '' : 'none';
  abrirModal('modal-adm-editar');
}

async function guardarEditarUsuario() {
  const id     = document.getElementById('adm-edit-id').value;
  const nombre = document.getElementById('adm-edit-nombre').value.trim();
  const email  = document.getElementById('adm-edit-email').value.trim();
  const activo = document.getElementById('adm-edit-activo').value === 'true';

  if (!nombre || !email) { notif('Nombre y email son obligatorios','error'); return; }

  const res = await apiRaw(`/rbac/usuarios/${id}`, {
    method: 'PUT',
    body: JSON.stringify({ nombre, email, activo }),
  });
  if (res.ok) {
    notif('Usuario actualizado');
    cerrarModal('modal-adm-editar');
    cargarUsuariosSistema();
  } else {
    const err = await res.json();
    notif(err.detail || 'Error al actualizar','error');
  }
}

// ── Modal accesos ─────────────────────────────────────
async function abrirModalAccesos(userId, userName) {
  admAccesoUserId   = userId;
  admAccesoUserName = userName;
  document.getElementById('adm-acc-title').textContent = `Accesos — ${userName}`;
  document.getElementById('adm-acc-lista').innerHTML =
    '<div style="color:var(--text3);padding:10px;text-align:center">Cargando...</div>';

  const [rolesData, empresasData] = await Promise.all([
    api('/rbac/roles'),
    api('/rbac/empresas-disponibles'),
  ]);
  admRolesCache   = rolesData   || [];
  admEmpresasDisp = empresasData || [];

  const rolSel = document.getElementById('adm-acc-rol');
  rolSel.innerHTML = '<option value="">Seleccionar rol...</option>' +
    admRolesCache.map(r =>
      `<option value="${r.id}" data-nombre="${r.nombre}">${r.nombre}${r.descripcion ? ' — ' + r.descripcion : ''}</option>`
    ).join('');
  rolSel.onchange = _actualizarEmpresaAccesoSel;
  _actualizarEmpresaAccesoSel();

  abrirModal('modal-adm-accesos');
  await _cargarAccesosLista();
}

function _actualizarEmpresaAccesoSel() {
  const rolSel = document.getElementById('adm-acc-rol');
  const empSel = document.getElementById('adm-acc-empresa');
  const opt    = rolSel.options[rolSel.selectedIndex];
  const rolNombre = opt?.dataset?.nombre || '';

  if (rolNombre === 'super_admin') {
    empSel.disabled = true;
    empSel.innerHTML = '<option value="">Todas las empresas (acceso global)</option>';
  } else {
    empSel.disabled = false;
    empSel.innerHTML = '<option value="">Seleccionar empresa...</option>' +
      admEmpresasDisp.map(e => `<option value="${e.id}">${e.nombre_empresa}</option>`).join('');
  }
}

async function _cargarAccesosLista() {
  const data = await api(`/rbac/usuarios/${admAccesoUserId}/accesos`);
  const lista = document.getElementById('adm-acc-lista');
  if (!data || !data.length) {
    lista.innerHTML = '<div style="color:var(--text3);padding:10px;text-align:center">Sin accesos asignados</div>';
    return;
  }
  lista.innerHTML = data.map(a => `
    <div class="acceso-row">
      <div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap">
        <span class="acceso-tag ${a.rol_nombre}">${a.rol_nombre}</span>
        <span style="font-size:11px;color:var(--text2)">${a.empresa_nombre || 'Todas las empresas'}</span>
      </div>
      <button class="btn btn-danger btn-sm" onclick="eliminarAcceso('${a.id}')">× Quitar</button>
    </div>`).join('');
}

async function agregarAcceso() {
  const rol_id     = document.getElementById('adm-acc-rol').value;
  const empresa_id = document.getElementById('adm-acc-empresa').value || null;
  if (!rol_id) { notif('Selecciona un rol','error'); return; }

  const res = await apiRaw(`/rbac/usuarios/${admAccesoUserId}/accesos`, {
    method: 'POST',
    body: JSON.stringify({ rol_id, empresa_id }),
  });
  if (res.ok) {
    notif('Acceso agregado correctamente');
    await _cargarAccesosLista();
    cargarUsuariosSistema();
  } else {
    const err = await res.json();
    notif(err.detail || 'Error al agregar acceso','error');
  }
}

async function eliminarAcceso(accesoId) {
  const res = await apiRaw(`/rbac/usuarios/${admAccesoUserId}/accesos/${accesoId}`, {
    method: 'DELETE',
  });
  if (res.ok || res.status === 204) {
    notif('Acceso eliminado');
    await _cargarAccesosLista();
    cargarUsuariosSistema();
  } else {
    const err = await res.json().catch(() => ({}));
    notif(err.detail || 'Error al eliminar acceso','error');
  }
}

// ── Modal cambiar contraseña ──────────────────────────
function abrirModalPassword(userId, userName) {
  if (!window.RBAC.is_super_admin) {
    notif('Solo super_admin puede cambiar contraseñas','error'); return;
  }
  document.getElementById('adm-pwd-id').value          = userId;
  document.getElementById('adm-pwd-nombre').textContent = userName;
  document.getElementById('adm-pwd-nueva').value        = '';
  document.getElementById('adm-pwd-confirmar').value    = '';
  abrirModal('modal-adm-password');
}

async function guardarPassword() {
  const id         = document.getElementById('adm-pwd-id').value;
  const nueva      = document.getElementById('adm-pwd-nueva').value;
  const confirmar  = document.getElementById('adm-pwd-confirmar').value;

  if (!nueva)             { notif('Ingresa la nueva contraseña','error'); return; }
  if (nueva.length < 6)  { notif('La contraseña debe tener al menos 6 caracteres','error'); return; }
  if (nueva !== confirmar){ notif('Las contraseñas no coinciden','error'); return; }

  const res = await apiRaw(`/rbac/usuarios/${id}/cambiar-password`, {
    method: 'POST',
    body: JSON.stringify({ nueva_password: nueva }),
  });
  if (res.ok) {
    notif('Contraseña actualizada correctamente');
    cerrarModal('modal-adm-password');
  } else {
    const err = await res.json();
    notif(err.detail || 'Error al cambiar contraseña','error');
  }
}

// ── TAB 3: Catálogos ──────────────────────────────────
const CATEGORIAS_CONFIG = [
  { key: 'tipo_activo',        label: 'Tipos de activo',        scope: 'global',  icon: 'ti-device-laptop' },
  { key: 'tipo_accesorio',     label: 'Tipos de accesorio',     scope: 'global',  icon: 'ti-device-gamepad' },
  { key: 'tipo_mantenimiento', label: 'Tipos de mantenimiento', scope: 'global',  icon: 'ti-tool' },
  { key: 'tipo_proveedor',     label: 'Tipos de proveedor',     scope: 'global',  icon: 'ti-building-store' },
  { key: 'ciudad',             label: 'Ciudades',               scope: 'global',  icon: 'ti-map-2' },
  { key: 'hosting',            label: 'Hosting (servidores)',   scope: 'global',  icon: 'ti-server' },
  { key: 'area',               label: 'Áreas',                  scope: 'empresa', icon: 'ti-sitemap' },
  { key: 'cargo',              label: 'Cargos',                 scope: 'empresa', icon: 'ti-id-badge' },
  { key: 'sede',               label: 'Sedes (empleados)',      scope: 'empresa', icon: 'ti-map-pin' },
  { key: 'ubicacion',          label: 'Ubicaciones (activos)',  scope: 'empresa', icon: 'ti-building-warehouse' },
  // Catálogo COMPARTIDO (tabla propia proveedores + ruta /api/proveedores). Renderer
  // dedicado (no el genérico). Gated por proveedores.ver.
  { key: 'proveedores',        label: 'Proveedores',            scope: 'empresa', icon: 'ti-building-store',
    special: 'proveedores', perm: 'proveedores.ver' },
];

let catActivaKey = 'tipo_activo';
let catItems = [];

async function cargarAdminCatalogos() {
  const wrap = document.getElementById('adm-panel-catalogos');
  if (!wrap) return;
  wrap.innerHTML = `
    <div style="display:grid;grid-template-columns:220px 1fr;gap:12px">
      <div id="cat-selector"></div>
      <div id="cat-items-panel"></div>
    </div>`;
  renderCatSelector();
  await cargarItemsCat(catActivaKey);
}

function renderCatSelector() {
  const sel = document.getElementById('cat-selector');
  if (!sel) return;
  // Los ítems con `perm` solo se muestran si el usuario tiene ese permiso.
  sel.innerHTML = CATEGORIAS_CONFIG.filter(c => !c.perm || hasPermiso(c.perm)).map(c => `
    <div class="cat-sel-item ${c.key === catActivaKey ? 'active' : ''}" onclick="seleccionarCategoria('${c.key}')">
      <i class="ti ${c.icon}"></i>
      <div>
        <div style="font-size:12px;font-weight:500;color:var(--text)">${c.label}</div>
        <div style="font-size:10px;color:var(--text4)">${c.scope === 'global' ? 'Global' : 'Por empresa'}</div>
      </div>
    </div>`).join('');
}

async function seleccionarCategoria(key) {
  catActivaKey = key;
  renderCatSelector();
  const config = CATEGORIAS_CONFIG.find(c => c.key === key);
  if (config && config.special === 'proveedores') {
    await cargarProveedoresMaster();
  } else {
    await cargarItemsCat(key);
  }
}

async function cargarItemsCat(key) {
  const config = CATEGORIAS_CONFIG.find(c => c.key === key);
  const empresa = empresaActual || '';
  const url = `/catalogos?categoria=${key}${config.scope === 'empresa' && empresa ? '&empresa_id=' + empresa : ''}`;
  const panel = document.getElementById('cat-items-panel');
  if (!panel) return;
  panel.innerHTML = '<div style="text-align:center;color:var(--text3);padding:20px">Cargando...</div>';
  const data = await api(url);
  catItems = data || [];

  const puedeEditar = hasPermiso('catalogos.editar');
  const esTipoActivo = key === 'tipo_activo';
  const colspan = 4 + (esTipoActivo ? 1 : 0) + (puedeEditar ? 1 : 0);
  const avisoEmpresa = (config.scope === 'empresa' && !empresa)
    ? '<div style="font-size:11px;color:var(--amber);padding:6px 0">Selecciona una empresa activa para gestionar este catálogo por empresa.</div>' : '';

  panel.innerHTML = `
    <div style="background:var(--bg3);border:0.5px solid var(--border);border-radius:10px;overflow:hidden">
      <div style="padding:10px 14px;border-bottom:0.5px solid var(--border);display:flex;align-items:center;justify-content:space-between">
        <div>
          <div style="font-size:12px;font-weight:500;color:var(--text)">${config.label}</div>
          <div style="font-size:10px;color:var(--text4)">${catItems.length} valores activos</div>
        </div>
        ${puedeEditar ? `<button class="btn btn-primary btn-sm" onclick="abrirModalNuevoValor('${key}')">+ Nuevo valor</button>` : ''}
      </div>
      ${avisoEmpresa}
      <table class="tbl" style="margin:0">
        <thead><tr><th>Orden</th><th>Valor</th><th>Descripción</th>${esTipoActivo ? '<th>Años obsolescencia</th>' : ''}<th>Estado</th>${puedeEditar ? '<th>Acciones</th>' : ''}</tr></thead>
        <tbody>
          ${catItems.length ? catItems.map(item => `
            <tr>
              <td style="color:var(--text3);font-size:11px">${item.orden}</td>
              <td>${item.color ? `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${item.color};margin-right:6px"></span>` : ''}<span style="font-weight:500;color:var(--text)">${item.valor}</span>${esTipoActivo && item.es_red ? '<span class="badge asignado" style="margin-left:6px"><i class="ti ti-network"></i> Red</span>' : ''}</td>
              <td style="color:var(--text3);font-size:11px">${item.descripcion || '—'}</td>
              ${esTipoActivo ? `<td style="color:var(--text2);font-size:11px">${item.anios_obsolescencia != null ? item.anios_obsolescencia + ' años' : '<span style="color:var(--text3)">—</span>'}</td>` : ''}
              <td><span class="badge ${item.activo ? 'asignado' : 'baja'}">${item.activo ? 'Activo' : 'Inactivo'}</span></td>
              ${puedeEditar ? `
                <td style="white-space:nowrap">
                  <button class="btn btn-ghost btn-sm" onclick="editarValorCat('${item.id}')">Editar</button>
                  <button class="btn btn-ghost btn-sm" style="color:var(--red);border-color:rgba(255,77,109,0.3)" onclick="desactivarValorCat('${item.id}','${(item.valor || '').replace(/'/g, "\\'")}')">Desactivar</button>
                </td>` : ''}
            </tr>`).join('') : `
            <tr><td colspan="${colspan}" style="text-align:center;color:var(--text3);padding:16px">Sin valores registrados. Agrega el primero con "+ Nuevo valor".</td></tr>`}
        </tbody>
      </table>
    </div>`;
}

function abrirModalNuevoValor(categoria) {
  const config = CATEGORIAS_CONFIG.find(c => c.key === categoria);
  document.getElementById('cat-modal-title').textContent = `Nuevo valor — ${config.label}`;
  document.getElementById('cat-modal-id').value    = '';
  document.getElementById('cat-modal-cat').value   = categoria;
  document.getElementById('cat-modal-valor').value = '';
  document.getElementById('cat-modal-desc').value  = '';
  document.getElementById('cat-modal-orden').value = catItems.length + 1;
  document.getElementById('cat-modal-color').value = '';
  _catToggleAnios(categoria, null);
  _catToggleRed(categoria, false);
  abrirModal('modal-catalogo');
  setTimeout(() => document.getElementById('cat-modal-valor').focus(), 150);
}

// Muestra el campo "Años de obsolescencia" solo para la categoría tipo_activo.
function _catToggleAnios(categoria, valor) {
  const wrap = document.getElementById('cat-anios-wrap');
  const inp  = document.getElementById('cat-modal-anios');
  if (!wrap || !inp) return;
  const esTipoActivo = categoria === 'tipo_activo';
  wrap.style.display = esTipoActivo ? '' : 'none';
  inp.value = (esTipoActivo && valor != null && valor !== '') ? valor : '';
}

// Muestra la casilla "Es de red" solo para la categoría tipo_activo.
function _catToggleRed(categoria, esRed) {
  const wrap = document.getElementById('cat-red-wrap');
  const chk  = document.getElementById('cat-modal-red');
  if (!wrap || !chk) return;
  const esTipoActivo = categoria === 'tipo_activo';
  wrap.style.display = esTipoActivo ? '' : 'none';
  chk.checked = esTipoActivo ? !!esRed : false;
}

function editarValorCat(id) {
  const item = catItems.find(i => i.id === id);
  if (!item) return;
  const config = CATEGORIAS_CONFIG.find(c => c.key === item.categoria);
  document.getElementById('cat-modal-title').textContent = `Editar — ${config.label}`;
  document.getElementById('cat-modal-id').value    = item.id;
  document.getElementById('cat-modal-cat').value   = item.categoria;
  document.getElementById('cat-modal-valor').value = item.valor;
  document.getElementById('cat-modal-desc').value  = item.descripcion || '';
  document.getElementById('cat-modal-orden').value = item.orden || 0;
  document.getElementById('cat-modal-color').value = item.color || '';
  _catToggleAnios(item.categoria, item.anios_obsolescencia);
  _catToggleRed(item.categoria, item.es_red);
  abrirModal('modal-catalogo');
}

async function guardarValorCat() {
  const id        = document.getElementById('cat-modal-id').value;
  const categoria = document.getElementById('cat-modal-cat').value;
  const valor     = document.getElementById('cat-modal-valor').value.trim();
  const desc      = document.getElementById('cat-modal-desc').value.trim();
  const orden     = parseInt(document.getElementById('cat-modal-orden').value) || 0;
  const color     = document.getElementById('cat-modal-color').value.trim() || null;

  if (!valor) { notif('El valor es obligatorio', 'error'); return; }

  const config = CATEGORIAS_CONFIG.find(c => c.key === categoria);
  const empresaId = config.scope === 'empresa' ? (empresaActual || null) : null;
  if (config.scope === 'empresa' && !empresaId) { notif('Selecciona una empresa activa primero', 'error'); return; }

  const body = id
    ? { valor, descripcion: desc || null, orden, color }
    : { categoria, valor, descripcion: desc || null, orden, color, empresa_id: empresaId };

  // Años de obsolescencia + "es de red": solo para tipo_activo
  if (categoria === 'tipo_activo') {
    const aniosRaw = document.getElementById('cat-modal-anios').value;
    body.anios_obsolescencia = aniosRaw === '' ? null : (parseInt(aniosRaw, 10) || 0);
    body.es_red = document.getElementById('cat-modal-red').checked;
  }

  const res = await apiRaw(id ? `/catalogos/${id}` : '/catalogos',
    { method: id ? 'PUT' : 'POST', body: JSON.stringify(body) });

  if (res.ok) {
    notif(id ? 'Valor actualizado' : 'Valor creado');
    cerrarModal('modal-catalogo');
    await cargarItemsCat(categoria);
    await cargarCatalogos();
  } else {
    const err = await res.json().catch(() => ({}));
    notif(err.detail || 'Error al guardar', 'error');
  }
}

async function desactivarValorCat(id, valor) {
  if (!confirm(`¿Desactivar "${valor}"? Seguirá visible en registros existentes pero no estará disponible para nuevas asignaciones.`)) return;
  const res = await apiRaw(`/catalogos/${id}`, { method: 'PUT', body: JSON.stringify({ activo: false }) });
  if (res.ok) {
    notif(`"${valor}" desactivado`);
    await cargarItemsCat(catActivaKey);
    await cargarCatalogos();
  } else {
    const err = await res.json().catch(() => ({}));
    notif(err.detail || 'Error al desactivar', 'error');
  }
}

// ── Catálogos → Proveedores (catálogo COMPARTIDO, ruta /api/proveedores) ──────
// Módulos disponibles para el flag `modulos`. Un proveedor puede aplicar a varios.
const PROV_MODULOS = [
  { key: 'compras',    label: 'Compras' },
  { key: 'impresoras', label: 'Impresoras' },
];
let provMasterItems = [];

async function cargarProveedoresMaster() {
  const panel = document.getElementById('cat-items-panel');
  if (!panel) return;
  const puedeGestionar = hasPermiso('proveedores.gestionar');

  // Proveedores GLOBALES: no dependen de la empresa activa; se listan todos.
  panel.innerHTML = '<div style="text-align:center;color:var(--text3);padding:20px">Cargando...</div>';
  provMasterItems = await api(`/proveedores`) || [];

  const filas = provMasterItems.length ? provMasterItems.map(p => {
    const badges = (p.modulos || []).map(m => {
      const cfg = PROV_MODULOS.find(x => x.key === m);
      return `<span class="badge asignado" style="margin-right:4px">${cfg ? cfg.label : m}</span>`;
    }).join('') || '<span style="color:var(--text3)">—</span>';
    const contacto = [p.contacto_nombre, p.telefono, p.correo].filter(Boolean).join(' · ') || '—';
    return `
      <tr>
        <td><span style="font-weight:500;color:var(--text)">${_hvEscA(p.nombre)}</span>
            ${p.activo === false ? '<span class="badge baja" style="margin-left:6px">Inactivo</span>' : ''}</td>
        <td style="color:var(--text3);font-size:11px">${_hvEscA(p.nit) || '—'}</td>
        <td style="font-size:11px">${_hvEscA(p.tipo) || '—'}</td>
        <td style="color:var(--text3);font-size:11px">${_hvEscA(contacto)}</td>
        <td style="color:var(--text3);font-size:11px">${_hvEscA(p.ciudad) || '—'}</td>
        <td>${badges}</td>
        ${puedeGestionar ? `<td style="white-space:nowrap"><button class="btn btn-ghost btn-sm" onclick="abrirModalProveedorMaster('${p.id}')">Editar</button></td>` : ''}
      </tr>`;
  }).join('') : `<tr><td colspan="${puedeGestionar ? 7 : 6}" style="text-align:center;color:var(--text3);padding:16px">Sin proveedores registrados para esta empresa.</td></tr>`;

  panel.innerHTML = `
    <div style="background:var(--bg3);border:0.5px solid var(--border);border-radius:10px;overflow:hidden">
      <div style="padding:10px 14px;border-bottom:0.5px solid var(--border);display:flex;align-items:center;justify-content:space-between">
        <div>
          <div style="font-size:12px;font-weight:500;color:var(--text)">Proveedores</div>
          <div style="font-size:10px;color:var(--text4)">${provMasterItems.length} proveedor(es) · catálogo compartido</div>
        </div>
        ${puedeGestionar ? `<button class="btn btn-primary btn-sm" onclick="abrirModalProveedorMaster()">+ Nuevo proveedor</button>` : ''}
      </div>
      <table class="tbl" style="margin:0">
        <thead><tr><th>Nombre</th><th>NIT</th><th>Tipo</th><th>Contacto</th><th>Ciudad</th><th>Módulos</th>${puedeGestionar ? '<th>Acciones</th>' : ''}</tr></thead>
        <tbody>${filas}</tbody>
      </table>
    </div>`;
}

// Escape helper local (evita depender de otros módulos).
function _hvEscA(s) {
  return String(s == null ? '' : s)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function abrirModalProveedorMaster(id = null) {
  if (!hasPermiso('proveedores.gestionar')) return;
  const p = id ? provMasterItems.find(x => x.id === id) : null;

  document.getElementById('provm-id').value    = p ? p.id : '';
  document.getElementById('provm-title').textContent = p ? 'Editar proveedor' : 'Nuevo proveedor';
  const set = (fid, v) => { const el = document.getElementById(fid); if (el) el.value = (v == null ? '' : v); };
  set('provm-nombre',   p ? p.nombre : '');
  set('provm-nit',      p ? p.nit : '');
  set('provm-contacto', p ? p.contacto_nombre : '');
  set('provm-telefono', p ? p.telefono : '');
  set('provm-correo',   p ? p.correo : '');
  set('provm-ciudad',   p ? p.ciudad : '');
  // tipo desde el catálogo tipo_proveedor (igual que el modal de compras), default vendedor
  llenarSelectCatalogo('provm-tipo', 'tipo_proveedor', p ? (p.tipo || 'vendedor') : 'vendedor');
  // módulos: pre-check desde la fila (nuevo → compras por defecto)
  const mods = p ? (p.modulos || []) : ['compras'];
  PROV_MODULOS.forEach(m => {
    const chk = document.getElementById(`provm-mod-${m.key}`);
    if (chk) chk.checked = mods.includes(m.key);
  });
  abrirModal('modal-proveedor-master');
}

async function guardarProveedorMaster() {
  const id     = document.getElementById('provm-id').value;
  const nombre = document.getElementById('provm-nombre').value.trim();
  if (!nombre) { notif('El nombre es obligatorio', 'error'); return; }

  const modulos = PROV_MODULOS
    .filter(m => document.getElementById(`provm-mod-${m.key}`)?.checked)
    .map(m => m.key);
  if (!modulos.length) { notif('Marca al menos un módulo (Compras o Impresoras)', 'error'); return; }

  const body = {
    nombre,
    nit:             document.getElementById('provm-nit').value.trim() || null,
    tipo:            document.getElementById('provm-tipo').value || 'vendedor',
    contacto_nombre: document.getElementById('provm-contacto').value.trim() || null,
    telefono:        document.getElementById('provm-telefono').value.trim() || null,
    correo:          document.getElementById('provm-correo').value.trim() || null,
    ciudad:          document.getElementById('provm-ciudad').value.trim() || null,
    modulos,
  };

  let res;
  if (id) {
    res = await apiRaw(`/proveedores/${id}`, { method: 'PUT', body: JSON.stringify(body) });
  } else {
    // Proveedor GLOBAL: sin empresa_id.
    res = await apiRaw('/proveedores', { method: 'POST', body: JSON.stringify(body) });
  }

  if (res.ok) {
    notif(id ? 'Proveedor actualizado' : 'Proveedor creado');
    cerrarModal('modal-proveedor-master');
    await cargarProveedoresMaster();
  } else {
    const err = await res.json().catch(() => ({}));
    notif(err.detail || 'Error al guardar el proveedor', 'error');
  }
}

// ── TAB 2: Roles y permisos ───────────────────────────
let admRolesRef = [];
let admPermisosGrupos = {};   // { modulo: [{codigo,accion,descripcion}] }

function _puedeGestionarRoles() {
  return window.RBAC.is_super_admin || (window.RBAC.roles || []).includes('admin');
}

async function cargarRolesRef() {
  const data = await api('/rbac/roles');
  admRolesRef = data || [];
  const container = document.getElementById('adm-roles-ref');
  const puede = _puedeGestionarRoles();

  const header = `
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px">
      <span style="font-size:12px;color:var(--text3)">${admRolesRef.length} roles configurados</span>
      ${puede ? `<button class="btn btn-primary btn-sm" onclick="abrirModalNuevoRol()">+ Nuevo rol</button>` : ''}
    </div>`;

  if (!admRolesRef.length) {
    container.innerHTML = header + '<div style="color:var(--text3);padding:20px;text-align:center">Sin roles configurados</div>';
    return;
  }

  container.innerHTML = header + admRolesRef.map(r => `
    <div class="panel" style="margin-bottom:12px">
      <div class="panel-head">
        <span class="panel-title">
          <span class="acceso-tag ${r.nombre}" style="margin-right:8px">${r.nombre}</span>
          <span style="font-size:12px;color:var(--text2)">${r.descripcion || ''}</span>
          ${r.es_sistema ? '<span style="font-size:9px;color:var(--text3);border:1px solid var(--border);border-radius:4px;padding:1px 6px;margin-left:6px">sistema</span>' : ''}
        </span>
        <span style="display:flex;align-items:center;gap:8px">
          <span style="font-size:11px;color:var(--text3)">${r.permisos.length} permisos · ${r.num_usuarios||0} usuario(s)</span>
          ${puede && r.nombre !== 'super_admin' ? `<button class="btn btn-ghost btn-sm" onclick="editarRol('${r.id}')">Editar</button>` : ''}
          ${puede && !r.es_sistema ? `<button class="btn btn-ghost btn-sm" style="color:var(--red);border-color:rgba(255,77,109,0.3)" onclick="eliminarRol('${r.id}','${r.nombre}')">Eliminar</button>` : ''}
        </span>
      </div>
      <div style="padding:10px 16px;display:flex;flex-wrap:wrap;gap:5px">
        ${r.permisos.length ? r.permisos.map(p => `<span style="font-size:10px;font-family:var(--mono);background:rgba(var(--accent-rgb),0.06);border:1px solid var(--border);border-radius:4px;padding:2px 7px;color:var(--text2)">${p}</span>`).join('') : '<span style="font-size:11px;color:var(--text3)">Sin permisos asignados</span>'}
      </div>
    </div>`).join('');
}

// ── Modal crear/editar rol ────────────────────────────
async function _cargarPermisosGrupos() {
  if (Object.keys(admPermisosGrupos).length) return admPermisosGrupos;
  admPermisosGrupos = await api('/rbac/permisos') || {};
  return admPermisosGrupos;
}

function _renderPermisosCheck(seleccionados) {
  const sel = new Set(seleccionados || []);
  const cont = document.getElementById('rol-permisos-cont');
  const grupos = admPermisosGrupos;
  cont.innerHTML = Object.keys(grupos).sort().map(modulo => `
    <div style="margin-bottom:12px">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:5px">
        <div style="font-size:11px;font-weight:600;color:var(--cyan);text-transform:uppercase;letter-spacing:0.5px">${modulo}</div>
        <label style="font-size:10px;color:var(--text3);cursor:pointer"><input type="checkbox" onchange="_toggleModuloPermisos('${modulo}',this.checked)"> todos</label>
      </div>
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px">
        ${grupos[modulo].map(p => `
          <label style="display:flex;align-items:center;gap:6px;font-size:11px;color:var(--text2);cursor:pointer;padding:3px 0">
            <input type="checkbox" class="rol-perm-chk" data-modulo="${modulo}" value="${p.codigo}" ${sel.has(p.codigo)?'checked':''}>
            <span title="${p.descripcion||''}">${p.accion}</span>
          </label>`).join('')}
      </div>
    </div>`).join('');
}

function _toggleModuloPermisos(modulo, checked) {
  document.querySelectorAll(`.rol-perm-chk[data-modulo="${modulo}"]`).forEach(chk => { chk.checked = checked; });
}

async function abrirModalNuevoRol() {
  if (!_puedeGestionarRoles()) { notif('Sin permiso para gestionar roles','error'); return; }
  await _cargarPermisosGrupos();
  document.getElementById('rol-modal-title').textContent = 'Nuevo rol';
  document.getElementById('rol-modal-id').value = '';
  document.getElementById('rol-modal-nombre').value = '';
  document.getElementById('rol-modal-nombre').disabled = false;
  document.getElementById('rol-modal-desc').value = '';
  _renderPermisosCheck([]);
  abrirModal('modal-rol');
}

async function editarRol(id) {
  if (!_puedeGestionarRoles()) { notif('Sin permiso para gestionar roles','error'); return; }
  const rol = admRolesRef.find(r => r.id === id);
  if (!rol) return;
  await _cargarPermisosGrupos();
  document.getElementById('rol-modal-title').textContent = `Editar rol — ${rol.nombre}`;
  document.getElementById('rol-modal-id').value = rol.id;
  document.getElementById('rol-modal-nombre').value = rol.nombre;
  document.getElementById('rol-modal-nombre').disabled = !!rol.es_sistema; // no renombrar roles del sistema
  document.getElementById('rol-modal-desc').value = rol.descripcion || '';
  _renderPermisosCheck(rol.permisos);
  abrirModal('modal-rol');
}

async function guardarRol() {
  const id     = document.getElementById('rol-modal-id').value;
  const nombre = document.getElementById('rol-modal-nombre').value.trim();
  const desc   = document.getElementById('rol-modal-desc').value.trim();
  const permisos = [...document.querySelectorAll('.rol-perm-chk:checked')].map(c => c.value);

  if (!nombre) { notif('El nombre del rol es obligatorio','error'); return; }
  if (!permisos.length && !confirm('Este rol no tiene permisos seleccionados. ¿Continuar?')) return;

  const body = id
    ? { nombre, descripcion: desc || null, permisos }
    : { nombre, descripcion: desc || null, permisos };
  const res = await apiRaw(id ? `/rbac/roles/${id}` : '/rbac/roles',
    { method: id ? 'PUT' : 'POST', body: JSON.stringify(body) });

  if (res.ok) {
    notif(id ? 'Rol actualizado' : 'Rol creado');
    cerrarModal('modal-rol');
    await cargarRolesRef();
  } else {
    const err = await res.json().catch(() => ({}));
    notif(err.detail || 'Error al guardar el rol','error');
  }
}

async function eliminarRol(id, nombre) {
  if (!confirm(`¿Eliminar el rol "${nombre}"? Solo es posible si no está asignado a ningún usuario.`)) return;
  const res = await apiRaw(`/rbac/roles/${id}`, { method: 'DELETE' });
  if (res.ok || res.status === 204) {
    notif(`Rol "${nombre}" eliminado`);
    await cargarRolesRef();
  } else {
    const err = await res.json().catch(() => ({}));
    notif(err.detail || 'Error al eliminar','error');
  }
}

// ══ IMPORTACIÓN MASIVA (Activos / Accesorios) ════════════════════════════════
let _impFile = null;        // archivo .xlsx seleccionado
let _impFallidas = [];      // filas con error del último /ejecutar (para descargar)
let _impTipo = 'activos';   // 'activos' | 'accesorios'
let _impEmpresas = [];      // empresas disponibles (para accesorios)

// Inicializa la pestaña: tipo por defecto, carga empresas, limpia estado
async function initImportacion() {
  if (!_impEmpresas.length) {
    _impEmpresas = await api('/rbac/empresas-disponibles') || [];
  }
  const sel = document.getElementById('imp-empresa');
  if (sel) {
    sel.innerHTML = '<option value="">Seleccionar empresa...</option>' +
      _impEmpresas.map(e => `<option value="${e.id}">${e.nombre_empresa}</option>`).join('');
  }
  setImpTipo('activos');
}

function setImpTipo(tipo) {
  _impTipo = tipo;
  // estilos del toggle
  document.getElementById('imp-tipo-activos').className = 'btn btn-sm ' + (tipo === 'activos' ? 'btn-primary' : 'btn-ghost');
  document.getElementById('imp-tipo-accesorios').className = 'btn btn-sm ' + (tipo === 'accesorios' ? 'btn-primary' : 'btn-ghost');
  // selector de empresa solo para accesorios
  document.getElementById('imp-empresa-wrap').style.display = (tipo === 'accesorios') ? '' : 'none';
  document.getElementById('imp-plantilla-label').textContent =
    tipo === 'accesorios' ? 'Descargar plantilla de accesorios' : 'Descargar plantilla de activos';
  // limpiar archivo + reportes
  const fileEl = document.getElementById('imp-file'); if (fileEl) fileEl.value = '';
  _impFile = null;
  resetImportacion();
  onArchivoImport();
}

function resetImportacion() {
  const p = document.getElementById('imp-preview'); if (p) p.innerHTML = '';
  const r = document.getElementById('imp-result');  if (r) r.innerHTML = '';
}

// ¿hay empresa elegida cuando se requiere (accesorios)?
function _impEmpresaOk() {
  if (_impTipo !== 'accesorios') return true;
  return !!document.getElementById('imp-empresa').value;
}

function onArchivoImport() {
  _impFile = document.getElementById('imp-file').files[0] || null;
  document.getElementById('imp-btn-validar').disabled = !(_impFile && _impEmpresaOk());
  resetImportacion();
}

function _impSaveBlob(blob, name) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = name; a.click();
  URL.revokeObjectURL(url);
}

// Subida multipart: fetch directo con SOLO Authorization (apiRaw forzaría JSON).
// Para accesorios añade empresa_id como campo del formulario.
async function _impUpload(action) {
  const fd = new FormData();
  fd.append('file', _impFile);
  if (_impTipo === 'accesorios') fd.append('empresa_id', document.getElementById('imp-empresa').value);
  return fetch(`${API}/importacion/${_impTipo}/${action}`, {
    method: 'POST', headers: { 'Authorization': `Bearer ${TOKEN}` }, body: fd,
  });
}

async function descargarPlantilla() {
  const res = await fetch(`${API}/importacion/plantilla/${_impTipo}`, { headers: { 'Authorization': `Bearer ${TOKEN}` } });
  if (!res.ok) { notif('No se pudo descargar la plantilla', 'error'); return; }
  _impSaveBlob(await res.blob(), `plantilla_${_impTipo}.xlsx`);
}

async function validarImportacion() {
  if (!_impFile) return;
  if (!_impEmpresaOk()) { notif('Selecciona la empresa del archivo', 'error'); return; }
  const cont = document.getElementById('imp-preview');
  cont.innerHTML = '<div style="color:var(--text3);padding:10px">Validando archivo…</div>';
  document.getElementById('imp-result').innerHTML = '';
  const res = await _impUpload('validar');
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    cont.innerHTML = `<div style="color:var(--red);padding:10px">${e.detail || 'Error al validar el archivo'}</div>`;
    return;
  }
  renderImportPreview(await res.json());
}

function renderImportPreview(rep) {
  const cont = document.getElementById('imp-preview');
  const importables = rep.validas + rep.con_advertencia;
  const filas = (rep.filas || []).map(f => {
    const color = f.estado_resultado === 'error' ? 'var(--red)'
      : f.estado_resultado === 'advertencia' ? 'var(--amber)' : 'var(--green)';
    const icon = f.estado_resultado === 'error' ? '✕'
      : f.estado_resultado === 'advertencia' ? '⚠' : '✓';
    return `<tr>
      <td style="color:var(--text3)">${f.fila_num}</td>
      <td><span class="mono-tag">${f.placa || '—'}</span></td>
      <td style="color:${color};font-weight:600;white-space:nowrap">${icon} ${f.estado_resultado}</td>
      <td style="font-size:11px;color:var(--text2)">${(f.mensajes || []).join('<br>') || '—'}</td>
    </tr>`;
  }).join('');
  cont.innerHTML = `
    <div style="display:flex;gap:8px;flex-wrap:wrap;margin:6px 0;align-items:center">
      <span class="dash-alerta-chip green">✓ ${rep.validas} válidas</span>
      <span class="dash-alerta-chip amber">⚠ ${rep.con_advertencia} advertencias</span>
      <span class="dash-alerta-chip red">✕ ${rep.con_error} errores</span>
      <span style="color:var(--text3);font-size:12px">de ${rep.total_filas} filas</span>
    </div>
    <div class="panel tabla-scroll" style="max-height:340px;overflow:auto">
      <table class="tbl"><thead><tr><th>Fila</th><th>Placa</th><th>Resultado</th><th>Mensajes</th></tr></thead>
      <tbody>${filas || '<tr><td colspan="4" style="text-align:center;color:var(--text3);padding:16px">Sin filas</td></tr>'}</tbody></table>
    </div>
    <div style="display:flex;gap:10px;margin-top:12px;align-items:center">
      <button class="btn btn-primary" id="imp-btn-ejecutar" onclick="ejecutarImportacion()" ${importables < 1 ? 'disabled' : ''}>Importar ${importables} fila(s) válida(s)</button>
      <button class="btn btn-ghost" onclick="cancelarImportacion()">Cancelar</button>
      ${importables < 1 ? '<span style="color:var(--text3);font-size:11px">No hay filas importables.</span>' : ''}
    </div>`;
}

function cancelarImportacion() {
  document.getElementById('imp-file').value = '';
  onArchivoImport();
}

async function ejecutarImportacion() {
  if (!_impFile) return;
  if (!confirm('Se importarán únicamente las filas válidas (las filas con error se omiten). ¿Continuar?')) return;
  const btn = document.getElementById('imp-btn-ejecutar');
  if (btn) { btn.disabled = true; btn.textContent = 'Importando…'; }
  const res = await _impUpload('ejecutar');
  if (!res.ok) {
    const e = await res.json().catch(() => ({}));
    notif(e.detail || 'Error al importar', 'error');
    if (btn) { btn.disabled = false; btn.textContent = 'Importar'; }
    return;
  }
  const r = await res.json();
  _impFallidas = r.filas_fallidas || [];
  document.getElementById('imp-preview').innerHTML = '';
  document.getElementById('imp-result').innerHTML = `
    <div style="background:rgba(0,229,160,.08);border:1px solid rgba(0,229,160,.3);border-radius:8px;padding:12px 14px;margin-top:8px">
      <div style="font-weight:700;color:var(--green)">✓ Importación finalizada</div>
      <div style="font-size:12px;color:var(--text2);margin-top:4px">
        Importados: <b>${r.importados}</b> · Omitidos (error): <b>${r.omitidos}</b> · Con advertencia: <b>${r.advertencias}</b> · Total filas: ${r.total_filas}
      </div>
      ${r.omitidos > 0 ? `<button class="btn btn-ghost btn-sm" style="margin-top:10px;color:var(--red);border-color:rgba(255,77,109,.3)" onclick="descargarFallidas()"><i class="ti ti-download"></i> Descargar filas fallidas (${r.omitidos})</button>` : ''}
    </div>`;
  notif(`Importación: ${r.importados} creados, ${r.omitidos} omitidos`);
  document.getElementById('imp-file').value = '';
  _impFile = null;
  document.getElementById('imp-btn-validar').disabled = true;
  if (_impTipo === 'accesorios') {
    if (typeof cargarAccesorios === 'function') cargarAccesorios();
  } else {
    if (typeof cargarActivos === 'function') cargarActivos();
  }
  if (typeof cargarDashboard === 'function') cargarDashboard();
}

async function descargarFallidas() {
  const res = await fetch(`${API}/importacion/${_impTipo}/exportar-fallidas`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${TOKEN}`, 'Content-Type': 'application/json' },
    body: JSON.stringify({ filas_fallidas: _impFallidas }),
  });
  if (!res.ok) { notif('No se pudo generar el archivo de fallidas', 'error'); return; }
  _impSaveBlob(await res.blob(), `filas_fallidas_${_impTipo}.xlsx`);
}
