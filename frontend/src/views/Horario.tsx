import { useEffect, useMemo, useState } from 'react';
import { Agenda, api, Bloque } from '../api';

/* Editor del horario semanal de atención del médico. */
const DIAS = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'];
const DURACIONES = [15, 20, 30, 45, 60];
const aMin = (h: string) => Number(h.slice(0, 2)) * 60 + Number(h.slice(3, 5));
const aHora = (m: number) => `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
const fmtFecha = new Intl.DateTimeFormat('es-PE', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' });

export function Horario() {
  const [agenda, setAgenda] = useState<Agenda | null>(null);
  const [nuevoBloqueo, setNuevoBloqueo] = useState('');
  const [estado, setEstado] = useState<{ tipo: 'ok' | 'error' | 'aviso'; texto: string } | null>(null);
  const [guardando, setGuardando] = useState(false);

  useEffect(() => {
    api.miAgenda().then((r) => setAgenda(normalizar(r.agenda))).catch((e) => setEstado({ tipo: 'error', texto: e.message }));
  }, []);

  const turnosSemana = useMemo(() => {
    if (!agenda) return 0;
    return agenda.bloques.reduce((n, b) => n + Math.floor((aMin(b.fin) - aMin(b.inicio)) / agenda.duracion_min), 0);
  }, [agenda]);

  if (!agenda) return estado ? <p className="error">{estado.texto}</p> : <p className="muted">Cargando…</p>;

  const cambiar = (a: Agenda) => { setAgenda(a); setEstado(null); };
  const bloquesDe = (dia: number) => agenda.bloques.map((b, i) => ({ b, i })).filter(({ b }) => b.dia === dia);
  const actualizarBloque = (i: number, campo: 'inicio' | 'fin', valor: string) =>
    cambiar({ ...agenda, bloques: agenda.bloques.map((b, j) => (j === i ? { ...b, [campo]: valor } : b)) });
  const quitarBloque = (i: number) => cambiar({ ...agenda, bloques: agenda.bloques.filter((_, j) => j !== i) });
  const agregarBloque = (dia: number) => {
    const ultimos = bloquesDe(dia).map(({ b }) => aMin(b.fin));
    const inicio = ultimos.length ? Math.max(...ultimos) + 60 : 8 * 60;
    const nuevo: Bloque = { dia, inicio: aHora(Math.min(inicio, 20 * 60)), fin: aHora(Math.min(inicio + 4 * 60, 23 * 60)) };
    cambiar({ ...agenda, bloques: [...agenda.bloques, nuevo] });
  };
  const copiarLunes = () => {
    const lunes = bloquesDe(0).map(({ b }) => b);
    const resto = agenda.bloques.filter((b) => b.dia === 0 || b.dia > 4);
    const copia = [1, 2, 3, 4].flatMap((d) => lunes.map((b) => ({ ...b, dia: d })));
    cambiar({ ...agenda, bloques: [...resto, ...copia] });
  };

  const guardar = async () => {
    setGuardando(true); setEstado(null);
    try {
      const r = await api.guardarAgenda(agenda);
      setAgenda(normalizar(r.agenda));
      setEstado(r.citas_fuera_de_horario
        ? { tipo: 'aviso', texto: `Horario guardado. Tiene ${r.citas_fuera_de_horario} cita(s) ya reservadas fuera del nuevo horario: se mantienen; revíselas en su agenda.` }
        : { tipo: 'ok', texto: 'Horario guardado. Los pacientes ya ven sus nuevos turnos.' });
    } catch (e) {
      setEstado({ tipo: 'error', texto: (e as Error).message });
    } finally {
      setGuardando(false);
    }
  };

  return (
    <section className="horario">
      <div className="horario-head">
        <div>
          <h2>Mi horario de atención</h2>
          <p className="muted small">Los pacientes solo pueden reservar dentro de estas franjas. Horas de Lima.</p>
        </div>
        <label className="duracion">Duración del turno
          <select value={agenda.duracion_min} onChange={(e) => cambiar({ ...agenda, duracion_min: Number(e.target.value) })}>
            {DURACIONES.map((d) => <option key={d} value={d}>{d} minutos</option>)}
          </select>
        </label>
      </div>

      <div className="semana">
        {DIAS.map((nombre, dia) => {
          const bloques = bloquesDe(dia);
          return (
            <div key={dia} className={bloques.length ? 'dia-fila activo' : 'dia-fila'}>
              <strong className="dia-nombre">{nombre}</strong>
              <div className="franjas">
                {bloques.length === 0 && <span className="muted small">No atiende</span>}
                {bloques.map(({ b, i }) => (
                  <span key={i} className="franja-edit">
                    <input type="time" step={900} aria-label={`${nombre}: inicio`} value={b.inicio} onChange={(e) => actualizarBloque(i, 'inicio', e.target.value)} />
                    <span aria-hidden>–</span>
                    <input type="time" step={900} aria-label={`${nombre}: fin`} value={b.fin} onChange={(e) => actualizarBloque(i, 'fin', e.target.value)} />
                    <button type="button" className="ghost small" aria-label={`Quitar franja del ${nombre}`} onClick={() => quitarBloque(i)}>Quitar</button>
                  </span>
                ))}
              </div>
              <button type="button" className="ghost small" onClick={() => agregarBloque(dia)}>+ Franja</button>
            </div>
          );
        })}
      </div>
      {bloquesDe(0).length > 0 && (
        <button type="button" className="link" onClick={copiarLunes}>Copiar el horario del lunes a martes–viernes</button>
      )}

      <div className="bloqueos">
        <h3>Días sin atención (vacaciones, campañas fuera del puesto)</h3>
        <div className="chips">
          {agenda.dias_bloqueados.map((f) => (
            <span key={f} className="chip">
              {fmtFecha.format(new Date(`${f}T12:00:00Z`))}
              <button type="button" className="link" aria-label={`Desbloquear ${f}`}
                onClick={() => cambiar({ ...agenda, dias_bloqueados: agenda.dias_bloqueados.filter((x) => x !== f) })}>✕</button>
            </span>
          ))}
          <span className="bloquear">
            <input type="date" aria-label="Fecha a bloquear" value={nuevoBloqueo} onChange={(e) => setNuevoBloqueo(e.target.value)} />
            <button type="button" className="ghost small" disabled={!nuevoBloqueo}
              onClick={() => { cambiar({ ...agenda, dias_bloqueados: [...new Set([...agenda.dias_bloqueados, nuevoBloqueo])].sort() }); setNuevoBloqueo(''); }}>
              Bloquear día
            </button>
          </span>
        </div>
      </div>

      <div className="horario-pie">
        <p><strong>{turnosSemana}</strong> turnos de {agenda.duracion_min} min por semana</p>
        <button className="primary" onClick={guardar} disabled={guardando}>{guardando ? 'Guardando…' : 'Guardar horario'}</button>
      </div>
      {estado && <p className={estado.tipo === 'error' ? 'error' : estado.tipo === 'aviso' ? 'notice' : 'ok'}>{estado.texto}</p>}
    </section>
  );
}

function normalizar(a: Agenda): Agenda {
  return { ...a, bloques: a.bloques.map((b) => ({ ...b, inicio: b.inicio.slice(0, 5), fin: b.fin.slice(0, 5) })) };
}
