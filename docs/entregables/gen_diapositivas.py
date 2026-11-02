import json, os, sys
from datetime import datetime, timezone

ROOT = sys.argv[1]
IMG_ARQ = "/_blob/84ba53ba26504c32715d0cf88ca093e1"

DARK = "#10283A"; BG = "#F5F7F4"; BG2 = "#E7F0EC"; CARD = "#FCFDFB"; LINE = "#D5DED9"
TEAL = "#0B7468"; TEAL_L = "#6FD6C5"; ORANGE = "#B8560F"; ORANGE_L = "#F2A35E"
SOFT = "#4A5A66"; SOFT_D = "#BFD3D0"
HEAD = "font-family:'Rubik', Arial, sans-serif"
BODY = "'Public Sans', Arial, sans-serif"

slides = []

def section(sid, inner, notes, bg=BG, color=DARK, footer=True, extra="", pad=None):
    pad = pad or ("128px 128px 160px" if footer else "128px")
    foot = ""
    if footer:
        n = len(slides) + 1
        foot = (f'<div style="position:absolute;left:128px;bottom:64px;width:1664px;display:flex;justify-content:space-between">'
                f'<p style="font-size:24px;color:{SOFT}">Telemedicina rural en Azure · Producto Académico Colaborativo</p>'
                f'<p style="font-size:24px;color:{SOFT}">{n}</p></div>')
    html = (f'<section id="{sid}" data-transition="fade" style="background:{bg};color:{color};font-family:{BODY};'
            f'padding:{pad};display:flex;flex-direction:column;gap:40px{extra}">\n{inner}\n{foot}\n<aside>{notes}</aside>\n</section>\n')
    slides.append((sid, html))

def heading(eyebrow, title, eb_color=TEAL, color=DARK):
    return (f'<div style="display:flex;flex-direction:column;gap:12px">'
            f'<p style="font-size:24px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{eb_color}">{eyebrow}</p>'
            f'<h2 style="{HEAD};font-size:64px;font-weight:600;line-height:1.1;color:{color}">{title}</h2></div>')

def card(title, body, accent=TEAL, extra=""):
    return (f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;background:{CARD};border:1px solid {LINE};'
            f'border-top:6px solid {accent};border-radius:16px;padding:32px{extra}">'
            f'<h3 style="{HEAD};font-size:32px;font-weight:600;line-height:1.2;color:{DARK}">{title}</h3>'
            f'<p style="font-size:26px;line-height:1.4;color:{SOFT}">{body}</p></div>')

# 1. Portada
section("cover", f'''
<div style="position:absolute;left:0;top:0;width:24px;height:1080px;background:{TEAL_L}"></div>
<p style="font-size:24px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{TEAL_L}">Desarrollo de Aplicaciones en la Nube · Universidad Continental</p>
<h1 style="{HEAD};font-size:104px;font-weight:600;line-height:1.05;color:#F5F7F4">Telemedicina para<br>zonas rurales en Azure</h1>
<p style="font-size:36px;line-height:1.35;color:{SOFT_D};width:1300px">Arquitectura nativa en la nube y demo de SaludCerca, la app para pacientes y médicos</p>
<div style="flex:1"></div>
<div style="display:flex;gap:48px">
<p style="font-size:26px;line-height:1.5;color:#F5F7F4">Jossip Jair Escalaya Juarez<br>Ivan Arturo Bolanos Victoria</p>
<p style="font-size:26px;line-height:1.5;color:#F5F7F4">Alejandro Andres Fernandez Alejandro<br>Carlos Eduardo Puma Mendoza</p>
<div style="flex:1"></div>
<p style="font-size:26px;line-height:1.5;color:{SOFT_D};text-align:right">Docente: Marlon Luis Leandro Ramirez<br>Noviembre de 2026</p>
</div>''', "Jossip Escalaya — 30 s. Saludo, presentación del equipo y del tema: una ONG quiere llevar consultas virtuales a zonas rurales con poco presupuesto. Hoy mostramos la arquitectura en Azure y la app funcionando.",
        bg=DARK, color="#F5F7F4", footer=False, pad="128px 128px 128px 176px")

