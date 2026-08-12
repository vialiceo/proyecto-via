const track    = document.getElementById('carouselTrack');
const prevBtn  = document.getElementById('prevBtn');
const nextBtn  = document.getElementById('nextBtn');
const dotsWrap = document.getElementById('carouselDots');
const cards    = track.querySelectorAll('.promo-card');
const visible  = 3;
let current    = 0;
const total    = Math.ceil(cards.length / visible);

for (let i = 0; i < total; i++) {
  const dot = document.createElement('button');
  dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
  dot.setAttribute('aria-label', `Página ${i + 1}`);
  dot.addEventListener('click', () => goTo(i));
  dotsWrap.appendChild(dot);
}

function goTo(index) {
  current = Math.max(0, Math.min(index, total - 1));
  track.style.transform = `translateX(-${current * 100}%)`;
  dotsWrap.querySelectorAll('.carousel-dot').forEach((d, i) => {
    d.classList.toggle('active', i === current);
  });
}

prevBtn.addEventListener('click', () => goTo(current - 1));
nextBtn.addEventListener('click', () => goTo(current + 1));

document.getElementById('btnBuscarAno').addEventListener('click', () => {
  const ano = document.getElementById('filtroAno').value.trim();
  if (ano) window.location.href = `/usuarios/promocion/${ano}`;
});

document.getElementById('filtroAno').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('btnBuscarAno').click();
});
