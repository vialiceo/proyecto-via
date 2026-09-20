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
  if (ano) window.location.href = `/usuarios/directorio?anio_promocion=${ano}`;
});

document.getElementById('filtroAno').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') document.getElementById('btnBuscarAno').click();
});

/*
 * --- Al hacer clic en una promoción del carrusel, sus egresados se despliegan
 * aquí mismo (sin cambiar de página). El clic en un egresado abre el modal.
 */
const inline       = document.getElementById('promoInline');
const inlineLista   = document.getElementById('promoInlineLista');
const inlineTitulo  = document.getElementById('promoInlineTitulo');
const inlineVerTodos = document.getElementById('promoInlineVerTodos');

function iconoGenericoEg() {
  return '<img src="/static/img/avatar.svg" alt="Sin foto" />';
}

function crearTarjetaEgresado(e) {
  const card = document.createElement('button');
  card.type = 'button';
  card.className = 'egresado-card';
  ['id', 'nombre', 'foto', 'anio', 'tecnico', 'profesion', 'residencia', 'estudio', 'correo', 'frase', 'destacado']
    .forEach((k) => { if (e[k] !== '' && e[k] != null) card.dataset[k] = e[k]; });
  if (e.destacado === '1') {
    const estrella = document.createElement('span');
    estrella.className = 'egresado-destacado';
    estrella.title = 'Egresado destacado';
    estrella.textContent = '★';
    card.appendChild(estrella);
  }
  const foto = document.createElement('div');
  foto.className = 'egresado-foto';
  foto.innerHTML = e.foto ? `<img src="${e.foto}" alt="Foto de ${e.nombre}" onerror="this.src='/static/img/avatar.svg'" />` : iconoGenericoEg();
  const nombre = document.createElement('span');
  nombre.className = 'egresado-nombre';
  nombre.textContent = e.nombre;
  const prof = document.createElement('span');
  prof.className = 'egresado-profesion';
  prof.textContent = e.tecnico || e.profesion || '';
  card.append(foto, nombre, prof);
  card.addEventListener('click', () => {
    if (window.abrirModalEgresado) window.abrirModalEgresado(card.dataset, card);
  });
  return card;
}

if (inline) {
  cards.forEach((tarjeta) => {
    tarjeta.addEventListener('click', async (evento) => {
      evento.preventDefault(); /* no navega: despliega aquí mismo */
      const anio = tarjeta.dataset.anio;
      inlineTitulo.textContent = `Egresados promoción ${anio}`;
      inlineVerTodos.href = `/usuarios/directorio?anio_promocion=${anio}`;
      inlineLista.innerHTML = '<p class="promocion-vacio">Cargando…</p>';
      inline.hidden = false;
      inline.scrollIntoView({ behavior: 'smooth', block: 'start' });
      try {
        const resp = await fetch(`/usuarios/promociones/${anio}/egresados`);
        const data = await resp.json();
        inlineLista.innerHTML = '';
        if (!data.egresados.length) {
          inlineLista.innerHTML = '<p class="promocion-vacio">Todavía no hay egresados registrados en esta promoción.</p>';
          return;
        }
        data.egresados.forEach((eg) => inlineLista.appendChild(crearTarjetaEgresado(eg)));
      } catch (err) {
        inlineLista.innerHTML = '<p class="promocion-vacio">No se pudieron cargar los egresados.</p>';
      }
    });
  });
}