# 2. Problema
section("problema", heading("El caso", "Llevar la consulta médica donde no llega el médico") + f'''
<div style="display:flex;gap:32px">
{card("Distancia", "Pacientes a horas de un establecimiento con especialista; viajar cuesta tiempo y dinero.", TEAL)}
{card("Conectividad limitada", "Señal 3G intermitente y muchos teléfonos básicos sin datos móviles.", ORANGE)}
{card("Presupuesto restringido", "Una ONG sin equipo de infraestructura y con picos de demanda en campañas de salud.", TEAL)}
</div>
<p style="font-size:32px;line-height:1.4;color:{DARK};width:1500px">Objetivo: consultas virtuales, historial clínico digital y avisos de citas, <b>aun con recursos limitados</b>.</p>''',
        "Jossip Escalaya — 1 min. Explicar el contexto: la telesalud está reconocida por la Ley 30421. Las tres restricciones del caso guían todas las decisiones de diseño: distancia, conectividad y presupuesto. Remarcar que el número de usuarios cambia mucho durante las campañas.")

# 3. Requisitos -> respuesta
rows = [
    ("Autenticación segura", "Microsoft Entra External ID con MFA y roles paciente / médico"),
    ("Historial confiable y accesible", "Cosmos DB + Blob Storage, cifrados y con backup continuo"),
    ("Notificaciones de citas", "Service Bus + Communication Services (SMS, email)"),
    ("Escalado elástico", "Servicios serverless que crecen solos y vuelven a cero"),
    ("Costos eficientes", "Pago por uso, almacenamiento por niveles y alertas de presupuesto"),
]
tr = "".join(f'<tr><td style="width:36%;font-weight:600">{a}</td><td style="width:64%">{b}</td></tr>' for a, b in rows)
section("requisitos", heading("Requisitos", "Cinco requisitos, cinco respuestas concretas") + f'''
<table style="font-size:28px;color:{DARK};padding:18px 24px">
<tr><th style="width:36%">Lo que pide el caso</th><th style="width:64%">Cómo lo resolvemos en Azure</th></tr>
{tr}
</table>''', "Jossip Escalaya — 1 min 30 s. Recorrer la tabla fila por fila: es el resumen de toda la propuesta. Cada respuesta se detalla en las siguientes diapositivas.")

# 4. Modelo de servicio
def col(title, tag, lines, hl=False):
    bg = DARK if hl else CARD; fg = "#F5F7F4" if hl else DARK; sub = SOFT_D if hl else SOFT
    border = f"border:3px solid {TEAL};" if hl else f"border:1px solid {LINE};"
    lis = "".join(f"<li>{l}</li>" for l in lines)
    return (f'<div style="flex:1;display:flex;flex-direction:column;gap:16px;background:{bg};{border}border-radius:16px;padding:40px">'
            f'<p style="font-size:24px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{TEAL_L if hl else SOFT}">{tag}</p>'
            f'<h3 style="{HEAD};font-size:44px;font-weight:600;color:{fg}">{title}</h3>'
            f'<ul style="font-size:26px;line-height:1.45;color:{sub}">{lis}</ul></div>')
section("modelo", heading("Modelo de servicio", "Elegimos PaaS serverless") + f'''
<div style="display:flex;gap:32px">
{col("IaaS", "Descartado", ["Control total del servidor", "Pagamos aunque no haya uso", "Parches y escalado manuales"])}
{col("PaaS serverless", "Seleccionado", ["Escala sola y baja a cero", "Pago por ejecución y por GB", "Azure opera la plataforma"], True)}
{col("SaaS", "Descartado", ["Rápido de adoptar", "Sin SMS ni modo offline", "No se adapta a la norma local"])}
</div>''', "Ivan Bolanos — 1 min. Justificación técnica: el equipo es pequeño, PaaS le quita la administración de servidores. Justificación económica: la demanda es intermitente; con máquinas virtuales pagaríamos el pico todo el mes. SaaS no permite SMS a teléfonos básicos ni interoperar con el RENHICE.")

