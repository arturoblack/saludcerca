# SaludCerca — Plataforma de telemedicina rural en Azure

App de referencia del Producto Académico Colaborativo del curso **Desarrollo de Aplicaciones en la Nube** (Maestría en Ingeniería de Software, Universidad Continental). Implementa la arquitectura del documento: PWA para pacientes y médicos, API serverless en Python, Cosmos DB, Blob Storage, Service Bus y Communication Services, con infraestructura en Terraform y CI/CD con GitHub Actions.

> Todos los datos de la demo (pacientes, médicos y teléfonos) son ficticios.

## Qué hace

| Rol | Funciones |
|---|---|
| Paciente | Inicia sesión, reserva una cita eligiendo **especialidad → médico (o cualquiera) → día → turno libre**, por video o solo audio, recibe confirmación y recordatorio 24 h antes (en la app, por correo o por SMS si usa teléfono básico), consulta su historial y se une a la teleconsulta. |
| Médico | Define su **horario de atención** (días, franjas, duración del turno y días bloqueados); los pacientes solo reservan dentro de él. Ve su agenda, abre la historia clínica **solo de sus pacientes** e inicia la teleconsulta; durante la llamada toma apuntes y consulta la historia en un panel lateral. Registra la atención: diagnóstico, indicaciones, receta, signos vitales, apuntes (no visibles para el paciente) y adjuntos. |
| Coordinación (ONG) | Ve citas, avisos enviados y la **demanda en espera por especialidad**; **registra médicos** (con horario inicial opcional). **No** puede leer historias clínicas. |
| Socio externo (hospital, DIRESA) | Consulta paciente y citas en **FHIR R4** con una clave de integración, sin acceso a contenido clínico. |

Si una especialidad o un médico no tiene turnos, el paciente puede pedir **"Avisarme cuando haya turnos"**: cuando la coordinación registra un médico de esa especialidad con horario, un médico publica o amplía su horario, o se cancela una cita, se le avisa una sola vez por su canal (SMS si usa teléfono básico). El aviso masivo sale por la cola de Service Bus, fuera de la solicitud HTTP.

Además, la app **mide la conexión real** (tiempo de respuesta al servidor) al reservar y al entrar a la consulta, y recomienda o activa solo audio si la señal es débil.

## Cómo se corresponde con la arquitectura

| Componente del diagrama | Dónde está |
|---|---|
| Static Web Apps (PWA, modo sin conexión) | `frontend/` (React + TypeScript, `public/sw.js`, `manifest.webmanifest`) |
| Entra External ID (login + MFA, roles) | `frontend/src/auth.ts` (MSAL) y `backend/app/auth.py` (validación del JWT) |
| Azure Functions: fn-citas, fn-historial, fn-documentos, fn-videoconsulta | `backend/app/main.py`, publicado con `func.AsgiFunctionApp` en `backend/function_app.py` |
| fn-notificador (disparado por la cola) | `notificador` en `backend/function_app.py` → `app/messaging.py:handle_event` |
| Cosmos DB serverless (partición por paciente) | `backend/app/repository.py` (`CosmosRepository`) |
| Blob Storage + SAS de delegación de usuario | `backend/app/integrations.py:url_subida` |
| Service Bus (confirmación inmediata, recordatorio programado) | `backend/app/messaging.py` (`schedule_messages` 24 h antes) |
| Communication Services (SMS, email, token de video) | `AcsNotifier` y `token_videollamada` |
| Cifrado AES-256-GCM del contenido clínico (llave en Key Vault) | `backend/app/cifrado.py` y `app/historial.py`; secreto `record-enc-key` en `infra/security.tf` |
| Horarios de atención y turnos libres | `backend/app/agenda.py`; rutas `/api/especialidades`, `/api/disponibilidad`, `/api/medicos/me/agenda`; contenedor `agendas` de Cosmos DB |
| Lista de espera y avisos de disponibilidad | `backend/app/avisos.py` (evento `disponibilidad` en la cola); rutas `/api/avisos-disponibilidad`, `POST /api/medicos`; contenedor `solicitudes` |
| Fachada FHIR R4 para socios | `backend/app/fhir.py`, rutas `/api/fhir/Patient/{id}` y `/api/fhir/Appointment?patient=` |
| Key Vault, Managed Identity, RBAC, auditoría con IP | `infra/security.tf` y el logger `saludcerca.audit` |
| Almacenamiento escalonado, presupuesto con alertas | `infra/main.tf` (política de ciclo de vida) e `infra/costs_edge.tf` |
| Front Door + WAF (opcional) | `infra/costs_edge.tf` (`habilitar_front_door = true`) |
| CI/CD con OIDC | `.github/workflows/ci.yml` y `deploy.yml` |

## Estructura

