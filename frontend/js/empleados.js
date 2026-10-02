let empleadosFiltrados = [];   // resultado tras aplicar filtros (listo para exportar)
async function cargarUsuarios() {
  const p = empresaActual ? `?empresa_id=${empresaActual}` : '';
  const data = await api(`/usuarios${p}`);
  usuariosCache = data || [];
  poblarFiltrosEmpleados();
  aplicarFiltrosEmpleados();
}
function renderUsuarios(list) {
  const tbody = document.getElementById('tbl-usuarios-body');
  tbody.innerHTML = list.length ? list.map(u=>`
    <tr class="clickable" onclick="editarUsuario('${u.id}')">
      <td><span class="mono-tag">${u.documento}</span></td>
      <td><div class="td-name">${u.nombre_completo}</div><div class="td-sub">${u.correo||''}</div></td>
      <td><div class="td-name" style="font-size:11px">${u.cargo||'—'}</div><div class="td-sub">${u.area||''}</div></td>
      <td style="font-size:11px">${u.sede||'—'}</td>
      <td><div class="td-sub">${u.nombre_empresa||'—'}</div></td>
      <td><span class="badge ${u.estado}">${u.estado}</span></td>
      <td><button class="btn btn-ghost btn-sm" style="color:var(--cyan);border-color:rgba(6,191,255,0.3)" onclick="event.stopPropagation();abrirRecursosEmpleado('${u.id}','${u.nombre_completo.replace(/'/g,"\\'")}','${u.documento}','${u.empresa_id}')">📦 Ver recursos</button></td>
      <td><button class="btn btn-ghost btn-sm" style="color:var(--green);border-color:rgba(0,229,160,0.3)" onclick="event.stopPropagation();verUltimaActa('${u.id}','${u.nombre_completo.replace(/'/g,"\\''")}')">📄 Última acta</button></td>
    </tr>`).join('')
    : '<tr><td colspan="8" style="text-align:center;color:var(--text3);padding:20px">Sin empleados</td></tr>';
}
function buscarUsuarios() { aplicarFiltrosEmpleados(); }

function poblarFiltrosEmpleados() {
  llenarSelectDistinct('filtro-empleados-empresa', usuariosCache, 'nombre_empresa', 'Todas');
  llenarSelectDistinct('filtro-empleados-sede',    usuariosCache, 'sede',           'Todas');
  llenarSelectDistinct('filtro-empleados-cargo',   usuariosCache, 'cargo',          'Todos');
  llenarSelectDistinct('filtro-empleados-area',    usuariosCache, 'area',           'Todas');
}

function aplicarFiltrosEmpleados() {
  const q       = (document.getElementById('search-usuarios').value || '').toLowerCase().trim();
  const empresa = document.getElementById('filtro-empleados-empresa').value;
  const sede    = document.getElementById('filtro-empleados-sede').value;
  const cargo   = document.getElementById('filtro-empleados-cargo').value;
  const area    = document.getElementById('filtro-empleados-area').value;
  const estado  = document.getElementById('filtro-empleados-estado').value;

  let lista = usuariosCache.slice();
  if (empresa) lista = lista.filter(u => (u.nombre_empresa || '') === empresa);
  if (sede)    lista = lista.filter(u => (u.sede || '') === sede);
  if (cargo)   lista = lista.filter(u => (u.cargo || '') === cargo);
  if (area)    lista = lista.filter(u => (u.area || '') === area);
  if (estado)  lista = lista.filter(u => u.estado === estado);
  if (q) lista = lista.filter(u =>
    (u.documento||'').includes(q) ||
    (u.nombre_completo||'').toLowerCase().includes(q) ||
    (u.correo||'').toLowerCase().includes(q));

  empleadosFiltrados = lista;
  renderUsuarios(lista);
  actualizarCount('count-empleados', lista.length, usuariosCache.length);
}

function limpiarFiltrosEmpleados() {
  ['filtro-empleados-empresa','filtro-empleados-sede','filtro-empleados-cargo','filtro-empleados-area','filtro-empleados-estado'].forEach(id => {
    const e = document.getElementById(id); if (e) e.value = '';
  });
  document.getElementById('search-usuarios').value = '';
  aplicarFiltrosEmpleados();
}