# 5. Arquitectura
layers = [("1", "Entrega e identidad", "Front Door + WAF, Static Web Apps (PWA) y Entra External ID", TEAL),
          ("2", "API y cómputo", "API Management y Azure Functions (Flex Consumption)", ORANGE),
          ("3", "Datos", "Cosmos DB serverless, Blob Storage y FHIR en fase 2", TEAL),
          ("4", "Mensajería", "Service Bus y Communication Services (SMS, video)", ORANGE)]
items = "".join(
    f'<div style="display:flex;gap:16px;align-items:start">'
    f'<p style="font-size:26px;font-weight:700;color:#F5F7F4;background:{c};border-radius:50%;padding:4px 16px">{n}</p>'
    f'<div style="flex:1;display:flex;flex-direction:column;gap:4px"><h3 style="{HEAD};font-size:28px;font-weight:600;color:{DARK}">{t}</h3>'
    f'<p style="font-size:24px;line-height:1.35;color:{SOFT}">{d}</p></div></div>' for n, t, d, c in layers)
section("arquitectura", heading("Arquitectura", "Cuatro capas sobre la región Chile Central") + f'''
<div style="display:flex;gap:40px;align-items:start">
<img src="{IMG_ARQ}" alt="Diagrama de arquitectura de la plataforma de telemedicina en Azure con capas de entrega, cómputo, datos, mensajería, seguridad y DevOps" style="width:1030px;height:640px;object-fit:contain;background:#FFFFFF;border:1px solid {LINE};border-radius:16px">
<div style="flex:1;display:flex;flex-direction:column;gap:28px">{items}</div>
</div>''', "Ivan Bolanos — 2 min. Recorrer el diagrama de izquierda a derecha: el usuario entra por Front Door, se autentica con Entra, la API pasa por API Management a las funciones, que leen y escriben en Cosmos DB y Blob Storage. Las citas generan eventos en Service Bus y el notificador envía SMS. Abajo: seguridad transversal y el pipeline DevOps. Región Chile Central porque no hay región Azure en Perú; copias en Brazil South.")

# 6. Servicios gestionados
svc = [("Entra External ID", "Login, MFA y roles. Gratis hasta 50 000 usuarios activos al mes.", TEAL),
       ("Azure Functions", "Lógica de citas e historial; escala por eventos y baja a cero.", ORANGE),
       ("Cosmos DB serverless", "Historias clínicas en JSON; se paga por solicitud consumida.", TEAL),
       ("Blob Storage", "Resultados e imágenes; pasan solos de Hot a Cool y a Archive.", ORANGE),
       ("Service Bus", "Cola de citas con reintentos; ningún aviso se pierde.", TEAL),
       ("Communication Services", "SMS, email y videollamada en un solo servicio.", ORANGE)]
cards = "".join(card(t, d, c) for t, d, c in svc)
section("servicios", heading("Servicios gestionados", "Seis servicios gestionados, el doble de lo pedido") + f'''
<div style="display:grid;grid-template-columns:repeat(3, 1fr);gap:28px">{cards}</div>''',
        "Ivan Bolanos — 1 min 30 s. La rúbrica pide al menos tres. Destacar tres: Cosmos DB por el esquema flexible del historial; Service Bus porque desacopla la reserva del envío masivo de SMS; Communication Services porque el SMS es clave para teléfonos básicos (hacia Perú se habilita con Messaging Connect).")

