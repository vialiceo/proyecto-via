# V.I.A — Vinculación Integral de Alumnos

Sistema de seguimiento a egresados de la Institución Educativa Liceo Tame.
Los egresados mantienen su perfil (profesión, contacto, dónde viven, dónde
estudiaron, una frase para su promoción), la institución administra las
cuentas y modera comentarios y solicitudes de soporte.

Roles: **egresado**, **administrador**, **institución**.

## Cómo correr el proyecto

La base de datos se llama **`egresados`**. Si en tu servidor tiene otro nombre,
cambia `MYSQL_DB` en el `.env`: el código lee ese valor y no tiene el nombre
escrito en ninguna parte.

**1. Entorno de Python**

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

**2. Base de datos y usuario de la aplicación**

Antes de correrlo, abre `database/crear_usuario_mysql.sql` y cambia
`CAMBIA_ESTA_CLAVE` por una contraseña tuya (aparece dos veces).

```bash
mysql -u root -p < database/crear_usuario_mysql.sql
```

Crea la base `egresados` y el usuario `via_app`, que solo tiene permisos
`SELECT/INSERT/UPDATE/DELETE` sobre esa base. No se usa `root` a propósito: si
alguien lograra inyectar SQL, `via_app` no puede leer ni borrar otras bases del
servidor ni cambiar la configuración de MySQL.

**3. Configuración**

```bash
copy .env.example .env
```

Y escribe en el `.env` la misma contraseña del paso 2:

```
MYSQL_PASSWORD=la-que-pusiste
```

Genera también una `SECRET_KEY` real:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**4. Tablas y datos de prueba**

```bash
mysql -u root -p egresados < database/schema.sql
```
```bash
mysql -u root -p egresados < database/datos.sql
```

Si ya tenías la base creada de antes, `schema.sql` agrega las tablas nuevas pero
no toca la tabla `usuarios` que ya existía. Para eso está la migración:

```bash
mysql -u root -p egresados < database/migracion_graduados.sql
```

Añade `usuarios.cedula` y `usuarios.graduado_id` con sus índices. Se corre una
sola vez; el archivo explica qué error significa que ya estaba aplicada.

**5. Arrancar**

```bash
python run.py
```

En <http://localhost:5000>. Si algo de MySQL quedó mal, la app **no muestra un
error genérico**: sale una página con el código que devolvió MySQL y los pasos
concretos para arreglarlo (ver *Manejo de errores* más abajo).

Cuentas de prueba (ver `database/datos.sql`, contraseñas solo para desarrollo):

| Usuario  | Contraseña          | Rol           |
|----------|----------------------|---------------|
| admin    | CambiarAhora2026!    | administrador |
| jgomez   | Egresado123!         | egresado      |

Ambas piden cambiar la contraseña en el primer ingreso.

## Variables de entorno (`.env`, ver `.env.example`)

