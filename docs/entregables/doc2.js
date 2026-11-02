const fs = require('fs');
const {
  Document, Packer, Paragraph, TextRun, HeadingLevel, AlignmentType, ImageRun, Table, TableRow, TableCell,
  WidthType, ShadingType, BorderStyle, LevelFormat, Footer, PageNumber, PageBreak, VerticalAlign, PageOrientation, Header, Tab, TabStopType, LeaderType, InternalHyperlink, Bookmark,
} = require('docx');

const OUT = process.argv[2];
const FONT = 'Arial';
const LINE = 360; // 1.5
const CONTENT_W = 9026; // A4 con márgenes de 2.54 cm

// ---------- helpers ----------
function runs(text, base = {}) {
  // **negrita** y *cursiva* simples
  const parts = [];
  const re = /(\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) parts.push(new TextRun({ text: text.slice(last, m.index), ...base }));
    const t = m[0];
    if (t.startsWith('**')) parts.push(new TextRun({ text: t.slice(2, -2), bold: true, ...base }));
    else parts.push(new TextRun({ text: t.slice(1, -1), italics: true, ...base }));
    last = m.index + t.length;
  }
  if (last < text.length) parts.push(new TextRun({ text: text.slice(last), ...base }));
  return parts;
}
const P = (text, opts = {}) => new Paragraph({
  children: runs(text), alignment: AlignmentType.LEFT,
  spacing: { line: LINE, after: 0 }, indent: { firstLine: 720 }, ...opts,
});
const TOC = [];
const H1 = (t) => { TOC.push([1, t]); return new Paragraph({ heading: HeadingLevel.HEADING_1, alignment: AlignmentType.CENTER, children: [new TextRun(t)] }); };
const H2 = (t) => { TOC.push([2, t]); return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] }); };
const B = (text) => new Paragraph({
  children: runs(text), numbering: { reference: 'bullets', level: 0 },
  alignment: AlignmentType.LEFT, spacing: { line: LINE, after: 0 },
});
const caption = (label, title) => [
  new Paragraph({ keepNext: true, spacing: { before: 120, after: 0, line: LINE }, children: [new TextRun({ text: label, bold: true })] }),
  new Paragraph({ keepNext: true, spacing: { after: 60, line: LINE }, children: [new TextRun({ text: title, italics: true })] }),
];
const note = (t) => new Paragraph({ spacing: { before: 60, after: 160, line: 276 }, children: runs(t, { size: 20 }) });

function figure(label, title, file, wPx, hPx, source, w = 600) {
  const h = Math.round(w * hPx / wPx);
  return [
    ...caption(label, title),
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: false, spacing: { after: 0 },
      children: [new ImageRun({ type: 'png', data: fs.readFileSync(file), transformation: { width: w, height: h } })] }),
    ...(source ? [note(source)] : [new Paragraph({ spacing: { after: 120 }, children: [] })]),
  ];
}

const rule = { style: BorderStyle.SINGLE, size: 8, color: '000000' };
const none = { style: BorderStyle.NONE, size: 0, color: 'FFFFFF' };
function table(headers, rows, widths) {
  const n = rows.length;
  const cell = (text, i, header, ri = -1) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    borders: { left: none, right: none, top: header ? rule : none, bottom: (header || ri === n - 1) ? rule : none },
    margins: { top: 60, bottom: 60, left: 90, right: 90 }, verticalAlign: VerticalAlign.CENTER,
    children: [new Paragraph({ spacing: { line: 240, after: 0 },
      children: runs(text, { size: 18, ...(header ? { bold: true } : {}) }) })],
  });
  return new Table({
    width: { size: widths.reduce((a, b) => a + b, 0), type: WidthType.DXA }, columnWidths: widths,
    rows: [
      new TableRow({ tableHeader: true, cantSplit: true, children: headers.map((h, i) => cell(h, i, true)) }),
      ...rows.map((r, ri) => new TableRow({ cantSplit: true, children: r.map((c, i) => {
        const tc = cell(c, i, false, ri);
        return tc;
      }) })),
    ],
  });
}