# 7. Divisor demo
section("demo-intro", f'''
<div style="flex:1"></div>
<p style="font-size:24px;font-weight:700;letter-spacing:3px;text-transform:uppercase;color:{ORANGE_L}">Demo en vivo</p>
<h2 style="{HEAD};font-size:104px;font-weight:600;line-height:1.05;color:#F5F7F4">SaludCerca,<br>de la reserva a la consulta</h2>
<p style="font-size:32px;line-height:1.4;color:{SOFT_D};width:1300px">Una paciente de una comunidad rural agenda su cita, recibe el recordatorio y se conecta con el médico.</p>
<div style="flex:1"></div>''', "Alejandro Fernandez — 15 s. Transición a la demo. Si la conexión falla durante la presentación, usar las capturas de las dos diapositivas siguientes.",
        bg=TEAL, color="#F5F7F4", footer=False)

# 8. Demo pantallas
def phone(label, screen):
    return (f'<div style="display:flex;flex-direction:column;gap:16px;align-items:center">'
            f'<div style="width:330px;height:580px;background:{DARK};border-radius:44px;padding:16px;display:flex;flex-direction:column">'
            f'<div style="flex:1;background:{CARD};border-radius:30px;padding:24px;display:flex;flex-direction:column;gap:14px">{screen}</div></div>'
            f'<p style="font-size:26px;font-weight:600;color:{DARK}">{label}</p></div>')
btn = lambda t, bg=TEAL, fg="#F5F7F4": f'<p style="font-size:24px;font-weight:700;text-align:center;color:{fg};background:{bg};border-radius:14px;padding:12px">{t}</p>'
field = lambda t: f'<p style="font-size:24px;color:{SOFT};border:2px solid {LINE};border-radius:12px;padding:10px 14px">{t}</p>'
s1 = (f'<p style="{HEAD};font-size:32px;font-weight:600;color:{TEAL}">SaludCerca</p>'
      f'<p style="font-size:24px;color:{SOFT}">Ingresa con tu DNI</p>' + field("DNI") + field("Código SMS") +
      '<div style="flex:1"></div>' + btn("Ingresar"))
s2 = (f'<p style="{HEAD};font-size:30px;font-weight:600;color:{DARK}">Mis citas</p>'
      f'<div style="background:{BG2};border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:6px">'
      f'<p style="font-size:24px;font-weight:700;color:{DARK}">Mañana, 10:00</p>'
      f'<p style="font-size:24px;color:{SOFT}">Medicina general</p></div>'
      f'<p style="font-size:24px;color:{SOFT}">Historial: 3 consultas</p>'
      '<div style="flex:1"></div>' + btn("Unirse a la consulta"))
s3 = (f'<div style="flex:1;background:{DARK};border-radius:16px;padding:16px;display:flex;flex-direction:column;justify-content:end">'
      f'<p style="font-size:24px;color:#F5F7F4">Médico conectado</p></div>'
      f'<p style="font-size:24px;color:{ORANGE}">Señal débil: solo audio</p>'
      f'<div style="display:flex;gap:10px"><div style="flex:1">{btn("Audio", BG2, DARK)}</div><div style="flex:1">{btn("Colgar", ORANGE)}</div></div>')
sms = (f'<div style="flex:1;display:flex;flex-direction:column;gap:20px;align-self:stretch;padding-top:24px">'
       f'<p style="font-size:24px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{ORANGE}">Teléfono básico</p>'
       f'<p style="font-size:28px;line-height:1.45;color:{DARK};background:{CARD};border:2px solid {LINE};border-radius:24px 24px 24px 4px;padding:28px">'
       f'SaludCerca: su cita es mañana a las 10:00 en la posta. Responda 1 para confirmar.</p>'
       f'<p style="font-size:26px;line-height:1.4;color:{SOFT}">Quien no tiene smartphone recibe el aviso por SMS; los demás, en la app o por correo.</p></div>')
