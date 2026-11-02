"""Genera los diagramas (SVG -> PNG) para el documento de arquitectura."""
import html, sys

FONT = "Arial, Helvetica, sans-serif"
CAT = {
    "user":  ("#F3F4F6", "#4B5563"),
    "edge":  ("#E6F0FB", "#0F5FB3"),
    "ident": ("#E8EAFD", "#3A47C4"),
    "comp":  ("#FFF1E3", "#C2620A"),
    "data":  ("#E5F5EC", "#1E7D45"),
    "msg":   ("#F3E8FB", "#7A2FB0"),
    "sec":   ("#FDECEC", "#B42318"),
    "ops":   ("#ECEFF3", "#334155"),
}


def box(x, y, w, h, cat, title, lines=(), dashed=False, badge=None):
    fill, stroke = CAT[cat]
    dash = ' stroke-dasharray="7 5"' if dashed else ""
    s = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="2"{dash}/>']
    s.append(f'<rect x="{x}" y="{y}" width="8" height="{h}" rx="4" fill="{stroke}"/>' if not dashed else "")
    ty = y + 26
    s.append(f'<text x="{x + w/2 + 3}" y="{ty}" text-anchor="middle" font-family="{FONT}" font-size="16" font-weight="bold" fill="{stroke}">{html.escape(title)}</text>')
    for i, ln in enumerate(lines):
        s.append(f'<text x="{x + w/2 + 3}" y="{ty + 22 + i*18}" text-anchor="middle" font-family="{FONT}" font-size="13" fill="#1F2937">{html.escape(ln)}</text>')
    if badge:
        bw = 9 * len(badge) + 14
        s.append(f'<rect x="{x + w - bw - 6}" y="{y - 11}" width="{bw}" height="22" rx="11" fill="{stroke}"/>')
        s.append(f'<text x="{x + w - bw/2 - 6}" y="{y + 5}" text-anchor="middle" font-family="{FONT}" font-size="12" font-weight="bold" fill="#fff">{html.escape(badge)}</text>')
    return "\n".join(s)


def arrow(points, label=None, lx=None, ly=None, dashed=False, color="#374151", both=False, anchor="middle"):
    d = "M " + " L ".join(f"{px} {py}" for px, py in points)
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    start = ' marker-start="url(#ahs)"' if both else ""
    s = [f'<path d="{d}" fill="none" stroke="{color}" stroke-width="2"{dash} marker-end="url(#ah)"{start}/>']
    if label:
        if lx is None:
            (x1, y1), (x2, y2) = points[0], points[-1]
            lx, ly = (x1 + x2) / 2, (y1 + y2) / 2 - 8
        for i, part in enumerate(label.split("\n")):
            s.append(f'<text x="{lx}" y="{ly + i*15}" text-anchor="{anchor}" font-family="{FONT}" font-size="12" font-style="italic" fill="#374151" paint-order="stroke" stroke="#ffffff" stroke-width="4">{html.escape(part)}</text>')
    return "\n".join(s)


DEFS = """<defs>
<marker id="ah" markerWidth="10" markerHeight="10" refX="9" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="#374151"/></marker>
<marker id="ahs" markerWidth="10" markerHeight="10" refX="1" refY="5" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="#374151"/></marker>
</defs>"""