// ---------- portada ----------
const center = (text, size, bold = false, after = 200) => new Paragraph({
  alignment: AlignmentType.CENTER, spacing: { after, line: 276 },
  children: [new TextRun({ text, size, bold })],
});
const portada = [
  center('ESCUELA DE POSGRADO UNIVERSIDAD CONTINENTAL', 28, true, 360),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 360 },
    children: [new ImageRun({ type: 'png', data: fs.readFileSync(`${OUT}/logo_uc.png`), transformation: { width: 246, height: 77 },
      altText: { title: 'Logo', description: 'Logo Universidad Continental', name: 'logo' } })] }),
  center('MAESTRÍA EN INGENIERÍA DE SOFTWARE', 26, true, 160),
  center('MODALIDAD A DISTANCIA', 24, false, 480),
  center('MATERIA:', 24, false, 120),
  center('Desarrollo de Aplicaciones en la Nube', 26, true, 420),
  center('PRODUCTO ACADÉMICO COLABORATIVO:', 24, false, 120),
  center('Diseño de la arquitectura nativa en la nube de una plataforma de telemedicina para zonas rurales en Microsoft Azure: servicios gestionados, escalabilidad, seguridad y optimización de costos', 26, true, 1500),
  center('AUTORES:', 24, false, 120),
  center('Jossip Jair Escalaya Juarez', 22, true, 40),
  center('Ivan Arturo Bolanos Victoria', 22, true, 40),
  center('Alejandro Andres Fernandez Alejandro', 22, true, 40),
  center('Carlos Eduardo Puma Mendoza', 22, true, 1900),
  center('DOCENTE:', 24, false, 120),
  center('Marlon Luis Leandro Ramirez', 26, true, 420),
  center('2026 - PERÚ', 26, true, 0),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---------- contenido ----------
const body = [];
const add = (...x) => body.push(...x.flat());

add(H1('1. Introducción'));
add(P('En el Perú, buena parte de la población rural vive a horas de distancia de un establecimiento de salud con médico especialista. La telesalud, reconocida por la Ley N.° 30421, Ley Marco de Telesalud, es una estrategia para reducir esa brecha; su uso creció de forma notable desde la pandemia de COVID-19 (Curioso & Galán-Rodas, 2020). El presente trabajo diseña la arquitectura de una plataforma de telemedicina para una organización sin fines de lucro que necesita ofrecer consultas virtuales, un historial clínico digitalizado y notificaciones de citas a pacientes de zonas rurales, con un presupuesto limitado y una demanda que cambia de forma brusca durante las campañas de salud.'));
add(P('La computación en la nube resulta adecuada para este escenario por tres razones. Primero, elimina la inversión inicial en servidores y la traslada a un gasto operativo que se paga según el uso (Mell & Grance, 2011). Segundo, ofrece elasticidad: la capacidad crece cuando una campaña atrae a miles de pacientes y se reduce cuando la demanda baja. Tercero, los proveedores ofrecen servicios gestionados con controles de seguridad, cifrado y certificaciones de cumplimiento que una ONG difícilmente podría construir por cuenta propia. Se eligió **Microsoft Azure** como proveedor y la propuesta sigue los cinco pilares del Azure Well-Architected Framework: confiabilidad, seguridad, optimización de costos, excelencia operativa y eficiencia del rendimiento (Microsoft, s.f.-a).'));

add(H1('2. Desarrollo'));
add(H2('2.1. Modelo de servicio seleccionado'));
add(P('Se adopta un modelo **PaaS con enfoque serverless**: la organización desarrolla y despliega su propio código (API, lógica de citas e historial), pero delega en Azure la administración de servidores, sistemas operativos, parches, balanceo y escalado. La Tabla 1 resume la comparación que sustenta la decisión.'));
add(caption('Tabla 1', 'Comparación de modelos de servicio para el caso de telemedicina rural'));
add(table(
  ['Criterio', 'IaaS (máquinas virtuales)', 'PaaS / serverless (seleccionado)', 'SaaS (plataforma comercial)'],
  [
    ['Control y personalización', 'Total, incluido el sistema operativo', 'Alto sobre la aplicación y los datos', 'Bajo; limitado a la configuración del proveedor'],
    ['Esfuerzo operativo', 'Alto: parches, respaldos y escalado manual', 'Bajo: el proveedor opera la plataforma', 'Mínimo'],
    ['Escalabilidad', 'Requiere configurar grupos de escalado', 'Automática y por evento; escala a cero', 'Depende del plan contratado'],
    ['Modelo de costo', 'Pago por hora aunque no haya uso', 'Pago por ejecución, solicitud o GB', 'Licencia por usuario o médico'],
    ['Adecuación al caso', 'Costosa para cargas intermitentes', 'Ideal para demanda variable y equipo técnico pequeño', 'Poca flexibilidad para SMS, offline y normativa local'],
  ],
  [1800, 2300, 2626, 2300]));
