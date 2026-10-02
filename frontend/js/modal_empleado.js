// ── DEVOLUCIÓN DESDE ACTIVOS / ACCESORIOS ────────────────────
async function devolverDesdeRecurso(usuarioId, placa) {
  if (!usuarioId) {
    notif('Este recurso no tiene empleado asignado','error');
    return;
  }
  const data = await api(`/usuarios/${usuarioId}`);
  if (!data?.id) {
    notif('No se encontró el empleado asignado','error');
    return;
  }
  // Abrir directamente el modal de devolución con la placa pre-seleccionada
  await _abrirModalDevolucion(null, usuarioId, placa || null);
}

let maeActivosDisp = [], maeAccDisp = [], maeSeleccionados = [];

async function abrirAsigDesdeEmpleado(empId, nombre, doc, empresaId) {
  document.getElementById('mae-empleado-id').value     = empId;
  document.getElementById('mae-empresa-id').value      = empresaId;
  document.getElementById('mae-emp-nombre').textContent = nombre;
  document.getElementById('mae-emp-info').textContent   = `Cédula: ${doc}`;
  document.getElementById('mae-title').textContent      = `Asignar equipos a ${nombre}`;
  document.getElementById('mae-responsable').value      = '';
  document.getElementById('mae-obs').value              = '';
  maeSeleccionados = [];
  actualizarMaeTags();

  // Activar tab activos
  document.querySelectorAll('.asig-tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.asig-panel').forEach(p=>p.classList.remove('active'));
  document.querySelector('.asig-tab').classList.add('active');
  document.getElementById('mae-panel-activos').classList.add('active');

  abrirModal('modal-asig-empleado');
  await cargarMaeItems(empresaId);
}

async function cargarMaeItems(empresaId) {
  const emp = empresaId || empresaActual || '';
  const params = emp ? `?empresa_id=${emp}&estado=disponible` : '?estado=disponible';

  const [activos, accesorios] = await Promise.all([
    api(`/activos${params}`),
    api(`/accesorios${params}`)
  ]);

  maeActivosDisp  = activos  || [];
  maeAccDisp      = accesorios || [];
  renderMaeLista('activos');
  renderMaeLista('accesorios');
}

function renderMaeLista(tipo) {
  const lista = document.getElementById(`mae-lista-${tipo}`);
  const items = tipo==='activos' ? maeActivosDisp : maeAccDisp;
  if (!items.length) {
    lista.innerHTML = `<div style="text-align:center;color:var(--text3);padding:16px">Sin ${tipo} disponibles</div>`;
    return;
  }
  lista.innerHTML = items.map(item => {
    const id    = tipo==='activos' ? item.id : item.id;
    const placa = tipo==='activos' ? item.id_placa_activo : item.id_placa_accesorio;
    const desc  = tipo==='activos'
      ? `${item.tipo_activo} · ${item.marca||''} ${item.modelo||''}`
      : `${item.tipo_accesorio} · ${item.marca||''} ${item.modelo||''}`;
    const empresa = item.nombre_empresa || '';
    const sel = maeSeleccionados.find(s=>s.id===id);
    return `<div class="asig-rapida-item ${sel?'selected':''}" id="mae-item-${id}"
      onclick="toggleMaeItem('${id}','${placa}','${desc.replace(/'/g,'').replace(/"/g,'')}','${tipo}')">
      <span class="item-placa">${placa}</span>
      <div class="item-desc">${desc}<div class="item-tipo">${empresa}</div></div>
      ${sel ? '<span style="color:var(--green);font-size:16px">✓</span>' : '<span style="color:var(--text3);font-size:14px">○</span>'}
    </div>`;
  }).join('');
}

function switchMaeTab(tipo, el) {
  document.querySelectorAll('.asig-tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.asig-panel').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById(`mae-panel-${tipo}`).classList.add('active');
}

function toggleMaeItem(id, placa, desc, tipo) {
  const idx = maeSeleccionados.findIndex(s=>s.id===id);
  if (idx > -1) {
    maeSeleccionados.splice(idx,1);
  } else {
    maeSeleccionados.push({id, placa, desc, tipo});
  }
  renderMaeLista('activos');
  renderMaeLista('accesorios');
  actualizarMaeTags();
}

function actualizarMaeTags() {
  const div  = document.getElementById('mae-seleccionados');
  const tags = document.getElementById('mae-tags');
  if (!maeSeleccionados.length) { div.classList.remove('visible'); return; }
  div.classList.add('visible');
  tags.innerHTML = maeSeleccionados.map(s=>`
    <span class="tag-item">${s.placa}
      <button onclick="toggleMaeItem('${s.id}','${s.placa}','${s.desc}','${s.tipo}')">×</button>
    </span>`).join('');
}