| Variable | Para qué |
|---|---|
| `SECRET_KEY` | Firma de sesiones/CSRF. Generar una real con `secrets.token_hex()`. |
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` | Conexión a MySQL. `MYSQL_USER` es `via_app`, no `root`. |
| `MYSQL_DB` | Nombre de la base: **`egresados`**. Es el único lugar donde está escrito; cambiarlo aquí basta para apuntar a otra base. |
| `MYSQL_POOL_SIZE` | Tamaño del pool de conexiones (ver `backend/db.py`). |
| `RATELIMIT_STORAGE_URI` | `memory://` alcanza para ~5000 usuarios en una sola instancia. Con varias instancias detrás de un balanceador, usar Redis: `redis://host:6379/0`. |
| `CACHE_TYPE` / `CACHE_REDIS_URL` | `SimpleCache` vive en el proceso Python — si se despliega con más de un worker, cambiar a `RedisCache` + `CACHE_REDIS_URL` para que todos vean la misma caché. |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` | SMTP real. Si se dejan vacías, el correo no se envía: queda registrado en el log (modo desarrollo). |
| `MAX_CONTENT_LENGTH_MB` | Límite de tamaño para la foto de perfil. |
| `SOLICITUDES_API_KEY` | Clave para `POST /api/v1/solicitudes-cuenta`. Si se deja vacía, ese endpoint queda cerrado (responde 401 siempre) y solo funciona el formulario interno. |

## Arquitectura del backend

App factory en `backend/app.py` / `backend/__init__.py`. Las extensiones
(`Flask-Login`, `Flask-Limiter`, `Flask-Caching`, `Flask-WTF`, `Flask-Mail`)
se instancian sin `app` en `backend/extensions.py` y se enlazan en
`create_app()` — así cada blueprint puede importarlas sin generar imports
circulares con `backend/app.py`.

Blueprints:

| Blueprint    | Prefijo      | Archivo               | Qué cubre |
|--------------|--------------|------------------------|-----------|
| `public`     | `/`          | `backend/routes.py`    | Portada, ayuda, contacto/soporte, aviso legal, solicitud de cuenta |
| `auth`       | `/`          | `backend/auth.py`      | Login, logout, recuperar contraseña, cambio obligatorio |
| `usuarios`   | `/usuarios`  | `backend/perfil.py`    | Perfil propio, foto, comentarios, página de promoción |
| `admin`      | `/admin`     | `backend/admin.py`     | Dashboard, cuentas, bandeja de solicitudes, archivo de graduados y tickets de soporte |
| `api`        | `/api/v1`    | `backend/api.py`       | JSON para el panel de admin y la entrada de solicitudes externas |

`backend/models.py` es la única capa que toca SQL (sin ORM: a esta escala el
cuello de botella nunca va a ser cuántas líneas de SQL se escriben, y tener
el query real a la vista permite correr `EXPLAIN` sobre él directamente).
`backend/experiencia.py` separa la validación/armado del "perfil extendido"
de las rutas HTTP en `perfil.py`. `backend/utils.py` reúne lo transversal:
hashing, tokens, control de acceso por rol, tareas en segundo plano, correo,
paginación y validación server-side.

## Base de datos

Ver `database/schema.sql`. Motor InnoDB, MySQL 8+.

| Tabla | Para qué |
|---|---|
| `graduados` | Archivo institucional: quién se graduó, en qué año, con qué técnico y bajo qué acta. **No son cuentas.** Es un registro histórico permanente que puede tener miles de filas sin que ninguna de esas personas use el portal. |
| `usuarios` | Cuentas. Nadie se registra solo: o las crea el admin, o nacen de una solicitud aprobada. `cedula` es `UNIQUE` y `graduado_id` apunta al archivo. |
| `solicitudes_cuenta` | Cola de aprobación. Una persona pide acceso; un admin la contrasta contra `graduados` y decide. |
| `perfil_extendido` | 1 fila por usuario: lo que el propio egresado edita (profesión, dónde vive, dónde estudió, fecha de nacimiento, frase). Separada de `usuarios` a propósito para que el admin nunca pise por accidente lo que el usuario mantiene. |
| `contactos` | Métodos de contacto del egresado, 1 a N (puede tener varios: celular, WhatsApp, redes). |
| `tecnicos` | Catálogo de programas técnicos del Liceo. |
| `comentarios` | Feed de la comunidad, moderable por admin. |
| `soporte_tickets` | Tickets creados desde `/contacto`, con la respuesta del administrador, quién la escribió y cuándo. Se atienden en `/admin/soporte`. |
| `password_reset_tokens` | Se guarda el hash del token, nunca el token en claro. |
| `bitacora` | Auditoría: login, cambios de contraseña, acciones de admin sobre una cuenta. |
| `solicitudes` | Certificados/constancias que pide un egresado, con estado (pendiente/en_proceso/aprobada/rechazada/cancelada). |
| `conversaciones` / `mensajes` | Mensajería 1 a 1 entre cualquier par de usuarios. `conversaciones` fija el par (usuario_uno_id, usuario_dos_id) una sola vez por `UNIQUE`; los mensajes cuelgan de ahí. |
| `eventos` | Eventos institucionales. Solo un administrador los crea/edita; todos los pueden ver. |

`perfil_extendido.fecha_nacimiento` se guarda como fecha, no como "edad": la
edad cambia con el tiempo y la app la calcula al vuelo (`utils.calcular_edad`).

### Índices (por qué existe cada uno, no "por si acaso")

- `usuarios.uq_usuarios_correo` / `uq_usuarios_usuario` / `uq_usuarios_cedula` —
  el login acepta correo, usuario o cédula, así que los tres son `UNIQUE` y
  los tres se resuelven por índice. `cedula` admite `NULL` (MySQL permite
  varios `NULL` en un índice `UNIQUE`) para las cuentas viejas que no la tienen.
- `usuarios.uq_usuarios_graduado (graduado_id)` — impide que dos cuentas
  reclamen al mismo graduado del archivo.
- `graduados.uq_graduados_cedula` — clave natural del archivo; es la que hace
  que reimportar el mismo CSV actualice en vez de duplicar
  (`ON DUPLICATE KEY UPDATE`).
- `graduados.uq_graduados_nombre_anio (nombre, anio_promocion)` — para las
  actas viejas que no traen cédula, el par nombre+año es lo único que
  identifica a la persona.
- `graduados.ix_graduados_anio_nombre (anio_promocion, nombre)` — listar una
  promoción completa en orden alfabético, que es como se consulta un archivo.
- `solicitudes_cuenta.ix_soli_cuenta_estado_fecha (estado, creado_en)` — la
  bandeja del admin: pendientes primero, más antiguas arriba.
- `solicitudes_cuenta.ix_soli_cuenta_cedula` / `ix_soli_cuenta_correo` — antes
  de aceptar una solicitud se comprueba que esa persona no tenga ya una en
  revisión.
- `usuarios.ix_usuarios_rol_estado_promocion (rol, estado, anio_promocion)` —
  cubre dos cosas con el mismo índice: el filtro por rol/estado que usa el
  panel de admin constantemente, y el `GROUP BY anio_promocion` que arma las
  "promociones recientes" del carrusel (el prefijo `rol, estado` sirve para
  ambos queries).
- `usuarios.ix_usuarios_tecnico_promocion (tecnico_id, anio_promocion)` —
  reporte típico "egresados de tal técnico en tal promoción".
- `contactos.ix_contactos_usuario` — el único acceso a esta tabla es "dame
  los contactos del usuario X".
- `password_reset_tokens.uq_reset_token_hash` — validar un token entrante es
  una búsqueda directa por su hash.
- `comentarios.ix_comentarios_estado_fecha (estado, creado_en)` — cubre el
  feed público (visibles, más recientes primero) y la cola de moderación.
- `soporte_tickets.ix_soporte_estado_fecha (estado, creado_en)` — bandeja de
  admin filtrando por estado, ordenada por fecha.
- `bitacora.ix_bitacora_usuario_fecha (usuario_id, creado_en)` — historial de
  actividad de una cuenta en la vista de admin.
- `solicitudes.ix_solicitudes_usuario_fecha (usuario_id, creado_en)` — "mis
  solicitudes" ordenadas por fecha; `ix_solicitudes_estado_fecha` cubre la
  cola de un admin filtrando por estado.
- `conversaciones.uq_conv_par (usuario_uno_id, usuario_dos_id)` — evita crear
  dos conversaciones para el mismo par de usuarios; también sirve para
  buscar "la conversación entre A y B" directo por índice.
- `mensajes.ix_mensajes_conversacion_fecha (conversacion_id, creado_en)` —
  el hilo completo de una conversación, en orden.
- `eventos.ix_eventos_fecha (fecha_inicio)` — listar próximos/pasados
  ordenados por fecha.

## Cómo nace una cuenta (archivo → solicitud → usuario)

Nadie se registra por su cuenta y nadie carga 3000 cuentas de golpe. Son tres
cosas distintas, y por eso son tres tablas distintas:

1. **El archivo (`graduados`).** Es el libro de grados digitalizado. La
   institución lo carga desde `/admin/graduados`, a mano o importando un CSV
   con columnas `cedula, nombre, anio_promocion, tecnico, libro_acta`. Vive
   aunque esa persona nunca entre al portal. Reimportar el mismo archivo no
   duplica: la cédula es clave única y la fila se actualiza.
2. **La solicitud (`solicitudes_cuenta`).** El egresado entra a
   `/solicitar-cuenta`, pone cédula, nombre, correo, año y (opcional) técnico.
   Al guardarla, el sistema busca sola una coincidencia en `graduados`: primero
   por cédula, y si no, por nombre exacto + año. Recibe un correo con su número
   de radicado. El formulario está limitado a 5 envíos por hora por IP.
3. **La cuenta (`usuarios`).** En `/admin/solicitudes-cuenta` el admin ve cada
   solicitud con un aviso verde ("coincide con Fulano, acta L-2019-014") o rojo
   ("no se encontró a esta persona en el archivo"). Para aprobar una sin
   coincidencia hay que marcar explícitamente "añadirla también al archivo":
   así el archivo nunca queda desactualizado en silencio. Al aprobar se genera
   el nombre de usuario, se crea la cuenta con contraseña temporal y
   `forzar_cambio_password = 1`, y se envían las credenciales por correo.
   Rechazar exige un motivo, que también se le envía.

Por qué el nombre no es la llave: los nombres se repiten, se escriben con y sin
tilde, y cambian. El nombre sirve para **verificar** (que un humano confirme que
es la persona del acta), nunca para **unir** filas. Lo que une es
`usuarios.graduado_id`.

Por qué la cédula no es la `PRIMARY KEY`: si lo fuera, ese dato personal se
copiaría a las diez tablas que referencian a `usuarios`, aparecería en las URLs
y en los logs, y corregir un dígito mal digitado obligaría a un `UPDATE` en
cascada. La clave primaria es el `id` autoincremental —un número sin significado,
como pide la Ley 1581 de 2012 al minimizar el tratamiento de datos personales— y
la cédula es una columna más, `UNIQUE`, que se puede corregir sin tocar nada.

### Solicitudes desde una plataforma externa

Si más adelante la institución quiere recoger las solicitudes desde otro sitio
(un formulario propio, otra plataforma), no hace falta duplicar la lógica:

```
POST /api/v1/solicitudes-cuenta
X-API-Key: <SOLICITUDES_API_KEY>
Content-Type: application/json

