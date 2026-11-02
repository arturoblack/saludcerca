import { FormEvent, useEffect, useState } from 'react';
import { api, Cita, fechaLarga, Nota, Signos, subirArchivo, Usuario } from '../api';
import { HistorialLista } from './Historial';
import { Teleconsulta } from './Teleconsulta';
import { Horario } from './Horario';

/*
 * Borrador de la atención: vive solo en memoria (no en el dispositivo), para que los datos
 * clínicos no queden guardados en tabletas compartidas. Se conserva al colgar la llamada
 * y al volver a la ficha del paciente, hasta que el médico lo guarda.
 */
export interface Borrador {
  motivo: string; diagnostico: string; indicaciones: string; receta: string; apuntes: string;
  signos: Record<keyof Signos, string>;
}

const borradorVacio = (cita: Cita): Borrador => ({
  motivo: cita.motivo ?? '', diagnostico: '', indicaciones: '', receta: '', apuntes: '',
  signos: { presion_sistolica: '', presion_diastolica: '', pulso: '', temperatura: '', peso_kg: '', saturacion: '' },
});

export function MedicoHome({ usuario }: { usuario: Usuario }) {
  const [citas, setCitas] = useState<Cita[]>([]);
  const [seleccion, setSeleccion] = useState<Cita | null>(null);
  const [enConsulta, setEnConsulta] = useState(false);
  const [borradores, setBorradores] = useState<Record<string, Borrador>>({});
  const [vista, setVista] = useState<'agenda' | 'horario'>('agenda');
  const [error, setError] = useState('');

  const recargar = () => api.citas().then((cs) => {
    setCitas(cs);
    setSeleccion((s) => (s ? cs.find((c) => c.id === s.id) ?? null : null));
  }).catch((e) => setError(e.message));
  useEffect(() => { recargar(); }, []);

  const borrador = seleccion ? borradores[seleccion.id] ?? borradorVacio(seleccion) : null;
  const setBorrador = (b: Borrador) => seleccion && setBorradores((bs) => ({ ...bs, [seleccion.id]: b }));
  const alGuardar = () => {
    if (seleccion) setBorradores((bs) => { const resto = { ...bs }; delete resto[seleccion.id]; return resto; });
    setEnConsulta(false);
    recargar();
  };

  if (seleccion && borrador && enConsulta) {
    return (
      <Teleconsulta cita={seleccion} rol="medico" onSalir={() => setEnConsulta(false)}
        panel={(segundos) => (
          <PanelConsulta cita={seleccion} borrador={borrador} setBorrador={setBorrador} segundos={segundos} onGuardado={alGuardar} />
        )} />
    );
  }

  const agenda = citas.filter((c) => c.estado === 'programada');
  const pestanas = (
    <nav className="tabs medico-tabs" role="tablist">
      <button role="tab" aria-selected={vista === 'agenda'} className={vista === 'agenda' ? 'active' : ''} onClick={() => setVista('agenda')}>Agenda</button>
      <button role="tab" aria-selected={vista === 'horario'} className={vista === 'horario' ? 'active' : ''} onClick={() => setVista('horario')}>Mi horario</button>
    </nav>
  );
  if (vista === 'horario') return <>{pestanas}<Horario /></>;
  return (
    <>
    {pestanas}
    <section className="split">
      <div>
        <h1>Agenda</h1>
        <p className="muted">{usuario.especialidad}</p>
        {error && <p className="error">{error}</p>}
        {agenda.length === 0 && <p className="muted">No hay citas programadas.</p>}
        <div className="list">
          {agenda.map((c) => (
            <button key={c.id} className={`row-button ${seleccion?.id === c.id ? 'selected' : ''}`} onClick={() => setSeleccion(c)}>
              <span className="grow">
                <strong>{c.paciente_nombre}</strong>
                <span className="small muted">{fechaLarga(c.fecha_hora)} · {c.modalidad === 'video' ? 'video' : 'solo audio'}</span>
                <span className="small muted">{c.establecimiento}</span>
              </span>
              {borradores[c.id] && <span className="pill">borrador</span>}
              <span aria-hidden>›</span>
            </button>
          ))}
        </div>
      </div>
      <div>
        {seleccion && borrador ? (
          <FichaPaciente cita={seleccion} borrador={borrador} setBorrador={setBorrador}
            onConsulta={() => setEnConsulta(true)} onGuardado={alGuardar} />
        ) : <p className="muted pad">Seleccione una cita para ver la historia clínica del paciente.</p>}
      </div>
    </section>
    </>
  );
}

