/* ============================================================
   admin.js — /static/js/admin.js
   Modal de gestión de cuentas en /admin/usuarios, hablando con la
   API REST (/api/v1/admin/usuarios/...). Todo mutation lleva el
   header X-CSRFToken que exige Flask-WTF.
   ============================================================ */

const csrfMeta = document.querySelector('meta[name="csrf-token"]');
const csrfToken = csrfMeta ? csrfMeta.content : null;

function apiFetch(url, opciones = {}) {
  const headers = Object.assign({ 'Content-Type': 'application/json' }, opciones.headers || {});
  if (csrfToken) headers['X-CSRFToken'] = csrfToken;

  return fetch(url, { ...opciones, headers }).then(async (respuesta) => {
    const cuerpo = await respuesta.json().catch(() => ({}));
    if (!respuesta.ok) throw new Error(cuerpo.error || 'Ocurrió un error inesperado.');
    return cuerpo.data;
  });
}

const modal = document.getElementById('modalGestion');
const modalCerrar = document.getElementById('modalCerrar');
const formEditar = document.getElementById('formEditarUsuario');
const btnActivar = document.getElementById('btnActivar');
const btnDesactivar = document.getElementById('btnDesactivar');
const btnResetPassword = document.getElementById('btnResetPassword');
const listaBitacora = document.getElementById('listaBitacora');

let usuarioActualId = null;

function cerrarModal() {
  if (modal) modal.hidden = true;
  usuarioActualId = null;
}

function cargarBitacora(usuarioId) {
  if (!listaBitacora) return;
  listaBitacora.innerHTML = '<li>Cargando…</li>';
  apiFetch(`/api/v1/admin/usuarios/${usuarioId}/bitacora`)
    .then((entradas) => {
      if (!entradas.length) {
        listaBitacora.innerHTML = '<li>Sin actividad registrada.</li>';
        return;
      }
      listaBitacora.innerHTML = '';
      entradas.forEach((entrada) => {
        const li = document.createElement('li');
        li.textContent = `${entrada.accion} — ${entrada.detalle || ''}`;
        listaBitacora.appendChild(li);
      });
    })
    .catch(() => { listaBitacora.innerHTML = '<li>No se pudo cargar la actividad.</li>'; });
}

function abrirModal(usuarioId) {
  usuarioActualId = usuarioId;
  apiFetch(`/api/v1/admin/usuarios/${usuarioId}`)
    .then((usuario) => {
      formEditar.nombre.value = usuario.nombre || '';
      formEditar.correo.value = usuario.correo || '';
      formEditar.usuario.value = usuario.usuario || '';
      formEditar.rol.value = usuario.rol || 'egresado';
      formEditar.anio_promocion.value = usuario.anio_promocion || '';
      formEditar.tecnico_id.value = usuario.tecnico_id || '';
      modal.hidden = false;
      cargarBitacora(usuarioId);
    })
    .catch((error) => alert(error.message));
}

document.querySelectorAll('.btn-gestionar').forEach((boton) => {
  boton.addEventListener('click', () => abrirModal(boton.dataset.usuarioId));
});

if (modalCerrar) modalCerrar.addEventListener('click', cerrarModal);
if (modal) modal.addEventListener('click', (evento) => { if (evento.target === modal) cerrarModal(); });

if (formEditar) {
  formEditar.addEventListener('submit', (evento) => {
    evento.preventDefault();
    const datos = Object.fromEntries(new FormData(formEditar).entries());
    datos.anio_promocion = datos.anio_promocion ? Number(datos.anio_promocion) : null;
    datos.tecnico_id = datos.tecnico_id ? Number(datos.tecnico_id) : null;

    apiFetch(`/api/v1/admin/usuarios/${usuarioActualId}`, { method: 'PUT', body: JSON.stringify(datos) })
      .then(() => window.location.reload())
      .catch((error) => alert(error.message));
  });
}

function cambiarEstado(estado) {
  if (!usuarioActualId) return;
  apiFetch(`/api/v1/admin/usuarios/${usuarioActualId}/estado`, {
    method: 'PATCH',
    body: JSON.stringify({ estado }),
  })
    .then(() => window.location.reload())
    .catch((error) => alert(error.message));
}

if (btnActivar) btnActivar.addEventListener('click', () => cambiarEstado('activo'));
if (btnDesactivar) {
  btnDesactivar.addEventListener('click', () => {
    if (confirm('¿Desactivar esta cuenta? La persona no podrá iniciar sesión.')) cambiarEstado('inactivo');
  });
}

if (btnResetPassword) {
  btnResetPassword.addEventListener('click', () => {
    if (!usuarioActualId) return;
    if (!confirm('¿Restablecer la contraseña de esta cuenta?')) return;

    apiFetch(`/api/v1/admin/usuarios/${usuarioActualId}/reset-password`, { method: 'POST' })
      .then((datos) => alert(`Contraseña temporal: ${datos.password_temporal}\n\nCompártela por un canal seguro.`))
      .catch((error) => alert(error.message));
  });
}