add(note('*Nota.* Elaboración propia a partir de Mell y Grance (2011) y Microsoft (s.f.-a).'));
add(P('**Justificación técnica.** La ONG no cuenta con un equipo grande de infraestructura; con PaaS sus pocos desarrolladores se concentran en las funciones clínicas y no en administrar servidores. Los servicios elegidos incluyen alta disponibilidad, cifrado y copias de seguridad sin configuración adicional. **Justificación económica.** La carga de una plataforma rural es intermitente: hay picos durante las campañas y valles en temporadas normales o de noche. Con IaaS se pagaría la capacidad del pico durante todo el mes; con serverless se paga solo lo consumido, y varios servicios incluyen cuotas mensuales gratuitas, como el millón de ejecuciones de Azure Functions en el plan Consumption o los primeros 50 000 usuarios activos mensuales de Microsoft Entra External ID (Microsoft, s.f.-b; Microsoft, s.f.-c). Se descarta SaaS porque una solución comercial cerrada no permitiría integrar SMS para teléfonos básicos, el funcionamiento sin conexión ni la interoperabilidad con el Registro Nacional de Historias Clínicas Electrónicas (RENHICE).'));

add(H2('2.2. Arquitectura de la aplicación'));
add(P('La Figura 1 presenta la arquitectura de referencia. La solución se despliega en la región **Chile Central**, la más cercana al Perú, con tres zonas de disponibilidad, y guarda copias de respaldo en **Brazil South**. Sus componentes se organizan en cuatro capas y un plano transversal de seguridad y operación.'));
add(B('**Capa de entrega e identidad.** Azure Front Door cachea el frontend, termina TLS y aplica reglas de firewall (WAF). El frontend es una aplicación web progresiva (PWA) en Azure Static Web Apps: se instala en el teléfono y funciona sin conexión en puestos de salud rurales. La autenticación se delega en Microsoft Entra External ID, que reemplazó a Azure AD B2C para nuevos clientes desde mayo de 2025 (Microsoft, s.f.-c).'));
add(B('**Capa de API y cómputo.** Azure API Management (plan Consumption) publica una API REST única, valida el token JWT emitido por Entra y aplica cuotas por usuario. La lógica de negocio se implementa como microfunciones en Azure Functions (plan Flex Consumption): *fn-citas*, *fn-historial*, *fn-documentos* y *fn-videoconsulta*. Una fachada FHIR R4 expone a socios externos (hospital de referencia, DIRESA) los datos básicos del paciente y el estado de sus citas, sin contenido clínico (HL7 International, 2019).'));
add(B('**Capa de datos.** Azure Cosmos DB (API NoSQL, modo serverless) almacena pacientes, citas e historias clínicas como documentos JSON particionados por paciente. Los adjuntos (resultados de laboratorio, imágenes, PDF) se guardan en Azure Blob Storage y se acceden con URL firmadas (SAS) de corta duración. En la fase 2 se incorporará Azure Health Data Services con un servidor FHIR (HL7) para interoperar con el RENHICE.'));
add(B('**Capa de mensajería.** Cada cita genera un evento en Azure Service Bus; una función desacoplada (*fn-notificador*) consume la cola y envía confirmaciones y recordatorios mediante Azure Communication Services (ACS), que además proporciona la videollamada WebRTC de la teleconsulta.'));
add(figure('Figura 1', 'Arquitectura de referencia de la plataforma de telemedicina rural en Microsoft Azure',
  `${OUT}/arquitectura.png`, 3640, 2260, '*Nota.* Elaboración propia. Las líneas discontinuas indican componentes de la fase 2 o flujos secundarios.'));
add(H2('2.3. Servicios gestionados integrados'));
add(P('La propuesta integra más de los tres servicios gestionados requeridos. La Tabla 2 detalla los seis principales, su función y la razón de su elección.'));
add(caption('Tabla 2', 'Servicios gestionados principales y justificación de su elección'));
add(table(
  ['Servicio', 'Función en la plataforma', 'Justificación de la elección'],
  [
    ['Microsoft Entra External ID', 'Registro, inicio de sesión, MFA y roles (paciente, médico, administrador)', 'Gestión de identidades para clientes (CIAM) con estándares OpenID Connect y OAuth 2.0; gratuito hasta 50 000 usuarios activos al mes (Microsoft, s.f.-c).'],
    ['Azure Functions (Flex Consumption)', 'Lógica de negocio de citas, historial, documentos y notificaciones', 'Escala por eventos y baja a cero instancias cuando no hay uso; es el plan serverless recomendado por Microsoft e incluye integración con red virtual (Microsoft, s.f.-b).'],
    ['Azure Cosmos DB (serverless)', 'Base de datos NoSQL de pacientes, citas e historias clínicas', 'Esquema flexible para historias heterogéneas, latencia baja y cobro por unidad de solicitud (RU) consumida; resulta más barato que la capacidad aprovisionada en cargas intermitentes (Microsoft, s.f.-d).'],
    ['Azure Blob Storage', 'Almacenamiento de resultados, imágenes y documentos', 'Niveles de acceso Hot, Cool, Cold y Archive con reglas automáticas de ciclo de vida, además de políticas de inmutabilidad para evidencias clínicas.'],
    ['Azure Service Bus', 'Cola de eventos de citas y notificaciones', 'Desacopla la reserva del envío de mensajes, reintenta ante fallos y aísla los mensajes no procesables en una cola de mensajes fallidos (dead-letter).'],
    ['Azure Communication Services', 'SMS, correo electrónico y videollamada', 'Un solo servicio para notificaciones y teleconsulta. El SMS hacia Perú se habilita con Messaging Connect, que amplía la cobertura a más de 190 países mediante socios (Microsoft, s.f.-e).'],
  ],
  [2100, 2500, 4426]));
