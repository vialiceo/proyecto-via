const btnAgregarContacto = document.getElementById('btnAgregarContacto');
const listaContactos = document.getElementById('listaContactos');
const plantillaContacto = document.getElementById('plantillaContacto');

if (btnAgregarContacto && listaContactos && plantillaContacto) {
  btnAgregarContacto.addEventListener('click', () => {
    listaContactos.appendChild(plantillaContacto.content.cloneNode(true));
  });
}

const vistaLectura = document.getElementById('vistaLectura');
const vistaEdicion = document.getElementById('vistaEdicion');
const btnEditarPerfil = document.getElementById('btnEditarPerfil');
const btnCancelarEdicion = document.getElementById('btnCancelarEdicion');

if (vistaLectura && vistaEdicion && btnEditarPerfil) {
  btnEditarPerfil.addEventListener('click', () => {
    vistaLectura.hidden = true;
    vistaEdicion.hidden = false;
  });
}

if (vistaLectura && vistaEdicion && btnCancelarEdicion) {
  btnCancelarEdicion.addEventListener('click', () => {
    vistaEdicion.hidden = true;
    vistaLectura.hidden = false;
  });
}