{"cedula": "1116803311", "nombre": "Laura Martínez",
 "correo": "laura@example.com", "anio_promocion": 2019}
```

Responde `201` con `{"id": ..., "estado": "pendiente", "coincide_con_archivo": true}`.
Cae en la misma bandeja, con las mismas validaciones y la misma verificación
contra el archivo; solo cambia `origen`, que queda como `api` para poder
distinguirlas. La clave se compara con `hmac.compare_digest` y el endpoint está
exento de CSRF (un servidor externo no puede tener el token de sesión) pero
limitado a 60 solicitudes por hora.

## Seguridad

- **Contraseñas**: `werkzeug.security` (scrypt), nunca texto plano. Cuentas
  creadas por el admin quedan con `forzar_cambio_password = 1`.
- **Recuperación de contraseña**: el mensaje es idéntico exista o no la
  cuenta con ese correo/usuario — no delata qué cuentas existen
  (`backend/auth.py`, ruta `/recuperar`).
- **CSRF**: Flask-WTF activo globalmente. Cada `<form>` lleva
  `{{ csrf_token() }}`; las llamadas fetch del panel de admin mandan el
  header `X-CSRFToken` (leído del `<meta name="csrf-token">` de
  `_layout.html`).
- **Rate limiting**: Flask-Limiter con límites más estrictos en las rutas
  sensibles (`/login`, `/recuperar`, creación de cuentas, reseteo de
  contraseña) además del límite global.
- **Redirect abierto**: el parámetro `?next=` del login se valida con
  `utils.redireccion_segura` — solo acepta rutas propias del sitio
  (empiezan por `/`, no por `//`), para que nadie pueda mandar un link de
  login que termine llevando a un sitio externo.
