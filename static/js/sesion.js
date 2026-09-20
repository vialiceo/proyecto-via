/* Contador de sesión: muestra el tiempo restante arriba a la derecha. La sesión
   dura un tiempo FIJO desde el login (no se renueva al navegar ni al hacer
   cambios), así que el contador solo cuenta hacia abajo hasta la hora de
   expiración que fija el servidor. Al llegar a cero, cierra la sesión. */
(function () {
  "use strict";

  var meta = document.querySelector('meta[name="session-expira"]');
  if (!meta) return;
  /* El servidor manda la hora exacta de expiración en segundos (epoch). */
  var expiraMs = parseInt(meta.content, 10) * 1000;
  if (!expiraMs || isNaN(expiraMs)) return;

  var pill = document.createElement('div');
  pill.className = 'sesion-contador';
  pill.setAttribute('title', 'Tiempo restante de sesión');
  pill.innerHTML =
    '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">' +
    '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>' +
    '<span class="sesion-tiempo">--:--</span>';
  document.body.appendChild(pill);
  var spanTiempo = pill.querySelector('.sesion-tiempo');

  function formato(seg) {
    var m = Math.floor(seg / 60), s = seg % 60;
    return (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
  }

  function restanteSeg() {
    return Math.round((expiraMs - Date.now()) / 1000);
  }

  function pintar() {
    var r = Math.max(restanteSeg(), 0);
    spanTiempo.textContent = formato(r);
    /* Últimos 5 minutos: se resalta en rojo. */
    pill.classList.toggle('sesion-contador--alerta', r <= 300);
  }

  function tick() {
    if (restanteSeg() <= 0) {
      window.location.href = '/logout';
      return;
    }
    pintar();
  }

  pintar();
  setInterval(tick, 1000);
})();
