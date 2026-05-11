
const navToggle  = document.getElementById('navToggle');
const sidebarNav = document.getElementById('sidebarNav');

navToggle.addEventListener('click', () => {
  sidebarNav.classList.toggle('open');
});