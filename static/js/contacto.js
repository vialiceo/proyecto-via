/* ============================================================
   contacto.js — /static/js/contacto.js
   Lógica de la página de contacto y equipo de trabajo.
   ============================================================ */

/* ── Tabs de navegación entre secciones ── */
const tabs     = document.querySelectorAll('.page-tab')
const secciones = {
  contacto: document.getElementById('contacto'),
  equipo:   document.getElementById('equipo')
}

tabs.forEach(tab => {
  tab.addEventListener('click', (e) => {
    // Marcar tab activo
    tabs.forEach(t => t.classList.remove('active'))
    tab.classList.add('active')
  })
})

/* Resalta el tab al hacer scroll hasta la sección */
const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      const id = entry.target.id
      tabs.forEach(t => {
        t.classList.toggle('active', t.dataset.section === id)
      })
    }
  })
}, { threshold: 0.4 })

Object.values(secciones).forEach(s => observer.observe(s))

/* ── Animación de entrada de tarjetas del equipo ── */
const miembros = document.querySelectorAll('.miembro-card')

const cardObserver = new IntersectionObserver((entries) => {
  entries.forEach((entry, i) => {
    if (entry.isIntersecting) {
      entry.target.style.transitionDelay = `${i * 0.08}s`
      entry.target.classList.add('visible')
      cardObserver.unobserve(entry.target)
    }
  })
}, { threshold: 0.15 })

miembros.forEach(m => {
  m.style.opacity = '0'
  m.style.transform = 'translateY(20px)'
  m.style.transition = 'opacity 0.4s ease, transform 0.4s ease, box-shadow 0.22s ease'
  cardObserver.observe(m)
})

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.miembro-card.visible').forEach(m => {
    m.style.opacity = '1'
    m.style.transform = 'translateY(0)'
  })
})

/* Clase visible activa la animación */
const style = document.createElement('style')
style.textContent = `.miembro-card.visible { opacity: 1 !important; transform: translateY(0) !important; }`
document.head.appendChild(style)