section("demo-pantallas", heading("Demo · lo que ve la paciente", "Tres pantallas y un SMS") + f'''
<div style="display:flex;gap:40px;align-items:start">
{phone("1. Ingreso con MFA", s1)}{phone("2. Cita y recordatorio", s2)}{phone("3. Teleconsulta", s3)}{sms}
</div>''', "Alejandro Fernandez — 2 min. Mostrar en vivo: (1) la paciente ingresa con su DNI y el código que llega por SMS, eso es Entra External ID con MFA; (2) agenda la cita y ve su historial; (3) al día siguiente se une a la videollamada y, si la señal cae, la app pasa a solo audio. A la derecha, el SMS que recibe un familiar con teléfono básico. Nombres y datos de la demo son ficticios.",
        pad="128px 128px 160px")

# 9. Demo detrás
steps = [("Inicio de sesión", "Entra External ID valida identidad y MFA."),
         ("Reserva", "La PWA llama a API Management y a fn-citas."),
         ("Registro", "La cita se guarda en Cosmos DB."),
         ("Evento", "fn-citas publica un mensaje en Service Bus."),
         ("Aviso", "fn-notificador envía SMS o email por ACS."),
         ("Teleconsulta", "fn-videoconsulta emite el token de la sala."),
         ("Historial", "El médico registra la nota; queda auditada.")]
grid = "".join(
    f'<div style="display:flex;gap:20px;align-items:start">'
    f'<p style="{HEAD};font-size:28px;font-weight:600;color:#F5F7F4;background:{TEAL if i % 2 == 0 else ORANGE};border-radius:12px;padding:6px 16px">{i+1}</p>'
    f'<div style="flex:1;display:flex;flex-direction:column;gap:4px"><h3 style="{HEAD};font-size:30px;font-weight:600;color:{DARK}">{t}</h3>'
    f'<p style="font-size:26px;line-height:1.35;color:{SOFT}">{d}</p></div></div>' for i, (t, d) in enumerate(steps))
section("demo-nube", heading("Demo · lo que pasa en la nube", "Siete pasos detrás de una consulta") + f'''
<div style="display:grid;grid-template-columns:repeat(2, 1fr);gap:36px 64px">{grid}</div>''',
        "Alejandro Fernandez — 1 min. Mientras se ve la demo, explicar qué servicio actúa en cada paso. Si hay tiempo, mostrar en el portal de Azure la métrica de ejecuciones de Functions o el mensaje en la cola de Service Bus.",
        bg=BG2)

# 10. Escalabilidad y automatización
scale = [("Front Door", "sirve la PWA desde caché"), ("Functions", "suma instancias en segundos"),
         ("Cosmos DB", "cobra solo lo consumido"), ("Service Bus", "encola los SMS masivos")]
sl = "".join(f'<div style="display:flex;gap:16px;align-items:baseline;border-bottom:1px solid {LINE};padding:0 0 14px 0">'
             f'<p style="font-size:28px;font-weight:700;color:{DARK};width:240px">{a}</p><p style="flex:1;font-size:26px;color:{SOFT}">{b}</p></div>' for a, b in scale)
pipe = [("Pull request", "pruebas, lint y escaneo SAST"), ("GitHub Actions", "login a Azure con OIDC, sin secretos"),
        ("Terraform", "plan, aprobación y apply"), ("Producción", "pruebas de humo y monitoreo")]
pl = "".join(
    (f'<div style="display:flex;flex-direction:column;gap:4px;background:{CARD};border:1px solid {LINE};border-left:6px solid {ORANGE};border-radius:12px;padding:18px 24px">'
     f'<h3 style="{HEAD};font-size:28px;font-weight:600;color:{DARK}">{a}</h3><p style="font-size:24px;color:{SOFT}">{b}</p></div>')
    + ('' if i == len(pipe) - 1 else f'<x-shape kind="arrow-down" style="background:{ORANGE};width:28px;height:28px;align-self:center"></x-shape>')
    for i, (a, b) in enumerate(pipe))