```
backend/            API Python (Starlette + Pydantic) que corre en Azure Functions o con uvicorn
  app/              dominio, auth, repositorios, mensajería, integraciones, datos de demo
  tests/            48 pruebas (pytest): API, permisos, cifrado, FHIR, auditoría
  function_app.py   entrada de Azure Functions (HTTP + disparador de Service Bus)
  dev_server.py     servidor local: API + PWA en http://localhost:8000
frontend/           PWA React + TypeScript (Vite)
infra/              Terraform (azurerm 4.x)
e2e/demo_flow.py    recorrido completo con Playwright; guarda capturas en docs/capturas/
.github/workflows/  CI (pruebas, build, terraform validate, CodeQL, e2e) y despliegue
```

## Correr la demo en local

### Opción A — Python y Node (recomendada para la presentación)

```bash
# 1. Frontend
cd frontend
npm install
npm run build            # genera frontend/dist

# 2. Backend (sirve también la PWA)
cd ../backend
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
python dev_server.py     # http://localhost:8000
```

Para desarrollar el frontend con recarga automática: `python dev_server.py` en una terminal y `npm run dev` en otra (http://localhost:5173; `/api` se redirige al puerto 8000).

### Opción B — Docker (contenedores separados)

```bash
docker compose up --build
```

| Contenedor | Qué hace | URL |
|---|---|---|
| `web` | Compila la PWA de React con Vite (etapa Node) y la sirve con nginx; reenvía `/api` a la API | http://localhost:8080 |
| `api` | API en Python con datos en memoria | http://localhost:8000/api/health |

### Opción C — Servicios de Azure emulados con floci-az

```bash
docker compose -f docker-compose.yml -f docker-compose.floci.yml up --build
```

Agrega el contenedor `floci-az` y cambia la API a **Cosmos DB, Blob Storage y Service Bus emulados** ([floci-az](https://floci.io/floci-az/)). La API crea la base y los contenedores de Cosmos al iniciar y `dev_server.py` hace de fn-notificador leyendo la cola por AMQP. floci-az levanta el broker de Service Bus (Artemis) como otro contenedor, por eso necesita el socket de Docker.

Diferencias con Azure: floci-az no implementa **mensajes programados** de Service Bus (responde 501), así que el recordatorio de 24 h queda registrado como "programado" en vez de encolarse. Communication Services, Entra ID y Static Web Apps no tienen emulador: la autenticación es de demostración, los SMS y correos se registran en "Avisos" y la videollamada es simulada.

### Opción D — Probar el login y los SMS en local (opcional)

```bash
docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up --build
# también se puede sumar floci: -f docker-compose.yml -f docker-compose.floci.yml -f docker-compose.pruebas.yml
```

| Servicio | Para qué | URL |
|---|---|---|
| `oidc` ([mock-oauth2-server](https://github.com/navikt/mock-oauth2-server)) | Login real con OpenID Connect (Authorization Code + PKCE) y tokens JWT firmados que la API valida (firma, emisor, vencimiento) | http://localhost:8090 |
| `mailpit` | Bandeja donde llegan los SMS (como "SMS para +51…") y los correos que envía la app | http://localhost:8025 |

En http://localhost:8080 pulse **Ingresar**; en la pantalla del proveedor de prueba escriba como *username* el usuario de la demo (`pac-rosa`, `pac-juan`, `med-luis`, `admin-ong`…). Las confirmaciones, recordatorios y avisos de disponibilidad aparecen en Mailpit.

Este archivo es solo para pruebas: **no cambia el despliegue en Azure ni el CI/CD**. En Azure el login es Entra External ID (`AUTH_MODE=entra`) y los avisos salen por Communication Services (`NOTIFIER_BACKEND=acs`); ambos valores los fija Terraform.

### Pruebas

```bash
cd backend && pytest -q                      # pruebas de la API
python e2e/demo_flow.py                      # con el servidor corriendo; requiere: pip install playwright && playwright install chromium
```

### Probar la fachada FHIR

En la demo local la clave de integración no está configurada. Para probarla:

```bash
export INTEGRATION_KEYS_SHA256=$(printf 'clave-hospital-demo' | sha256sum | cut -d' ' -f1)
python dev_server.py
curl -H "x-api-key: clave-hospital-demo" http://localhost:8000/api/fhir/Patient/pac-rosa
curl -H "x-api-key: clave-hospital-demo" "http://localhost:8000/api/fhir/Appointment?patient=pac-rosa"
```

## Guion de la demo (2–3 minutos)

1. **Ingreso**: elegir a *Rosa Quispe* (paciente que usa la app). En Azure este paso es Entra External ID con código por SMS o correo.
2. **Mis citas**: mostrar la cita de mañana. **Reservar nueva cita**: elegir *Pediatría*, dejar *Cualquiera disponible*, escoger un día (cada uno muestra cuántos turnos libres tiene) y un turno; señalar la línea "Su conexión: … ms" (si es lenta, se preselecciona solo audio).
3. **Avisos**: aparece la confirmación y el recordatorio programado para 24 h antes (en Azure, un mensaje programado en Service Bus).
4. **Mi historial**: la atención anterior con receta y signos vitales (se guardan cifrados y se descifran solo al mostrarlos).
5. **Unirse a la consulta**: cámara y micrófono, botón **Solo audio** (para señal débil) y **Colgar**.
6. **Salir** y entrar como *Juan Ccahuana* (teléfono básico): reservar *Medicina general* con el Dr. Luis Herrera y mostrar en **Avisos** que el mensaje sale **por SMS**.
7. **Salir** y entrar como el *Dr. Luis Herrera*: abrir a Rosa e **Iniciar teleconsulta**. Durante la llamada, el panel lateral permite tomar **apuntes con marca de tiempo**, llenar la atención y revisar la **historia del paciente** sin colgar. Al colgar, el borrador se conserva en la ficha; completar receta y signos vitales y guardar (la cita pasa a "atendida").
8. En la pestaña **Mi horario** del Dr. Herrera: agregar una franja el sábado por la tarde o bloquear un día y guardar. Volver como paciente: los turnos cambian de inmediato.
9. Como *Juan*, reservar *Cardiología* (aún sin médicos) y pulsar **Avisarme cuando haya turnos**.
10. Entrar como *Coordinación*: ver "1 en espera" en la demanda, **registrar** un cardiólogo con horario de lunes a viernes y ver que se avisó a 1 paciente. Volver como *Juan*: en **Avisos** llegó el SMS de turnos disponibles.
11. Entrar como *Coordinación*: indicadores y avisos, **sin acceso** a historias clínicas.

Si la red falla durante la presentación, usar las capturas de `docs/capturas/`.

## Despliegue en Azure

### 1. Requisitos previos (una sola vez)

1. **Suscripción de Azure** (Azure for Students sirve para el piloto).
2. **Cuenta de Storage para el estado de Terraform** (ver `infra/backend.hcl.example`).
3. **Microsoft Entra External ID** (no se automatiza con Terraform):
   - Crear un *tenant externo* (p. ej. `saludcerca.ciamlogin.com`).
   - Registrar la **API**: exponer el ámbito `access_as_user` y crear los App Roles `Paciente`, `Medico` y `Admin`.
   - Registrar la **SPA** con la URL de Static Web Apps como redirect URI y permiso al ámbito de la API.
   - Crear el flujo de registro e inicio de sesión con código de un solo uso por correo y MFA por SMS.
4. **Identidad para GitHub Actions (OIDC)**: un registro de aplicación con *federated credential* para el repositorio, con rol `Owner` (o `Contributor` + `User Access Administrator`) sobre la suscripción del proyecto.
5. En GitHub, crear el entorno `produccion` con **aprobación obligatoria** y estas *variables*: `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `TFSTATE_RG`, `TFSTATE_ACCOUNT`, `ENTORNO`, `ENTRA_TENANT_SUBDOMAIN`, `ENTRA_TENANT_ID`, `ENTRA_API_CLIENT_ID`, `ENTRA_SPA_CLIENT_ID`.

### 2. Pipeline

Cada *push* a `main` ejecuta: `terraform plan` → **aprobación manual** → `terraform apply` → despliegue de la API en Functions (con prueba de humo a `/api/health`) → despliegue de la PWA en Static Web Apps.

### 3. Antes de producción

- **Región**: comprobar que Functions Flex Consumption esté disponible en `chilecentral` (`az functionapp list-flexconsumption-locations`); si no, usar `brazilsouth`.
- **SMS hacia Perú**: requiere un remitente habilitado con *Messaging Connect* en Communication Services (`acs_sms_from`).
- **Videollamada real**: el backend ya emite el token de ACS; falta integrar `@azure/communication-calling` en `frontend/src/views/Teleconsulta.tsx` (hoy simula la sala con la cámara local).
- **Rotación de la llave de cifrado**: las notas guardan la versión del formato (`v1`); para rotar la llave hay que agregar el identificador de llave al formato y volver a cifrar las notas existentes con un proceso por lotes.
- **Claves FHIR**: guardar en el secreto `INTEGRATION_KEYS_SHA256` de GitHub el hash de cada clave entregada a un socio (nunca la clave en claro).
- **Endurecimiento pendiente**: Private Endpoints con integración de red virtual, llaves administradas por el cliente (CMK) en Cosmos DB y Storage, API Management delante de la Function App y servidor FHIR (fase 2).

## Estado de verificación

- ✅ Pruebas del backend (48) y recorrido de punta a punta con Playwright, en modo local en memoria.
- ⚠️ No ejecutados en el entorno donde se generó el código (sin acceso a los registros de paquetes ni a HashiCorp): `terraform validate`, `ruff` y el despliegue real. El pipeline de CI los ejecuta en el primer *push*; revisar y corregir lo que reporte.
