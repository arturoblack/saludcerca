import { useEffect, useMemo, useState } from 'react';
import { api, Cita, fechaCorta, fechaLarga, Nota, Notificacion, Solicitud, Usuario } from '../api';
import { Teleconsulta } from './Teleconsulta';
import { Reserva } from './Reserva';
import { HistorialLista } from './Historial';

type Tab = 'citas' | 'historial' | 'avisos';

/*
 * Avisos en vivo: se consultan cada 15 s y al volver a la pestaña del navegador, así el paciente
 * se entera sin recargar (p. ej. cuando un médico publica turnos). En producción se puede
 * reemplazar por notificaciones push (Web Push) o Azure SignalR sin cambiar la API.
 */
const SONDEO_MS = 15000;

function useAvisos() {
  const [avisos, setAvisos] = useState<Notificacion[] | null>(null);
  const [espera, setEspera] = useState<Solicitud[]>([]);
  const cargar = () => {
    api.notificaciones().then(setAvisos).catch(() => undefined);
    api.misAvisos().then(setEspera).catch(() => undefined);
  };
  useEffect(() => {
    cargar();
    const i = setInterval(() => { if (document.visibilityState === 'visible') cargar(); }, SONDEO_MS);
    const alVolver = () => { if (document.visibilityState === 'visible') cargar(); };
    document.addEventListener('visibilitychange', alVolver);
    window.addEventListener('focus', alVolver);
    return () => { clearInterval(i); document.removeEventListener('visibilitychange', alVolver); window.removeEventListener('focus', alVolver); };
  }, []);
  return { avisos: avisos ?? [], cargado: avisos !== null, espera, cargar };
}

export function PacienteHome({ usuario }: { usuario: Usuario }) {
  const [tab, setTab] = useState<Tab>('citas');
  const { avisos, cargado, espera, cargar: recargarAvisos } = useAvisos();
  const [vistos, setVistos] = useState<Set<string> | null>(null);
  const [toast, setToast] = useState<Notificacion | null>(null);

  // Al cargar por primera vez, lo existente cuenta como visto; lo que llegue después es "nuevo".
  useEffect(() => { if (cargado && vistos === null) setVistos(new Set(avisos.map((a) => a.id))); }, [cargado]);
  const nuevos = vistos && tab !== 'avisos' ? avisos.filter((a) => !vistos.has(a.id) && a.estado !== 'programada') : [];
  useEffect(() => {
    if (nuevos.length && tab !== 'avisos') setToast(nuevos[0]);
  }, [nuevos.map((n) => n.id).join()]);
  useEffect(() => {
    if (tab === 'avisos' && vistos) { setVistos(new Set(avisos.map((a) => a.id))); setToast(null); }
  }, [tab, avisos.length]);
  const [citas, setCitas] = useState<Cita[]>([]);
  const [enConsulta, setEnConsulta] = useState<Cita | null>(null);
  const [nueva, setNueva] = useState(false);
  const [error, setError] = useState('');

  const recargar = () => api.citas().then(setCitas).catch((e) => setError(e.message));
  useEffect(() => { recargar(); }, []);

  const proximas = useMemo(() => citas.filter((c) => c.estado === 'programada'), [citas]);
  const anteriores = useMemo(() => citas.filter((c) => c.estado !== 'programada').reverse(), [citas]);

  if (enConsulta) return <Teleconsulta cita={enConsulta} rol="paciente" onSalir={() => { setEnConsulta(null); recargar(); }} />;

  return (
    <section>
      <h1>Hola, {usuario.nombre.split(' ')[0]}</h1>
      <nav className="tabs" role="tablist">
        {(['citas', 'historial', 'avisos'] as Tab[]).map((t) => (
          <button key={t} role="tab" aria-selected={tab === t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {t === 'citas' ? 'Mis citas' : t === 'historial' ? 'Mi historial' : 'Avisos'}
            {t === 'avisos' && nuevos.length > 0 && <span className="badge" aria-label={`${nuevos.length} nuevos`}>{nuevos.length}</span>}
          </button>
        ))}
      </nav>
      {error && <p className="error">{error}</p>}

      {tab === 'citas' && (
        <>
          {proximas.length === 0 && <p className="muted">No tiene citas programadas.</p>}
          {proximas.map((c) => (
            <article key={c.id} className="card cita">
              <p className="eyebrow">{c.modalidad === 'video' ? 'Teleconsulta por video' : 'Teleconsulta por audio'}</p>
              <h2>{fechaLarga(c.fecha_hora)}</h2>
              <p>{c.especialidad} · {c.medico_nombre}</p>
              {c.motivo && <p className="small muted">Motivo: {c.motivo}</p>}
              <div className="actions">
                <button className="primary" onClick={() => setEnConsulta(c)}>Unirse a la consulta</button>
                <button className="ghost" onClick={async () => {
                  if (!confirm('¿Cancelar esta cita?')) return;
                  try { await api.cancelarCita(c.id); recargar(); } catch (e) { setError((e as Error).message); }
                }}>Cancelar</button>
              </div>
            </article>
          ))}
          {nueva ? <Reserva usuario={usuario} onListo={() => { setNueva(false); recargar(); recargarAvisos(); setTab('avisos'); }} onCancelar={() => setNueva(false)}
              onAviso={() => { setNueva(false); recargarAvisos(); setTab('avisos'); }} />
            : <button className="primary block" onClick={() => setNueva(true)}>+ Reservar nueva cita</button>}
          {anteriores.length > 0 && (
            <>
              <h3 className="section">Citas anteriores</h3>
              {anteriores.map((c) => (
                <div key={c.id} className="row">
                  <span>{fechaCorta(c.fecha_hora)} · {c.especialidad}</span>
                  <span className={`pill ${c.estado}`}>{c.estado}</span>
                </div>
              ))}
            </>
          )}
        </>
      )}
      {tab === 'historial' && <MiHistorial pacienteId={usuario.id} />}
      {tab === 'avisos' && <Avisos avisos={avisos} espera={espera} recargar={recargarAvisos} />}
      {toast && (
        <div className="toast" role="status">
          <p><strong>{TIPO[toast.tipo] ?? 'Nuevo aviso'}</strong> · {toast.mensaje}</p>
          <div className="actions">
            <button className="primary" onClick={() => { setTab('avisos'); setToast(null); }}>Ver aviso</button>
            <button className="ghost" onClick={() => setToast(null)}>Cerrar</button>
          </div>
        </div>
      )}
    </section>
  );
}

function MiHistorial({ pacienteId }: { pacienteId: string }) {
  const [notas, setNotas] = useState<Nota[] | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { api.historial(pacienteId).then((h) => setNotas(h.notas)).catch((e) => setError(e.message)); }, [pacienteId]);
  if (error) return <p className="error">{error}</p>;
  if (!notas) return <p className="muted">Cargando…</p>;
  return <HistorialLista notas={notas} />;
}