- **Privacidad entre egresados**: correo, teléfono y demás métodos de
  contacto **no se muestran a otros egresados** — la consulta de
  `/usuarios/promocion/<anio>` solo trae nombre, foto, profesión y frase
  (ver `models.listar_egresados_por_promocion`). El resto queda solo para el
  dueño de la cuenta y el admin. Ver `templates/aviso_legal.html`.
- **Consultas parametrizadas** en toda la capa de datos (`backend/models.py`
  vía `backend/db.py`) — nunca se concatena SQL con datos del usuario.

## Caché y tareas asíncronas

Flask-Caching (`SimpleCache` en memoria por defecto; cambiar `CACHE_TYPE` a
Redis en `.env` si algún día hay más de un worker). Lo que se cachea y por
qué:

- Estadísticas del dashboard de admin (2 min) — no cambian tan rápido como
  para recalcularlas en cada carga.
- Feed de comentarios (30s) — no necesita ser exacto al segundo; se invalida
  al publicar/moderar un comentario.
- Egresados por promoción (2 min) y promociones recientes del carrusel
  (3 min) — una sola consulta por año calcula tarjeta + datos del pop-up
  para todos los egresados de esa promoción a la vez, sin ir a buscar cada
  tarjeta por separado.

Tareas en segundo plano (`utils.encolar_tarea`, un `ThreadPoolExecutor`
compartido): enviar correo y escribir en la bitácora no bloquean la
respuesta HTTP. A la escala de un colegio (~5000 usuarios) esto alcanza sin
necesitar un broker externo tipo Celery/Redis; si en algún momento hace
falta escalar a varios workers de verdad, `encolar_tarea()` es el único
punto que habría que cambiar por un `.delay()` de Celery/RQ.

Si `MAIL_SERVER` no está configurado en `.env`, los correos no se envían de
verdad: quedan registrados en el log del servidor (modo desarrollo).

## Frontend

- **Tipografías**: Cinzel (display), Playfair Display (serif), Lato (cuerpo).
- **Colores**: verde institucional + dorado (variables en
  `static/css/usuarios/Base usuarios.css`).
- **`templates/usuarios/_layout.html`**: plantilla base del área de usuarios
  (sidebar a la derecha, topbar con accesos rápidos, mensajes flash, footer).
  Las páginas nuevas (`admin`, `perfiles`, `registro`, `perfil`,
  `comentarios`, `promocion`) la extienden con `{% extends %}`; `index.html`,
  `login.html`, `contacto.html`, `ayuda.html` y `recuperar.html` son
  independientes (no la usan) porque ya traían su propio maquetado.
- **CSS**: un archivo por página bajo `static/css/`; lo compartido entre
  varias páginas del área de usuarios vive en `static/css/usuarios/`
  (`Base usuarios.css` = variables + sidebar + footer; `layout.css` = topbar
  + menú de perfil + mensajes flash, para no repetirlo en cada página nueva).
- **JS**: un archivo por página bajo `static/js/`, sin build step.
- **Encabezados**: cada página tiene exactamente un `<h1>` y la jerarquía baja
  sin saltos (`h1 → h2 → h3`). Los íconos son SVG escritos en línea con
  `stroke="currentColor"`, así que toman el color del texto y cambian solos en
  hover, sin peticiones extra ni librerías de íconos.

## Responsive (móvil y tablet)

Probado en 320, 375, 414, 768, 1024 y 1280 px sobre las 18 páginas del sitio:
**108 combinaciones sin desbordamiento horizontal.**

El punto de quiebre es **768 px**. Por encima, el menú lateral está fijo a la
derecha y ocupa 120 px; por debajo se esconde y se abre con un botón.

### El menú en móvil

Aquí había un fallo real: el botón de hamburguesa vivía **dentro** de
`.sidebar-nav`, y en móvil ese panel se desplaza fuera de la pantalla con
`transform: translateX(100%)`. El botón se iba con él, así que en un teléfono
no había forma de abrir el menú — Mis solicitudes, Mensajes, Eventos,
Configuración y Cerrar sesión quedaban inalcanzables.

Ahora hay dos botones distintos:

| Botón | Dónde vive | Cuándo se ve |
|---|---|---|
| `#navAbrir` (`.nav-abrir`) | Fuera del panel, fijo arriba a la derecha | Solo ≤768px y con el menú cerrado |
| `#navToggle` (`.nav-toggle`) | Dentro del panel | Siempre; en móvil solo se alcanza con el menú abierto |

`static/js/nav.js` mantiene los dos sincronizados con `aria-expanded`, muestra
un fondo oscuro (`#navFondo`) que cierra al tocarlo, bloquea el scroll del
fondo con `body.nav-abierto`, cierra con `Escape` y al tocar cualquier enlace,
y cierra solo si la ventana se agranda por encima de 768px (si no, el fondo
oscuro se quedaría tapando la página al girar el teléfono).

### `static/css/movil.css`

Hoja aparte, cargada de última en las 7 plantillas con `<head>` propio. Al ir
al final gana por orden de cascada sin necesidad de `!important`.

