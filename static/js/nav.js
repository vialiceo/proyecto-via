
const navToggle  = document.getElementById('navToggle');
const sidebarNav = document.getElementById('sidebarNav');

if (navToggle && sidebarNav) {
  navToggle.addEventListener('click', () => {
    sidebarNav.classList.toggle('open');
  });
}