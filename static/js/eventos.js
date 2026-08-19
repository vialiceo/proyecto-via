const modalEvento = document.getElementById('modalEvento');
const modalEventoCerrar = document.getElementById('modalEventoCerrar');
const modalEventoTitulo = document.getElementById('modalEventoTitulo');
const formEvento = document.getElementById('formEvento');
const btnNuevoEvento = document.getElementById('btnNuevoEvento');

const URL_NUEVO = '/usuarios/eventos/nuevo';

function abrirModalEvento() {
  modalEvento.hidden = false;
}

function cerrarModalEvento() {
  modalEvento.hidden = true;
}

if (btnNuevoEvento) {
  btnNuevoEvento.addEventListener('click', () => {
    formEvento.action = URL_NUEVO;
    formEvento.reset();
    modalEventoTitulo.textContent = 'Crear evento';
    abrirModalEvento();
  });
}

document.querySelectorAll('.btn-editar-evento').forEach((boton) => {
  boton.addEventListener('click', () => {
    const { id, titulo, descripcion, categoria, lugar, fecha } = boton.dataset;
    formEvento.action = `/usuarios/eventos/${id}/editar`;
    formEvento.titulo.value = titulo;
    formEvento.descripcion.value = descripcion;
    formEvento.categoria.value = categoria;
    formEvento.lugar.value = lugar;
    formEvento.fecha_inicio.value = fecha;
    modalEventoTitulo.textContent = 'Editar evento';
    abrirModalEvento();
  });
});

if (modalEventoCerrar) modalEventoCerrar.addEventListener('click', cerrarModalEvento);
if (modalEvento) {
  modalEvento.addEventListener('click', (evento) => {
    if (evento.target === modalEvento) cerrarModalEvento();
  });
}