const COLUMNAS_EXPORT_EMPLEADOS = [
  {key:'documento',       label:'Cédula'},
  {key:'nombre_completo', label:'Nombre completo'},
  {key:'cargo',           label:'Cargo'},
  {key:'area',            label:'Área'},
  {key:'unidad_negocio',  label:'Unidad de negocio'},
  {key:'sede',            label:'Sede'},
  {key:'correo',          label:'Correo'},
  {key:'telefono',        label:'Teléfono'},
  {key:'nombre_empresa',  label:'Empresa'},
  {key:'estado',          label:'Estado'},
];
function exportarEmpleados(formato, btn) {
  exportarDatos(formato, 'Empleados', COLUMNAS_EXPORT_EMPLEADOS, empleadosFiltrados, btn);
}
// Pobla el <select> de sedes con las sedes de la empresa indicada.
// `valorActual` se conserva como opción aunque no esté en la lista (datos antiguos).
function llenarSelectSedes(selId, empresaId, valorActual) {
  const sel = document.getElementById(selId);
  if (!sel) return;
  const emp = empresasCache.find(e => e.id === empresaId);
  const sedes = (emp && Array.isArray(emp.sedes)) ? emp.sedes : [];
  sel.innerHTML = '<option value="">Seleccionar...</option>';
  sedes.forEach(s => {
    const o = document.createElement('option');
    o.value = s; o.textContent = s;
    sel.appendChild(o);
  });
  if (valorActual && !sedes.includes(valorActual)) {
    const o = document.createElement('option');
    o.value = valorActual; o.textContent = `${valorActual} (actual)`;
    sel.appendChild(o);
  }
  sel.value = valorActual || '';
}

function onCambioEmpresaUsuario() {
  llenarSelectSedes('usr-sede', document.getElementById('usr-empresa').value, '');
}

function abrirModalUsuario() {
  limpiarModal(['usr-id','usr-cedula','usr-nombre','usr-cargo','usr-area','usr-unidad-negocio','usr-sede','usr-correo','usr-telefono']);
  document.getElementById('usr-estado').value = 'activo';
  document.getElementById('modal-usr-title').textContent = 'Nuevo empleado';
  llenarSelectEmpresas('usr-empresa');
  if (empresaActual) document.getElementById('usr-empresa').value = empresaActual;
  llenarSelectSedes('usr-sede', document.getElementById('usr-empresa').value, '');
  abrirModal('modal-usuario');
}
function editarUsuario(id) {
  if (!hasPermiso('usuarios.editar')) return;
  const u = usuariosCache.find(x=>x.id===id);
  if (!u) return;
  document.getElementById('usr-id').value       = u.id;
  document.getElementById('usr-cedula').value   = u.documento;
  document.getElementById('usr-nombre').value   = u.nombre_completo;
  document.getElementById('usr-cargo').value          = u.cargo||'';
  document.getElementById('usr-area').value           = u.area||'';
  document.getElementById('usr-unidad-negocio').value = u.unidad_negocio||'';
  document.getElementById('usr-correo').value         = u.correo||'';
  document.getElementById('usr-telefono').value       = u.telefono||'';
  document.getElementById('usr-estado').value   = u.estado;
  document.getElementById('modal-usr-title').textContent = `Editar — ${u.nombre_completo}`;
  llenarSelectEmpresas('usr-empresa');
  document.getElementById('usr-empresa').value = u.empresa_id;
  llenarSelectSedes('usr-sede', u.empresa_id, u.sede||'');
  abrirModal('modal-usuario');
}
async function guardarUsuario() {
  const id = document.getElementById('usr-id').value;
  const body = {
    empresa_id:      document.getElementById('usr-empresa').value,
    documento:       document.getElementById('usr-cedula').value.trim(),
    nombre_completo: document.getElementById('usr-nombre').value.trim(),
    cargo:           document.getElementById('usr-cargo').value||null,
    area:            document.getElementById('usr-area').value||null,
    unidad_negocio:  document.getElementById('usr-unidad-negocio').value||null,
    sede:            document.getElementById('usr-sede').value||null,
    correo:          document.getElementById('usr-correo').value||null,
    telefono:        document.getElementById('usr-telefono').value||null,
    estado:          document.getElementById('usr-estado').value,
  };
  if (!body.empresa_id||!body.documento||!body.nombre_completo) {
    notif('Empresa, cédula y nombre son obligatorios','error'); return;
  }
  const res = await apiRaw(id?`/usuarios/${id}`:`/usuarios`, {
    method: id?'PUT':'POST', body: JSON.stringify(body)
  });
  if (res.ok) {
    notif(id?'Empleado actualizado':'Empleado creado');
    cerrarModal('modal-usuario'); cargarUsuarios();
  } else {
    const err = await res.json();
    notif(err.detail||'Error al guardar','error');
  }
}

