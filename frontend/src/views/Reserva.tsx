import { FormEvent, useEffect, useMemo, useState } from 'react';
import { api, ApiError, DiaDisponible, fechaLarga, hora, Medico, Turno, Usuario } from '../api';
import { useConexion } from '../conexion';

/*
 * Reserva de cita en 4 pasos: especialidad → médico (o cualquiera) → día → turno libre.
 * Los turnos salen de los horarios que cada médico define en "Mi horario".
 */
const DIAS_VISTA = 14;
const fmtDia = new Intl.DateTimeFormat('es-PE', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' });
const fmtDiaLargo = new Intl.DateTimeFormat('es-PE', { weekday: 'long', day: 'numeric', month: 'long', timeZone: 'UTC' });
const diaCorto = (f: string) => fmtDia.format(new Date(`${f}T12:00:00Z`));
const diaLargo = (f: string) => fmtDiaLargo.format(new Date(`${f}T12:00:00Z`));
const apellido = (n: string) => n.replace(/^(Dr|Dra)\.\s*/, '').split(' ').slice(0, 2).join(' ');

export function Reserva({ usuario, onListo, onCancelar, onAviso }: {
  usuario: Usuario; onListo: () => void; onCancelar: () => void; onAviso: () => void;
}) {
  const [especialidades, setEspecialidades] = useState<{ especialidad: string; medicos: number }[]>([]);
  const [especialidad, setEspecialidad] = useState('');
  const [medicos, setMedicos] = useState<Medico[]>([]);
  const [medicoId, setMedicoId] = useState(''); // '' = cualquiera de la especialidad
  const [dias, setDias] = useState<DiaDisponible[] | null>(null);
  const [dia, setDia] = useState('');
  const [turno, setTurno] = useState<Turno | null>(null);
  const [modalidad, setModalidad] = useState<'video' | 'audio'>('video');
  const [motivo, setMotivo] = useState('');
  const [error, setError] = useState('');
  const [enviando, setEnviando] = useState(false);
  const conexion = useConexion();

  useEffect(() => { if (conexion?.lenta) setModalidad('audio'); }, [conexion]);
  useEffect(() => { api.especialidades().then(setEspecialidades).catch((e) => setError(e.message)); }, []);

  useEffect(() => {
    if (!especialidad) return;
    setMedicoId(''); setMedicos([]);
    api.medicos(especialidad).then(setMedicos).catch((e) => setError(e.message));
  }, [especialidad]);

  const cargarTurnos = () => {
    if (!especialidad) return;
    setDias(null); setTurno(null);
    api.disponibilidad({ especialidad: medicoId ? undefined : especialidad, medico_id: medicoId || undefined, dias: DIAS_VISTA })
      .then((r) => {
        setDias(r.dias);
        setDia((actual) => (r.dias.find((d) => d.fecha === actual && d.turnos.length) ? actual : r.dias.find((d) => d.turnos.length)?.fecha ?? ''));
      })
      .catch((e) => setError(e.message));
  };
  useEffect(cargarTurnos, [especialidad, medicoId]);

  const turnosDelDia = useMemo(() => dias?.find((d) => d.fecha === dia)?.turnos ?? [], [dias, dia]);
  const manana = turnosDelDia.filter((t) => Number(hora(t.fecha_hora).slice(0, 2)) < 13);
  const tarde = turnosDelDia.filter((t) => Number(hora(t.fecha_hora).slice(0, 2)) >= 13);
  const hayTurnos = !!dias?.some((d) => d.turnos.length);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    if (!turno) return;
    setEnviando(true); setError('');
    try {
      await api.crearCita({ medico_id: turno.medico_id, fecha_hora: turno.fecha_hora, modalidad, motivo: motivo || undefined });
      onListo();
    } catch (err) {
      setError((err as Error).message);
      if (err instanceof ApiError && err.status === 409) cargarTurnos(); // alguien tomó el turno: refrescar
    } finally {
      setEnviando(false);
    }
  };

  const BotonesTurno = ({ lista }: { lista: Turno[] }) => (
    <div className="slots">
      {lista.map((t) => {
        const sel = turno?.fecha_hora === t.fecha_hora && turno.medico_id === t.medico_id;
        return (
          <button type="button" key={t.fecha_hora + t.medico_id} className={sel ? 'slot sel' : 'slot'} aria-pressed={sel}
            onClick={() => setTurno(t)}>
            <strong>{hora(t.fecha_hora)}</strong>
            {!medicoId && <span>{apellido(t.medico_nombre)}</span>}
          </button>
        );
      })}
    </div>
  );

  return (
    <form className="card form reserva" onSubmit={enviar}>
      <h2>Reservar cita</h2>

      <fieldset>
        <legend><span className="paso">1</span> ¿Qué especialidad necesita?</legend>
        <div className="chips">
          {especialidades.map((e) => (
            <button type="button" key={e.especialidad} aria-pressed={especialidad === e.especialidad}
              className={especialidad === e.especialidad ? 'chip sel' : 'chip'} onClick={() => setEspecialidad(e.especialidad)}>
              {e.especialidad}{e.medicos === 0 && <span className="sin">sin médicos aún</span>}
            </button>
          ))}
        </div>
      </fieldset>

      {especialidad && (
        <fieldset>
          <legend><span className="paso">2</span> Médico</legend>
          {medicos.length === 0 ? <p className="muted small">Aún no hay médicos de {especialidad} en la red.</p> : (
          <div className="chips">
            <button type="button" aria-pressed={!medicoId} className={!medicoId ? 'chip sel' : 'chip'} onClick={() => setMedicoId('')}>
              Cualquiera disponible
            </button>
            {medicos.map((m) => (
              <button type="button" key={m.id} aria-pressed={medicoId === m.id} disabled={!m.tiene_horario}
                className={medicoId === m.id ? 'chip sel' : 'chip'} onClick={() => setMedicoId(m.id)}>
                {m.nombre}{!m.tiene_horario && ' (sin horario)'}
              </button>
            ))}
          </div>
          )}
        </fieldset>
      )}

      {especialidad && (
        <fieldset>
          <legend><span className="paso">3</span> Día</legend>
          {!dias ? <p className="muted small">Buscando turnos…</p>
            : !hayTurnos ? (
              <Avisarme usuario={usuario} especialidad={especialidad} medico={medicos.find((m) => m.id === medicoId)} onListo={onAviso} />
            )
            : (
              <div className="dias" role="listbox" aria-label="Días con atención">
                {dias.map((d) => (
                  <button type="button" key={d.fecha} role="option" aria-selected={dia === d.fecha} disabled={!d.turnos.length}
                    className={dia === d.fecha ? 'dia sel' : 'dia'} onClick={() => { setDia(d.fecha); setTurno(null); }}>
                    <span className="dia-nombre">{diaCorto(d.fecha)}</span>
                    <span className="small">{d.turnos.length ? `${d.turnos.length} turnos` : '—'}</span>
                  </button>
                ))}
              </div>
            )}
        </fieldset>
      )}

      {especialidad && dia && turnosDelDia.length > 0 && (
        <fieldset>
          <legend><span className="paso">4</span> Turnos libres del {diaLargo(dia)}</legend>
          {manana.length > 0 && <><p className="franja">Mañana</p><BotonesTurno lista={manana} /></>}
          {tarde.length > 0 && <><p className="franja">Tarde</p><BotonesTurno lista={tarde} /></>}
        </fieldset>
      )}

      {turno && (
        <>
          <fieldset className="segmented">
            <legend>Tipo de consulta</legend>
            <label><input type="radio" checked={modalidad === 'video'} onChange={() => setModalidad('video')} /> Video</label>
            <label><input type="radio" checked={modalidad === 'audio'} onChange={() => setModalidad('audio')} /> Solo audio (señal débil)</label>
          </fieldset>
          <p className="small conexion" aria-live="polite">
            {conexion ? (<><span className={`dot ${conexion.lenta ? 'lenta' : 'buena'}`} aria-hidden />
              Su conexión: {conexion.ms} ms. {conexion.lenta ? 'Le recomendamos solo audio: usa menos datos.' : 'Alcanza para video.'}</>)
              : 'Midiendo su conexión…'}
          </p>
          <label>Motivo (opcional)<textarea value={motivo} maxLength={280} onChange={(e) => setMotivo(e.target.value)} rows={2} /></label>
          <div className="resumen">
            <p className="eyebrow">Su cita</p>
            <p><strong>{fechaLarga(turno.fecha_hora)}</strong> · {turno.duracion_min} min</p>
            <p>{especialidad} · {turno.medico_nombre} · {modalidad === 'video' ? 'video' : 'solo audio'}</p>
          </div>
        </>
      )}

      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button className="primary" disabled={enviando || !turno}>{enviando ? 'Reservando…' : 'Confirmar cita'}</button>
        <button type="button" className="ghost" onClick={onCancelar}>Volver</button>
      </div>
    </form>
  );
}

