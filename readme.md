# V.I.A — Vinculación Integral de Alumnos

Sistema de seguimiento a egresados de la Institución Educativa Liceo Tame.
Los egresados mantienen su perfil (profesión, contacto, dónde viven, dónde
estudiaron, una frase para su promoción), la institución administra las
cuentas y modera comentarios y solicitudes de soporte.

Roles: **egresado**, **administrador**, **institución**.

## Cómo correr el proyecto

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt

copy .env.example .env         # y llenar credenciales reales de MySQL
```

Crear la base de datos y cargar el esquema + datos de prueba:

```sql
mysql -u root -p < database/schema.sql
mysql -u root -p < database/datos.sql
```

Correr la app:

```bash
python run.py
```

Cuentas de prueba (ver `database/datos.sql`, contraseñas solo para desarrollo):

| Usuario  | Contraseña          | Rol           |
|----------|----------------------|---------------|
| admin    | CambiarAhora2026!    | administrador |
| jgomez   | Egresado123!         | egresado      |

Ambas piden cambiar la contraseña en el primer ingreso.

## Arquitectura del backend

App factory en `backend/app.py` / `backend/__init__.py`. Las extensiones
(`Flask-Login`, `Flask-Limiter`, `Flask-Caching`, `Flask-WTF`, `Flask-Mail`)
se instancian sin `app` en `backend/extensions.py` y se enlazan en
`create_app()` — así cada blueprint puede importarlas sin generar imports
circulares con `backend/app.py`.

Blueprints:

| Blueprint    | Prefijo      | Archivo               | Qué cubre |
|--------------|--------------|------------------------|-----------|
| `public`     | `/`          | `backend/routes.py`    | Portada, ayuda, contacto/soporte, aviso legal |
| `auth`       | `/`          | `backend/auth.py`      | Login, logout, recuperar contraseña, cambio obligatorio |
| `usuarios`   | `/usuarios`  | `backend/perfil.py`    | Perfil propio, foto, comentarios, página de promoción |
| `admin`      | `/admin`     | `backend/admin.py`     | Dashboard, listado y alta de egresados |
| `api`        | `/api/v1`    | `backend/api.py`       | JSON para las acciones dinámicas del panel de admin |

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
| `usuarios` | Cuentas. Solo el admin crea filas (registro cerrado). Identidad, credenciales, promoción, técnico. |
| `perfil_extendido` | 1 fila por usuario: lo que el propio egresado edita (profesión, dónde vive, dónde estudió, fecha de nacimiento, frase). Separada de `usuarios` a propósito para que el admin nunca pise por accidente lo que el usuario mantiene. |
| `contactos` | Métodos de contacto del egresado, 1 a N (puede tener varios: celular, WhatsApp, redes). |
| `tecnicos` | Catálogo de programas técnicos del Liceo. |
| `comentarios` | Feed de la comunidad, moderable por admin. |
| `soporte_tickets` | Tickets creados desde `/contacto` o el área de usuarios. |
| `password_reset_tokens` | Se guarda el hash del token, nunca el token en claro. |
| `bitacora` | Auditoría: login, cambios de contraseña, acciones de admin sobre una cuenta. |

`perfil_extendido.fecha_nacimiento` se guarda como fecha, no como "edad": la
edad cambia con el tiempo y la app la calcula al vuelo (`utils.calcular_edad`).

### Índices (por qué existe cada uno, no "por si acaso")

- `usuarios.uq_usuarios_correo` / `uq_usuarios_usuario` — login acepta correo
  o usuario (ver `recuperar.html`), ambos son `UNIQUE`.
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

## Pendientes conocidos

Cosas que ya estaban marcadas como incompletas en el código original y
siguen así (no se resolvieron en esta ronda de trabajo):

- Los enlaces a redes sociales (Instagram/Facebook/WhatsApp) en
  `login.html`, `templates/usuarios/_footer.html` y `templates/base.html`
  apuntan a `#`: falta poner las URLs reales.
- Las tarjetas del equipo de trabajo en `contacto.html` son estáticas
  (placeholder); la idea original era cargarlas desde una API cuando
  existiera.
- Las imágenes de portada de cada promoción
  (`static/img/promociones/<año>.jpg`) no existen todavía — el carrusel cae
  al placeholder de texto si no encuentra el archivo.
- `templates/base.html` es una prueba independiente del footer, sin usar
  desde ninguna ruta; se dejó tal cual por si sirve de referencia.