function useHistorial(pacienteId: string) {
  const [notas, setNotas] = useState<Nota[] | null>(null);
  const [error, setError] = useState('');
  const cargar = () => api.historial(pacienteId).then((h) => setNotas(h.notas)).catch((e) => setError(e.message));
  useEffect(() => { setNotas(null); cargar(); }, [pacienteId]);
  return { notas, error, cargar };
}

interface PropsAtencion { cita: Cita; borrador: Borrador; setBorrador: (b: Borrador) => void; onGuardado: () => void }

function FichaPaciente({ cita, borrador, setBorrador, onConsulta, onGuardado }: PropsAtencion & { onConsulta: () => void }) {
  const { notas, error, cargar } = useHistorial(cita.paciente_id);
  return (
    <div>
      <div className="card">
        <p className="eyebrow">Cita {cita.estado}</p>
        <h2>{cita.paciente_nombre}</h2>
        <p>{fechaLarga(cita.fecha_hora)}</p>
        {cita.motivo && <p className="small muted">Motivo: {cita.motivo}</p>}
        {cita.estado === 'programada' && <button className="primary" onClick={onConsulta}>Iniciar teleconsulta</button>}
      </div>
      {cita.estado === 'programada' && (
        <NuevaNota cita={cita} borrador={borrador} setBorrador={setBorrador} onGuardado={() => { cargar(); onGuardado(); }} />
      )}
      <h3 className="section">Historia clínica</h3>
      {error && <p className="error">{error}</p>}
      {notas ? <HistorialLista notas={notas} /> : <p className="muted">Cargando…</p>}
    </div>
  );
}

/* Panel lateral durante la videollamada: tomar notas y revisar la historia sin colgar. */
function PanelConsulta({ cita, borrador, setBorrador, segundos, onGuardado }: PropsAtencion & { segundos: number }) {
  const [pestana, setPestana] = useState<'notas' | 'historia'>('notas');
  const { notas, error } = useHistorial(cita.paciente_id);
  const mmss = `${String(Math.floor(segundos / 60)).padStart(2, '0')}:${String(segundos % 60).padStart(2, '0')}`;

  const marcarHora = () => {
    const prefijo = borrador.apuntes && !borrador.apuntes.endsWith('\n') ? '\n' : '';
    setBorrador({ ...borrador, apuntes: `${borrador.apuntes}${prefijo}[${mmss}] ` });
    setTimeout(() => document.getElementById('apuntes')?.focus(), 0);
  };

  return (
    <aside className="panel-consulta" aria-label="Notas e historia del paciente">
      <nav className="tabs" role="tablist">
        <button role="tab" aria-selected={pestana === 'notas'} className={pestana === 'notas' ? 'active' : ''} onClick={() => setPestana('notas')}>Notas</button>
        <button role="tab" aria-selected={pestana === 'historia'} className={pestana === 'historia' ? 'active' : ''} onClick={() => setPestana('historia')}>
          Historia{notas ? ` (${notas.length})` : ''}
        </button>
      </nav>
      {pestana === 'notas' ? (
        <>
          <div className="apuntes">
            <div className="apuntes-head">
              <label htmlFor="apuntes">Apuntes de la consulta</label>
              <button type="button" className="ghost small" onClick={marcarHora}>+ Marca {mmss}</button>
            </div>
            <textarea id="apuntes" rows={5} value={borrador.apuntes} placeholder="Lo que refiere el paciente, hallazgos, dudas…"
              onChange={(e) => setBorrador({ ...borrador, apuntes: e.target.value })} />
            <p className="small muted">Solo los ve el personal de salud. Se guardan cifrados con la atención.</p>
          </div>
          <NuevaNota cita={cita} borrador={borrador} setBorrador={setBorrador} onGuardado={onGuardado} compacta />
        </>
      ) : (
        <div className="panel-historia">
          {error && <p className="error">{error}</p>}
          {notas ? <HistorialLista notas={notas} /> : <p className="muted">Cargando…</p>}
        </div>
      )}
    </aside>
  );
}