def architecture():
    W, H = 1820, 1130
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', DEFS,
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{W/2}" y="40" text-anchor="middle" font-family="{FONT}" font-size="24" font-weight="bold" fill="#111827">Arquitectura de referencia: Plataforma de Telemedicina Rural en Microsoft Azure</text>']

    # Región Azure
    p.append(f'<rect x="270" y="80" width="1300" height="840" rx="16" fill="#FAFCFF" stroke="#0F5FB3" stroke-width="2" stroke-dasharray="10 6"/>')
    p.append(f'<text x="290" y="106" font-family="{FONT}" font-size="15" font-weight="bold" fill="#0F5FB3">Suscripción Azure  ·  Región principal: Chile Central (3 zonas de disponibilidad)  ·  Modelo PaaS / serverless</text>')

    # Encabezados de capa
    for x, t in [(300, "ENTREGA E IDENTIDAD"), (580, "API Y CÓMPUTO"), (885, "DATOS"), (1200, "MENSAJERÍA")]:
        p.append(f'<text x="{x}" y="140" font-family="{FONT}" font-size="12" font-weight="bold" letter-spacing="1.5" fill="#6B7280">{t}</text>')

    # Usuarios (izquierda)
    p.append(f'<text x="40" y="140" font-family="{FONT}" font-size="12" font-weight="bold" letter-spacing="1.5" fill="#6B7280">USUARIOS</text>')
    p.append(box(30, 160, 210, 100, "user", "Pacientes", ["Smartphone / PWA", "Conexión 3G/4G limitada"]))
    p.append(box(30, 300, 210, 100, "user", "Médicos", ["Navegador web", "Teleconsulta y registro"]))
    p.append(box(30, 440, 210, 100, "user", "Puesto de salud rural", ["Tablet compartida", "Modo offline + sync"]))

    # Capa de entrega e identidad
    p.append(box(300, 160, 220, 100, "edge", "Azure Front Door", ["CDN global + WAF", "TLS 1.2+ / anti-DDoS"]))
    p.append(box(300, 300, 220, 100, "edge", "Static Web Apps", ["Frontend PWA", "(HTML/JS, caché offline)"]))
    p.append(box(300, 440, 220, 110, "ident", "Entra External ID", ["Registro e inicio de sesión", "MFA (SMS/email OTP)", "Roles: paciente / médico"]))

    # API y cómputo
    p.append(box(580, 160, 240, 100, "comp", "API Management", ["Plan Consumption", "Valida JWT · cuotas · rate limit"]))
    p.append(f'<rect x="580" y="300" width="240" height="320" rx="10" fill="#FFF1E3" stroke="#C2620A" stroke-width="2"/>')
    p.append(f'<rect x="580" y="300" width="8" height="320" rx="4" fill="#C2620A"/>')
    p.append(f'<text x="703" y="326" text-anchor="middle" font-family="{FONT}" font-size="16" font-weight="bold" fill="#C2620A">Azure Functions</text>')
    p.append(f'<text x="703" y="346" text-anchor="middle" font-family="{FONT}" font-size="13" fill="#1F2937">Plan Flex Consumption (escala a 0)</text>')
    for i, (n, d) in enumerate([("fn-citas", "agenda / cancela citas"), ("fn-historial", "CRUD historia clínica"),
                                 ("fn-documentos", "SAS para adjuntos"), ("fn-videoconsulta", "tokens de sala ACS")]):
        yy = 362 + i * 63
        p.append(f'<rect x="600" y="{yy}" width="206" height="52" rx="8" fill="#ffffff" stroke="#E2A36A" stroke-width="1.5"/>')
        p.append(f'<text x="703" y="{yy+22}" text-anchor="middle" font-family="{FONT}" font-size="14" font-weight="bold" fill="#7C3D06">{n}</text>')
        p.append(f'<text x="703" y="{yy+40}" text-anchor="middle" font-family="{FONT}" font-size="12" fill="#374151">{d}</text>')

    # Datos
    p.append(box(885, 160, 250, 110, "data", "Azure Cosmos DB", ["API NoSQL · modo serverless", "Pacientes, citas, historias", "Backup continuo (PITR)"]))
    p.append(box(885, 310, 250, 110, "data", "Azure Blob Storage", ["Resultados, imágenes, PDF", "Hot → Cool → Cold → Archive", "Inmutabilidad (WORM)"]))
    p.append(box(885, 460, 250, 100, "data", "Health Data Services", ["Servidor FHIR (HL7)", "Interoperabilidad RENHICE"], dashed=True, badge="Fase 2"))

    # Mensajería
    p.append(box(1200, 160, 240, 100, "msg", "Azure Service Bus", ["Cola: notificaciones", "Reintentos + dead-letter"]))
    p.append(box(1200, 300, 240, 90, "comp", "fn-notificador", ["Trigger de cola", "Plantillas y recordatorios"]))
    p.append(box(1200, 430, 240, 120, "msg", "Communication Services", ["SMS (Messaging Connect)", "Email", "Video WebRTC (teleconsulta)"]))

    # Usuario derecha
    p.append(f'<text x="1600" y="140" font-family="{FONT}" font-size="12" font-weight="bold" letter-spacing="1.5" fill="#6B7280">CANALES</text>')
    p.append(box(1600, 430, 200, 120, "user", "Teléfono básico", ["Recibe SMS de cita", "(sin internet)"]))
    p.append(box(1600, 160, 200, 100, "data", "Región secundaria", ["Brazil South", "Copias de Cosmos DB y Blob"], dashed=True))

    # Flechas usuarios -> Front Door
    p.append(arrow([(240, 210), (300, 210)]))
    p.append(arrow([(240, 350), (265, 350), (265, 230), (300, 230)]))
    p.append(arrow([(240, 490), (275, 490), (275, 245), (300, 245)]))
    # Front Door -> SWA, -> APIM
    p.append(arrow([(410, 260), (410, 300)]))
    p.append(arrow([(520, 210), (580, 210)], "/api", 550, 200))
    # SWA <-> Entra
    p.append(arrow([(410, 400), (410, 440)], "OIDC + MFA", 455, 425, both=True, anchor="start"))
    # APIM -> Entra (validación token)
    p.append(arrow([(640, 260), (640, 280), (550, 280), (550, 500), (520, 500)], "valida JWT", 598, 276, dashed=True))
    # APIM -> Functions
    p.append(arrow([(760, 260), (760, 300)]))
    # Functions -> datos
    p.append(arrow([(806, 451), (850, 451), (850, 240), (885, 240)]))
    p.append(arrow([(806, 514), (866, 514), (866, 380), (885, 380)], "SAS", 836, 506))
    # fn-citas -> Service Bus (por arriba)
    p.append(arrow([(806, 382), (830, 382), (830, 290), (1165, 290), (1165, 210), (1200, 210)], "publica evento de cita", 1010, 304))
    # Service Bus -> fn-notificador -> ACS -> teléfono
    p.append(arrow([(1320, 260), (1320, 300)]))
    p.append(arrow([(1320, 390), (1320, 430)]))
    p.append(arrow([(1440, 490), (1600, 490)], "SMS", 1520, 482))
    # fn-videoconsulta -> ACS (por abajo)
    p.append(arrow([(806, 577), (830, 577), (830, 590), (1180, 590), (1180, 530), (1200, 530)], "token de videollamada", 1000, 584))
    # Replicación

    # Banda transversal de seguridad / observabilidad
    p.append(f'<rect x="295" y="650" width="1255" height="250" rx="12" fill="#ffffff" stroke="#CBD5E1" stroke-width="1.5"/>')
    p.append(f'<text x="315" y="676" font-family="{FONT}" font-size="12" font-weight="bold" letter-spacing="1.5" fill="#6B7280">SEGURIDAD, GOBIERNO, OBSERVABILIDAD Y COSTOS (TRANSVERSAL A TODOS LOS COMPONENTES)</text>')
    items = [
        ("sec", "Key Vault", ["Llaves CMK y secretos", "Rotación automática"]),
        ("sec", "Managed Identity", ["+ RBAC mínimo privilegio", "Sin credenciales en código"]),
        ("sec", "Defender for Cloud", ["Postura de seguridad", "Alertas de amenazas"]),
        ("sec", "Azure Policy", ["Iniciativa HIPAA/HITRUST", "Residencia de datos"]),
        ("ops", "Azure Monitor", ["App Insights + Log", "Analytics · auditoría"]),
        ("ops", "Cost Management", ["Presupuestos y alertas", "Etiquetas por campaña"]),
    ]
    for i, (c, t, l) in enumerate(items):
        p.append(box(315 + i * 205, 700, 190, 95, c, t, l))
    p.append(f'<text x="922" y="835" text-anchor="middle" font-family="{FONT}" font-size="13" fill="#374151">Cifrado en tránsito (TLS 1.2+) y en reposo (AES-256) · Private Endpoints para Cosmos DB y Storage · Registros de auditoría retenidos según normativa</text>')
    p.append(f'<text x="922" y="860" text-anchor="middle" font-family="{FONT}" font-size="13" fill="#374151">Cumplimiento: Ley 29733 y su Reglamento (D.S. 016-2024-JUS) · Ley 30024 (RENHICE) · Ley 30421 (Telesalud) · HIPAA como referencia</text>')

    # DevOps (abajo)
    p.append(f'<text x="300" y="965" font-family="{FONT}" font-size="12" font-weight="bold" letter-spacing="1.5" fill="#6B7280">AUTOMATIZACIÓN (DEVOPS)</text>')
    p.append(box(300, 985, 250, 95, "ops", "Repositorio GitHub", ["Código de app + infraestructura", "Revisión por pull request"]))
    p.append(box(640, 985, 300, 95, "ops", "GitHub Actions (CI/CD)", ["Pruebas, lint, escaneo SAST", "Login a Azure con OIDC (sin secretos)"]))
    p.append(box(1030, 985, 270, 95, "ops", "Terraform (IaC)", ["plan → aprobación → apply", "Entornos dev / prod"]))
    p.append(arrow([(550, 1032), (640, 1032)]))
    p.append(arrow([(940, 1032), (1030, 1032)]))
    p.append(arrow([(1300, 1032), (1400, 1032), (1400, 920)], "aprovisiona y despliega", 1410, 960, anchor="start"))

    # Leyenda
    lx, ly = 1600, 600
    p.append(f'<text x="{lx}" y="{ly}" font-family="{FONT}" font-size="12" font-weight="bold" letter-spacing="1.5" fill="#6B7280">LEYENDA</text>')
    for i, (c, t) in enumerate([("edge", "Entrega / red"), ("ident", "Identidad"), ("comp", "Cómputo"), ("data", "Datos"),
                                ("msg", "Mensajería"), ("sec", "Seguridad"), ("ops", "Operación / DevOps")]):
        f, s = CAT[c]
        yy = ly + 16 + i * 26
        p.append(f'<rect x="{lx}" y="{yy}" width="22" height="16" rx="3" fill="{f}" stroke="{s}" stroke-width="2"/>')
        p.append(f'<text x="{lx+32}" y="{yy+13}" font-family="{FONT}" font-size="13" fill="#1F2937">{t}</text>')
    yy = ly + 16 + 7 * 26
    p.append(f'<line x1="{lx}" y1="{yy+8}" x2="{lx+22}" y2="{yy+8}" stroke="#374151" stroke-width="2" stroke-dasharray="6 5"/>')
    p.append(f'<text x="{lx+32}" y="{yy+13}" font-family="{FONT}" font-size="13" fill="#1F2937">Fase 2 / flujo secundario</text>')

    p.append("</svg>")
    return "\n".join(p)


