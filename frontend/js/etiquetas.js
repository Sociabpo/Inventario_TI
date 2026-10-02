// ── Etiquetas para impresión (Zebra GT800, 38×25mm) ──────────────────────────
let etiquetaActual = null;

// Logo de respaldo si la empresa no tiene logo propio en backend/templates/img/
const ETIQUETA_LOGO_FALLBACK = '/logos-empresa/logo.png';

// Devuelve la URL del logo de la empresa (por prefijo) buscando en empresasCache
function _logoEmpresaUrl(empresaId) {
  const emp = (typeof empresasCache !== 'undefined' ? empresasCache : []).find(e => e.id === empresaId);
  const prefijo = emp && emp.prefijo ? emp.prefijo : null;
  return prefijo ? `/logos-empresa/logo_${prefijo}.png` : ETIQUETA_LOGO_FALLBACK;
}

// onerror: si el logo de la empresa no existe, intenta el genérico; si tampoco, oculta
const _ETQ_ONERROR = "this.onerror=null;this.src='" + ETIQUETA_LOGO_FALLBACK + "';this.addEventListener('error',function(){this.style.display='none'})";

// empresaId: id de la empresa del activo/accesorio (para usar SU logo)
function abrirEtiqueta(placa, tipo, empresaId) {
  if (!placa) { notif('Este registro no tiene placa asignada', 'error'); return; }
  const logoUrl = _logoEmpresaUrl(empresaId);
  etiquetaActual = { placa, tipo: tipo || '', empresaId: empresaId || '', logoUrl };

  const preview = document.getElementById('etiqueta-preview');
  preview.innerHTML = `
    <div class="etq-logo"><img src="${logoUrl}" alt="logo" onerror="${_ETQ_ONERROR}"></div>
    <div class="etq-qr" id="etq-qr-box"></div>
    <div class="etq-placa">${placa}</div>
  `;

  const qrBox = document.getElementById('etq-qr-box');
  qrBox.innerHTML = '';
  if (typeof QRCode === 'undefined') {
    qrBox.innerHTML = '<span style="font-size:10px;color:#c00">QR no disponible</span>';
  } else {
    new QRCode(qrBox, {
      text: placa,
      width: 70,
      height: 70,
      correctLevel: QRCode.CorrectLevel.M,
    });
  }
  abrirModal('modal-etiqueta');
}

// Abrir etiqueta desde el modal de edición (lee el registro del cache)
function _etiquetaDesdeModalActivo() {
  const id = document.getElementById('activo-id').value;
  const a = (typeof activosCache !== 'undefined' ? activosCache : []).find(x => x.id === id);
  if (a) abrirEtiqueta(a.id_placa_activo, a.tipo_activo, a.empresa_id);
}
function _etiquetaDesdeModalAccesorio() {
  const id = document.getElementById('acc-id').value;
  const a = (typeof accCache !== 'undefined' ? accCache : []).find(x => x.id === id);
  if (a) abrirEtiqueta(a.id_placa_accesorio, a.tipo_accesorio, a.empresa_id);
}

function imprimirEtiqueta() {
  if (!etiquetaActual) return;

  // QR como data URL (qrcodejs genera <img> con dataURL o <canvas>)
  const qrEl = document.querySelector('#etq-qr-box img, #etq-qr-box canvas');
  let qrSrc = '';
  if (qrEl) qrSrc = qrEl.tagName === 'CANVAS' ? qrEl.toDataURL('image/png') : qrEl.src;

  const logoAbs = window.location.origin + (etiquetaActual.logoUrl || ETIQUETA_LOGO_FALLBACK);
  const win = window.open('', '_blank', 'width=400,height=300');
  if (!win) { notif('Permite las ventanas emergentes para imprimir', 'error'); return; }

  win.document.write(`
    <html>
    <head>
      <title>Etiqueta ${etiquetaActual.placa}</title>
      <style>
        @page { size: 38mm 25mm; margin: 0; }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        html, body { width: 38mm; height: 25mm; }
        .label {
          width: 38mm; height: 25mm;
          display: flex; flex-direction: column;
          align-items: center; justify-content: space-between;
          padding: 1mm 1mm 1.5mm;
          font-family: Arial, sans-serif;
        }
        .label .logo { height: 4mm; display:flex; align-items:center; justify-content:center; }
        .label .logo img { max-height: 4mm; max-width: 30mm; object-fit: contain; }
        .label .qr { flex: 1; display:flex; align-items:center; justify-content:center; padding: 0.5mm 0; }
        .label .qr img { width: 13mm; height: 13mm; }
        .label .placa {
          font-size: 9pt; font-weight: bold; letter-spacing: 0.5px;
          font-family: 'Courier New', monospace;
        }
      </style>
    </head>
    <body>
      <div class="label">
        <div class="logo"><img src="${logoAbs}" onerror="this.style.display='none'"></div>
        <div class="qr"><img src="${qrSrc}"></div>
        <div class="placa">${etiquetaActual.placa}</div>
      </div>
      <script>
        window.onload = function() {
          setTimeout(function() { window.print(); window.close(); }, 300);
        };
      <\/script>
    </body>
    </html>
  `);
  win.document.close();
}
