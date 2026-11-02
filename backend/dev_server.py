"""Servidor local de demostración: API + frontend compilado en http://localhost:8000.

Uso:
    python dev_server.py            # API en memoria con datos ficticios
    PORT=9000 python dev_server.py

Si existe ../frontend/dist (npm run build), también sirve la PWA.
"""
import logging
import os
from pathlib import Path

import uvicorn
from starlette.responses import FileResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

from app.main import create_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")

app = create_app()
dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if dist.exists():
    async def spa(request):  # rutas del frontend -> index.html
        return FileResponse(dist / "index.html")

    app.router.routes.append(Mount("/assets", StaticFiles(directory=dist / "assets"), name="assets"))
    for f in dist.iterdir():
        if f.is_file() and f.name != "index.html":
            app.router.routes.append(Route(f"/{f.name}", lambda r, f=f: FileResponse(f)))
    app.router.routes.append(Route("/{ruta:path}", spa))

def worker_service_bus() -> None:  # pragma: no cover - requiere Service Bus o el emulador
    """Hace de fn-notificador en local cuando el emulador no ejecuta disparadores de Service Bus."""
    import json

    from azure.servicebus import ServiceBusClient

    from app.messaging import build_notifier, handle_event

    svc = app.state.services
    s = svc.settings
    client = ServiceBusClient.from_connection_string(s.servicebus_connection_string)
    with client.get_queue_receiver(s.servicebus_queue, max_wait_time=5) as receiver:
        while True:
            for msg in receiver.receive_messages(max_message_count=10, max_wait_time=5):
                try:
                    handle_event(json.loads(str(msg)), svc.repo, build_notifier(s))
                    receiver.complete_message(msg)
                except Exception:
                    logging.exception("fallo al procesar el mensaje; se reintentará")
                    receiver.abandon_message(msg)


if __name__ == "__main__":
    if os.getenv("LOCAL_SB_WORKER", "").lower() == "true":
        import threading
        threading.Thread(target=worker_service_bus, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8000")))
