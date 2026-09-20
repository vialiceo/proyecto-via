/*
 * Interruptor de modo claro/oscuro. El tema se guarda en localStorage y se
 * aplica antes de pintar (script en el <head>); aquí solo se maneja el botón
 * del menú de perfil y se actualiza su etiqueta.
 */
(function () {
  "use strict";
  var KEY = "via-tema";
  var root = document.documentElement;
  var btn = document.getElementById("temaToggle");
  var txt = document.getElementById("temaToggleTexto");

  function esOscuro() { return root.getAttribute("data-theme") === "dark"; }

  function pintar() {
    if (txt) txt.textContent = esOscuro() ? "Modo claro" : "Modo oscuro";
    if (btn) btn.setAttribute("aria-pressed", String(esOscuro()));
  }

  if (btn) {
    btn.addEventListener("click", function (e) {
      e.stopPropagation();
      var nuevo = esOscuro() ? "light" : "dark";
      root.setAttribute("data-theme", nuevo);
      try { localStorage.setItem(KEY, nuevo); } catch (_) {}
      pintar();
    });
  }
  pintar();
})();