add(note('*Nota.* Elaboración propia. Servicios complementarios: Front Door, API Management, Static Web Apps, Key Vault, Azure Monitor, Defender for Cloud y Cost Management.'));
add(P('El SMS es un requisito crítico del caso: en muchas comunidades rurales los pacientes usan teléfonos básicos sin datos móviles. Por eso el canal de notificación se elige según el perfil del paciente: SMS para quienes no tienen smartphone y correo o notificación en la PWA para los demás, lo que además reduce costos.'));

add(H2('2.4. Estrategia de escalabilidad y automatización'));
add(P('**Escalabilidad horizontal y elástica.** Cada componente escala de forma independiente y automática, sin intervención del equipo (Tabla 3). Como la arquitectura no guarda estado en el cómputo (las funciones no conservan sesión y todo el estado vive en Cosmos DB y Blob Storage), es posible agregar instancias en paralelo sin coordinación.'));
add(caption('Tabla 3', 'Mecanismo de escalado por componente'));
add(table(
  ['Componente', 'Mecanismo de escalado', 'Comportamiento en una campaña'],
  [
    ['Front Door + Static Web Apps', 'Red perimetral (edge) global con caché', 'El contenido estático se sirve desde la caché y no consume cómputo.'],
    ['API Management (Consumption)', 'Serverless, sin capacidad fija', 'Absorbe picos de solicitudes; los límites por usuario evitan abusos.'],
    ['Azure Functions (Flex)', 'Escalado por concurrencia de solicitudes y por longitud de cola', 'Agrega instancias en segundos y vuelve a cero al terminar; para la jornada de campaña se pueden configurar instancias «siempre listas» y evitar arranques en frío.'],
    ['Cosmos DB', 'Serverless (hasta 5000 RU/s por contenedor)', 'Si el consumo supera unos 100 millones de RU al mes, se migra a capacidad aprovisionada con escalado automático.'],
    ['Service Bus + fn-notificador', 'Nivelación de carga mediante cola', 'Los envíos masivos se encolan y se procesan al ritmo que admite el proveedor de SMS.'],
  ],
  [2300, 2900, 3826]));
add(note('*Nota.* Elaboración propia con base en Microsoft (s.f.-b) y Microsoft (s.f.-d).'));
add(P('**Infraestructura como código.** Toda la infraestructura se declara con **Terraform** (proveedor *azurerm*), organizada en módulos (identidad, red, datos, cómputo, mensajería y monitoreo) y con estado remoto en Blob Storage. Así se pueden recrear entornos idénticos de desarrollo y producción, revisar los cambios antes de aplicarlos y recuperar la plataforma completa ante un desastre (Morris, 2020).'));
add(P('**Integración y despliegue continuos (CI/CD).** Se usa **GitHub Actions** con dos flujos de trabajo: (a) en cada *pull request*: pruebas unitarias, análisis estático de seguridad (SAST), escaneo de dependencias y `terraform plan`; (b) al fusionar con la rama principal: despliegue en desarrollo, pruebas de humo, aprobación manual y despliegue en producción. La autenticación de GitHub ante Azure usa federación OIDC, por lo que no se almacenan contraseñas ni secretos en el repositorio.'));
add(P('**Alternativa evaluada: Kubernetes.** Se consideró Azure Kubernetes Service (AKS). Ofrece portabilidad y control fino (Burns et al., 2022), pero exige mantener un clúster con nodos encendidos permanentemente y personal especializado, lo que contradice la restricción presupuestal. Si en el futuro se necesitaran contenedores, por ejemplo para un servicio de inteligencia artificial de apoyo al triaje, la opción intermedia sería Azure Container Apps, que también escala a cero.'));

