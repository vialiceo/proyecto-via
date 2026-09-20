"""
Envía un correo a cada persona que marcó como favorito un evento que ocurre HOY,
y marca el recordatorio para no repetirlo. Está pensado para correr UNA VEZ AL
DÍA con una tarea programada.

python enviar_recordatorios.py

En PythonAnywhere se agenda en "Scheduled tasks" con la línea de arriba (usando
la ruta completa al proyecto y al intérprete del virtualenv). En Linux se pone
en el crontab, por ejemplo a las 7:00 de la mañana:

0 7 * * *  cd /ruta/al/proyecto && venv/bin/python enviar_recordatorios.py

falta buscar el dominio del correo @ieliceotame.edu.co para que resend funcione, ya coloque la api key
"""
import sys

from backend import create_app, models, utils


def main():
    app = create_app()
    with app.app_context():
        pendientes = models.eventos_para_recordar()
        if not pendientes:
            print("No hay recordatorios para hoy.")
            return 0

        enviados = 0
        for r in pendientes:
            hora = r["fecha_inicio"].strftime("%H:%M")
            cuerpo = (
                f"Hola {r['usuario_nombre']}:\n\n"
                f"Hoy es el evento que marcaste: \"{r['titulo']}\".\n"
                f"Hora: {hora}\n"
                + (f"Lugar: {r['lugar']}\n" if r.get("lugar") else "")
                + "\n¡No faltes! Te esperamos.\n\n"
                "Institución Educativa Liceo Tame — V.I.A"
            )
            try:
                utils.enviar_correo_sync(
                    r["correo"],
                    f"Recordatorio: hoy es \"{r['titulo']}\"",
                    cuerpo,
                )
                models.marcar_recordatorio_enviado(r["usuario_id"], r["evento_id"])
                enviados += 1
            except Exception as e:  # noqa: BLE001
                print(f"Error enviando a {r['correo']}: {e}", file=sys.stderr)

        print(f"Recordatorios enviados: {enviados} de {len(pendientes)}.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
