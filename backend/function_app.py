"""Punto de entrada de Azure Functions (modelo de programación v2 de Python).

- Todas las rutas HTTP /api/* las atiende la app ASGI (fn-citas, fn-historial,
  fn-documentos y fn-videoconsulta del diagrama son grupos de rutas de esta app).
- `notificador` es la función disparada por la cola de Service Bus (fn-notificador).
"""
import json
import logging

import azure.functions as func

from app.config import get_settings
from app.main import create_app
from app.messaging import build_notifier, handle_event
from app.repository import build_repository

settings = get_settings()
repo = build_repository(settings)
asgi = create_app(settings, repo)

app = func.AsgiFunctionApp(app=asgi, http_auth_level=func.AuthLevel.ANONYMOUS)


@app.function_name(name="notificador")
@app.service_bus_queue_trigger(arg_name="msg", queue_name="%SERVICEBUS_QUEUE%",
                               connection="SERVICEBUS")
def notificador(msg: func.ServiceBusMessage) -> None:
    event = json.loads(msg.get_body().decode("utf-8"))
    logging.info("notificador: evento %s de la cita %s (intento %s)",
                 event.get("tipo"), event.get("cita_id"), msg.delivery_count)
    # Si falla, la excepción hace que Service Bus reintente; tras el máximo de
    # entregas el mensaje pasa a la cola de mensajes fallidos (dead-letter).
    handle_event(event, repo, build_notifier(settings))