add(H2('2.5. Seguridad y cumplimiento'));
add(P('La historia clínica es un dato personal sensible. La seguridad se diseña con el enfoque de **confianza cero** (*Zero Trust*): verificar siempre la identidad, aplicar el mínimo privilegio y suponer que una brecha es posible. Los controles de la aplicación siguen el OWASP Top 10 (OWASP Foundation, 2021).'));
add(B('**Identidad y control de acceso.** MFA obligatoria para médicos y opcional para pacientes (código por SMS o correo); control de acceso basado en roles (RBAC) en la aplicación, de modo que un médico solo ve a los pacientes asignados. Los servicios se comunican entre sí con identidades administradas (*Managed Identities*), sin contraseñas en el código.'));
add(B('**Cifrado.** En tránsito, TLS 1.2 o superior en todos los extremos. En reposo, AES-256 del servicio en Cosmos DB y Blob Storage, con opción de llaves administradas por el cliente (CMK) en Key Vault. Además, el contenido clínico (diagnóstico, indicaciones, receta y signos vitales) se cifra en la aplicación con AES-256-GCM antes de guardarse, con una llave que vive en Key Vault: quien acceda directamente a la base solo ve texto cifrado.'));
add(B('**Red.** Cosmos DB y Storage solo aceptan tráfico mediante *Private Endpoints*; el WAF de Front Door aplica reglas de limitación de solicitudes y filtrado geográfico.'));
add(B('**Monitoreo y auditoría.** Azure Monitor y Log Analytics registran cada acceso a una historia clínica (quién, cuándo y desde qué dirección IP); Microsoft Defender for Cloud evalúa la postura de seguridad y emite alertas de amenazas.'));
add(B('**Integraciones.** Los socios externos usan claves de integración de las que solo se guarda el hash SHA-256, comparado en tiempo constante; la fachada FHIR aplica minimización de datos.'));
add(B('**Gobierno.** Azure Policy asigna la iniciativa integrada *HIPAA/HITRUST*, que evalúa de forma continua los controles técnicos, y una política que restringe las regiones permitidas (Microsoft, s.f.-f).'));
add(P('La Tabla 4 relaciona los requisitos normativos aplicables con los controles de la arquitectura. HIPAA es una ley estadounidense y no rige en el Perú, pero se usa como referencia internacional de buenas prácticas, tal como sugiere el enunciado del caso.'));
add(caption('Tabla 4', 'Correspondencia entre requisitos normativos y controles implementados'));
add(table(
  ['Norma', 'Requisito principal', 'Control en la arquitectura'],
  [
    ['Ley N.° 29733 y su Reglamento (D.S. 016-2024-JUS)', 'Consentimiento, medidas de seguridad y regulación del flujo transfronterizo de datos personales', 'Consentimiento informado en el registro, cifrado con CMK, Private Endpoints y evaluación del flujo transfronterizo (datos alojados en Chile y Brasil).'],
    ['Ley N.° 30024 (modificada por la Ley N.° 31750)', 'Confidencialidad, accesibilidad e interoperabilidad de las historias clínicas electrónicas', 'RBAC por médico asignado, auditoría de accesos con IP, fachada FHIR R4 implementada y servidor FHIR en la fase 2 para interoperar con el RENHICE.'],
    ['Ley N.° 30421, D. Leg. N.° 1490 y su reglamento (D.S. N.° 005-2021-SA)', 'Telesalud como estrategia para ampliar la cobertura', 'Teleconsulta por video con opción de solo audio según la conexión medida.'],
    ['HIPAA Security Rule (referencia)', 'Salvaguardas administrativas, físicas y técnicas', 'Iniciativa HIPAA/HITRUST en Azure Policy, registros de auditoría y backup continuo con restauración a un punto en el tiempo.'],
  ],
  [2300, 3000, 3726]));
add(note('*Nota.* Elaboración propia a partir de Congreso de la República del Perú (2011, 2013, 2016), Presidencia de la República del Perú (2020), Ministerio de Salud del Perú (2021), Ministerio de Justicia y Derechos Humanos (2024) y U.S. Department of Health and Human Services (2022).'));

