

const profileBtn      = document.getElementById('profileBtn');
const profileDropdown = document.getElementById('profileDropdown');

if (profileBtn && profileDropdown) {
  profileBtn.addEventListener('click', () => {
    const open = profileDropdown.classList.toggle('open');
    profileBtn.setAttribute('aria-expanded', open);
    profileDropdown.setAttribute('aria-hidden', !open);
  });

  document.addEventListener('click', (e) => {
    if (!profileBtn.contains(e.target) && !profileDropdown.contains(e.target)) {
      profileDropdown.classList.remove('open');
      profileBtn.setAttribute('aria-expanded', false);
      profileDropdown.setAttribute('aria-hidden', true);
    }
  });
}