section("escala", heading("Escalabilidad y automatización", "Crece solo en campañas y se despliega solo") + f'''
<div style="display:flex;gap:64px;align-items:start">
<div style="flex:1;display:flex;flex-direction:column;gap:18px">
<p style="font-size:24px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{TEAL}">Escala elástica</p>{sl}
<p style="font-size:26px;line-height:1.4;color:{DARK};padding-top:8px">Funciones sin estado: agregar instancias no requiere coordinación. AKS se evaluó y se descartó por costo fijo.</p>
</div>
<div style="flex:1;display:flex;flex-direction:column;gap:10px">
<p style="font-size:24px;font-weight:700;letter-spacing:2px;text-transform:uppercase;color:{ORANGE}">CI/CD e infraestructura como código</p>{pl}
</div></div>''', "Carlos Puma — 1 min 30 s. Izquierda: cómo responde cada componente a una campaña. Derecha: el pipeline de GitHub Actions; toda la infraestructura está en Terraform, así que podemos recrear el entorno completo en minutos. Mostrar en el repositorio el último workflow en verde si hay tiempo.")

# 11. Seguridad
sec = [("Identidad", "MFA, roles y Managed Identities: sin contraseñas en el código."),
       ("Cifrado", "TLS 1.2+ en tránsito; AES-256 con llaves propias en Key Vault."),
       ("Red", "Private Endpoints para datos; WAF con límite de solicitudes."),
       ("Auditoría", "Cada acceso a una historia queda registrado en Azure Monitor.")]
sc = "".join(card(t, d, TEAL if i % 2 == 0 else ORANGE) for i, (t, d) in enumerate(sec))
norms = ["Ley 29733 y D.S. 016-2024-JUS", "Ley 30024 (RENHICE)", "Ley 30421 (Telesalud)", "HIPAA como referencia"]
pills = "".join(f'<p style="font-size:24px;font-weight:600;color:{DARK};background:{BG2};border-radius:40px;padding:10px 24px">{n}</p>' for n in norms)
section("seguridad", heading("Seguridad y cumplimiento", "Confianza cero sobre datos clínicos sensibles") + f'''
<div style="display:grid;grid-template-columns:repeat(4, 1fr);gap:24px">{sc}</div>
<div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center"><p style="font-size:26px;font-weight:700;color:{DARK}">Cumplimiento:</p>{pills}</div>''',
        "Carlos Puma — 1 min 30 s. La historia clínica es dato sensible. Explicar los cuatro controles. Cumplimiento: Azure Policy aplica la iniciativa HIPAA/HITRUST; en Perú rigen la Ley de Protección de Datos y su nuevo reglamento, que regula el flujo transfronterizo (los datos están en Chile y Brasil), la ley del RENHICE y la Ley Marco de Telesalud.")

# 12. Costos
def big(n, cap, c):
    return (f'<div style="flex:1;display:flex;flex-direction:column;gap:12px;background:{CARD};border:1px solid {LINE};border-radius:16px;padding:40px">'
            f'<p style="{HEAD};font-size:96px;font-weight:600;line-height:1;color:{c}">{n}</p>'
            f'<p style="font-size:28px;line-height:1.35;color:{SOFT}">{cap}</p></div>')
section("costos", heading("Optimización de costos", "Pagamos por consulta, no por servidor") + f'''
<div style="display:flex;gap:32px">
{big("≈ $436", "al mes en el escenario base: 3000 pacientes y 1500 teleconsultas", DARK)}
{big("≈ $75", "de infraestructura base; el resto es video y SMS", TEAL)}
{big("≈ $0,25", "por teleconsulta, sumando video y recordatorios", ORANGE)}
</div>
<p style="font-size:28px;line-height:1.45;color:{DARK}"><b>Palancas:</b> escala a cero · almacenamiento Hot → Cool → Archive · SMS solo a teléfonos básicos · presupuestos con alertas al 50, 80 y 100 % · etiquetas por campaña</p>''',
        "Carlos Puma — 1 min. Montos en dólares, precios de lista referenciales (Tabla 5 del documento). Mensaje clave: más del 80 % del gasto es comunicación y solo existe si hay consultas; la infraestructura fija cuesta alrededor de 75 dólares al mes.")