add(H2('2.6. Optimización de costos'));
add(P('La Tabla 5 estima el costo mensual para un escenario base de 3000 pacientes activos, 1500 teleconsultas de 15 minutos, 4500 SMS y 100 GB de documentos. Los precios son referenciales, en dólares estadounidenses y sin impuestos; deben confirmarse en la Calculadora de precios de Azure para la región elegida.'));
add(caption('Tabla 5', 'Estimación referencial de costo mensual en el escenario base'));
add(table(
  ['Servicio', 'Supuesto de uso', 'USD/mes (aprox.)'],
  [
    ['Entra External ID', '3000 usuarios activos al mes (gratis hasta 50 000)', '0'],
    ['Static Web Apps (Standard)', 'Una aplicación con dominio propio', '9'],
    ['Front Door (Standard)', 'Tarifa base de USD 35 más tráfico reducido', '40'],
    ['API Management + Functions', 'Menos de 1 millón de llamadas; gran parte dentro de la cuota gratuita', '5'],
    ['Cosmos DB (serverless)', '30 millones de RU y 10 GB a USD 0,25 cada uno', '10'],
    ['Blob Storage', '100 GB repartidos entre los niveles Hot y Cool', '3'],
    ['Service Bus (Basic) + Key Vault', 'Mensajes y operaciones con llaves', '2'],
    ['ACS: videollamadas', '1500 × 15 min × 2 participantes × USD 0,004', '180'],
    ['ACS: SMS (Messaging Connect)', '4500 SMS a unos USD 0,04 cada uno (tarifa variable según el socio)', '180'],
    ['Monitor, Defender (CSPM básico) y Cost Management', 'Registros dentro de la cuota gratuita', '5'],
    ['**Total estimado**', '', '**≈ 436**'],
  ],
  [3000, 4426, 1600]));
add(note('*Nota.* Elaboración propia con tarifas publicadas por Microsoft (s.f.-b, s.f.-d, s.f.-e, s.f.-g). Los costos de comunicación son variables y crecen en proporción al número de consultas.'));
add(P('Más del 80 % del gasto corresponde a comunicaciones (video y SMS) y depende directamente de la actividad clínica; la infraestructura base cuesta alrededor de USD 75 al mes. En consecuencia, el costo marginal de una teleconsulta, sumando video y recordatorios, ronda los USD 0,25. Las medidas de control son las siguientes:'));
add(B('**Pago por uso y escala a cero:** Functions, API Management y Cosmos DB en modo serverless no cobran cuando no hay actividad.'));
add(B('**Almacenamiento escalonado:** una regla de ciclo de vida mueve los documentos a Cool a los 30 días, a Cold a los 90 y a Archive al año, lo que permite conservarlos durante el plazo legal a una fracción del costo.'));
add(B('**Optimización de canales:** se envía SMS solo a quienes no tienen smartphone; la teleconsulta usa por defecto la resolución de video más baja aceptable y ofrece un modo de solo audio.'));
add(B('**Monitoreo de consumo:** presupuestos en Cost Management con alertas al 50 %, 80 % y 100 %, y etiquetas (*tags*) por entorno y por campaña para atribuir el gasto a cada financiador.'));

add(H2('2.7. Prototipo implementado y verificación'));
add(P('Para validar el diseño, el equipo construyó **SaludCerca**, un prototipo funcional de la arquitectura: una API en Python que se ejecuta en Azure Functions, una PWA en React, la infraestructura en Terraform y los flujos de GitHub Actions. También corre en un computador con datos ficticios, sin costo. La Tabla 6 relaciona cada requisito del caso con el componente que lo resuelve y con la evidencia disponible en el prototipo.'));
add(caption('Tabla 6', 'Trazabilidad entre requisitos, componentes y evidencia del prototipo'));
add(table(
  ['Requisito del caso', 'Componente', 'Evidencia en el prototipo'],
  [
    ['1. Autenticación segura', 'Entra External ID con MFA y roles; la API valida firma, emisor y audiencia del token', 'Pruebas automáticas: sin token responde 401; un rol sin permiso responde 403.'],
    ['2. Historial confiable y accesible', 'Cosmos DB con backup continuo; contenido clínico cifrado con AES-256-GCM y llave en Key Vault', 'Prueba: el diagnóstico y la receta no aparecen en el registro guardado; el texto cifrado no se puede copiar a otro paciente.'],
    ['3. Mensajería de citas', 'Service Bus y Communication Services; SMS solo para teléfonos básicos', 'Confirmación inmediata y recordatorio programado 24 h antes; el paciente con teléfono básico recibe SMS.'],
    ['4. Escalado elástico', 'Functions Flex Consumption con tope de instancias, Cosmos DB serverless y cola', 'API sin estado; tope y memoria por instancia definidos como variables de Terraform.'],
    ['5. Costos eficientes', 'Pago por uso, almacenamiento escalonado, presupuesto con alertas y cuota de registros', 'Recursos de Terraform: política de ciclo de vida, presupuesto 50/80/100 % y cuota diaria de 1 GB.'],
    ['Interoperabilidad', 'Fachada FHIR R4 con clave de integración', 'Pruebas: Patient y Appointment responden sin datos clínicos; sin clave válida responde 401.'],
  ],
  [2000, 3300, 3726]));
