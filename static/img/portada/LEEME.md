# Imágenes de la portada (ayuda.html)

Coloca aquí las fotos con EXACTAMENTE estos nombres. Si falta alguna, la tarjeta
o el hero muestran un verde de relleno (no se rompe nada).

Las rutas ya están conectadas en `static/css/ayuda.css`.

| Archivo | Dónde se ve | Tamaño recomendado | Formato / peso |
|---|---|---|---|
| `hero.jpg` | Fondo del encabezado grande (banner superior) | **1920 × 1080 px** (16:9, horizontal) | JPG, ~200–400 KB |
| `egresados.jpg` | Tarjeta "EGRESADOS" | **1200 × 675 px** (16:9) | JPG, ~100–250 KB |
| `admin.jpg` | Tarjeta "ADMINISTRADORES" | **1200 × 675 px** (16:9) | JPG, ~100–250 KB |
| `institucion.jpg` | Tarjeta "INSTITUCIÓN" | **1200 × 675 px** (16:9) | JPG, ~100–250 KB |

Notas:
- El texto del hero va a la izquierda: deja el motivo visual hacia el centro/derecha.
  En celular el hero se oscurece para que el texto blanco se lea.
- Las tarjetas llevan una capa oscura encima que se aclara al pasar el cursor
  (en celular/tablet se mantiene clara). No hay que tocar nada del CSS para eso.
- Puedes usar .png o .webp si prefieres, pero entonces cambia la extensión en las
  reglas de `static/css/ayuda.css` (busca `/static/img/portada/`).