function filtrarMaeItems(tipo) {
  const q     = document.getElementById(`mae-search-${tipo}`).value.toLowerCase();
  const items = tipo==='activos' ? maeActivosDisp : maeAccDisp;
  const lista = document.getElementById(`mae-lista-${tipo}`);
  const filtrados = q ? items.filter(i => {
    const placa = (tipo==='activos'?i.id_placa_activo:i.id_placa_accesorio)||'';
    const desc  = `${tipo==='activos'?i.tipo_activo:i.tipo_accesorio} ${i.marca||''} ${i.modelo||''}`;
    return placa.toLowerCase().includes(q) || desc.toLowerCase().includes(q);
  }) : items;
  const orig = tipo==='activos' ? maeActivosDisp : maeAccDisp;
  const backup = tipo==='activos' ? maeActivosDisp : maeAccDisp;
  if (tipo==='activos') maeActivosDisp = filtrados; else maeAccDisp = filtrados;
  renderMaeLista(tipo);
  if (tipo==='activos') maeActivosDisp = backup; else maeAccDisp = backup;
}

async function confirmarAsigEmpleado() {
  const empId      = document.getElementById('mae-empleado-id').value;
  const empresaId  = document.getElementById('mae-empresa-id').value;
  const responsable= document.getElementById('mae-responsable').value.trim();
  const obs        = document.getElementById('mae-obs').value.trim();

  if (!maeSeleccionados.length) { notif('Selecciona al menos un ítem para asignar','error'); return; }
  if (!responsable)              { notif('Ingresa el nombre del responsable de entrega','error'); return; }

  const activos    = maeSeleccionados.filter(s=>s.tipo==='activos');
  const accesorios = maeSeleccionados.filter(s=>s.tipo==='accesorios');
  let errores = 0, exitos = 0;

  if (activos.length > 0) {
    // Caso: hay activos seleccionados
    // Los accesorios van dentro del primer activo; los activos restantes van solos
    for (let i = 0; i < activos.length; i++) {
      const item   = activos[i];
      const activo = maeActivosDisp.find(a=>a.id===item.id) || activosCache.find(a=>a.id===item.id);
      // Solo el primer activo lleva los accesorios seleccionados
      const accsParaEsteActivo = i === 0 ? accesorios.map(s=>s.id) : [];
      const res = await apiRaw('/asignaciones', { method:'POST', body: JSON.stringify({
        empresa_id: empresaId || activo?.empresa_id,
        id_activo: item.id,
        id_usuario: empId,
        accesorios_ids: accsParaEsteActivo,
        responsable_entrega: responsable,
        responsable_recibe: document.getElementById('mae-emp-nombre').textContent,
        observaciones: obs||null
      })});
      if (res.ok) {
        const data = await res.json();
        await apiRaw(`/actas/${data.acta_id}/generar-pdf`, {method:'POST'});
        exitos += (i === 0 ? 1 + accesorios.length : 1);
      } else errores++;
    }
  } else if (accesorios.length > 0) {
    // Caso: solo accesorios, sin activos → asignar-lote
    const primerAcc    = maeAccDisp.find(a=>a.id===accesorios[0].id) || accCache.find(a=>a.id===accesorios[0].id);
    const empresaIdAcc = empresaId || primerAcc?.empresa_id;
    const res = await apiRaw('/accesorios/asignar-lote', { method:'POST', body: JSON.stringify({
      empresa_id: empresaIdAcc,
      id_usuario: empId,
      accesorios_ids: accesorios.map(s=>s.id),
      responsable_entrega: responsable,
      responsable_recibe: document.getElementById('mae-emp-nombre').textContent,
      observaciones: obs||null
    })});
    if (res.ok) exitos += accesorios.length;
    else errores += accesorios.length;
  }

  if (exitos > 0)  notif(`${exitos} ítem(s) asignado(s) correctamente — Actas PDF generadas`);
  if (errores > 0) notif(`${errores} ítem(s) no pudieron asignarse`,'error');

  cerrarModal('modal-asig-empleado');
  maeSeleccionados = [];
  cargarActivos(); cargarAccesorios(); cargarUsuarios(); cargarDashboard();
}

// Cerrar modal con Escape (se mantiene: es una pulsación intencional, no un clic accidental)
document.addEventListener('keydown', e => {
  if (e.key==='Escape') document.querySelectorAll('.modal-overlay.open').forEach(m=>m.classList.remove('open'));
});
// NOTA: el cierre por clic fuera del modal (en el backdrop) se eliminó a propósito
// para evitar perder datos del formulario por un clic accidental. Los modales solo
// se cierran con la X o con el botón Cancelar/Cerrar.

// ── RECURSOS DEL EMPLEADO (ver + devolver) ────────────
let recursosEmpData = null;

