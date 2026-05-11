
const hamburger   = document.getElementById('hamburger')
const navbarLinks = document.querySelector('.navbar-links')

hamburger.addEventListener('click', () => {
  navbarLinks.classList.toggle('open')
})


const cards = document.querySelectorAll('.perfil-card')

const observer = new IntersectionObserver((entries) => {
  entries.forEach(entry => {
    if (entry.isIntersecting) {
      entry.target.classList.add('visible')
      observer.unobserve(entry.target)
    }
  })
}, { threshold: 0.15 })

cards.forEach(card => observer.observe(card))