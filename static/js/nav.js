/* Menú lateral: en escritorio está siempre visible; en móvil se abre y cierra. */

const sidebarNav = document.getElementById('sidebarNav');
const navToggle  = document.getElementById('navToggle');
const navAbrir   = document.getElementById('navAbrir');
const navFondo   = document.getElementById('navFondo');

if (sidebarNav) {
  const marcarEstado = (abierto) => {
    sidebarNav.classList.toggle('open', abierto);
    if (navFondo) navFondo.hidden = !abierto;
    [navToggle, navAbrir].forEach((b) => {
      if (b) b.setAttribute('aria-expanded', String(abierto));
    });
    /* Con el menú abierto, el fondo no debe poder desplazarse. */
    document.body.classList.toggle('nav-abierto', abierto);
  };

  const abrir  = () => marcarEstado(true);
  const cerrar = () => marcarEstado(false);

  if (navAbrir) navAbrir.addEventListener('click', abrir);
  if (navToggle) navToggle.addEventListener('click', () => {
    marcarEstado(!sidebarNav.classList.contains('open'));
  });
  if (navFondo) navFondo.addEventListener('click', cerrar);

  /* Al tocar un enlace del menú se navega: cerrarlo evita que quede abierto
     encima de la página nueva si el navegador restaura desde caché. */
  sidebarNav.querySelectorAll('a').forEach((enlace) => {
    enlace.addEventListener('click', cerrar);
  });

  document.addEventListener('keydown', (evento) => {
    if (evento.key === 'Escape' && sidebarNav.classList.contains('open')) {
      cerrar();
      if (navAbrir) navAbrir.focus();
    }
  });

}