// ── EMPRESAS CRUD ─────────────────────────────────────
let empSedes = [];
function renderEmpSedes() {
  const cont = document.getElementById('emp-sedes-lista');
  cont.innerHTML = empSedes.map((s, i) => `
    <span style="display:inline-flex;align-items:center;gap:6px;background:rgba(6,191,255,0.1);border:1px solid var(--border2);border-radius:20px;padding:3px 10px;font-size:11px;color:var(--cyan)">
      🏢 ${s}
      <button type="button" onclick="quitarSedeEmp(${i})" style="background:none;border:none;color:var(--red);cursor:pointer;font-size:13px;padding:0;line-height:1">×</button>
    </span>`).join('');
}
function agregarSedeEmp() {
  const inp = document.getElementById('emp-sede-input');
  const v = inp.value.trim();
  if (!v) return;
  if (empSedes.some(s => s.toLowerCase() === v.toLowerCase())) {
    notif('Esa sede ya está en la lista','error'); inp.value=''; return;
  }
  empSedes.push(v);
  inp.value = '';
  inp.focus();
  renderEmpSedes();
}
function quitarSedeEmp(i) {
  empSedes.splice(i, 1);
  renderEmpSedes();
}

// URL del logo servido por /logos-empresa (mismo archivo que leen las actas).
// El ?t= evita que el navegador muestre una versión cacheada tras cambiarlo.
function _logoEmpresaUrl(prefijo) {
  const origin = API.replace(/\/api\/?$/, '');
  return `${origin}/logos-empresa/logo_${prefijo}.png?t=${Date.now()}`;
}

// Previsualiza la imagen elegida en el input de logo.
function previewLogoEmpresa(input) {
  const img = document.getElementById('emp-logo-preview');
  const file = input.files && input.files[0];
  if (!file) return;
  if (!file.type || !file.type.startsWith('image/')) {
    notif('El archivo debe ser una imagen', 'error');
    input.value = ''; return;
  }
  const reader = new FileReader();
  reader.onload = e => { img.src = e.target.result; img.style.display = ''; };
  reader.readAsDataURL(file);
}

// Reinicia el input de logo del modal (input file + preview).
function _resetLogoEmpresaInput() {
  const inp = document.getElementById('emp-logo');
  const img = document.getElementById('emp-logo-preview');
  if (inp) inp.value = '';
  if (img) { img.src = ''; img.style.display = 'none'; }
}

function abrirModalEmpresa() {
  limpiarModal(['emp-id','emp-nit','emp-prefijo','emp-nombre','emp-ciudad','emp-telefono','emp-correo','emp-direccion','emp-sede-input']);
  document.getElementById('modal-emp-title').textContent = 'Nueva empresa';
  empSedes = [];
  renderEmpSedes();
  // Logo: obligatorio al crear
  _resetLogoEmpresaInput();
  document.getElementById('emp-logo-req').style.display = '';
  const hint = document.getElementById('emp-logo-hint');
  hint.textContent = 'Imagen PNG o JPG obligatoria. Aparecerá en las actas de la empresa.';
  hint.style.color = 'var(--text3)';
  // Las relaciones requieren que la empresa exista primero → ocultar al crear
  const relWrap = document.getElementById('emp-relaciones-wrap');
  if (relWrap) relWrap.style.display = 'none';
  abrirModal('modal-empresa');
}
async function editarEmpresa(id) {
  const e = empresasCache.find(x=>x.id===id);
  if (!e) return;
  document.getElementById('emp-id').value        = e.id;
  document.getElementById('emp-nit').value       = e.nit;
  document.getElementById('emp-prefijo').value   = e.prefijo;
  document.getElementById('emp-nombre').value    = e.nombre_empresa;
  document.getElementById('emp-ciudad').value    = e.ciudad||'';
  document.getElementById('emp-telefono').value  = e.telefono||'';
  document.getElementById('emp-correo').value    = e.correo||'';
  document.getElementById('emp-direccion').value = e.direccion||'';
  document.getElementById('emp-sede-input').value = '';
  empSedes = Array.isArray(e.sedes) ? e.sedes.slice() : [];
  renderEmpSedes();
  // Logo: NO obligatorio al editar. Mostrar el actual si existe, o avisar si falta.
  _resetLogoEmpresaInput();
  document.getElementById('emp-logo-req').style.display = 'none';
  const hint = document.getElementById('emp-logo-hint');
  if (e.tiene_logo) {
    const img = document.getElementById('emp-logo-preview');
    img.src = _logoEmpresaUrl(e.prefijo);
    img.style.display = '';
    hint.textContent = 'Puedes cambiar el logo o dejar el actual.';
    hint.style.color = 'var(--text3)';
  } else {
    hint.textContent = '⚠ Falta cargar el logo de esta empresa (no aparecerá en sus actas hasta que lo subas).';
    hint.style.color = 'var(--amber)';
  }
  document.getElementById('modal-emp-title').textContent = `Editar — ${e.nombre_empresa}`;
  abrirModal('modal-empresa');
  _empCargarRelaciones(id);
}

