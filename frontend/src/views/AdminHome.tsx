import { FormEvent, useEffect, useState } from 'react';
import { Agenda, api, Cita, fechaLarga, Notificacion } from '../api';

const PLANTILLAS: { etiqueta: string; agenda?: Agenda }[] = [
  { etiqueta: 'Sin horario (lo define el médico)' },
  { etiqueta: 'Lunes a viernes, 08:00–12:00', agenda: plantilla([0, 1, 2, 3, 4], '08:00', '12:00') },
  { etiqueta: 'Lunes a viernes, 14:00–18:00', agenda: plantilla([0, 1, 2, 3, 4], '14:00', '18:00') },
  { etiqueta: 'Lunes a sábado, 08:00–13:00', agenda: plantilla([0, 1, 2, 3, 4, 5], '08:00', '13:00') },
];

function plantilla(dias: number[], inicio: string, fin: string): Agenda {
  return { duracion_min: 30, bloques: dias.map((dia) => ({ dia, inicio, fin })), dias_bloqueados: [] };
}

export function AdminHome() {
  const [citas, setCitas] = useState<Cita[]>([]);
  const [avisos, setAvisos] = useState<Notificacion[]>([]);
  const [demanda, setDemanda] = useState<{ especialidad: string; pendientes: number }[]>([]);
  const cargar = () => {
    api.citas().then(setCitas).catch(() => setCitas([]));
    api.notificaciones().then(setAvisos).catch(() => setAvisos([]));
    api.demanda().then(setDemanda).catch(() => setDemanda([]));
  };
  useEffect(cargar, []);

  const porEstado = (e: string) => citas.filter((c) => c.estado === e).length;
  const sms = avisos.filter((a) => a.canal === 'sms').length;
  const enEspera = demanda.reduce((n, d) => n + d.pendientes, 0);

  return (
    <section>
      <h1>Coordinación</h1>
      <p className="muted">La coordinación ve citas, avisos y la demanda en espera, pero no las historias clínicas.</p>
      <div className="kpis">
        <div className="card kpi"><strong>{porEstado('programada')}</strong><span>citas programadas</span></div>
        <div className="card kpi"><strong>{avisos.length}</strong><span>avisos ({sms} por SMS)</span></div>
        <div className="card kpi"><strong>{enEspera}</strong><span>pacientes esperando turnos</span></div>
      </div>

      <div className="split admin">
        <div>
          <h3 className="section">Demanda sin atender</h3>
          {demanda.length === 0 ? <p className="muted small">Nadie está esperando turnos.</p>
            : demanda.map((d) => (
              <div key={d.especialidad} className="row"><span>{d.especialidad}</span><span className="pill sms">{d.pendientes} en espera</span></div>
            ))}
          <RegistrarMedico onRegistrado={cargar} />
        </div>
        <div>
          <h3 className="section">Próximas citas</h3>
          {citas.filter((c) => c.estado === 'programada').slice(0, 8).map((c) => (
            <div key={c.id} className="row"><span>{fechaLarga(c.fecha_hora)}</span><span className="small">{c.paciente_nombre} · {c.especialidad}</span></div>
          ))}
          <h3 className="section">Últimos avisos</h3>
          {avisos.slice(0, 10).map((a) => (
            <div key={a.id} className="row"><span className={`pill ${a.canal}`}>{a.canal}</span><span className="grow small">{a.mensaje}</span></div>
          ))}
        </div>
      </div>
    </section>
  );
}

function RegistrarMedico({ onRegistrado }: { onRegistrado: () => void }) {
  const [especialidades, setEspecialidades] = useState<string[]>([]);
  const [nombre, setNombre] = useState('');
  const [especialidad, setEspecialidad] = useState('');
  const [email, setEmail] = useState('');
  const [plantillaIdx, setPlantillaIdx] = useState(1);
  const [estado, setEstado] = useState<{ ok: boolean; texto: string } | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    api.especialidades().then((es) => { setEspecialidades(es.map((e) => e.especialidad)); setEspecialidad(es[0]?.especialidad ?? ''); });
  }, []);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setEnviando(true); setEstado(null);
    try {
      const antes = (await api.notificaciones()).filter((n) => n.tipo === 'disponibilidad').length;
      const m = await api.registrarMedico({ nombre, especialidad, email: email || undefined, horario_inicial: PLANTILLAS[plantillaIdx].agenda });
      const despues = (await api.notificaciones()).filter((n) => n.tipo === 'disponibilidad').length;
      const avisados = despues - antes;
      setEstado({ ok: true, texto: `${m.nombre} quedó registrado en ${especialidad}.` +
        (avisados > 0 ? ` Se avisó a ${avisados} paciente(s) que esperaban turnos.` : PLANTILLAS[plantillaIdx].agenda ? '' : ' Cuando publique su horario se avisará a quienes esperan.') });
      setNombre(''); setEmail('');
      onRegistrado();
    } catch (err) {
      setEstado({ ok: false, texto: (err as Error).message });
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form className="card form" onSubmit={enviar}>
      <h3>Registrar médico</h3>
      <label>Nombre completo<input value={nombre} onChange={(e) => setNombre(e.target.value)} required minLength={5} placeholder="Dr. Nombre Apellido Apellido" /></label>
      <div className="two">
        <label>Especialidad
          <select value={especialidad} onChange={(e) => setEspecialidad(e.target.value)}>
            {especialidades.map((e) => <option key={e}>{e}</option>)}
          </select>
        </label>
        <label>Correo (opcional)<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
      </div>
      <label>Horario inicial
        <select value={plantillaIdx} onChange={(e) => setPlantillaIdx(Number(e.target.value))}>
          {PLANTILLAS.map((p, i) => <option key={p.etiqueta} value={i}>{p.etiqueta}</option>)}
        </select>
      </label>
      {estado && <p className={estado.ok ? 'ok' : 'error'}>{estado.texto}</p>}
      <button className="primary" disabled={enviando}>{enviando ? 'Registrando…' : 'Registrar médico'}</button>
      <p className="small muted">En producción, el médico además se da de alta en Entra External ID con el rol Medico.</p>
    </form>
  );
}