| Regla | Por qué |
|---|---|
| `min-height: 44px` en botones y campos | Es el mínimo que un dedo acierta con fiabilidad. Antes había botones de 28 y 29 px. |
| `font-size: 16px` en los campos | Por debajo de 16px, Safari en iPhone hace **zoom automático** al enfocar el campo y descuadra la página. |
| `flex-direction: column` en filas de filtros | Dos campos lado a lado en 375px quedan inservibles. |
| `overflow-x: auto` en las tablas | La tabla ancha se desplaza dentro de su caja; la página nunca se mueve de lado. |
| `padding-right: 68px` en la topbar | Deja hueco para el botón flotante del menú. |
| Modales a `calc(100vw - 1.6rem)` | Un modal centrado y pequeño no cabe en un teléfono. |

Dos detalles de CSS que parecen rebuscados y no lo son:

- `select:not([multiple]):not([size])` en vez de `select` a secas. Un `select`
  suelto tiene especificidad (0,0,1) y **pierde** contra `.filtros-form select`
  (0,1,1) de la hoja de cada página. Los `:not()` la suben lo justo para ganar
  sin recurrir a `!important`.
- `input:not([type="checkbox"])…` en vez de `input[type="text"]`. Varios campos
  del proyecto se escriben como `<input name="x">` sin atributo `type`; son de
  texto por defecto, pero `input[type="text"]` **no los alcanza** si el
  atributo no está escrito.

### Qué falta para móvil

Los modales siguen sin `role="dialog"` ni atrapar el foco del teclado.

## Tickets de soporte

Cualquiera puede escribir desde `/contacto` sin tener cuenta. Cada mensaje se
guarda en `soporte_tickets` y aparece en la bandeja del administrador en
`/admin/soporte`.

Antes de esta ronda los tickets **se guardaban pero no se podian ver**: existia
la tabla y la API, pero ninguna pagina HTML los mostraba, asi que quien escribia
por Contacto nunca recibia respuesta.

### El ciclo de un ticket

| Estado | Que significa |
|---|---|
| `abierto` | Recien llegado, nadie lo ha mirado |
| `en_proceso` | Alguien lo esta atendiendo (se marca a mano) |
| `cerrado` | Respondido, o cerrado sin responder |

La lista se ordena con `FIELD(estado, 'abierto', 'en_proceso', 'cerrado')` y
dentro de cada estado por fecha **ascendente**: lo urgente primero, y dentro de
lo urgente lo que lleva mas tiempo esperando.

### Responder

`responder_ticket()` guarda la respuesta, el autor, la fecha y pone el estado en
`cerrado` **en un solo UPDATE**. Si fueran dos operaciones separadas, un fallo
entre ambas dejaria el ticket contestado pero abierto, o cerrado sin respuesta.

Al responder se dispara un correo al remitente con el texto de la respuesta.
El envio va en segundo plano (`encolar_tarea`), asi que el administrador no
espera al servidor de correo.

Un ticket ya cerrado no se puede responder otra vez: la ruta lo rechaza antes
de tocar la base.

### Rutas

| Ruta | Metodo | Que hace |
|---|---|---|
| `/admin/soporte` | GET | Bandeja, con filtro por estado y busqueda por nombre/correo/asunto |
| `/admin/soporte/<id>/responder` | POST | Guarda la respuesta, envia el correo y cierra |
| `/admin/soporte/<id>/estado` | POST | Cambia el estado a mano |
| `/api/v1/soporte` | POST | Crea un ticket (lo usa el formulario de Contacto) |
| `/api/v1/admin/soporte` | GET | Los mismos datos en JSON |

## Correos

`utils.enviar_correo_async(destinatario, asunto, cuerpo)` es el unico punto de
envio. Se usa en 8 sitios: contrasenas temporales al crear una cuenta, al
aprobar una solicitud, al resetear una contrasena, recuperacion de contrasena,
aviso de ticket nuevo y respuesta de soporte.

### Sin servidor de correo tambien funciona

Con `MAIL_SERVER` vacio en el `.env` **no falla**: escribe el correo completo
—remitente, destinatario, asunto y cuerpo— en `logs/correos.log` y en la
consola. Ese archivo hace de bandeja de salida: ahi se lee la contrasena
temporal de una cuenta recien aprobada sin montar SMTP.

Esto antes estaba escrito pero **no se veia**. Un `logging.Logger` recien
creado no tiene manejadores y su nivel efectivo es WARNING, asi que todos los
`logger.info` de la aplicacion —correos incluidos— se perdian en silencio.
`_configurar_logging()` en `backend/app.py` lo arregla:

| Destino | Que recibe |
|---|---|
| Consola | Todo, mientras corre `python run.py` |
| `logs/via.log` | Todo, rotando cada 1 MB con 3 respaldos |
| `logs/correos.log` | Solo los correos (filtro por `extra={"es_correo": True}`) |

La carpeta `logs/` esta en `.gitignore`.

### Enviar correos de verdad

Llena estas variables del `.env` y reinicia. Con Gmail hay que usar una
"contrasena de aplicacion", no la del correo:

```
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=tucorreo@gmail.com
MAIL_PASSWORD=la-contrasena-de-aplicacion
MAIL_DEFAULT_SENDER=tucorreo@gmail.com
```

## Pruebas

Hay dos capas, y hacen cosas distintas:

