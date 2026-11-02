import { getToken } from './auth';

export type Rol = 'paciente' | 'medico' | 'admin';
export type Canal = 'sms' | 'email' | 'app';

export interface Usuario {
  id: string; nombre: string; rol: Rol; email?: string; telefono?: string;
  canal_preferido: Canal; especialidad?: string; establecimiento?: string;
}
export interface Cita {
  id: string; paciente_id: string; medico_id: string; especialidad: string; fecha_hora: string;
  modalidad: 'video' | 'audio'; motivo?: string; estado: 'programada' | 'cancelada' | 'atendida';
  paciente_nombre?: string; medico_nombre?: string; establecimiento?: string;
}
export interface Signos {
  presion_sistolica?: number | null; presion_diastolica?: number | null; pulso?: number | null;
  temperatura?: number | null; peso_kg?: number | null; saturacion?: number | null;
}
export interface Nota {
  id: string; paciente_id: string; medico_id: string; medico_nombre?: string; cita_id?: string;
  fecha: string; motivo: string; diagnostico: string; indicaciones: string; receta: string[];
  signos?: Signos | null; apuntes?: string | null; adjuntos: string[];
}
export interface Notificacion {
  id: string; cita_id: string; paciente_id: string; tipo: string; canal: Canal; destino: string;
  mensaje: string; estado: string; programada_para?: string; creada_en: string;
}
export interface Medico extends Usuario { tiene_horario?: boolean; duracion_min?: number | null }
export interface Turno { fecha_hora: string; medico_id: string; medico_nombre: string; duracion_min: number }
export interface DiaDisponible { fecha: string; turnos: Turno[] }
export interface Bloque { dia: number; inicio: string; fin: string }
export interface Agenda { duracion_min: number; bloques: Bloque[]; dias_bloqueados: string[] }

export interface Solicitud {
  id: string; especialidad: string; medico_id?: string | null; medico_nombre?: string | null;
  estado: 'activa' | 'notificada' | 'cancelada'; creada_en: string; notificada_en?: string | null;
}

export interface Sala { sala: string; token: string; acs_user_id: string; expira: string; modo: string; modalidad: 'video' | 'audio' }

export class ApiError extends Error {
  constructor(public status: number, message: string) { super(message); }
}

// En Azure, la PWA (Static Web Apps) llama a la Function App por su URL; en local, al mismo origen.
export const API_BASE: string = ((import.meta as any).env ?? {}).VITE_API_BASE_URL ?? '';

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = await getToken();
  let res: Response;
  try {
    res = await fetch(API_BASE + path, {
      method,
      headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, 'Sin conexión. Se mostrarán los últimos datos guardados cuando estén disponibles.');
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detalle = Array.isArray(data.detalle) ? `: ${data.detalle.map((d: { mensaje: string }) => d.mensaje).join('; ')}` : '';
    throw new ApiError(res.status, (data.error ?? `Error ${res.status}`) + detalle);
  }
  return data as T;
}

export const api = {
  devUsuarios: () => request<Usuario[]>('GET', '/api/dev/usuarios'),
  me: () => request<Usuario>('GET', '/api/me'),
  actualizarPerfil: (b: { telefono?: string; email?: string; canal_preferido: Canal }) => request<Usuario>('PUT', '/api/me', b),
  medicos: (especialidad?: string) =>
    request<Medico[]>('GET', `/api/medicos${especialidad ? `?especialidad=${encodeURIComponent(especialidad)}` : ''}`),
  especialidades: () => request<{ especialidad: string; medicos: number }[]>('GET', '/api/especialidades'),
  disponibilidad: (p: { especialidad?: string; medico_id?: string; desde?: string; dias?: number }) => {
    const q = new URLSearchParams();
    Object.entries(p).forEach(([k, v]) => { if (v !== undefined && v !== '') q.set(k, String(v)); });
    return request<{ desde: string; dias: DiaDisponible[] }>('GET', `/api/disponibilidad?${q}`);
  },
  misAvisos: () => request<Solicitud[]>('GET', '/api/avisos-disponibilidad'),
  demanda: () => request<{ especialidad: string; pendientes: number }[]>('GET', '/api/avisos-disponibilidad'),
  crearAviso: (especialidad: string, medico_id?: string) =>
    request<Solicitud>('POST', '/api/avisos-disponibilidad', { especialidad, medico_id: medico_id || undefined }),
  cancelarAviso: (id: string) => request<Solicitud>('POST', `/api/avisos-disponibilidad/${id}/cancelar`),
  registrarMedico: (b: { nombre: string; especialidad: string; email?: string; horario_inicial?: Agenda }) =>
    request<Usuario>('POST', '/api/medicos', b),
  miAgenda: () => request<{ agenda: Agenda; citas_fuera_de_horario: number }>('GET', '/api/medicos/me/agenda'),
  guardarAgenda: (a: Agenda) => request<{ agenda: Agenda; citas_fuera_de_horario: number }>('PUT', '/api/medicos/me/agenda', a),
  citas: () => request<Cita[]>('GET', '/api/citas'),
  crearCita: (b: { medico_id: string; fecha_hora: string; modalidad: string; motivo?: string }) =>
    request<Cita>('POST', '/api/citas', b),
  cancelarCita: (id: string) => request<Cita>('POST', `/api/citas/${id}/cancelar`),
  historial: (pid: string) => request<{ paciente: Usuario; notas: Nota[] }>('GET', `/api/pacientes/${pid}/historial`),
  agregarNota: (pid: string, b: { cita_id?: string; motivo: string; diagnostico: string; indicaciones: string; receta?: string[]; signos?: Signos; apuntes?: string; adjuntos?: string[] }) =>
    request<Nota>('POST', `/api/pacientes/${pid}/historial`, b),
  urlSubida: (paciente_id: string, nombre_archivo: string, tipo_contenido: string) =>
    request<{ blob: string; upload_url: string; modo: string }>('POST', '/api/documentos', { paciente_id, nombre_archivo, tipo_contenido }),
  videoconsulta: (id: string) => request<Sala>('POST', `/api/citas/${id}/videoconsulta`),
  notificaciones: () => request<Notificacion[]>('GET', '/api/notificaciones'),
};

export async function subirArchivo(pacienteId: string, file: File): Promise<string> {
  const { blob, upload_url, modo } = await api.urlSubida(pacienteId, file.name, file.type || 'application/octet-stream');
  const headers: Record<string, string> = { 'Content-Type': file.type || 'application/octet-stream' };
  if (modo === 'azure') headers['x-ms-blob-type'] = 'BlockBlob';
  const url = upload_url.startsWith('/') ? API_BASE + upload_url : upload_url;
  const res = await fetch(url, { method: 'PUT', headers, body: file });
  if (!res.ok) throw new ApiError(res.status, 'No se pudo subir el archivo');
  return blob;
}

const fmt = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit', timeZone: 'America/Lima' });
export const fechaLarga = (iso: string) => fmt.format(new Date(iso));
const fmtCorta = new Intl.DateTimeFormat('es-PE', { day: '2-digit', month: '2-digit', year: 'numeric', timeZone: 'America/Lima' });
const fmtHora = new Intl.DateTimeFormat('es-PE', { hour: '2-digit', minute: '2-digit', hour12: false, timeZone: 'America/Lima' });
export const hora = (iso: string) => fmtHora.format(new Date(iso));
export const fechaCorta = (iso: string) => fmtCorta.format(new Date(iso));