const TIPO: Record<string, string> = { confirmacion: 'Confirmación', recordatorio: 'Recordatorio', cancelacion: 'Cancelación', disponibilidad: 'Turnos disponibles' };

export function Avisos({ avisos, espera, recargar: cargar }: { avisos: Notificacion[]; espera: Solicitud[]; recargar: () => void }) {
  const activas = espera.filter((s) => s.estado === 'activa');
  return (
    <div className="list">
      {activas.length > 0 && (
        <div className="card espera">
          <p className="eyebrow">Esperando turnos</p>
          {activas.map((s) => (
            <div key={s.id} className="row">
              <span className="grow"><strong>{s.medico_nombre ?? s.especialidad}</strong>
                <span className="small muted">{s.medico_nombre ? s.especialidad + ' · ' : ''}le avisaremos cuando haya turnos</span></span>
              <button className="ghost small" onClick={async () => { await api.cancelarAviso(s.id); cargar(); }}>Cancelar</button>
            </div>
          ))}
        </div>
      )}
      {!avisos.length && !activas.length && <p className="muted">Aún no hay avisos.</p>}
      {avisos.map((n) => (
        <article key={n.id} className={`card aviso ${n.canal}`}>
          <p className="eyebrow">
            {n.canal === 'sms' ? 'SMS' : n.canal === 'email' ? 'Correo' : 'En la app'} · {TIPO[n.tipo] ?? n.tipo}
            {n.estado === 'programada' && n.programada_para ? ` · se enviará el ${fechaLarga(n.programada_para)}` : ''}
          </p>
          <p>{n.mensaje}</p>
          {n.canal === 'sms' && <p className="small muted">{n.estado === 'programada' ? 'Se enviará a' : 'Enviado a'} {n.destino}</p>}
        </article>
      ))}
    </div>
  );
}