def flujo():
    W, H = 1820, 470
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">', DEFS,
         f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{W/2}" y="40" text-anchor="middle" font-family="{FONT}" font-size="24" font-weight="bold" fill="#111827">Flujo de una teleconsulta: de la reserva al historial clínico</text>']
    steps = [
        ("ident", "1. Inicio de sesión", ["Paciente se autentica", "en Entra External ID", "(MFA por SMS/email)"]),
        ("comp", "2. Reserva de cita", ["PWA → Front Door →", "API Management →", "fn-citas"]),
        ("data", "3. Registro", ["Cita guardada en", "Cosmos DB con", "partición por paciente"]),
        ("msg", "4. Evento en cola", ["Mensaje en Service Bus", "(confirmación +", "recordatorio 24 h)"]),
        ("msg", "5. Notificación", ["fn-notificador envía", "SMS / email vía", "Communication Services"]),
        ("comp", "6. Teleconsulta", ["fn-videoconsulta emite", "token; video WebRTC", "(modo solo audio)"]),
        ("data", "7. Historial", ["Médico registra nota;", "adjuntos a Blob;", "auditoría en Monitor"]),
    ]
    bw, gap, x0, y0 = 220, 34, 30, 90
    for i, (c, t, l) in enumerate(steps):
        x = x0 + i * (bw + gap)
        p.append(box(x, y0, bw, 140, c, t, l))
        if i < len(steps) - 1:
            p.append(arrow([(x + bw, y0 + 70), (x + bw + gap, y0 + 70)]))
    # Escalado elástico
    p.append(f'<rect x="30" y="280" width="1760" height="160" rx="12" fill="#FFF8F0" stroke="#E2A36A" stroke-width="1.5"/>')
    p.append(f'<text x="50" y="308" font-family="{FONT}" font-size="15" font-weight="bold" fill="#C2620A">Comportamiento durante una campaña de salud (pico de demanda)</text>')
    lines = [
        "• Front Door absorbe y cachea el contenido estático; el WAF filtra tráfico malicioso antes de llegar a la API.",
        "• API Management aplica límites por usuario; Azure Functions crea instancias nuevas según solicitudes concurrentes y vuelve a 0 al terminar.",
        "• Cosmos DB serverless cobra solo las RU consumidas; Service Bus desacopla los envíos masivos de SMS y los reintenta sin perder mensajes.",
        "• Cost Management dispara alertas al 50 %, 80 % y 100 % del presupuesto mensual etiquetado para la campaña.",
    ]
    for i, ln in enumerate(lines):
        p.append(f'<text x="50" y="{338 + i*24}" font-family="{FONT}" font-size="14" fill="#1F2937">{html.escape(ln)}</text>')
    p.append("</svg>")
    return "\n".join(p)


if __name__ == "__main__":
    out = sys.argv[1]
    open(f"{out}/arquitectura.svg", "w").write(architecture())
    open(f"{out}/flujo.svg", "w").write(flujo())
