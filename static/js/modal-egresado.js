/*
 * Modal de detalle de un egresado. Compartido por el directorio, la página de
 * promociones (vía tarjetas) y el panel de administración (vía "Ver perfil").
 *
 * Expone window.abrirModalEgresado(datos, fuente) para que otras vistas (p. ej.
 * la tabla de admin o el carrusel del inicio) lo abran con sus propios datos.
 */
(function () {
  const modal = document.getElementById('modalEgresado');
  if (!modal) return;

  /*
   * El modal se saca al <body>. Si queda dentro de .main-content —que lleva un
   * transform por la animación de entrada— su position:fixed se vuelve relativo
   * a ese contenedor y la caja aparece centrada en el documento, no en la
   * pantalla (se veía "descentrado" en páginas largas). En el body no hay
   * ningún ancestro con transform, así que centra respecto a la ventana.
   */
  if (modal.parentElement !== document.body) document.body.appendChild(modal);

  const foto = document.getElementById('modalEgresadoFoto');
  const nombre = document.getElementById('modalEgresadoNombre');
  const profesion = document.getElementById('modalEgresadoProfesion');
  const datos = document.getElementById('modalEgresadoDatos');
  const frase = document.getElementById('modalEgresadoFrase');
  const insignia = document.getElementById('modalEgresadoInsignia');
  const adminNota = document.getElementById('modalEgresadoAdminNota');
  const mensaje = document.getElementById('modalEgresadoMensaje');
  const btnDestacar = document.getElementById('btnDestacar');

  const esAdmin = modal.dataset.admin === '1';
  let fuenteActual = null; /* tarjeta/fila que abrió el modal (para reflejar cambios) */

  function iconoGenerico() {
    /* Imagen por defecto cuando el egresado no subió foto. */
    return '<img src="/static/img/avatar.svg" alt="Sin foto" />';
  }

  /* Filas del detalle: solo se muestran las que traen valor. El orden es fijo. */
  const FILAS = [
    ['anio', 'Promoción'],
    ['tecnico', 'Datos de estudio'],
    ['estudio', 'Estudió en'],
    ['profesion', 'Trabajo / profesión'],
    ['residencia', 'Reside en'],
    ['correo', 'Correo'],
  ];

  function pintarDestacado(estaDestacado) {
    if (insignia) insignia.hidden = !estaDestacado;
    if (btnDestacar) {
      btnDestacar.classList.toggle('activo', estaDestacado);
      const texto = btnDestacar.querySelector('.btn-destacar-texto');
      if (texto) texto.textContent = estaDestacado ? 'Quitar destacado' : 'Destacar alumno';
    }
  }

  function abrirModalEgresado(d, fuente) {
    fuenteActual = fuente || null;

    foto.innerHTML = d.foto ? `<img src="${d.foto}" alt="Foto de ${d.nombre}" onerror="this.src='/static/img/avatar.svg'" />` : iconoGenerico();
    nombre.textContent = d.nombre || '';
    if (profesion) profesion.textContent = d.profesion || '';
    if (frase) frase.textContent = d.frase ? `“${d.frase}”` : '';

    if (datos) {
      datos.innerHTML = '';
      FILAS.forEach(([clave, etiqueta]) => {
        const valor = (d[clave] || '').toString().trim();
        if (!valor) return;
        const dt = document.createElement('dt');
        dt.textContent = etiqueta;
        const dd = document.createElement('dd');
        if (clave === 'correo') {
          const a = document.createElement('a');
          a.href = `mailto:${valor}`;
          a.textContent = valor;
          dd.appendChild(a);
        } else {
          dd.textContent = valor;
        }
        datos.appendChild(dt);
        datos.appendChild(dd);
      });
    }

    if (adminNota) adminNota.hidden = !d.esadmin;

    pintarDestacado(d.destacado === '1' || d.destacado === 1 || d.destacado === true);
    if (btnDestacar) {
      btnDestacar.hidden = !esAdmin;
      btnDestacar.disabled = false;
    }

    if (mensaje) {
      const esYoMismo = modal.dataset.yo && modal.dataset.yo === String(d.id);
      mensaje.hidden = Boolean(esYoMismo);
      mensaje.href = `/usuarios/mensajes/con/${d.id}`;
    }

    modal.hidden = false;
  }

  /* Tarjetas de egresado (directorio / promociones): abren el modal con su dataset. */
  document.querySelectorAll('.egresado-card').forEach((tarjeta) => {
    tarjeta.addEventListener('click', () => abrirModalEgresado(tarjeta.dataset, tarjeta));
  });

  /* Destacar / quitar destacado (solo admins, botón solo presente en páginas admin). */
  if (btnDestacar) {
    btnDestacar.addEventListener('click', async () => {
      if (!fuenteActual) return;
      const id = fuenteActual.dataset.id;
      const csrf = document.querySelector('meta[name="csrf-token"]')?.content || '';
      btnDestacar.disabled = true;
      try {
        const resp = await fetch(`/usuarios/directorio/${id}/destacar`, {
          method: 'POST',
          headers: { 'X-CSRFToken': csrf },
        });
        const data = await resp.json();
        if (!resp.ok || !data.ok) throw new Error(data.error || 'Error');
        const estaDestacado = Boolean(data.destacado);
        fuenteActual.dataset.destacado = estaDestacado ? '1' : '0';
        pintarDestacado(estaDestacado);
        fuenteActual.dispatchEvent(new CustomEvent('destacado-cambiado', {
          bubbles: true, detail: { id, destacado: estaDestacado },
        }));
      } catch (e) {
        alert('No se pudo cambiar el destacado. Intenta de nuevo.');
      } finally {
        btnDestacar.disabled = false;
      }
    });
  }

  function cerrarModal() { modal.hidden = true; }
  const cerrar = document.getElementById('modalEgresadoCerrar');
  if (cerrar) cerrar.addEventListener('click', cerrarModal);
  modal.addEventListener('click', (e) => { if (e.target === modal) cerrarModal(); });
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !modal.hidden) cerrarModal();
  });

  window.abrirModalEgresado = abrirModalEgresado;
})();