/* Lista de espera: "Avisarme cuando haya turnos" (por SMS si el paciente usa teléfono básico). */
function Avisarme({ usuario, especialidad, medico, onListo }: { usuario: Usuario; especialidad: string; medico?: Medico; onListo: () => void }) {
  const [estado, setEstado] = useState<'inicio' | 'enviando' | 'listo'>('inicio');
  const [error, setError] = useState('');
  const canal = usuario.canal_preferido === 'sms' && usuario.telefono ? `por SMS al ${usuario.telefono}`
    : usuario.canal_preferido === 'email' && usuario.email ? `por correo a ${usuario.email}` : 'en la app (pestaña Avisos)';
  const objetivo = medico ? medico.nombre : `un médico de ${especialidad}`;

  const suscribir = async () => {
    setEstado('enviando'); setError('');
    try {
      await api.crearAviso(especialidad, medico?.id);
      setEstado('listo');
    } catch (e) {
      setError((e as Error).message); setEstado('inicio');
    }
  };

  if (estado === 'listo') {
    return (
      <div className="avisarme listo" role="status">
        <p><strong>Listo.</strong> Le avisaremos {canal} apenas {objetivo} tenga turnos libres.</p>
        <button type="button" className="ghost small" onClick={onListo}>Ver mis avisos</button>
      </div>
    );
  }
  return (
    <div className="avisarme">
      <p><strong>No hay turnos libres de {medico ? medico.nombre : especialidad} en las próximas dos semanas.</strong></p>
      <p className="small muted">Podemos avisarle {canal} cuando {objetivo} publique su horario o se libere un turno.</p>
      {error && <p className="error">{error}</p>}
      <button type="button" className="primary" disabled={estado === 'enviando'} onClick={suscribir}>
        {estado === 'enviando' ? 'Guardando…' : 'Avisarme cuando haya turnos'}
      </button>
    </div>
  );
}