# 13. Conclusiones
ben = ["Plataforma profesional con un equipo técnico pequeño", "Costo alineado con la actividad clínica", "Infraestructura reproducible y auditable"]
ret = ["Conectividad rural: offline y solo audio", "Costo de SMS y video a negociar", "Datos fuera del país: cumplir la Ley 29733", "Interoperabilidad FHIR con el RENHICE", "Capacitación de médicos y pacientes"]
ul = lambda xs, c: "".join(f'<li>{x}</li>' for x in xs)
section("conclusiones", heading("Conclusiones", "Viable hoy, con retos claros para el piloto") + f'''
<div style="display:flex;gap:48px">
<div style="flex:1;display:flex;flex-direction:column;gap:16px;background:{CARD};border:1px solid {LINE};border-top:6px solid {TEAL};border-radius:16px;padding:40px">
<h3 style="{HEAD};font-size:40px;font-weight:600;color:{TEAL}">Beneficios</h3><ul style="font-size:28px;line-height:1.5;color:{DARK}">{ul(ben, TEAL)}</ul></div>
<div style="flex:1;display:flex;flex-direction:column;gap:16px;background:{CARD};border:1px solid {LINE};border-top:6px solid {ORANGE};border-radius:16px;padding:40px">
<h3 style="{HEAD};font-size:40px;font-weight:600;color:{ORANGE}">Retos</h3><ul style="font-size:28px;line-height:1.5;color:{DARK}">{ul(ret, ORANGE)}</ul></div>
</div>
<p style="font-size:28px;color:{DARK}"><b>Siguiente paso:</b> piloto en una región sanitaria, medir el costo por consulta y ampliar de forma gradual.</p>''',
        "Jossip Escalaya — 1 min. Cerrar respondiendo al caso: la arquitectura cumple los cinco requisitos. Mencionar los retos con honestidad y la recomendación del piloto.", bg=BG2)

# 14. Gracias
section("gracias", f'''
<div style="flex:1"></div>
<h2 style="{HEAD};font-size:120px;font-weight:600;line-height:1.05;color:#F5F7F4">Gracias</h2>
<p style="font-size:40px;line-height:1.35;color:{SOFT_D}">¿Preguntas?</p>
<div style="flex:1"></div>
<p style="font-size:26px;color:{SOFT_D}">Jossip Escalaya · Ivan Bolanos · Alejandro Fernandez · Carlos Puma</p>''',
        "Todos — tiempo restante para preguntas. Preguntas probables: por qué no AKS (costo fijo y personal), por qué Chile Central (no hay región en Perú, menor latencia), qué pasa sin internet (PWA offline y SMS).",
        bg=DARK, color="#F5F7F4", footer=False)

os.makedirs(f"{ROOT}/project/slides", exist_ok=True)
for sid, html in slides:
    open(f"{ROOT}/project/slides/{sid}.html", "w").write(html)
deck = {
    "v": 4, "createdOnFiles": {"v": 1, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}, "lists": "css",
    "title": "Telemedicina rural en Azure — Presentación PAC", "cover": "cover",
    "order": [s for s, _ in slides],
    "sections": {
        "s1": {"description": "El caso y lo que pide", "start": "cover"},
        "s2": {"description": "Diseño de la arquitectura en Azure", "start": "modelo"},
        "s3": {"description": "Demo de la app SaludCerca", "start": "demo-intro"},
        "s4": {"description": "Escala, seguridad y costos", "start": "escala"},
        "s5": {"description": "Cierre", "start": "conclusiones"},
    },
    "faces": {
        "rubik": {"family": "Rubik", "href": "https://fonts.googleapis.com/css2?family=Rubik:wght@400..700&display=swap"},
        "public-sans": {"family": "Public Sans", "href": "https://fonts.googleapis.com/css2?family=Public+Sans:wght@400..700&display=swap"},
    },
    "designSystems": [],
}
json.dump(deck, open(f"{ROOT}/project/deck.json", "w"), ensure_ascii=False, indent=1)
print(len(slides))
