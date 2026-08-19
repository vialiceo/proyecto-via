const modal = document.getElementById('modalEgresado');
const modalCerrar = document.getElementById('modalEgresadoCerrar');
const modalFoto = document.getElementById('modalEgresadoFoto');
const modalNombre = document.getElementById('modalEgresadoNombre');
const modalProfesion = document.getElementById('modalEgresadoProfesion');
const modalFrase = document.getElementById('modalEgresadoFrase');
const modalMensaje = document.getElementById('modalEgresadoMensaje');

function iconoGenerico() {
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.2">
    <circle cx="12" cy="8" r="4"/><path d="M4 20c0-4 3.6-7 8-7s8 3 8 7"/>
  </svg>`;
}

document.querySelectorAll('.egresado-card').forEach((tarjeta) => {
  tarjeta.addEventListener('click', () => {
    const { id, nombre, foto, profesion, frase } = tarjeta.dataset;

    modalFoto.innerHTML = foto ? `<img src="${foto}" alt="Foto de ${nombre}" />` : iconoGenerico();
    modalNombre.textContent = nombre;
    modalProfesion.textContent = profesion || '';
    modalFrase.textContent = frase ? `“${frase}”` : '';
    if (modalMensaje) modalMensaje.href = `/usuarios/mensajes/con/${id}`;

    modal.hidden = false;
  });
});

function cerrarModal() {
  modal.hidden = true;
}

if (modalCerrar) modalCerrar.addEventListener('click', cerrarModal);
if (modal) {
  modal.addEventListener('click', (evento) => {
    if (evento.target === modal) cerrarModal();
  });
}
document.addEventListener('keydown', (evento) => {
  if (evento.key === 'Escape' && modal && !modal.hidden) cerrarModal();
});