add(note('*Nota.* Elaboración propia.'));
add(P('Una función pensada para el contexto rural es la **medición real de la conexión**: al reservar y al entrar a la consulta, la app mide el tiempo de respuesta del servidor y, si es lento, preselecciona la consulta solo por audio (Figura 2). El médico registra la atención de forma estructurada, con receta y signos vitales, que el paciente ve descifrados en su historial.'));
add(figure('Figura 2', 'Prototipo SaludCerca (datos ficticios): reserva con medición de la conexión, historial del paciente y registro de la atención por el médico',
  `${OUT}/prototipo.png`, 3678, 1500, '', 500));
add(P('La verificación combinó 24 pruebas automáticas de la API (autenticación, permisos por rol, reserva y doble reserva, notificaciones, cifrado, auditoría y FHIR) y un recorrido de punta a punta con Playwright en un navegador real por las pantallas de paciente, médico y coordinación. El flujo de integración continua repite en cada cambio esas pruebas, la validación de Terraform y el análisis de seguridad con CodeQL.'));

add(H1('3. Conclusiones'));
add(P('La arquitectura PaaS/serverless propuesta en Azure responde a los cinco requisitos del caso. La autenticación segura se resuelve con Entra External ID y MFA; el historial clínico se guarda de forma confiable en Cosmos DB y Blob Storage, con cifrado y copias continuas; las notificaciones se envían por Service Bus y Communication Services, con SMS para teléfonos básicos; la escalabilidad es elástica y automática en todas las capas; y el costo fijo es bajo, porque la mayor parte del gasto varía con el uso real. El prototipo SaludCerca demuestra que el diseño es implementable y deja pruebas automáticas como evidencia de cada requisito.'));
add(P('El principal beneficio para la ONG es que puede operar una plataforma de nivel profesional con un equipo técnico pequeño y pagar en función de la actividad clínica. La infraestructura como código y el CI/CD con GitHub Actions hacen que el sistema sea reproducible, auditable y fácil de recuperar ante desastres.'));
add(P('La implementación enfrenta, sin embargo, retos importantes: (a) la conectividad rural, que obliga a diseñar el modo sin conexión y el modo de solo audio desde el inicio; (b) el costo de las comunicaciones, que se vuelve el rubro dominante y debe negociarse con los socios de SMS; (c) el flujo transfronterizo de datos, porque no existe una región de Azure en el Perú, lo que exige cumplir el Reglamento de la Ley N.° 29733; (d) la interoperabilidad con el RENHICE, que requiere adoptar el estándar FHIR; y (e) la adopción por parte de médicos y pacientes, que demanda capacitación y una interfaz muy sencilla. Se recomienda empezar con un piloto en una región sanitaria, medir el costo por consulta y luego ampliar el alcance de forma gradual.'));

