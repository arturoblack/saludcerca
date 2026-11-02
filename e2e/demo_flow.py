"""Recorrido de punta a punta de la demo con Playwright (Python).

Requiere el servidor local corriendo (cd backend && python dev_server.py) y el frontend compilado.
Uso:
    pip install playwright && playwright install chromium
    python e2e/demo_flow.py [http://localhost:8000]
Guarda capturas en docs/capturas/ (sirven para la presentación si la demo en vivo falla).
"""
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
OUT = Path(__file__).resolve().parent.parent / "docs" / "capturas"
OUT.mkdir(parents=True, exist_ok=True)


def shot(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"), full_page=False)
    print("captura", name)


def entrar(page, nombre):
    page.goto(BASE)
    page.get_by_role("button", name=nombre).click()


def salir(page):
    page.get_by_role("button", name="Salir").click()


with sync_playwright() as p:
    browser = p.chromium.launch(args=["--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream"])
    movil = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2,
                                permissions=["camera", "microphone"], locale="es-PE", timezone_id="America/Lima")
    page = movil.new_page()
    page.on("dialog", lambda d: d.accept())

    # 1. Ingreso
    page.goto(BASE)
    expect(page.get_by_role("heading", name="Ingresar")).to_be_visible()
    shot(page, "01-ingreso")

    # 2. Paciente: próximas citas
    entrar(page, "Rosa Quispe Mamani")
    expect(page.get_by_role("button", name="Unirse a la consulta")).to_be_visible()
    shot(page, "02-paciente-mis-citas")

    # 3. Reservar una cita nueva
    page.get_by_role("button", name="+ Reservar nueva cita").click()
    page.get_by_role("button", name="Pediatría").click()                     # 1. especialidad
    expect(page.get_by_role("button", name="Cualquiera disponible")).to_be_visible()  # 2. médico (o cualquiera)
    expect(page.locator(".dia.sel")).to_be_visible()                          # 3. primer día con turnos
    shot(page, "03a-paciente-turnos")
    page.locator(".slot").last.click()                                        # 4. turno libre
    page.get_by_label("Motivo (opcional)").fill("Fiebre de mi hija desde ayer")
    expect(page.get_by_text("Su conexión:")).to_be_visible()  # medición real de la conexión
    shot(page, "03-paciente-reserva")
    page.get_by_role("button", name="Confirmar cita").click()

    # 4. Avisos: confirmación enviada y recordatorio programado 24 h antes
    expect(page.get_by_text("su cita de Pediatría").first).to_be_visible()
    shot(page, "04-paciente-avisos")

    # 5. Historial
    page.get_by_role("tab", name="Mi historial").click()
    expect(page.get_by_text("Hipertensión arterial controlada")).to_be_visible()
    expect(page.get_by_text("PA 132/84 mmHg")).to_be_visible()  # signos vitales descifrados
    shot(page, "05-paciente-historial")

    # 6. Teleconsulta
    page.get_by_role("tab", name="Mis citas").click()
    page.get_by_role("button", name="Unirse a la consulta").first.click()
    expect(page.get_by_role("button", name="Colgar")).to_be_visible()
    page.wait_for_timeout(3200)
    shot(page, "06-teleconsulta")
    page.get_by_role("button", name="Solo audio").click()
    shot(page, "07-teleconsulta-solo-audio")
    page.get_by_role("button", name="Colgar").click()
    salir(page)

    # 7. Paciente con teléfono básico: su aviso sale por SMS
    entrar(page, "Juan Ccahuana Huamán")
    page.get_by_role("button", name="+ Reservar nueva cita").click()
    page.get_by_role("button", name="Medicina general").click()
    page.get_by_role("button", name="Dr. Luis Herrera Paredes").click()
    page.locator(".dia:not([disabled])").nth(1).click()
    page.locator(".slot").first.click()
    page.get_by_role("button", name="Confirmar cita").click()
    expect(page.get_by_text("Enviado a +51").first).to_be_visible()
    shot(page, "08-aviso-sms")

    # Lista de espera: no hay cardiólogos todavía -> "Avisarme cuando haya turnos"
    page.get_by_role("tab", name="Mis citas").click()
    page.get_by_role("button", name="+ Reservar nueva cita").click()
    page.get_by_role("button", name="Cardiología").click()
    page.get_by_role("button", name="Avisarme cuando haya turnos").click()
    expect(page.get_by_text("Le avisaremos por SMS")).to_be_visible()
    shot(page, "08a-avisarme")
    page.get_by_role("button", name="Ver mis avisos").click()
    expect(page.get_by_text("Esperando turnos")).to_be_visible()
    salir(page)

    # 8. Médico (pantalla de escritorio)
    escritorio = browser.new_context(viewport={"width": 1280, "height": 860}, locale="es-PE", timezone_id="America/Lima",
                                     permissions=["camera", "microphone"])
    med = escritorio.new_page()
    entrar(med, "Dr. Luis Herrera Paredes")
    med.get_by_role("button", name="Rosa Quispe Mamani").first.click()
    expect(med.get_by_text("Hipertensión arterial controlada")).to_be_visible()

    # Durante la videollamada: apuntes con marca de tiempo y consulta de la historia sin colgar
    med.get_by_role("button", name="Iniciar teleconsulta").click()
    expect(med.get_by_role("tab", name="Notas")).to_be_visible()
    med.wait_for_timeout(3200)
    med.get_by_role("button", name="+ Marca").click()
    expect(med.locator("#apuntes")).to_be_focused()
    med.keyboard.type("Refiere mareos leves por las mañanas; toma la medicación con el desayuno.")
    med.get_by_label("Diagnóstico").fill("Hipertensión arterial controlada; sin signos de alarma")
    shot(med, "09a-medico-llamada-notas")
    med.get_by_role("tab", name="Historia (1)").click()
    expect(med.get_by_text("Enalapril 10 mg").first).to_be_visible()
    shot(med, "09b-medico-llamada-historia")
    med.get_by_role("button", name="Colgar").click()

    # Al colgar, el borrador sigue en la ficha
    expect(med.get_by_label("Diagnóstico")).to_have_value("Hipertensión arterial controlada; sin signos de alarma")
    expect(med.get_by_label("Apuntes de la consulta (opcional)")).to_have_value(__import__("re").compile(r"^\[00:0\d\] Refiere mareos"))
    med.get_by_label("Indicaciones").fill("Control de presión en el puesto de salud en 30 días.")
    med.get_by_label("Receta (un medicamento por línea)").fill("Enalapril 10 mg: 1 tableta cada 12 horas por 30 días")
    med.get_by_label("PA sistólica").fill("128")
    med.get_by_label("PA diastólica").fill("80")
    med.get_by_label("Pulso (lpm)").fill("74")
    med.get_by_label("Temp. (°C)").fill("36.6")
    shot(med, "09-medico-ficha")
    med.get_by_role("button", name="Guardar y cerrar la cita").click()
    expect(med.get_by_text("sin signos de alarma")).to_be_visible()
    expect(med.get_by_text("PA 128/80 mmHg")).to_be_visible()
    med.get_by_text("Apuntes de la consulta").first.click()
    expect(med.get_by_text("Refiere mareos leves")).to_be_visible()
    shot(med, "10-medico-nota-guardada")

    # Horario de atención: el médico agrega una franja el sábado por la tarde
    med.get_by_role("tab", name="Mi horario").click()
    expect(med.get_by_role("heading", name="Mi horario de atención")).to_be_visible()
    fila_sabado = med.locator(".dia-fila").nth(5)
    fila_sabado.get_by_role("button", name="+ Franja").click()
    med.get_by_label("Sábado: inicio").nth(1).fill("14:00")
    med.get_by_label("Sábado: fin").nth(1).fill("17:00")
    med.get_by_role("button", name="Guardar horario").click()
    expect(med.get_by_text("Horario guardado")).to_be_visible()
    shot(med, "10b-medico-horario")
    salir(med)

    # 9. Coordinación
    entrar(med, "Coordinación ONG")
    expect(med.get_by_text("citas programadas")).to_be_visible()
    expect(med.get_by_text("1 en espera")).to_be_visible()      # demanda de Cardiología
    med.get_by_label("Nombre completo").fill("Dr. Raúl Quispe Arce")
    med.get_by_label("Especialidad").select_option("Cardiología")
    med.get_by_role("button", name="Registrar médico").click()
    expect(med.get_by_text("Se avisó a 1 paciente")).to_be_visible()
    shot(med, "11-coordinacion")

    # Juan recibe el SMS de disponibilidad y ya puede reservar con el cardiólogo
    entrar(page, "Juan Ccahuana Huamán")
    page.get_by_role("tab", name="Avisos").click()
    expect(page.get_by_text("ya hay turnos de Cardiología")).to_be_visible()
    shot(page, "12-sms-disponibilidad")

    browser.close()
    print("Recorrido completo OK")
