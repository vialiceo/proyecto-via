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
/*
 * Se saca el modal al <body>: dentro de .main-content (que tiene transform por
 * la animacion de entrada) su position:fixed se centra respecto al documento y
 * no a la pantalla. En el body queda centrado en la ventana.
 */
if (modal && modal.parentElement !== document.body) document.body.appendChild(modal);
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

/*
 * Filas de esqueleto: barras grises que laten mientras llega la respuesta.
 * Da sensación de que algo está pasando en vez de una pausa en blanco.
 */
function filasEsqueleto(n) {
  let html = '';
  for (let i = 0; i < n; i++) {
    html += '<li class="bitacora-skel"><span class="via-esqueleto via-esqueleto--linea"></span></li>';
  }
  return html;
}

function cargarBitacora(usuarioId) {
  if (!listaBitacora) return;
  listaBitacora.innerHTML = filasEsqueleto(3);
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

  /*
   * El modal aparece de una vez con los campos marcados como "cargando":
   * así el clic responde al instante y el usuario ve que va en camino, en
   * lugar de una pausa antes de que salga la ventana.
   */
  if (formEditar) formEditar.classList.add('form-cargando');
  if (modal) modal.hidden = false;
  if (listaBitacora) listaBitacora.innerHTML = filasEsqueleto(3);

  apiFetch(`/api/v1/admin/usuarios/${usuarioId}`)
    .then((usuario) => {
      formEditar.nombre.value = usuario.nombre || '';
      formEditar.correo.value = usuario.correo || '';
      formEditar.usuario.value = usuario.usuario || '';
      formEditar.rol.value = usuario.rol || 'egresado';
      formEditar.anio_promocion.value = usuario.anio_promocion || '';
      formEditar.tecnico_id.value = usuario.tecnico_id || '';
      formEditar.classList.remove('form-cargando');
      cargarBitacora(usuarioId);
    })
    .catch((error) => {
      cerrarModal();
      alert(error.message);
    });
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
      .then((datos) => {
        if (datos.enviado_por_correo) {
          alert(`Contraseña temporal enviada al correo de la persona (${datos.correo}).`);
        } else {
          alert(`Se restableció la contraseña.\n\nEl correo no está configurado, así que entrégala tú por un canal seguro:\nContraseña temporal: ${datos.password_temporal}`);
        }
      })
      .catch((error) => alert(error.message));
  });
}

/* --- Menú de 3 puntos por fila: "Gestionar" y "Ver perfil" ----------------- */
document.querySelectorAll('.btn-tres-puntos').forEach((boton) => {
  boton.addEventListener('click', (evento) => {
    evento.stopPropagation();
    const lista = boton.nextElementSibling;
    const estabaAbierto = !lista.hidden;
    document.querySelectorAll('.fila-menu-lista').forEach((l) => (l.hidden = true));
    lista.hidden = estabaAbierto;
    boton.setAttribute('aria-expanded', String(!estabaAbierto));
  });
});

/* Un clic en cualquier parte cierra los menús abiertos. */
document.addEventListener('click', () => {
  document.querySelectorAll('.fila-menu-lista').forEach((l) => (l.hidden = true));
});

/* "Ver perfil": abre el modal de egresado con los datos de la fila (todo, admin). */
document.querySelectorAll('.btn-ver-perfil').forEach((boton) => {
  boton.addEventListener('click', () => {
    const fila = boton.closest('tr');
    if (fila && window.abrirModalEgresado) window.abrirModalEgresado(fila.dataset, fila);
  });
});

/* Si desde el modal se destaca/quita a alguien, refleja la estrella en su fila. */
document.addEventListener('destacado-cambiado', (evento) => {
  const fila = document.querySelector(`tr[data-id="${evento.detail.id}"]`);
  const avatar = fila ? fila.querySelector('.celda-avatar') : null;
  if (!avatar) return;
  let estrella = avatar.querySelector('.celda-avatar-estrella');
  if (evento.detail.destacado && !estrella) {
    estrella = document.createElement('span');
    estrella.className = 'celda-avatar-estrella';
    estrella.title = 'Destacado';
    estrella.textContent = '★';
    avatar.appendChild(estrella);
  } else if (!evento.detail.destacado && estrella) {
    estrella.remove();
  }
});
