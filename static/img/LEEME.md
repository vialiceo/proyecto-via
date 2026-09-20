#Donde va cada imagen

Todo lo que esté dentro de `static/` se sirve solo: si el archivo existe en
`static/img/escudo/escudo-liceo.png`, el navegador lo pide como
`/static/img/escudo/escudo-liceo.png`. no hay que registrar nada en python


## 1. Escudo — `static/img/escudo/`

**Nombre exacto: `escudo-liceo.png`**

Se muestra en la barra superior de todas las páginas y **ya es un botón**: está
envuelto en un `<a href="https://ieliceotame.edu.co" target="_blank">`, así que
al hacerle clic abre el sitio de la institución en otra pestaña.

- Tamaño en pantalla: 46×46 px
- Sube el archivo a **138×138 px** (el triple, para pantallas Retina)
- PNG **con fondo transparente**, o mejor aún SVG
- Si lo haces SVG, cámbiale el nombre en las 3 plantillas
  (`index.html`, `usuarios/_layout.html`, `contacto.html`) a `escudo-liceo.svg`

Si el archivo **no existe**, no se rompe nada: el `onerror` borra la `<img>` y
se sigue viendo el escudo dibujado con CSS que hay ahora

Para cambiar a dónde apunta el botón, edita el `href` en esas 3 plantillas.

---

## 2. Favicon — `static/img/favicon/`

`favicon.svg` (escudo verde con la V dorada) y enlazado en las
7 plantillas que tienen `<head>`. 



```html
<link rel="icon" href="/static/img/favicon/favicon.ico" sizes="any" />
<link rel="apple-touch-icon" href="/static/img/favicon/apple-touch-icon.png" />
```

---

## 3. Portadas de promociones — `static/img/promociones/`

**Nombre exacto: el año y punto jpg.** `2019.jpg`, `2020.jpg`, `2021.jpg`…

Salen en el carrusel de la página principal. La plantilla las arma sola con el
año que venga de la base de datos, así que **no hay que tocar código**: basta
con dejar el archivo con el nombre correcto.

- Proporción **4:3** (así está el recuadro)
- **1200×900 px** 
- JPG con calidad 80 — pesa poco y se ve bien
- Máximo ~300 KB por foto

Si falta el archivo, aparece el recuadro verde que dice "PROMOCIÓN". No es un
error

---

## 4. Fotos del equipo — `static/img/equipo/`

Para las tarjetas de `contacto.html`, que hoy dicen "Nombre Apellido".

- Cuadradas, **600×600 px**
- JPG, máximo ~200 KB
- Nombre sugerido: `nombre-apellido.jpg` en minúsculas y con guiones

Estas sí hay que enlazarlas a mano en `templates/contacto.html`.

---

## 5. Fotos de perfil — `static/uploads/perfiles/`

**Esta carpeta no se toca a mano.** La llena la aplicación cuando un egresado
sube su foto desde *Mi perfil → Cambiar foto*.

El nombre lo genera el servidor: `usuario_<id>_<12 caracteres al azar>.jpg`.
El azar es a propósito — si el nombre fuera predecible, cualquiera podría
adivinar la URL de la foto de otra persona.

| Parámetro | Valor |
|---|---|
| Extensiones | `png`, `jpg`, `jpeg`, `webp` |
| Peso máximo | 3 MB (`MAX_CONTENT_LENGTH_MB` en `.env`) |
| Tamaño recomendado | cuadrada, mínimo 400×400 px |
| Se muestra a | 40 px (barra superior), 72 px (tarjetas), ~140 px (perfil) |
| Validación | extensión **y** cabecera del archivo |
| Foto anterior | se borra al subir una nueva |

La carpeta se crea sola al arrancar la app (`create_app()` hace `makedirs`), así
que funciona en una copia recién clonada aunque git no guarde la carpeta.

---

## 6. Fotos de los graduados del archivo

**Todavía no existe.** La tabla `graduados` no tiene columna `foto`.

Hoy la foto vive en `usuarios.foto`, o sea que solo tiene foto quien ya tiene
cuenta. Un graduado de 1985 que está en el archivo pero nunca pidió cuenta no
puede tener retrato.

Para agregarlo hace falta: una columna `foto` en `graduados`, su migración, un
campo de subida en la ficha del archivo, y decidir si el admin puede subir
varias de golpe. Es un trabajo aparte, no un ajuste.