// Llena el checklist de empresas relacionadas (hermanas) para la empresa en edición.
async function _empCargarRelaciones(empresaId) {
  const wrap = document.getElementById('emp-relaciones-wrap');
  const cont = document.getElementById('emp-relaciones-lista');
  if (!wrap || !cont) return;
  wrap.style.display = '';
  const otras = (empresasCache || []).filter(e => e.id !== empresaId)
    .sort((a, b) => (a.nombre_empresa||'').localeCompare(b.nombre_empresa||'', 'es'));
  if (!otras.length) {
    cont.innerHTML = '<div style="font-size:12px;color:var(--text3)">No hay otras empresas para relacionar.</div>';
    return;
  }
  const rel = await api(`/empresas/${empresaId}/relaciones`) || [];
  const relIds = new Set(rel.map(r => r.empresa_id));
  cont.innerHTML = otras.map(e => `
    <label style="display:flex;align-items:center;gap:8px;font-size:12px;color:var(--text2);cursor:pointer">
      <input type="checkbox" class="emp-rel-chk" value="${e.id}" ${relIds.has(e.id) ? 'checked' : ''}>
      ${e.nombre_empresa} <span style="color:var(--text3);font-size:10px">(${e.prefijo || ''})</span>
    </label>`).join('');
}
async function guardarEmpresa() {
  const id = document.getElementById('emp-id').value;
  // Incluir cualquier sede escrita y no agregada aún con el botón
  const pendiente = document.getElementById('emp-sede-input').value.trim();
  if (pendiente && !empSedes.some(s => s.toLowerCase() === pendiente.toLowerCase())) {
    empSedes.push(pendiente);
    document.getElementById('emp-sede-input').value = '';
    renderEmpSedes();
  }
  const nit           = document.getElementById('emp-nit').value.trim();
  const prefijo       = document.getElementById('emp-prefijo').value.trim().toUpperCase();
  const nombre_empresa= document.getElementById('emp-nombre').value.trim();
  if (!nit||!prefijo||!nombre_empresa) {
    notif('NIT, prefijo y nombre son obligatorios','error'); return;
  }
  const logoFile = document.getElementById('emp-logo').files[0] || null;
  // El logo es obligatorio SOLO al crear (el servidor también lo valida).
  if (!id && !logoFile) {
    notif('El logo es obligatorio para crear la empresa','error'); return;
  }

  // multipart/form-data (igual que la carga de cotizaciones): incluye el logo.
  const fd = new FormData();
  fd.append('nit', nit);
  fd.append('prefijo', prefijo);
  fd.append('nombre_empresa', nombre_empresa);
  fd.append('ciudad',    document.getElementById('emp-ciudad').value||'');
  fd.append('telefono',  document.getElementById('emp-telefono').value||'');
  fd.append('correo',    document.getElementById('emp-correo').value||'');
  fd.append('direccion', document.getElementById('emp-direccion').value||'');
  fd.append('sedes', JSON.stringify(empSedes));
  if (logoFile) fd.append('logo', logoFile);

  // NO fijar Content-Type: el navegador pone el boundary del multipart.
  const res = await fetch(`${API}${id?`/empresas/${id}`:`/empresas`}`, {
    method: id?'PUT':'POST',
    headers: { 'Authorization': `Bearer ${TOKEN}` },
    body: fd
  });
  if (res.ok) {
    // En edición, reconciliar las relaciones (hermanas) con el set marcado
    if (id) {
      const relIds = [...document.querySelectorAll('#emp-relaciones-lista .emp-rel-chk:checked')].map(c => c.value);
      const relRes = await apiRaw(`/empresas/${id}/relaciones`, { method: 'PUT', body: JSON.stringify({ relacionadas: relIds }) });
      if (relRes.ok) notif('Relaciones actualizadas');
      else { const e2 = await relRes.json().catch(() => ({})); notif(e2.detail || 'Error al guardar relaciones', 'error'); }
    }
    notif(id?'Empresa actualizada':'Empresa creada');
    cerrarModal('modal-empresa');
    await cargarEmpresas(); cargarEmpresasTabla();
  } else {
    const err = await res.json();
    notif(err.detail||'Error al guardar','error');
  }
}

// ── ASIGNACIONES ──────────────────────────────────────