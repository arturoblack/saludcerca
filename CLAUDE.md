# SaludCerca — contexto para Claude Code

Proyecto del PAC "Desarrollo de Aplicaciones en la Nube" (Maestría en Ingeniería de Software, U. Continental,
docente Marlon Luis Leandro Ramirez). Caso: plataforma de telemedicina para zonas rurales del Perú, en **Azure**.
Equipo: Jossip Jair Escalaya Juarez, Ivan Arturo Bolanos Victoria, Alejandro Andres Fernandez Alejandro,
Carlos Eduardo Puma Mendoza. Entrega: 8 de noviembre de 2026 (documento 8–10 págs, APA 7) + exposición de ~15 min con demo.

## Estructura
- `backend/` Python 3.11, Starlette + Pydantic, empaquetado como Azure Functions (Flex Consumption) vía `function_app.py`;
  `dev_server.py` para local. Tests: `cd backend && python -m pytest -q` (61 tests).
- `frontend/` React + TypeScript (Vite o `scripts/build-esbuild.mjs`). Modos de login: dev | oidc (mock) | entra (MSAL).
- `infra/` Terraform azurerm ~>4.50 (Cosmos serverless, Functions Flex, Service Bus, ACS, Blob con lifecycle, Key Vault, SWA, budget).
- `.github/workflows/` CI (pytest, ruff, build, terraform validate, CodeQL, e2e) y deploy con OIDC + aprobación manual.
- `e2e/demo_flow.py` recorrido Playwright completo; capturas en `docs/capturas/`.
- `docs/entregables/` documento Word del PAC y los scripts que lo generan (docx-js).

## Cómo correr
- Rápido: `docker compose up --build` → http://localhost:8080 (login dev).
- Pruebas de login real y SMS: `docker compose -f docker-compose.yml -f docker-compose.pruebas.yml up --build -d`
  → login OIDC (mock-oauth2-server 2.1.10, puerto 8090; usuario = id del seed, p. ej. `juan`), correos/SMS en Mailpit http://localhost:8025.
- Emulador Azure: `docker-compose.floci.yml` (floci-az: Cosmos + Service Bus).
- `./diagnostico.sh` junta estado, health, Mailpit y logs en `diagnostico.txt`.

## Reglas de diseño acordadas
- Debe poder desplegarse en local para pruebas **y** en Azure con Terraform; nada local debe romper el flujo CI/CD.
- Contenido clínico cifrado AES-256-GCM a nivel app (AAD paciente_id:nota_id); llave en Key Vault (`RECORD_ENC_KEY`).
- Agenda real: médicos definen bloques semanales; pacientes reservan por especialidad en turnos libres (1 h anticipación, 30 días).
- Lista de espera "Avisarme disponibilidad": al registrarse/abrir horario un médico de esa especialidad se avisa (SMS/correo/app) una vez.
- "Mis datos" (PUT /api/me): el usuario cambia celular, correo y canal de avisos.
- En modo SMTP local, los avisos de canal "app" también se copian a Mailpit (`<id>@app.saludcerca.local`).

## Pendiente
- Verificar en Docker del usuario que Mailpit recibe los avisos tras rebuild.
- Actualizar diapositivas de la demo (artifact Slides) con capturas reales y comparación Cosmos vs MySQL (ofrecido).
- Añadir al documento las líneas de agenda/lista de espera (ofrecido).
