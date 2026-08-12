const btnAgregarContacto = document.getElementById('btnAgregarContacto');
const listaContactos = document.getElementById('listaContactos');
const plantillaContacto = document.getElementById('plantillaContacto');

if (btnAgregarContacto && listaContactos && plantillaContacto) {
  btnAgregarContacto.addEventListener('click', () => {
    listaContactos.appendChild(plantillaContacto.content.cloneNode(true));
  });
}