async function abrirRecursosEmpleado(empId, nombre, doc, empresaId) {
  document.getElementById('remp-emp-nombre').textContent = nombre;
  document.getElementById('remp-emp-info').textContent   = `Cédula: ${doc}`;
  document.getElementById('remp-body').innerHTML =
    '<div style="text-align:center;color:var(--text3);padding:30px">Cargando recursos...</div>';
  document.getElementById('remp-btn-devolver').style.display = 'none';
  abrirModal('modal-recursos-empleado');

  const data = await api(`/asignaciones/usuario/${empId}/items-asignados`);
  recursosEmpData = data;

  if (!data || (!data.activos?.length && !data.accesorios?.length && !data.en_custodia?.length)) {
    document.getElementById('remp-body').innerHTML =
      '<div style="text-align:center;color:var(--text3);padding:30px">Este empleado no tiene recursos asignados ni en custodia actualmente.</div>';
    return;
  }

  let html = '';

  if (data.activos?.length) {
    html += `<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--text3);margin-bottom:8px;font-weight:600">Activos (${data.activos.length})</div>`;
    html += data.activos.map(a => `
      <div class="remp-item">
        <div class="remp-item-left">
          <span class="mono-tag">${a.id_placa_activo}</span>
          <div class="remp-item-desc">
            <div style="font-size:12px;font-weight:600;color:var(--text)">${a.tipo_activo}${a.marca?' · '+a.marca:''} ${a.modelo||''}</div>
            ${a.serial ? `<div style="font-size:10px;color:var(--text3)">S/N: ${a.serial}</div>` : ''}
            ${a.procesador ? `<div style="font-size:10px;color:var(--text3)">${a.procesador}${a.memoria_ram?' · '+a.memoria_ram:''}</div>` : ''}
          </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px">
          <button class="btn btn-ghost btn-sm" style="color:var(--purple);border-color:rgba(167,139,255,0.3)" onclick="cerrarModal('modal-recursos-empleado');abrirHojaVida('${a.id}')"><i class="ti ti-id-badge"></i> Hoja de vida</button>
          <span class="badge asignado">Asignado</span>
        </div>
      </div>`).join('');
    html += '<div style="margin-bottom:14px"></div>';
  }

  if (data.accesorios?.length) {
    html += `<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:var(--text3);margin-bottom:8px;font-weight:600">Accesorios (${data.accesorios.length})</div>`;
    html += data.accesorios.map(a => `
      <div class="remp-item">
        <div class="remp-item-left">
          <span class="mono-tag" style="color:var(--purple);background:rgba(167,139,255,0.1)">${a.id_placa_accesorio}</span>
          <div class="remp-item-desc">
            <div style="font-size:12px;font-weight:600;color:var(--text)">${a.tipo_accesorio}${a.marca?' · '+a.marca:''} ${a.modelo||''}</div>
            ${a.serial ? `<div style="font-size:10px;color:var(--text3)">S/N: ${a.serial}</div>` : ''}
          </div>
        </div>
        <span class="badge mantenimiento">Asignado</span>
      </div>`).join('');
  }

  // ── En custodia (responsable de recursos DISPONIBLES, no en uso) ──
  if (data.en_custodia?.length) {
    html += `<div style="font-size:10px;text-transform:uppercase;letter-spacing:1px;color:#2DD4BF;margin:16px 0 8px;font-weight:600">🛡 En custodia (${data.en_custodia.length}) — disponibles, bajo su responsabilidad</div>`;
    html += data.en_custodia.map(a => `
      <div class="remp-item" style="border-left:2px solid #2DD4BF">
        <div class="remp-item-left">
          <span class="mono-tag" style="color:#2DD4BF;background:rgba(45,212,191,0.1)">${a.placa}</span>
          <div class="remp-item-desc">
            <div style="font-size:12px;font-weight:600;color:var(--text)">${a.tipo || (a.tipo_recurso==='activo'?'Activo':'Accesorio')}${a.marca?' · '+a.marca:''} ${a.modelo||''}</div>
            ${a.ubicacion ? `<div style="font-size:10px;color:var(--text3)">📍 ${a.ubicacion}</div>` : ''}
          </div>
        </div>
        <span class="badge disponible">Disponible · custodia</span>
      </div>`).join('');
  }

  document.getElementById('remp-body').innerHTML = html;

  // Mostrar botón devolver si tiene recursos y tiene permiso
  if (hasPermiso('asignaciones.devolver') && (data.activos?.length || data.accesorios?.length)) {
    document.getElementById('remp-btn-devolver').style.display = '';
    document.getElementById('remp-btn-devolver').onclick = () => {
      cerrarModal('modal-recursos-empleado');
      _abrirModalDevolucion(null, empId, null);
    };
  }
}