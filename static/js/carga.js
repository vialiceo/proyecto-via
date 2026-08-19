/* Estados de carga: barra de progreso, botones ocupados e imágenes que aparecen. */
(function () {
  "use strict";

  var barra = null;
  var avance = 0;
  var temporizador = null;

  function crearBarra() {
    if (barra) return barra;
    barra = document.createElement("div");
    barra.className = "via-barra-carga";
    barra.setAttribute("role", "progressbar");
    barra.setAttribute("aria-label", "Cargando");
    document.body.appendChild(barra);
    return barra;
  }

  /* La barra avanza sola y cada vez más lento, para que nunca llegue al 100%
     antes de que la página realmente cambie. */
  function iniciarBarra() {
    if (temporizador) return;
    crearBarra();
    avance = 0;
    barra.classList.remove("via-barra-carga--lista");
    temporizador = setInterval(function () {
      avance += (92 - avance) * 0.08;
      barra.style.width = avance + "%";
    }, 130);
  }

  function terminarBarra() {
    if (!temporizador) return;
    clearInterval(temporizador);
    temporizador = null;
    barra.style.width = "100%";
    barra.classList.add("via-barra-carga--lista");
    setTimeout(function () {
      if (!temporizador && barra) barra.style.width = "0";
    }, 350);
  }

  function esNavegacionReal(enlace) {
    if (!enlace || !enlace.href) return false;
    if (enlace.target === "_blank") return false;
    if (enlace.hasAttribute("download")) return false;
    if (enlace.origin !== window.location.origin) return false;
    var protocolo = enlace.protocol;
    if (protocolo !== "http:" && protocolo !== "https:") return false;
    /* Un ancla dentro de la misma página no recarga nada. */
    return !(enlace.pathname === window.location.pathname && enlace.hash);
  }

  document.addEventListener("click", function (evento) {
    if (evento.defaultPrevented || evento.button !== 0) return;
    if (evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return;
    var enlace = evento.target.closest("a");
    if (esNavegacionReal(enlace)) iniciarBarra();
  });

  document.addEventListener("submit", function (evento) {
    var formulario = evento.target;
    if (evento.defaultPrevented || formulario.hasAttribute("data-sin-carga")) return;

    iniciarBarra();

    var boton = formulario.querySelector('button[type="submit"], button:not([type])');
    if (boton && !boton.classList.contains("esta-cargando")) {
      /* Se marca después del envío para no bloquear el propio submit. */
      setTimeout(function () {
        boton.classList.add("esta-cargando");
        boton.setAttribute("aria-busy", "true");
      }, 0);
    }
  });

  /* Al volver con el botón "atrás" el navegador restaura la página desde caché:
     hay que devolver los botones a su estado normal. */
  window.addEventListener("pageshow", function (evento) {
    if (!evento.persisted) return;
    terminarBarra();
    document.querySelectorAll(".esta-cargando").forEach(function (elemento) {
      elemento.classList.remove("esta-cargando");
      elemento.removeAttribute("aria-busy");
    });
  });

  window.addEventListener("beforeunload", iniciarBarra);
  window.addEventListener("load", terminarBarra);

  /* Las imágenes marcadas con data-carga aparecen con un fundido cuando
     terminan de descargar, en vez de dibujarse a medias. */
  function prepararImagenes() {
    document.querySelectorAll("img[data-carga]").forEach(function (img) {
      if (img.complete && img.naturalWidth > 0) {
        img.classList.remove("via-img-cargando");
        return;
      }
      img.classList.add("via-img-cargando");
      img.addEventListener("load", function () {
        img.classList.remove("via-img-cargando");
      });
      img.addEventListener("error", function () {
        img.classList.remove("via-img-cargando");
      });
    });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", prepararImagenes);
  } else {
    prepararImagenes();
  }

  /* Expuesto para que otros scripts marquen sus propios estados de carga. */
  window.VIACarga = { iniciar: iniciarBarra, terminar: terminarBarra };
})();
