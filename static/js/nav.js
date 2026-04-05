/* ============================================================
   nav.js — /static/js/nav.js
   Toggle del sidebar nav (compartido en todas las páginas
   del área de usuarios).
   ============================================================ */

const navToggle  = document.getElementById('navToggle');
const sidebarNav = document.getElementById('sidebarNav');

navToggle.addEventListener('click', () => {
  sidebarNav.classList.toggle('open');
});