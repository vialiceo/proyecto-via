# V.I.A — Vinculación Integral de Alumnos

Aplicación web de seguimiento a egresados para la **Institución Educativa Liceo Tame**.
Los egresados mantienen su perfil (profesión, contacto, dónde viven, dónde estudiaron,
una frase para su promoción); la institución administra las cuentas, publica eventos,
modera la comunidad y atiende solicitudes de soporte.

Roles: **egresado**, **administrador**, **institución**.

> 📄 **Documentación para no-desarrolladores** (funcionamiento contado por capítulos,
> glosario de términos, dónde se guarda cada cosa): ver **`Documentacion_VIA.docx`** en
> la raíz del proyecto. Este `readme.md` es la referencia **técnica** para quien vaya a
> mantener o extender el código.

---

## Índice

1. [Características](#características)
2. [Stack tecnológico](#stack-tecnológico)
3. [Requisitos](#requisitos)
4. [Instalación y puesta en marcha](#instalación-y-puesta-en-marcha)
5. [Variables de entorno (`.env`)](#variables-de-entorno-env)
6. [Estructura del proyecto](#estructura-del-proyecto)
7. [Arquitectura del backend](#arquitectura-del-backend)
8. [Base de datos](#base-de-datos)
9. [Cómo nace una cuenta](#cómo-nace-una-cuenta-archivo--solicitud--usuario)
10. [Seguridad](#seguridad)
11. [Sistema de correos](#sistema-de-correos)
12. [Caché y tareas asíncronas](#caché-y-tareas-asíncronas)
13. [Frontend](#frontend)
14. [Responsive (móvil y tablet)](#responsive-móvil-y-tablet)
15. [Tickets de soporte](#tickets-de-soporte)
16. [Manejo de errores](#manejo-de-errores)
17. [Animaciones y estados de carga](#animaciones-y-estados-de-carga)
18. [Imágenes: dónde va cada cosa](#imágenes-dónde-va-cada-cosa)
19. [Referencia rápida de funciones y archivos](#referencia-rápida-de-funciones-y-archivos)
20. [Despliegue (PythonAnywhere)](#despliegue-pythonanywhere)
21. [Créditos](#créditos)

---

## Características

- Cuentas verificadas contra un archivo histórico de graduados (solicitud → aprobación).
- Perfil del egresado con **privacidad por campo** (cada dato decide si se muestra en el directorio).
- Directorio de alumnos y promociones, con mensajería 1 a 1 entre egresados.
- Eventos institucionales con **favoritos y recordatorio por correo** el día del evento.
- Egresados **destacados**, comentarios moderables y tickets de soporte.
- Panel de administración: cuentas, solicitudes, archivo de graduados (importación CSV) y soporte.
- **Modo oscuro** y diseño responsive (móvil, tablet y escritorio).

## Stack tecnológico

Python 3 · Flask (app factory + blueprints) · Jinja2 · MySQL 8+ (`mysql-connector`, sin ORM) ·
Flask-Login · Flask-WTF (CSRF) · Flask-Limiter (rate limiting) · Flask-Caching · Flask-Mail
(sobre **Resend**) · `cryptography` (cifrado AES-SIV de la cédula) · Werkzeug (hashing scrypt) ·
HTML/CSS/JS sin framework ni build step · Google Fonts. Despliegue en **PythonAnywhere**.

## Requisitos

- **Python 3.11+** y **MySQL 8+**.
- Dependencias de Python en `requirements.txt`.

## Instalación y puesta en marcha

La base de datos se llama **`egresados`**. Si en tu servidor tiene otro nombre, cambia
`MYSQL_DB` en el `.env`: el código lee ese valor y no tiene el nombre escrito en ninguna
otra parte.

**1. Entorno de Python**

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
```

**2. Base de datos y usuario de la aplicación**

Antes de correrlo, abre `database/crear_usuario_mysql.sql` y cambia `CAMBIA_ESTA_CLAVE`
por una contraseña tuya (aparece dos veces).

```bash
mysql -u root -p < database/crear_usuario_mysql.sql
```

Crea la base `egresados` y el usuario `via_app`, que solo tiene permisos
`SELECT/INSERT/UPDATE/DELETE` sobre esa base. No se usa `root` a propósito: si alguien
lograra inyectar SQL, `via_app` no puede leer ni borrar otras bases del servidor ni cambiar
la configuración de MySQL.

**3. Configuración (`.env`)**

Crea un archivo `.env` en la raíz (no se sube a git). El detalle de cada variable está en
[Variables de entorno](#variables-de-entorno-env); lo mínimo es la contraseña del paso 2 y
una `SECRET_KEY` real:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

**4. Tablas y datos iniciales**

```bash
mysql -u root -p egresados < database/schema.sql
mysql -u root -p egresados < database/datos.sql
```

En una instalación nueva basta con `schema.sql` + `datos.sql`. Los `database/migracion_*.sql`
solo se aplican para **actualizar una base que ya existía** (ver [Base de datos](#base-de-datos)).

**5. Arrancar**

```bash
python run.py
```

Disponible en <http://localhost:5000>. Si algo de MySQL quedó mal, la app **no muestra un
error genérico**: sale una página con el código que devolvió MySQL y los pasos concretos para
arreglarlo (ver [Manejo de errores](#manejo-de-errores)).

Cuenta de administrador inicial (de `datos.sql`, solo para el primer ingreso):

| Usuario | Contraseña        | Rol           |
|---------|-------------------|---------------|
| `admin` | `CambiarAhora2026!` | administrador |

Pide cambiar la contraseña en el primer ingreso (`forzar_cambio_password = 1`).

## Variables de entorno (`.env`)

| Variable | Para qué |
|---|---|
| `FLASK_ENV` | `development` o `production`. En producción se apaga el debug, las cookies quedan solo-HTTPS y se cachean los estáticos. |
| `SECRET_KEY` | Firma de sesiones/CSRF. Generar una real con `secrets.token_hex(32)`. |
| `MYSQL_HOST` / `MYSQL_PORT` / `MYSQL_USER` / `MYSQL_PASSWORD` | Conexión a MySQL. `MYSQL_USER` es `via_app`, no `root`. |
| `MYSQL_DB` | Nombre de la base: **`egresados`**. Es el único lugar donde está escrito; cambiarlo aquí basta para apuntar a otra base. |
| `MYSQL_POOL_SIZE` | Tamaño del pool de conexiones (ver `backend/db.py`). |
| `CEDULA_ENC_KEY` | Clave para el cifrado por columna de la cédula (AES-SIV). Si falta, se genera una al vuelo, pero **en producción hay que fijarla en el `.env`**: si cambia, las cédulas ya guardadas dejan de poder descifrarse. |
| `RATELIMIT_STORAGE_URI` | `memory://` alcanza para ~5000 usuarios en una sola instancia. Con varias instancias detrás de un balanceador, usar Redis: `redis://host:6379/0`. |
| `CACHE_TYPE` / `CACHE_REDIS_URL` | `SimpleCache` vive en el proceso Python; con más de un worker, cambiar a `RedisCache` + `CACHE_REDIS_URL` para que todos vean la misma caché. |
| `MAIL_SERVER`, `MAIL_PORT`, `MAIL_USE_TLS`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_DEFAULT_SENDER` | SMTP real (Resend). Si se dejan vacías, el correo no se envía: queda registrado en `logs/correos.log` (modo desarrollo). |
| `MAX_CONTENT_LENGTH_MB` | Límite de tamaño para la foto de perfil (por defecto 3 MB). |
| `SOLICITUDES_API_KEY` | Clave para `POST /api/v1/solicitudes-cuenta`. Si se deja vacía, ese endpoint queda cerrado (responde 401 siempre) y solo funciona el formulario interno. |

Ejemplo de bloque de correo (Resend) en el `.env`:

```
MAIL_SERVER=smtp.resend.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=resend
MAIL_PASSWORD=<tu API key de Resend>
MAIL_DEFAULT_SENDER=no-responder@liceotame.edu.co
```

## Estructura del proyecto

```
backend/     Lógica del servidor (rutas, modelos, utilidades)
templates/   Páginas HTML (Jinja2)
static/      CSS, JS e imágenes
database/    Scripts SQL (schema, datos, migraciones)
run.py       Arranque en desarrollo
config.py    Configuración por entorno (Development / Production)
enviar_recordatorios.py   Tarea diaria de recordatorios de eventos
```

## Arquitectura del backend

App factory en `backend/app.py` / `backend/__init__.py`. Las extensiones (`Flask-Login`,
`Flask-Limiter`, `Flask-Caching`, `Flask-WTF`, `Flask-Mail`) se instancian sin `app` en
`backend/extensions.py` y se enlazan en `create_app()` — así cada blueprint puede importarlas
sin generar imports circulares con `backend/app.py`.

Blueprints:

| Blueprint  | Prefijo     | Archivo             | Qué cubre |
|------------|-------------|---------------------|-----------|
| `public`   | `/`         | `backend/routes.py` | Portada, ayuda, contacto/soporte, aviso legal, solicitud de cuenta |
| `auth`     | `/`         | `backend/auth.py`   | Login, logout, recuperar contraseña, cambio obligatorio |
| `usuarios` | `/usuarios` | `backend/perfil.py` | Perfil propio, foto, comentarios, directorio, promociones, mensajes, eventos |
| `admin`    | `/admin`    | `backend/admin.py`  | Dashboard, cuentas, bandeja de solicitudes, archivo de graduados y tickets de soporte |
| `api`      | `/api/v1`   | `backend/api.py`    | JSON para el panel de admin y la entrada de solicitudes externas |

`backend/models.py` es la única capa que toca SQL (sin ORM: a esta escala el cuello de
botella nunca va a ser cuántas líneas de SQL se escriben, y tener el query real a la vista
permite correr `EXPLAIN` sobre él directamente). `backend/experiencia.py` separa la
validación/armado del "perfil extendido" de las rutas HTTP en `perfil.py`. `backend/utils.py`
reúne lo transversal: hashing, tokens, control de acceso por rol, cifrado de la cédula,
tareas en segundo plano, correo, paginación y validación server-side. `backend/db.py` maneja
el pool de conexiones y ejecuta las consultas parametrizadas.

## Base de datos

Ver `database/schema.sql`. Motor InnoDB, MySQL 8+.

| Tabla | Para qué |
|---|---|
| `graduados` | Archivo institucional: quién se graduó, en qué año, con qué técnico y bajo qué acta. **No son cuentas.** Es un registro histórico permanente que puede tener miles de filas sin que ninguna de esas personas use el portal. |
| `usuarios` | Cuentas. Nadie se registra solo: o las crea el admin, o nacen de una solicitud aprobada. `cedula` es `UNIQUE` (guardada **cifrada**) y `graduado_id` apunta al archivo. |
| `solicitudes_cuenta` | Cola de aprobación. Una persona pide acceso; un admin la contrasta contra `graduados` y decide. |
| `perfil_extendido` | 1 fila por usuario: lo que el propio egresado edita (profesión, dónde vive, dónde estudió, fecha de nacimiento, frase). Separada de `usuarios` a propósito para que el admin nunca pise por accidente lo que el usuario mantiene. |
| `contactos` | Métodos de contacto del egresado, 1 a N (celular, WhatsApp, redes). |
| `tecnicos` | Catálogo de programas técnicos del Liceo. |
| `comentarios` | Feed de la comunidad, moderable por admin. |
| `soporte_tickets` | Tickets creados desde `/contacto`, con la respuesta del administrador, quién la escribió y cuándo. Se atienden en `/admin/soporte`. |
| `password_reset_tokens` | Se guarda el hash del token, nunca el token en claro. |
| `bitacora` | Auditoría: login, cambios de contraseña, acciones de admin sobre una cuenta. |
| `solicitudes` | Certificados/constancias que pide un egresado, con estado (pendiente/en_proceso/aprobada/rechazada/cancelada). |
| `conversaciones` / `mensajes` | Mensajería 1 a 1 entre cualquier par de usuarios. `conversaciones` fija el par (usuario_uno_id, usuario_dos_id) una sola vez por `UNIQUE`; los mensajes cuelgan de ahí. |
| `eventos` | Eventos institucionales. Solo un administrador los crea/edita; todos los pueden ver, marcar como favoritos y recibir recordatorio. |

`perfil_extendido.fecha_nacimiento` se guarda como fecha, no como "edad": la edad cambia con
el tiempo y la app la calcula al vuelo (`utils.calcular_edad`).

### Scripts de `database/`

| Archivo | Para qué |
|---|---|
| `schema.sql` | Estructura completa (todas las tablas e índices). Punto de partida de una base nueva. |
| `datos.sql` | Datos iniciales: catálogo de técnicos y la cuenta `admin`. |
| `crear_usuario_mysql.sql` | Crea la base `egresados` y el usuario `via_app` con permisos mínimos. |
| `migracion_graduados.sql` | `ALTER TABLE` para bases anteriores a `graduados` / `solicitudes_cuenta` (añade `usuarios.cedula` y `usuarios.graduado_id`). |
| `migracion_campos_publicos.sql` | Añade la privacidad por campo (qué se muestra en el directorio). |
| `migracion_promociones.sql` | Soporte de promociones / año de promoción. |
| `migracion_soporte.sql` | Columnas de respuesta en `soporte_tickets`. |
| `migracion_eventos_favoritos.sql` | Tablas/columnas de eventos y favoritos. |
| `migracion_destacado.sql` | Columna `usuarios.destacado` (egresado destacado por el admin). |
| `migracion_cedula_cifrada.sql` | Amplía la columna de cédula para guardar el texto cifrado (AES-SIV). |

Las migraciones solo se corren **una vez sobre una base ya existente**; cada archivo explica
al inicio qué error significa que ya estaba aplicada (típicamente el 1060, *Duplicate column*).

### Índices (por qué existe cada uno, no "por si acaso")

- `usuarios.uq_usuarios_correo` / `uq_usuarios_usuario` / `uq_usuarios_cedula` — el login
  acepta correo, usuario o cédula, así que los tres son `UNIQUE` y se resuelven por índice.
  `cedula` admite `NULL` (MySQL permite varios `NULL` en un índice `UNIQUE`) para las cuentas
  viejas que no la tienen; el valor guardado es el **texto cifrado**, determinista, para que
  siga sirviendo como clave de búsqueda.
- `usuarios.uq_usuarios_graduado (graduado_id)` — impide que dos cuentas reclamen al mismo
  graduado del archivo.
- `graduados.uq_graduados_cedula` — clave natural del archivo; es la que hace que reimportar
  el mismo CSV actualice en vez de duplicar (`ON DUPLICATE KEY UPDATE`).
- `graduados.uq_graduados_nombre_anio (nombre, anio_promocion)` — para las actas viejas que
  no traen cédula, el par nombre+año es lo único que identifica a la persona.
- `graduados.ix_graduados_anio_nombre (anio_promocion, nombre)` — listar una promoción
  completa en orden alfabético, que es como se consulta un archivo.
- `solicitudes_cuenta.ix_soli_cuenta_estado_fecha (estado, creado_en)` — la bandeja del admin:
  pendientes primero, más antiguas arriba.
- `solicitudes_cuenta.ix_soli_cuenta_cedula` / `ix_soli_cuenta_correo` — antes de aceptar una
  solicitud se comprueba que esa persona no tenga ya una en revisión.
- `usuarios.ix_usuarios_rol_estado_promocion (rol, estado, anio_promocion)` — cubre dos cosas
  con el mismo índice: el filtro por rol/estado del panel de admin, y el `GROUP BY
  anio_promocion` que arma las "promociones recientes" del carrusel.
- `usuarios.ix_usuarios_tecnico_promocion (tecnico_id, anio_promocion)` — reporte típico
  "egresados de tal técnico en tal promoción".
- `contactos.ix_contactos_usuario` — el único acceso a esta tabla es "dame los contactos del
  usuario X".
- `password_reset_tokens.uq_reset_token_hash` — validar un token entrante es una búsqueda
  directa por su hash.
- `comentarios.ix_comentarios_estado_fecha (estado, creado_en)` — cubre el feed público
  (visibles, más recientes primero) y la cola de moderación.
- `soporte_tickets.ix_soporte_estado_fecha (estado, creado_en)` — bandeja de admin filtrando
  por estado, ordenada por fecha.
- `bitacora.ix_bitacora_usuario_fecha (usuario_id, creado_en)` — historial de actividad de una
  cuenta en la vista de admin.
- `solicitudes.ix_solicitudes_usuario_fecha (usuario_id, creado_en)` — "mis solicitudes"
  ordenadas por fecha; `ix_solicitudes_estado_fecha` cubre la cola de un admin filtrando por
  estado.
- `conversaciones.uq_conv_par (usuario_uno_id, usuario_dos_id)` — evita crear dos
  conversaciones para el mismo par de usuarios; también sirve para buscar "la conversación
  entre A y B" directo por índice.
- `mensajes.ix_mensajes_conversacion_fecha (conversacion_id, creado_en)` — el hilo completo de
  una conversación, en orden.
- `eventos.ix_eventos_fecha (fecha_inicio)` — listar próximos/pasados ordenados por fecha.

## Cómo nace una cuenta (archivo → solicitud → usuario)

Nadie se registra por su cuenta y nadie carga 3000 cuentas de golpe. Son tres cosas distintas,
y por eso son tres tablas distintas:

1. **El archivo (`graduados`).** Es el libro de grados digitalizado. La institución lo carga
   desde `/admin/graduados`, a mano o importando un CSV con columnas
   `cedula, nombre, anio_promocion, tecnico, libro_acta`. Vive aunque esa persona nunca entre
   al portal. Reimportar el mismo archivo no duplica: la cédula es clave única y la fila se
   actualiza.
2. **La solicitud (`solicitudes_cuenta`).** El egresado entra a `/solicitar-cuenta`, pone
   cédula, nombre, correo, año y (opcional) técnico. Al guardarla, el sistema busca sola una
   coincidencia en `graduados`: primero por cédula, y si no, por nombre exacto + año. Recibe un
   correo con su número de radicado. El formulario está limitado a 5 envíos por hora por IP.
3. **La cuenta (`usuarios`).** En `/admin/solicitudes-cuenta` el admin ve cada solicitud con un
   aviso verde ("coincide con Fulano, acta L-2019-014") o rojo ("no se encontró a esta persona
   en el archivo"). Para aprobar una sin coincidencia hay que marcar explícitamente "añadirla
   también al archivo": así el archivo nunca queda desactualizado en silencio. Al aprobar se
   genera el nombre de usuario, se crea la cuenta con contraseña temporal y
   `forzar_cambio_password = 1`, y se envían las credenciales por correo. Rechazar exige un
   motivo, que también se le envía.

Por qué el nombre no es la llave: los nombres se repiten, se escriben con y sin tilde, y
cambian. El nombre sirve para **verificar** (que un humano confirme que es la persona del
acta), nunca para **unir** filas. Lo que une es `usuarios.graduado_id`.

Por qué la cédula no es la `PRIMARY KEY`: si lo fuera, ese dato personal se copiaría a las diez
tablas que referencian a `usuarios`, aparecería en las URLs y en los logs, y corregir un dígito
mal digitado obligaría a un `UPDATE` en cascada. La clave primaria es el `id` autoincremental
—un número sin significado, como pide la Ley 1581 de 2012 al minimizar el tratamiento de datos
personales— y la cédula es una columna más, `UNIQUE` y **cifrada**, que se puede corregir sin
tocar nada.

### Solicitudes desde una plataforma externa

Si más adelante la institución quiere recoger las solicitudes desde otro sitio (un formulario
propio, otra plataforma), no hace falta duplicar la lógica:

```
POST /api/v1/solicitudes-cuenta
X-API-Key: <SOLICITUDES_API_KEY>
Content-Type: application/json

{"cedula": "1116803311", "nombre": "Laura Martínez",
 "correo": "laura@example.com", "anio_promocion": 2019}
```

Responde `201` con `{"id": ..., "estado": "pendiente", "coincide_con_archivo": true}`.
Cae en la misma bandeja, con las mismas validaciones y la misma verificación contra el archivo;
solo cambia `origen`, que queda como `api` para poder distinguirlas. La clave se compara con
`hmac.compare_digest` y el endpoint está exento de CSRF (un servidor externo no puede tener el
token de sesión) pero limitado a 60 solicitudes por hora.

## Seguridad

- **Contraseñas**: `werkzeug.security` (scrypt), nunca texto plano. Cuentas creadas por el
  admin quedan con `forzar_cambio_password = 1`.
- **Cédula cifrada por columna**: se guarda cifrada con **AES-SIV** (`cryptography`), un modo
  determinista, de modo que sigue siendo `UNIQUE` y sirve para buscar/loguear, pero en la base
  no aparece en claro. `utils.cifrar_cedula` / `utils.descifrar_cedula` son el único punto de
  entrada; la clave sale de `CEDULA_ENC_KEY`.
- **Sesión de duración fija**: la sesión expira a una hora fija contada **desde el login**
  (`session["expira_en"]`), no se renueva en cada navegación
  (`SESSION_REFRESH_EACH_REQUEST = False`) y el servidor la fuerza en cada petición
  (`_enforce_expiracion_sesion`).
- **Recuperación de contraseña**: el mensaje es idéntico exista o no la cuenta con ese
  correo/usuario — no delata qué cuentas existen (`backend/auth.py`, ruta `/recuperar`).
- **CSRF**: Flask-WTF activo globalmente. Cada `<form>` lleva `{{ csrf_token() }}`; las
  llamadas `fetch` del panel de admin mandan el header `X-CSRFToken` (leído del
  `<meta name="csrf-token">` del layout).
- **Rate limiting**: Flask-Limiter con límites más estrictos en las rutas sensibles (`/login`,
  `/recuperar`, creación de cuentas, reseteo de contraseña) además del límite global. Es la
  defensa contra bots (no hay CAPTCHA).
- **Redirect abierto**: el parámetro `?next=` del login se valida con `utils.redireccion_segura`
  — solo acepta rutas propias del sitio (empiezan por `/`, no por `//`).
- **Control de acceso por rol**: forzado desde el servidor en cada ruta protegida; la propiedad
  de los recursos (que un egresado solo edite lo suyo) se comprueba en la capa de datos, no en
  el cliente.
- **Privacidad entre egresados**: correo, teléfono y demás métodos de contacto **no se muestran
  a otros egresados** — la consulta del directorio/promoción solo trae nombre, foto, profesión
  y frase. El resto queda solo para el dueño de la cuenta y el admin. Ver
  `templates/aviso_legal.html`.
- **Consultas parametrizadas** en toda la capa de datos (`backend/models.py` vía
  `backend/db.py`) — nunca se concatena SQL con datos del usuario.
- **Cabeceras de seguridad**: CSP, HSTS (solo bajo HTTPS, `if request.is_secure`),
  `X-Content-Type-Options`, etc. `ProxyFix` permite detectar HTTPS detrás del proxy de
  PythonAnywhere.
- **Secretos fuera de git**: `.env` está en `.gitignore` y nunca se sube. El repositorio es
  **privado**.

## Sistema de correos

`utils.enviar_correo_async(destinatario, asunto, cuerpo_texto)` es el único punto de envío
(internamente usa `enviar_correo_sync` en segundo plano). Se dispara en ~8 sitios:
contraseñas temporales al crear una cuenta, al aprobar una solicitud, al resetear una
contraseña, recuperación de contraseña, aviso de ticket nuevo, respuesta de soporte y
recordatorios de eventos.

- **Servidor SMTP: Resend** (`smtp.resend.com`, usuario `resend`, contraseña = API key).
  Documentación: <https://resend.com/docs/send-with-python>.
- **Plantilla HTML**: no es un archivo `.html` aparte. La arma la función
  `_cuerpo_html(asunto, cuerpo_texto)` en **`backend/utils.py`** (CSS en línea, cabecera verde
  y filete dorado) y la devuelve como string; `enviar_correo_sync` la usa como cuerpo `html`.
- **La API key y los correos donde está enlazado el proyecto** (GitHub, PythonAnywhere, Resend,
  etc.) se entregan **en físico** como credencial, para mantener la privacidad y que el proyecto
  se sostenga en el tiempo. No van en el repositorio.

### Sin servidor de correo también funciona

Con `MAIL_SERVER` vacío en el `.env` **no falla**: escribe el correo completo —remitente,
destinatario, asunto y cuerpo— en `logs/correos.log` y en la consola. Ese archivo hace de
bandeja de salida: ahí se lee la contraseña temporal de una cuenta recién aprobada sin montar
SMTP.

Para que eso se vea, `_configurar_logging()` en `backend/app.py` configura los manejadores (un
`Logger` recién creado no tiene ninguno y su nivel efectivo es WARNING, así que los
`logger.info` se perderían en silencio):

| Destino | Qué recibe |
|---|---|
| Consola | Todo, mientras corre `python run.py` |
| `logs/via.log` | Todo, rotando cada 1 MB con 3 respaldos |
| `logs/correos.log` | Solo los correos (filtro por `extra={"es_correo": True}`) |

La carpeta `logs/` está en `.gitignore`.

## Caché y tareas asíncronas

Flask-Caching (`SimpleCache` en memoria por defecto; cambiar `CACHE_TYPE` a Redis en `.env` si
algún día hay más de un worker). Lo que se cachea y por qué:

- Estadísticas del dashboard de admin (2 min) — no cambian tan rápido como para recalcularlas
  en cada carga.
- Feed de comentarios (30 s) — no necesita ser exacto al segundo; se invalida al
  publicar/moderar un comentario.
- Egresados por promoción (2 min) y promociones recientes del carrusel (3 min) — una sola
  consulta por año calcula tarjeta + datos del pop-up para todos los egresados de esa promoción
  a la vez.

Tareas en segundo plano (`utils.encolar_tarea`, un `ThreadPoolExecutor` compartido): enviar
correo y escribir en la bitácora no bloquean la respuesta HTTP. A la escala de un colegio
(~5000 usuarios) esto alcanza sin necesitar un broker externo tipo Celery/Redis; si en algún
momento hace falta escalar a varios workers de verdad, `encolar_tarea()` es el único punto que
habría que cambiar por un `.delay()` de Celery/RQ.

## Frontend

- **Tipografías**: 
|Uso	             |Fuente	                    | Fallback|
|---|---|---|
|Marca / escudo	      Marcellus	                     serif
|Títulos	          Cormorant Garamond	         Georgia, serif
|Cuerpo / texto	      Source Sans 3	                 Segoe UI, Arial, sans-serif

- **Paleta de colores** (tokens de tema en `static/css/tema.css`; cambian con el modo claro /
  oscuro):

| Token | Claro | Oscuro | Uso |
|---|---|---|---|
| `--fondo` | `#f4f6f2` | `#0f1a14` | Fondo de la página |
| `--superficie` | `#ffffff` | `#16241c` | Tarjetas, modales, paneles |
| `--superficie-2` | `#f4f6f2` | `#1b2d22` | Superficie secundaria / rayado |
| `--campo-bg` | `#fbfbfa` | `#12201a` | Fondo de campos de formulario |
| `--texto` | `#1a1a1a` | `#e7efe9` | Texto principal y títulos |
| `--texto-medio` | `#444a46` | `#c2d0c7` | Texto de datos / valores |
| `--texto-suave` | `#7a8a80` | `#8ba394` | Texto secundario, etiquetas |
| `--borde` | `#e6ebe4` | `#294034` | Bordes de tarjetas y campos |
| `--borde-suave` | `#eef2ec` | `#223429` | Separadores tenues |
| `--avatar-bg` | `#eef2ea` | `#22332a` | Fondo del avatar por defecto |

- **Colores en hexadecimal** (identidad institucional, fijos; variables en
  `static/css/usuarios/Base usuarios.css`):

| Variable | Hex | Uso |
|---|---|---|
| `--verde-oscuro` | `#0d2318` | Base del degradado del sidebar, verdes profundos |
| `--verde-base` | `#1a3d2b` | Verde institucional principal |
| `--verde-medio` | `#22502f` | Verde intermedio (hovers, acentos) |
| `--verde-nav` | `#8fac5e` | Verde claro de navegación |
| `--verde-nav-claro` | `#b5c98a` | Verde de navegación aún más claro |
| `--oro` | `#c9a227` | Dorado institucional (filetes, acentos) |
| `--oro-claro` | `#f0c84a` | Dorado claro (hover del dorado) |
| `--blanco` | `#ffffff` | Texto sobre verde, superficies claras |

- **Modo oscuro**: se activa con `data-theme="dark"` en `<html>`. `static/js/tema.js` guarda la
  preferencia en `localStorage` y un pequeño script en el `<head>` la aplica antes de pintar
  para evitar el parpadeo. Los tokens de la tabla anterior son los que cambian.
- **`templates/usuarios/_layout.html`**: plantilla base del área de usuarios (sidebar a la
  derecha, topbar con accesos rápidos, mensajes flash, footer). Las páginas del área la
  extienden con `{% extends %}`; `index.html`, `login.html`, `contacto.html`, `ayuda.html` y
  `recuperar.html` son independientes (no la usan) porque ya traían su propio maquetado.
- **CSS**: un archivo por página bajo `static/css/`; lo compartido entre varias páginas del
  área de usuarios vive en `static/css/usuarios/` (`Base usuarios.css` = variables + sidebar +
  footer; `layout.css` = topbar + menú de perfil + mensajes flash). `tema.css` centraliza los
  tokens claro/oscuro y `movil.css` los ajustes responsive.
- **JS**: un archivo por página bajo `static/js/`, sin build step. Los transversales son
  `carga.js` (barra de progreso), `nav.js` (menú móvil), `tema.js` (modo oscuro),
  `sesion.js` (contador de sesión), `modal.js` / `modal-egresado.js` (modales).
- **Encabezados**: cada página tiene exactamente un `<h1>` y la jerarquía baja sin saltos
  (`h1 → h2 → h3`). Los íconos son SVG en línea con `stroke="currentColor"`, así que toman el
  color del texto y cambian solos en hover, sin peticiones extra ni librerías de íconos.

## Responsive (móvil y tablet)

Probado en 320, 375, 414, 768, 1024 y 1280 px sobre las páginas del sitio, sin desbordamiento
horizontal. El punto de quiebre es **768 px**: por encima, el menú lateral está fijo y ocupa un
ancho fijo; por debajo se esconde y se abre con un botón.

### El menú en móvil

Aquí había un fallo real: el botón de hamburguesa vivía **dentro** de `.sidebar-nav`, y en
móvil ese panel se desplaza fuera de la pantalla con `transform: translateX(100%)`. El botón se
iba con él, así que en un teléfono no había forma de abrir el menú. Ahora hay dos botones:

| Botón | Dónde vive | Cuándo se ve |
|---|---|---|
| `#navAbrir` (`.nav-abrir`) | Fuera del panel, fijo arriba a la derecha | Solo ≤768 px y con el menú cerrado |
| `#navToggle` (`.nav-toggle`) | Dentro del panel | Siempre; en móvil solo se alcanza con el menú abierto |

`static/js/nav.js` mantiene los dos sincronizados con `aria-expanded`, muestra un fondo oscuro
(`#navFondo`) que cierra al tocarlo, bloquea el scroll del fondo con `body.nav-abierto`, cierra
con `Escape` y al tocar cualquier enlace, y cierra solo si la ventana se agranda por encima de
768 px.

### `static/css/movil.css`

Hoja aparte, cargada de última en las plantillas con `<head>` propio. Al ir al final gana por
orden de cascada sin necesidad de `!important`.

| Regla | Por qué |
|---|---|
| `min-height: 44px` en botones y campos | Es el mínimo que un dedo acierta con fiabilidad. |
| `font-size: 16px` en los campos | Por debajo de 16 px, Safari en iPhone hace **zoom automático** al enfocar el campo y descuadra la página. |
| `flex-direction: column` en filas de filtros | Dos campos lado a lado en 375 px quedan inservibles. |
| `overflow-x: auto` en las tablas | La tabla ancha se desplaza dentro de su caja; la página nunca se mueve de lado. |
| `padding-right: 68px` en la topbar | Deja hueco para el botón flotante del menú. |
| Modales a `calc(100vw - 1.6rem)` | Un modal centrado y pequeño no cabe en un teléfono. |

Dos detalles de CSS que parecen rebuscados y no lo son:

- `select:not([multiple]):not([size])` en vez de `select` a secas: un `select` suelto tiene
  especificidad (0,0,1) y **pierde** contra `.filtros-form select` (0,1,1). Los `:not()` la
  suben lo justo para ganar sin `!important`.
- `input:not([type="checkbox"])…` en vez de `input[type="text"]`: varios campos se escriben como
  `<input name="x">` sin atributo `type`; son de texto por defecto, pero `input[type="text"]`
  **no los alcanza** si el atributo no está escrito.

## Tickets de soporte

Cualquiera puede escribir desde `/contacto` sin tener cuenta. Cada mensaje se guarda en
`soporte_tickets` y aparece en la bandeja del administrador en `/admin/soporte`.

### El ciclo de un ticket

| Estado | Qué significa |
|---|---|
| `abierto` | Recién llegado, nadie lo ha mirado |
| `en_proceso` | Alguien lo está atendiendo (se marca a mano) |
| `cerrado` | Respondido, o cerrado sin responder |

La lista se ordena con `FIELD(estado, 'abierto', 'en_proceso', 'cerrado')` y dentro de cada
estado por fecha **ascendente**: lo urgente primero, y dentro de lo urgente lo que lleva más
tiempo esperando.

`responder_ticket()` guarda la respuesta, el autor, la fecha y pone el estado en `cerrado` **en
un solo UPDATE** (si fueran dos operaciones separadas, un fallo entre ambas dejaría el ticket
contestado pero abierto). Al responder se dispara un correo al remitente en segundo plano. Un
ticket ya cerrado no se puede responder otra vez: la ruta lo rechaza antes de tocar la base.

### Rutas

| Ruta | Método | Qué hace |
|---|---|---|
| `/admin/soporte` | GET | Bandeja, con filtro por estado y búsqueda por nombre/correo/asunto |
| `/admin/soporte/<id>/responder` | POST | Guarda la respuesta, envía el correo y cierra |
| `/admin/soporte/<id>/estado` | POST | Cambia el estado a mano |
| `/api/v1/soporte` | POST | Crea un ticket (lo usa el formulario de Contacto) |
| `/api/v1/admin/soporte` | GET | Los mismos datos en JSON |

## Manejo de errores

Todos los errores pasan por `_registrar_manejadores_error()` en `backend/app.py`, que decide el
formato según la ruta: si la URL empieza por `/api/`, responde JSON; si no, renderiza
`templates/error.html`.

| Código | Cuándo |
|---|---|
| 403 | El rol de la cuenta no alcanza para esa sección |
| 404 | La URL no existe |
| 413 | La foto subida pasa de `MAX_CONTENT_LENGTH_MB` |
| 429 | Se pasó un límite de peticiones (login, API pública) |
| 500 | Cualquier excepción no controlada |

`templates/error.html` extiende `_auth_card.html`, así que reusa el marco visual del login
(tarjeta blanca sobre verde) sin depender de la sesión ni de la base de datos — importante,
porque un 500 puede venir justamente de que la base no responde.

### Errores de MySQL

Hay un handler aparte para `mysql.connector.Error`. En **desarrollo**
(`FLASK_ENV=development`) muestra el mensaje real de MySQL, la configuración que se está usando
y una lista numerada de pasos concretos según el código de error:

| `errno` | Qué significa | Qué sugiere la página |
|---|---|---|
| 1045 | Usuario o contraseña incorrectos | Correr `crear_usuario_mysql.sql` y llenar `MYSQL_PASSWORD` |
| 1049 | La base no existe | Crear la base y cargar `schema.sql` + `datos.sql` |
| 1146 | Falta una tabla | Correr `schema.sql`, y las `migracion_*.sql` si ya había datos |
| 2003 | El servidor MySQL no responde | Arrancar el servicio y revisar `MYSQL_HOST` / `MYSQL_PORT` |

En **producción** ese handler devuelve el mismo mensaje genérico que un 500 cualquiera: no se
filtra el usuario, el host ni el nombre de la base.

## Animaciones y estados de carga

`static/css/carga.css` + `static/js/carga.js`, enlazados en las plantillas con `<head>` propio.
No dependen de ninguna librería.

| Qué | Cómo funciona |
|---|---|
| Barra de progreso | Franja dorada de 3 px fija arriba. Se activa al hacer clic en un enlace interno o enviar un formulario. Avanza con desaceleración para no llegar al 100 % antes de que la página cambie. |
| Botones ocupados | Al enviar un formulario el botón recibe `.esta-cargando`: opacidad 0.75, spinner y `pointer-events: none`. Evita el doble clic que crearía dos cuentas o dos comentarios. |
| Entrada de página | El contenido principal sube 8 px con un fundido de 0.42 s (`via-aparecer`). |
| Grillas escalonadas | Las tarjetas de `.stats-grid`, `.promocion-grid`, `.config-grid` y `.lista-solicitudes` entran con 0.04 s de diferencia entre una y otra. |
| Esqueletos | `.via-esqueleto` (+ `--linea`, `--titulo`, `--foto`, `--avatar`): bloques grises con un brillo que se desliza, para usar mientras carga una lista. |
| Imágenes | Las que llevan `data-carga` aparecen con fundido cuando terminan de descargar. |

Dos detalles que no se ven pero importan:

- **`prefers-reduced-motion`**: si el sistema del usuario pide menos movimiento, las
  animaciones se apagan y los spinners pasan a un pulso suave.
- **Evento `pageshow`**: al volver con el botón "atrás" el navegador restaura la página desde su
  caché, y los botones se quedarían trabados en "cargando". El handler los libera.

`window.VIACarga.iniciar()` / `.terminar()` quedan expuestos para que otros scripts marquen sus
propios estados de carga.

## Imágenes: dónde va cada cosa

Detalle completo en `static/img/LEEME.md`. Resumen:

| Carpeta | Qué guarda | ¿Va a git? |
|---|---|---|
| `static/img/escudo/` | `escudo-liceo.svg` / `.png` / `.webp` | Sí |
| `static/img/favicon/` | `favicon.svg` + `site.webmanifest` | Sí |
| `static/img/promociones/` | `2019.jpg`, `2020.jpg`… (el nombre es el año) | Sí |
| `static/img/equipo/` | Fotos del equipo para `contacto.html` | Sí |
| `static/img/avatar.svg` | Avatar por defecto cuando el egresado no tiene foto | Sí |
| `static/uploads/perfiles/` | Fotos que suben los egresados | No (`.gitignore`) |

### Escudo

Va en la barra superior de `index.html`, `usuarios/_layout.html` y `contacto.html`, envuelto en
un `<a href="https://ieliceotame.edu.co" target="_blank" rel="noopener">`: **es un botón que
abre el sitio de la institución en otra pestaña.**

No se pide el archivo a ciegas. `_registrar_contexto()` en `backend/app.py` mira si existe
alguno de los tres nombres y expone `escudo_url` a todas las plantillas; si no hay archivo vale
`None` y se dibuja el escudo hecho con CSS. Así no se genera un 404 por página. En modo
desarrollo vuelve a mirar en cada petición, para que aparezca al copiar el archivo sin
reiniciar.

### Fotos de perfil

| Parámetro | Valor |
|---|---|
| Extensiones | `png`, `jpg`, `jpeg`, `webp` (`EXTENSIONES_FOTO_PERMITIDAS`) |
| Peso máximo | `MAX_CONTENT_LENGTH_MB`, por defecto 3 MB |
| Tamaño recomendado | cuadrada, mínimo 400×400 px |
| Nombre en disco | `usuario_<id>_<12 hex al azar>.<ext>` |
| Ruta guardada en BD | `/static/uploads/perfiles/<nombre>` en `usuarios.foto` |

El nombre lleva 12 caracteres al azar a propósito: si fuera `usuario_12.jpg` cualquiera podría
adivinar la URL de la foto de otra persona. La carpeta la crea `create_app()` con `makedirs`,
así que funciona en una copia recién clonada aunque git no guarde carpetas vacías.

**Los graduados del archivo todavía no tienen foto**: la tabla `graduados` no tiene columna
`foto`. Hoy la foto vive en `usuarios.foto`, o sea que solo tiene retrato quien ya tiene cuenta.

## Referencia rápida de funciones y archivos

### `backend/app.py`

| Función | Qué hace |
|---|---|
| `_registrar_contexto(app)` | Expone `escudo_url` a todas las plantillas buscando el archivo del escudo en disco. |
| `_registrar_manejadores_error(app)` | Registra los handlers de 403, 404, 413, 429, 500 y `mysql.connector.Error`. |
| `_responder(codigo, titulo, mensaje, detalle, pasos)` | Decide JSON (rutas `/api/`) o `error.html` y arma la respuesta. |
| `_configurar_logging()` | Configura consola + `via.log` + `correos.log`. |
| `_PASOS_MYSQL` | Diccionario `errno` → lista de pasos para arreglarlo. |

### `backend/utils.py`

| Función | Qué hace |
|---|---|
| `cifrar_cedula(cedula)` / `descifrar_cedula(token)` | Cifrado/descifrado determinista (AES-SIV) de la cédula. Único punto de entrada. |
| `enviar_correo_async(...)` / `enviar_correo_sync(...)` | Envío de correo (async encola en segundo plano). |
| `_cuerpo_html(asunto, cuerpo_texto)` | Arma la plantilla HTML del correo y la devuelve como string. |
| `encolar_tarea(fn, *args, **kwargs)` | Corre una función en el `ThreadPoolExecutor` compartido. |
| `es_imagen_real(stream)` | Lee los primeros 12 bytes y compara contra las firmas de PNG, JPEG y WEBP (falsificar la extensión es trivial; la cabecera no). Deja el cursor donde estaba. |
| `borrar_archivo_subido(ruta_publica)` | Borra la foto anterior; solo acepta rutas bajo `/static/uploads/` y comprueba con `commonpath` que no se salga de la carpeta (defensa contra `../`). |
| `calcular_edad(fecha_nacimiento)` | Calcula la edad al vuelo a partir de la fecha guardada. |
| `redireccion_segura(destino)` | Valida el `?next=` del login (solo rutas propias). |

### `static/js`

| Archivo | Qué hace |
|---|---|
| `carga.js` | Barra de progreso, botones ocupados, imágenes con fundido. Expone `window.VIACarga`. |
| `nav.js` | Menú lateral en móvil: sincroniza los dos botones, fondo oscuro, `Escape`, bloqueo de scroll. |
| `tema.js` | Alterna modo claro/oscuro y guarda la preferencia en `localStorage`. |
| `sesion.js` | Contador de tiempo restante de la sesión (fijo desde el login). |
| `modal.js` / `modal-egresado.js` | Accesibilidad de los modales y pop-up de egresado (portal a `<body>` para no romperse dentro de contenedores con `transform`). |
| `carrusel.js` | Carrusel de promociones del inicio (despliegue en línea) y navegación al directorio. |

## Despliegue (PythonAnywhere)

1. `FLASK_ENV=production` en el `.env` (apaga debug, cookies solo HTTPS, caché de estáticos).
2. WSGI: `from backend import create_app` y `application = create_app()`.
3. Mapear `/static/` a la carpeta `static/` (lo sirve Nginx, más rápido).
4. Programar `python enviar_recordatorios.py` una vez al día (Tasks).
5. Fijar `CEDULA_ENC_KEY` y `SECRET_KEY` en el `.env` (no dejar que se generen solas).
6. Verificar el dominio del remitente en Resend para que los correos lleguen a cualquier
   destinatario.

## Créditos

Desarrollado por el equipo de trabajo del proyecto — **Sovietech**, para la Institución
Educativa Liceo Tame (60 años, 1967–2027).