// ---------- referencias ----------
const refs = [
  'Burns, B., Beda, J., Hightower, K., & Evenson, L. (2022). *Kubernetes: Up and running* (3.ª ed.). O’Reilly Media.',
  'Congreso de la República del Perú. (2011). *Ley N.° 29733, Ley de Protección de Datos Personales*. Diario Oficial El Peruano.',
  'Congreso de la República del Perú. (2013). *Ley N.° 30024, Ley que crea el Registro Nacional de Historias Clínicas Electrónicas*. Diario Oficial El Peruano.',
  'Congreso de la República del Perú. (2016). *Ley N.° 30421, Ley Marco de Telesalud*. Diario Oficial El Peruano.',
  'Curioso, W. H., & Galán-Rodas, E. (2020). El rol de la telesalud en la lucha contra el COVID-19 y la evolución del marco normativo peruano. *Acta Médica Peruana, 37*(3), 366–375. https://doi.org/10.35663/amp.2020.373.1004',
  'HL7 International. (2019). *FHIR release 4 (v4.0.1)*. https://hl7.org/fhir/R4/',
  'Mell, P., & Grance, T. (2011). *The NIST definition of cloud computing* (NIST Special Publication 800-145). National Institute of Standards and Technology. https://doi.org/10.6028/NIST.SP.800-145',
  'Microsoft. (s.f.-a). *Azure Well-Architected Framework*. Microsoft Learn. Recuperado el 2 de noviembre de 2026, de https://learn.microsoft.com/azure/well-architected/',
  'Microsoft. (s.f.-b). *Azure Functions pricing*. Recuperado el 2 de noviembre de 2026, de https://azure.microsoft.com/pricing/details/functions/',
  'Microsoft. (s.f.-c). *Overview of Microsoft Entra External ID in external tenants*. Microsoft Learn. Recuperado el 2 de noviembre de 2026, de https://learn.microsoft.com/entra/external-id/customers/overview-customers-ciam',
  'Microsoft. (s.f.-d). *Understand your Azure Cosmos DB bill*. Microsoft Learn. Recuperado el 2 de noviembre de 2026, de https://learn.microsoft.com/azure/cosmos-db/understand-your-bill',
  'Microsoft. (s.f.-e). *Pricing scenarios: Azure Communication Services*. Microsoft Learn. Recuperado el 2 de noviembre de 2026, de https://learn.microsoft.com/azure/communication-services/concepts/pricing',
  'Microsoft. (s.f.-f). *Regulatory compliance details for HIPAA HITRUST*. Microsoft Learn. Recuperado el 2 de noviembre de 2026, de https://learn.microsoft.com/azure/governance/policy/samples/hipaa-hitrust',
  'Microsoft. (s.f.-g). *Compare pricing between Azure Front Door tiers*. Microsoft Learn. Recuperado el 2 de noviembre de 2026, de https://learn.microsoft.com/azure/frontdoor/understanding-pricing',
  'Ministerio de Justicia y Derechos Humanos. (2024, 30 de noviembre). *Decreto Supremo N.° 016-2024-JUS, que aprueba el Reglamento de la Ley N.° 29733, Ley de Protección de Datos Personales*. https://www.gob.pe/institucion/anpd/normas-legales/6554453-16-2024-jus',
  'Ministerio de Salud del Perú. (2021). *Decreto Supremo N.° 005-2021-SA, que aprueba el Reglamento de la Ley N.° 30421, Ley Marco de Telesalud, y del Decreto Legislativo N.° 1490*. Diario Oficial El Peruano. https://busquedas.elperuano.pe/dispositivo/NL/1922320-2',
  'Morris, K. (2020). *Infrastructure as code: Dynamic systems for the cloud age* (2.ª ed.). O’Reilly Media.',
  'OWASP Foundation. (2021). *OWASP Top 10:2021*. https://owasp.org/Top10/',
  'Presidencia de la República del Perú. (2020). *Decreto Legislativo N.° 1490, que fortalece los alcances de la telesalud*. Diario Oficial El Peruano. https://busquedas.elperuano.pe/dispositivo/NL/1866212-2',
  'U.S. Department of Health and Human Services. (2022). *Summary of the HIPAA Security Rule*. https://www.hhs.gov/hipaa/for-professionals/security/laws-regulations/index.html',
];
add(H1('4. Referencias'));
for (const r of refs) add(new Paragraph({ children: runs(r), spacing: { line: LINE, after: 0 }, indent: { left: 720, hanging: 720 } }));

// ---------- índice (estático, páginas del render previo) ----------
let pages = {};
try { pages = JSON.parse(fs.readFileSync(`${OUT}/toc_pages.json`, 'utf8')); } catch (e) {}
const indice = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { line: LINE, after: 120 }, children: [new TextRun({ text: 'Índice', bold: true })] }),
  ...TOC.map(([lvl, t]) => new Paragraph({
    tabStops: [{ type: TabStopType.RIGHT, position: 9016, leader: LeaderType.DOT }],
    indent: { left: lvl === 2 ? 220 : 0 }, spacing: { after: 100 },
    children: [new TextRun(t), new TextRun({ text: '\t' + (pages[t] || '0') })],
  })),
  new Paragraph({ children: [new PageBreak()] }),
];

// ---------- documento ----------
const footer = () => new Footer({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
  children: [new TextRun({ children: [PageNumber.CURRENT], size: 18 })] })] });
const header = () => new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT,
  children: [new TextRun({ children: [PageNumber.CURRENT] })] })] });
const emptyHeader = () => new Header({ children: [new Paragraph({ children: [] })] });
const doc = new Document({
  creator: 'Grupo PAC', title: 'Arquitectura cloud - Telemedicina rural en Azure',
  styles: {
    default: { document: { run: { font: FONT, size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 22, bold: true, font: FONT, color: '000000' },
        paragraph: { spacing: { before: 240, after: 0, line: LINE }, outlineLevel: 0, keepNext: true } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true,
        run: { size: 22, bold: true, font: FONT, color: '000000' },
        paragraph: { spacing: { before: 120, after: 0, line: LINE }, outlineLevel: 1, keepNext: true } },
    ],
  },
  numbering: { config: [{ reference: 'bullets', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT,
    style: { paragraph: { indent: { left: 1080, hanging: 360 } } } }] }] },
  sections: [
    { properties: { titlePage: true, page: { size: { width: 11906, height: 16838 }, margin: { top: 1440, bottom: 1440, left: 1440, right: 1440 } } },
      headers: { default: header(), first: emptyHeader() },
      children: [...portada, ...indice, ...body] },
  ],
});
Packer.toBuffer(doc).then((b) => fs.writeFileSync(`${OUT}/PAC_Arquitectura_Telemedicina_Azure.docx`, b));