| Capa | Con qué | Qué comprueba |
|---|---|---|
| Python | test client de Flask | Rutas, validaciones, permisos y mensajes. Rápido, sin navegador. |
| Playwright | Chromium de verdad | Lo que el usuario ve y toca: clics, formularios, foco del teclado, medidas en pantalla. |

```bash
npm test
```

Levanta Flask si no está corriendo, inicia sesión una vez por rol y ejecuta
**34 pruebas** en escritorio y móvil (Pixel 5).

### Por qué se guarda la sesión en disco

`/login` admite **10 intentos por minuto**. Cuando cada prueba hacía su propio
login, la suite se bloqueaba a sí misma a partir de la sexta y fallaba por 429,
no por lo que estaba comprobando. `tests/auth.setup.js` entra una vez por rol y
guarda las cookies en `tests/.sesiones/`; el resto las reutiliza.

**El límite es correcto y no se tocó** — es la defensa contra fuerza bruta. Lo
que estaba mal eran las pruebas.

### Límites que importan para la sustentación

| Ruta | Límite |
|---|---|
| `POST /login` | 10 por minuto |
| `POST /solicitar-cuenta` | **5 por hora** |
| `POST /contacto` | 6 por hora |
| `POST /api/v1/solicitudes-cuenta` | 60 por hora |

El de solicitar cuenta es el que puede sorprender: si en la demostración se
llena el formulario más de cinco veces desde el mismo computador, el sexto
intento recibe la página de "Demasiados intentos". Las pruebas lo detectan y
se marcan como omitidas en vez de fallar.

### Qué cubren

`tests/portada.spec.js` — la portada pública, su jerarquía de encabezados, el
escudo como enlace externo y que no se desborde.
`tests/cuenta.spec.js` — solicitud de cuenta de punta a punta (formulario →
bandeja del admin), edición de perfil, cambio de correo con su validación de
duplicados, y los parámetros del campo de foto.
`tests/admin.spec.js` — ciclo completo de un ticket (Contacto → bandeja →
respuesta → cerrado), control de acceso, y la paginación con sus filtros.
`tests/accesibilidad.spec.js` — `role="dialog"`, foco atrapado, Escape,
páginas de error, y el menú de móvil.

Al fallar algo se guarda captura y traza en `test-results/`:

```bash
npx playwright show-report tests/reporte
```

## Skills instaladas

En `.claude/skills/` (14 MB). Son paquetes de instrucciones para Claude Code,
no dependencias de la aplicación: **Flask corre igual sin ellas**.

