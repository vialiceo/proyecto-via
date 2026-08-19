/* Accesibilidad de los modales: foco atrapado, Escape y clic fuera.

   Sin esto, un modal abierto es solo un div encima: con Tab el foco se va a
   los enlaces de la pagina de atras, que el usuario no ve, y no hay forma de
   cerrarlo con el teclado. */
(function () {
  "use strict";

  var FOCALIZABLES = 'a[href], button:not([disabled]), textarea, input:not([type="hidden"]), select, [tabindex]:not([tabindex="-1"])';

  function focalizables(modal) {
    return Array.prototype.filter.call(
      modal.querySelectorAll(FOCALIZABLES),
      function (el) {
        return el.offsetWidth > 0 || el.offsetHeight > 0 || el === document.activeElement;
      }
    );
  }

  function estaAbierto(modal) {
    return !modal.hasAttribute("hidden");
  }

  /* Se guarda quien tenia el foco para devolverselo al cerrar: si no, el foco
     salta al principio de la pagina y el usuario pierde el hilo. */
  var focoPrevio = new WeakMap();

  function alAbrir(modal) {
    focoPrevio.set(modal, document.activeElement);
    document.body.classList.add("modal-abierto");
    var lista = focalizables(modal);
    if (lista.length) lista[0].focus();
  }

  function alCerrar(modal) {
    document.body.classList.remove("modal-abierto");
    var previo = focoPrevio.get(modal);
    if (previo && document.contains(previo)) previo.focus();
    focoPrevio.delete(modal);
  }

  function cerrar(modal) {
    if (!estaAbierto(modal)) return;
    modal.setAttribute("hidden", "");
  }

  document.querySelectorAll(".modal-fondo").forEach(function (modal) {
    /* El HTML se abre y cierra quitando y poniendo `hidden` desde otros
       scripts; en vez de reescribirlos, se observa ese atributo. */
    new MutationObserver(function () {
      if (estaAbierto(modal)) alAbrir(modal);
      else alCerrar(modal);
    }).observe(modal, { attributes: true, attributeFilter: ["hidden"] });

    /* Clic en el fondo, pero no dentro de la caja. */
    modal.addEventListener("mousedown", function (evento) {
      if (evento.target === modal) cerrar(modal);
    });

    modal.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape") {
        evento.stopPropagation();
        cerrar(modal);
        return;
      }

      if (evento.key !== "Tab") return;

      var lista = focalizables(modal);
      if (!lista.length) return;

      var primero = lista[0];
      var ultimo = lista[lista.length - 1];

      /* El ciclo: desde el ultimo, Tab vuelve al primero; desde el primero,
         Shift+Tab salta al ultimo. Asi el foco nunca sale del modal. */
      if (evento.shiftKey && document.activeElement === primero) {
        evento.preventDefault();
        ultimo.focus();
      } else if (!evento.shiftKey && document.activeElement === ultimo) {
        evento.preventDefault();
        primero.focus();
      }
    });

    if (estaAbierto(modal)) alAbrir(modal);
  });
})();
