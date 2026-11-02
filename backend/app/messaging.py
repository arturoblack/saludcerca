"""Eventos de citas, cola de mensajes y envío de notificaciones.

Flujo en Azure:
  fn-citas  --publica-->  Service Bus (cola "notificaciones")  --trigger-->  fn-notificador  -->  ACS (SMS / email)

El recordatorio se publica como mensaje programado (scheduled_enqueue_time) para que
Service Bus lo entregue 24 h antes de la cita; así no hace falta un proceso que haga polling.
En local (MESSAGING_BACKEND=inline) el evento se procesa en el mismo proceso.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo

from .config import Settings
from .models import Canal, Cita, Notificacion, Usuario, now_utc
from .repository import Repository

log = logging.getLogger("saludcerca.messaging")
LIMA = ZoneInfo("America/Lima")


# ---------- Notificadores (canal de salida) ----------

class Notifier(Protocol):
    def send(self, canal: Canal, destino: str, asunto: str, mensaje: str) -> None: ...


class ConsoleNotifier:
    """Solo registra el envío. Útil en local y en la demo."""

    def send(self, canal: Canal, destino: str, asunto: str, mensaje: str) -> None:
        log.info("[%s -> %s] %s", canal.value.upper(), destino, mensaje)


class SmtpNotifier:
    """Envía SMS y correos a una bandeja SMTP local (Mailpit) para verlos durante las pruebas.

    Un SMS llega como correo a <numero>@sms.saludcerca.local con el asunto "SMS para <numero>".
    Solo se usa en local; en Azure el notificador es ACS.
    """

    def __init__(self, settings: Settings) -> None:
        self.s = settings

    def send(self, canal: Canal, destino: str, asunto: str, mensaje: str) -> None:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg["From"] = self.s.smtp_from
        if canal == Canal.app:
            # En la nube un aviso "app" solo queda en la pestaña Avisos; en pruebas locales también
            # se copia a Mailpit para que todo aviso sea visible, sea cual sea el canal del paciente.
            msg["To"] = f"{destino}@app.saludcerca.local"
            msg["Subject"] = f"[Aviso en la app] {asunto}"
        elif canal == Canal.sms:
            msg["To"] = f"{destino.lstrip('+')}@sms.saludcerca.local"
            msg["Subject"] = f"SMS para {destino}"
        else:
            msg["To"] = destino
            msg["Subject"] = asunto
        msg.set_content(mensaje)
        with smtplib.SMTP(self.s.smtp_host, self.s.smtp_port, timeout=10) as smtp:
            smtp.send_message(msg)
        log.info("[%s -> %s] enviado por SMTP a %s:%s", canal.value.upper(), destino, self.s.smtp_host, self.s.smtp_port)


class AcsNotifier:  # pragma: no cover - requiere un recurso de Communication Services
    """Envía SMS y correo con Azure Communication Services.

    El SMS hacia números de Perú requiere un remitente habilitado con Messaging Connect.
    """

    def __init__(self, settings: Settings) -> None:
        self.s = settings

    def send(self, canal: Canal, destino: str, asunto: str, mensaje: str) -> None:
        if canal == Canal.sms:
            from azure.communication.sms import SmsClient
            client = SmsClient.from_connection_string(self.s.acs_connection_string)
            client.send(from_=self.s.acs_sms_from, to=[destino], message=mensaje)
        elif canal == Canal.email:
            from azure.communication.email import EmailClient
            client = EmailClient.from_connection_string(self.s.acs_connection_string)
            poller = client.begin_send({
                "senderAddress": self.s.acs_email_from,
                "recipients": {"to": [{"address": destino}]},
                "content": {"subject": asunto, "plainText": mensaje},
            })
            poller.result()
        # Canal.app: la PWA muestra el aviso desde /api/notificaciones; no hay envío externo.


# ---------- Plantillas ----------

def _fecha_legible(dt: datetime) -> str:
    local = dt.astimezone(LIMA)
    return local.strftime("%d/%m/%Y a las %H:%M")


def construir_mensaje(tipo: str, cita: Cita, medico: Usuario | None) -> tuple[str, str]:
    cuando = _fecha_legible(cita.fecha_hora)
    quien = medico.nombre if medico else "su médico"
    if tipo == "confirmacion":
        return ("Cita confirmada",
                f"SaludCerca: su cita de {cita.especialidad} con {quien} es el {cuando}. "
                f"Le recordaremos un día antes.")
    if tipo == "recordatorio":
        return ("Recordatorio de cita",
                f"SaludCerca: mañana tiene cita de {cita.especialidad} ({cuando}). "
                f"Ingrese a la app 5 minutos antes o acuda a su puesto de salud.")
    if tipo == "cancelacion":
        return ("Cita cancelada", f"SaludCerca: su cita del {cuando} fue cancelada. Puede reprogramarla en la app.")
    raise ValueError(f"tipo de notificación desconocido: {tipo}")


def destino_para(paciente: Usuario) -> tuple[Canal, str]:
    """Elige el canal según el perfil: SMS solo para quien no usa la app (teléfono básico)."""
    if paciente.canal_preferido == Canal.sms and paciente.telefono:
        return Canal.sms, paciente.telefono
    if paciente.canal_preferido == Canal.email and paciente.email:
        return Canal.email, paciente.email
    return Canal.app, paciente.id


# ---------- Procesamiento de eventos (lo que hace fn-notificador) ----------

def handle_event(event: dict, repo: Repository, notifier: Notifier) -> Notificacion | None:
    tipo = event["tipo"]
    if tipo == "disponibilidad":  # aviso masivo a la lista de espera de una especialidad
        from .avisos import notificar_disponibilidad
        notificar_disponibilidad(repo, notifier, event["especialidad"])
        return None
    cita = repo.get_cita(event["cita_id"])
    if cita is None:
        log.warning("evento %s para cita inexistente %s", tipo, event["cita_id"])
        return None
    if tipo == "recordatorio" and cita.estado != "programada":
        log.info("recordatorio omitido: la cita %s está %s", cita.id, cita.estado)
        return None
    paciente = repo.get_usuario(cita.paciente_id)
    if paciente is None:
        return None
    medico = repo.get_usuario(cita.medico_id)
    canal, destino = destino_para(paciente)
    asunto, mensaje = construir_mensaje(tipo, cita, medico)
    notif = Notificacion(cita_id=cita.id, paciente_id=paciente.id, tipo=tipo, canal=canal, destino=destino, mensaje=mensaje)
    try:
        notifier.send(canal, destino, asunto, mensaje)
    except Exception:  # el reintento lo hace Service Bus; aquí solo registramos
        notif.estado = "fallida"
        repo.add_notificacion(notif)
        raise
    repo.add_notificacion(notif)
    return notif


# ---------- Publicadores (lo que hace fn-citas) ----------

class Publisher(Protocol):
    def publish(self, event: dict, deliver_at: datetime | None = None) -> None: ...


class InlinePublisher:
    """Procesa el evento al instante; los programados quedan registrados como 'programada'."""

    def __init__(self, repo: Repository, notifier: Notifier) -> None:
        self.repo = repo
        self.notifier = notifier

    def publish(self, event: dict, deliver_at: datetime | None = None) -> None:
        if deliver_at and deliver_at > now_utc():
            cita = self.repo.get_cita(event["cita_id"])
            paciente = self.repo.get_usuario(cita.paciente_id) if cita else None
            if cita and paciente:
                canal, destino = destino_para(paciente)
                _, mensaje = construir_mensaje(event["tipo"], cita, self.repo.get_usuario(cita.medico_id))
                self.repo.add_notificacion(Notificacion(
                    cita_id=cita.id, paciente_id=paciente.id, tipo=event["tipo"], canal=canal, destino=destino,
                    mensaje=mensaje, estado="programada", programada_para=deliver_at))
            return
        try:
            handle_event(event, self.repo, self.notifier)
        except Exception:
            # Sin cola no hay reintentos: se registra el fallo y la reserva/el horario igual se guardan.
            log.exception("no se pudo procesar el evento %s; revise la configuración de avisos", event.get("tipo"))


class ServiceBusPublisher:  # pragma: no cover - requiere un namespace de Service Bus
    def __init__(self, settings: Settings, repo: Repository | None = None) -> None:
        self._repo = repo
        from azure.servicebus import ServiceBusClient
        if settings.servicebus_connection_string:  # emulador local
            self._client = ServiceBusClient.from_connection_string(settings.servicebus_connection_string)
        else:
            from azure.identity import DefaultAzureCredential
            self._client = ServiceBusClient(settings.servicebus_namespace, credential=DefaultAzureCredential())
        self._queue = settings.servicebus_queue

    def publish(self, event: dict, deliver_at: datetime | None = None) -> None:
        from azure.servicebus import ServiceBusMessage
        msg = ServiceBusMessage(json.dumps(event), content_type="application/json",
                                subject=event["tipo"],
                                message_id=event.get("id") or f'{event.get("cita_id")}-{event["tipo"]}')
        with self._client.get_queue_sender(self._queue) as sender:
            if deliver_at and deliver_at > now_utc():
                try:
                    sender.schedule_messages(msg, deliver_at)
                except Exception:
                    # Algunos emuladores (floci-az) no implementan mensajes programados (501).
                    # Se registra el recordatorio como pendiente para no perder la reserva.
                    log.warning("Service Bus no aceptó el mensaje programado; se registra como pendiente")
                    if self._repo is not None:
                        InlinePublisher(self._repo, ConsoleNotifier()).publish(event, deliver_at)
            else:
                sender.send_messages(msg)


def build_notifier(settings: Settings) -> Notifier:
    if settings.notifier_backend == "acs":
        return AcsNotifier(settings)
    if settings.notifier_backend == "smtp":
        return SmtpNotifier(settings)
    return ConsoleNotifier()


def build_publisher(settings: Settings, repo: Repository, notifier: Notifier) -> Publisher:
    if settings.messaging_backend == "servicebus":
        return ServiceBusPublisher(settings, repo)
    return InlinePublisher(repo, notifier)


def publicar_cita_creada(publisher: Publisher, cita: Cita, horas_antes: int) -> None:
    publisher.publish({"tipo": "confirmacion", "cita_id": cita.id})
    recordar_en = cita.fecha_hora - timedelta(hours=horas_antes)
    if recordar_en > now_utc():  # si la cita es en menos de 24 h, basta la confirmación
        publisher.publish({"tipo": "recordatorio", "cita_id": cita.id}, deliver_at=recordar_en)