| Skill | Origen | Para qué |
|---|---|---|
| `ui-ux-pro-max`, `ui-styling`, `design`, `design-system`, `brand`, `banner-design`, `slides` | [nextlevelbuilder/ui-ux-pro-max-skill](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) | Paletas, tipografías, guías de UX, tokens de diseño |
| `impeccable` | [pbakaus/impeccable](https://github.com/pbakaus/impeccable) | Auditar y pulir interfaces: jerarquía visual, accesibilidad, motion |

Aparte, dos herramientas de línea de comandos:

- **Playwright** ([microsoft/playwright](https://github.com/microsoft/playwright)) —
  instalado como dependencia de desarrollo. Es lo que corre `npm test`.
- **skillui** ([amaancoderx/npxskillui](https://github.com/amaancoderx/npxskillui)) —
  se usa con `npx`, no se instala. Extrae el sistema de diseño del proyecto
  por análisis estático:

  ```bash
  npx skillui --dir . --out docs/diseno --name "V.I.A Liceo Tame" --no-skill
  ```

  El resultado está en `docs/diseno/v-i-a-liceo-tame-design/DESIGN.md`:
  20 colores, la retícula de 4px, 5 animaciones y las variables CSS que ya
  usa el proyecto. Sirve de punto de partida para la ronda de diseño.

## Manejo de errores

Todos los errores pasan por `_registrar_manejadores_error()` en
`backend/app.py`, que decide el formato según la ruta: si la URL empieza por
`/api/`, responde JSON; si no, renderiza `templates/error.html`.

| Código | Cuándo |
|---|---|
| 403 | El rol de la cuenta no alcanza para esa sección |
| 404 | La URL no existe |
| 413 | La foto subida pasa de `MAX_CONTENT_LENGTH_MB` |
| 429 | Se pasó un límite de peticiones (login, API pública) |
| 500 | Cualquier excepción no controlada |

`templates/error.html` extiende `_auth_card.html`, así que reusa el marco
visual del login (tarjeta blanca sobre verde) sin depender de la sesión ni de
la base de datos — importante, porque un 500 puede venir justamente de que la
base no responde.

### Errores de MySQL

Hay un handler aparte para `mysql.connector.Error`. En **desarrollo**
(`FLASK_ENV=development`) muestra el mensaje real de MySQL, la configuración
que se está usando y una lista numerada de pasos concretos según el código de
error:

| `errno` | Qué significa | Qué sugiere la página |
|---|---|---|
| 1045 | Usuario o contraseña incorrectos | Correr `crear_usuario_mysql.sql` y llenar `MYSQL_PASSWORD` |
| 1049 | La base no existe | Crear la base y cargar `schema.sql` + `datos.sql` |
| 1146 | Falta una tabla | Correr `schema.sql`, y `migracion_graduados.sql` si ya había datos |
| 2003 | El servidor MySQL no responde | Arrancar el servicio y revisar `MYSQL_HOST` / `MYSQL_PORT` |

En **producción** ese handler devuelve el mismo mensaje genérico que un 500
cualquiera: no se filtra el usuario, el host ni el nombre de la base.

## Animaciones y estados de carga

`static/css/carga.css` + `static/js/carga.js`, enlazados en las 7 plantillas
que tienen `<head>` propio. No dependen de ninguna librería.

| Qué | Cómo funciona |
|---|---|
| Barra de progreso | Franja dorada de 3px fija arriba. Se activa al hacer clic en un enlace interno o enviar un formulario. Avanza con desaceleración (`avance += (92 - avance) * 0.08`) para no llegar al 100% antes de que la página cambie. |
| Botones ocupados | Al enviar un formulario el botón recibe `.esta-cargando`: opacidad 0.75, spinner y `pointer-events: none`. Evita el doble clic que crearía dos cuentas o dos comentarios. |
| Entrada de página | El contenido principal sube 8px con un fundido de 0.42s (`via-aparecer`). |
| Grillas escalonadas | Las tarjetas de `.stats-grid`, `.promocion-grid`, `.config-grid` y `.lista-solicitudes` entran con 0.04s de diferencia entre una y otra. |
| Esqueletos | `.via-esqueleto` (+ `--linea`, `--titulo`, `--foto`, `--avatar`): bloques grises con un brillo que se desliza, para usar mientras carga una lista. |
| Imágenes | Las que llevan `data-carga` aparecen con fundido cuando terminan de descargar, en vez de dibujarse a medias. |

Dos detalles que no se ven pero importan:

- **`prefers-reduced-motion`**: si el sistema del usuario pide menos
  movimiento, las animaciones se apagan y los spinners pasan a un pulso suave.
- **Evento `pageshow`**: al volver con el botón "atrás" el navegador restaura
  la página desde su caché, y los botones se quedarían trabados en "cargando".
  El handler los libera.

`window.VIACarga.iniciar()` / `.terminar()` quedan expuestos para que otros
scripts marquen sus propios estados de carga.

## Imágenes: dónde va cada cosa

Detalle completo en `static/img/LEEME.md`. Resumen:

| Carpeta | Qué guarda | ¿Va a git? |
|---|---|---|
| `static/img/escudo/` | `escudo-liceo.svg` / `.png` / `.webp` | Sí |
| `static/img/favicon/` | `favicon.svg` + `site.webmanifest` | Sí |
| `static/img/promociones/` | `2019.jpg`, `2020.jpg`… (el nombre es el año) | Sí |
| `static/img/equipo/` | Fotos del equipo para `contacto.html` | Sí |
| `static/uploads/perfiles/` | Fotos que suben los egresados | No (`.gitignore`) |

### Escudo

Va en la barra superior de `index.html`, `usuarios/_layout.html` y
`contacto.html`, envuelto en un `<a href="https://ieliceotame.edu.co"
target="_blank" rel="noopener">`: **es un botón que abre el sitio de la
institución en otra pestaña.**

No se pide el archivo a ciegas. `_registrar_contexto()` en `backend/app.py`
mira si existe alguno de los tres nombres y expone `escudo_url` a todas las
plantillas; si no hay archivo vale `None` y se dibuja el escudo hecho con CSS
que hay hoy. Así no se genera un 404 por página. En modo desarrollo vuelve a
mirar en cada petición, para que aparezca al copiar el archivo sin reiniciar.

### Favicon

`static/img/favicon/favicon.svg` (escudo verde con la V dorada) y
`site.webmanifest`, enlazados en las 7 plantillas con `<head>`. Cubre Chrome,
Firefox, Edge y Safari 17+. Para navegadores viejos e iOS faltan
`favicon.ico` (16+32+48) y `apple-touch-icon.png` (180×180); el `LEEME.md`
explica cómo generarlos y qué dos líneas descomentar.

### Fotos de perfil

| Parámetro | Valor |
|---|---|
| Extensiones | `png`, `jpg`, `jpeg`, `webp` (`EXTENSIONES_FOTO_PERMITIDAS`) |
| Peso máximo | `MAX_CONTENT_LENGTH_MB`, por defecto 3 MB |
| Tamaño recomendado | cuadrada, mínimo 400×400 px |
| Nombre en disco | `usuario_<id>_<12 hex al azar>.<ext>` |
| Ruta guardada en BD | `/static/uploads/perfiles/<nombre>` en `usuarios.foto` |

El nombre lleva 12 caracteres al azar a propósito: si fuera `usuario_12.jpg`
cualquiera podría adivinar la URL de la foto de otra persona. La carpeta la
crea `create_app()` con `makedirs`, así que funciona en una copia recién
clonada aunque git no guarde carpetas vacías.

**Los graduados del archivo todavía no tienen foto**: la tabla `graduados` no
tiene columna `foto`. Hoy la foto vive en `usuarios.foto`, o sea que solo
tiene retrato quien ya tiene cuenta.

## Funciones nuevas (referencia rápida)

### `backend/app.py`

| Función | Qué hace |
|---|---|
| `_registrar_contexto(app)` | Expone `escudo_url` a todas las plantillas buscando el archivo del escudo en disco. |
| `_registrar_manejadores_error(app)` | Registra los handlers de 403, 404, 413, 429, 500 y `mysql.connector.Error`. |
| `_responder(codigo, titulo, mensaje, detalle, pasos)` | Función interna: decide JSON (rutas `/api/`) o `error.html` y arma la respuesta. |
| `_PASOS_MYSQL` | Diccionario `errno` → lista de pasos para arreglarlo. |

### `backend/utils.py`

| Función | Qué hace |
|---|---|
| `es_imagen_real(stream)` | Lee los primeros 12 bytes y compara contra las firmas de PNG, JPEG y WEBP. Cambiarle la extensión a un archivo es trivial; falsificar la cabecera no. Deja el cursor donde estaba para poder guardar el archivo completo después. |
| `borrar_archivo_subido(ruta_publica)` | Borra la foto anterior para que `static/uploads/` no crezca sin control. Solo acepta rutas bajo `/static/uploads/` y comprueba con `commonpath` que el destino no se salga de la carpeta (defensa contra `../`). |
| `extension_permitida(nombre)` | Ya existía: valida la extensión contra la lista blanca. |
| `nombre_archivo_seguro(usuario_id, nombre)` | Ya existía: genera el nombre aleatorio. |

### `static/js/carga.js`

| Función | Qué hace |
|---|---|
| `iniciarBarra()` / `terminarBarra()` | Muestran y cierran la barra de progreso. Expuestas como `window.VIACarga`. |
| `esNavegacionReal(enlace)` | Filtra qué clics deben mostrar la barra: descarta anclas de la misma página, `target="_blank"`, descargas, otros orígenes y protocolos que no sean http/https. |
| `prepararImagenes()` | Marca las `img[data-carga]` para que aparezcan con fundido al terminar de descargar. |

### `static/js/nav.js`

| Función | Qué hace |
|---|---|
| `marcarEstado(abierto)` | Único punto que cambia el estado del menú: clase `open`, visibilidad del fondo, `aria-expanded` de los dos botones y bloqueo del scroll. |
| `abrir()` / `cerrar()` | Atajos sobre `marcarEstado`. Se enlazan al botón flotante, al de cerrar, al fondo, a `Escape`, a los enlaces del menú y al `resize`. |

## Archivos nuevos de esta ronda

| Archivo | Para qué |
|---|---|
| `database/crear_usuario_mysql.sql` | Crea la base `egresados` y el usuario `via_app` con permisos mínimos. |
| `database/migracion_graduados.sql` | `ALTER TABLE` para bases que ya existían antes de `graduados` / `solicitudes_cuenta`. |
| `templates/error.html` | Página única para 403, 404, 413, 429 y 500. |
| `static/css/error.css` | Estilos de esa página. |
| `static/css/carga.css` | Animaciones y estados de carga. |
| `static/js/carga.js` | Barra de progreso, botones ocupados, imágenes con fundido. |
| `static/img/favicon/favicon.svg` | Favicon. |
| `static/img/favicon/site.webmanifest` | Nombre, colores y `start_url` de la app. |
| `static/css/movil.css` | Ajustes de móvil comunes a todas las páginas. |
| `templates/portada.html` | Portada pública para visitantes sin cuenta. |
| `static/css/portada.css` | Estilos de la portada. |
| `templates/_paginacion.html` | Macro de paginación reutilizable. |
| `static/js/modal.js` | Accesibilidad de los modales. |
| `playwright.config.js` + `tests/` | Pruebas end-to-end. |
| `database/migracion_soporte.sql` | Columnas de respuesta en `soporte_tickets`. |
| `templates/soporte.html` | Bandeja de tickets del administrador. |
| `static/css/soporte.css` | Estilos de esa bandeja. |
| `static/img/LEEME.md` | Guía de dónde va cada imagen y con qué medidas. |

Se eliminó `templates/base.html`: era una maqueta suelta del footer, con su
propio `<!DOCTYPE>` y CSS embebido, que ninguna ruta renderizaba.

## Pendientes conocidos

Cosas que ya estaban marcadas como incompletas en el código original y
siguen así (no se resolvieron en esta ronda de trabajo):

- Los enlaces a redes sociales (Instagram/Facebook/WhatsApp) en
  `login.html` y `templates/usuarios/_footer.html` apuntan a `#`: falta
  poner las URLs reales.
- Las tarjetas del equipo de trabajo en `contacto.html` son estáticas
  (placeholder); la idea original era cargarlas desde una API cuando
  existiera.
- Las imágenes de portada de cada promoción
  (`static/img/promociones/<año>.jpg`) no existen todavía — el carrusel cae
  al placeholder de texto si no encuentra el archivo.
- **`.env` está rastreado por git.** Está listado en `.gitignore`, pero eso no
  tiene efecto sobre un archivo que ya se había commiteado antes (entró en el
  commit `estructura`). Mientras esté vacío no pasa nada, pero al llenarlo con
  la contraseña real de MySQL y hacer commit, esa contraseña queda en el
  historial del repositorio para siempre. Se saca del seguimiento con
  `git rm --cached .env` (el archivo local no se borra).
- `templates/admin.html` no lo renderiza ninguna ruta. Quedó de cuando
  `/admin/` tenía su propio dashboard; hoy ese dashboard vive en `index.html`
  y las rutas `/admin/` y `/admin/usuarios` solo redirigen a `/`.