const CAMPOS_SIGNOS: [keyof Signos, string, string][] = [
  ['presion_sistolica', 'PA sistólica', '1'], ['presion_diastolica', 'PA diastólica', '1'], ['pulso', 'Pulso (lpm)', '1'],
  ['temperatura', 'Temp. (°C)', '0.1'], ['peso_kg', 'Peso (kg)', '0.1'], ['saturacion', 'SatO₂ (%)', '1'],
];

function NuevaNota({ cita, borrador, setBorrador, onGuardado, compacta = false }: PropsAtencion & { compacta?: boolean }) {
  const [archivo, setArchivo] = useState<File | null>(null);
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);
  const b = borrador;
  const set = (campo: keyof Borrador, valor: string) => setBorrador({ ...b, [campo]: valor });

  const guardar = async (e: FormEvent) => {
    e.preventDefault();
    setGuardando(true); setError('');
    try {
      const adjuntos = archivo ? [await subirArchivo(cita.paciente_id, archivo)] : [];
      const sv: Signos = {};
      for (const [k, v] of Object.entries(b.signos) as [keyof Signos, string][]) if (v.trim()) sv[k] = Number(v.replace(',', '.'));
      await api.agregarNota(cita.paciente_id, {
        cita_id: cita.id, motivo: b.motivo, diagnostico: b.diagnostico, indicaciones: b.indicaciones, adjuntos,
        receta: b.receta.split('\n').map((l) => l.trim()).filter(Boolean),
        signos: Object.keys(sv).length ? sv : undefined,
        apuntes: b.apuntes.trim() || undefined,
      });
      onGuardado();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <form className={`card form ${compacta ? 'compacta' : ''}`} onSubmit={guardar}>
      <h3>Registrar atención</h3>
      <label>Motivo<input value={b.motivo} onChange={(e) => set('motivo', e.target.value)} required minLength={3} /></label>
      <label>Diagnóstico<textarea value={b.diagnostico} onChange={(e) => set('diagnostico', e.target.value)} required minLength={3} rows={2} /></label>
      <label>Indicaciones<textarea value={b.indicaciones} onChange={(e) => set('indicaciones', e.target.value)} required minLength={3} rows={2} /></label>
      <label>Receta (un medicamento por línea)<textarea value={b.receta} onChange={(e) => set('receta', e.target.value)} rows={2}
        placeholder="Omeprazol 20 mg cada 24 h por 14 días" /></label>
      <fieldset className="vitals">
        <legend>Signos vitales (opcional)</legend>
        {CAMPOS_SIGNOS.map(([k, etiqueta, paso]) => (
          <label key={k}>{etiqueta}
            <input inputMode="decimal" type="number" step={paso} value={b.signos[k]}
              onChange={(e) => setBorrador({ ...b, signos: { ...b.signos, [k]: e.target.value } })} />
          </label>
        ))}
      </fieldset>
      {!compacta && (
        <>
          <label>Apuntes de la consulta (opcional)<textarea value={b.apuntes} onChange={(e) => set('apuntes', e.target.value)} rows={2} /></label>
          <label>Adjunto (opcional)<input type="file" accept="application/pdf,image/*" onChange={(e) => setArchivo(e.target.files?.[0] ?? null)} /></label>
        </>
      )}
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={guardando}>{guardando ? 'Guardando…' : compacta ? 'Guardar y terminar la consulta' : 'Guardar y cerrar la cita'}</button>
    </form>
  );
}
