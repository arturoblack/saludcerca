import { fechaCorta, Nota, Signos } from '../api';

function resumenSignos(s?: Signos | null): string[] {
  if (!s) return [];
  const r: string[] = [];
  if (s.presion_sistolica && s.presion_diastolica) r.push(`PA ${s.presion_sistolica}/${s.presion_diastolica} mmHg`);
  if (s.pulso) r.push(`Pulso ${s.pulso} lpm`);
  if (s.temperatura) r.push(`${s.temperatura} °C`);
  if (s.saturacion) r.push(`SatO₂ ${s.saturacion} %`);
  if (s.peso_kg) r.push(`${s.peso_kg} kg`);
  return r;
}

export function HistorialLista({ notas }: { notas: Nota[] }) {
  if (!notas.length) return <p className="muted">Sin atenciones registradas.</p>;
  return (
    <div className="timeline">
      {notas.map((n) => (
        <article key={n.id} className="card nota">
          <p className="eyebrow">{fechaCorta(n.fecha)} · {n.medico_nombre ?? 'Médico'}</p>
          <h3>{n.motivo}</h3>
          <dl>
            <dt>Diagnóstico</dt><dd>{n.diagnostico}</dd>
            <dt>Indicaciones</dt><dd>{n.indicaciones}</dd>
            {(n.receta ?? []).length > 0 && (<><dt>Receta</dt><dd><ul className="receta">{n.receta.map((r, i) => <li key={i}>{r}</li>)}</ul></dd></>)}
            {n.adjuntos.length > 0 && (<><dt>Adjuntos</dt><dd>{n.adjuntos.map((a) => a.split('/').pop()).join(', ')}</dd></>)}
          </dl>
          {n.apuntes && (
            <details className="apuntes-hist"><summary>Apuntes de la consulta</summary><p>{n.apuntes}</p></details>
          )}
          {resumenSignos(n.signos).length > 0 && (
            <div className="signos">{resumenSignos(n.signos).map((s) => <span key={s} className="pill">{s}</span>)}</div>
          )}
        </article>
      ))}
    </div>
  );
}
