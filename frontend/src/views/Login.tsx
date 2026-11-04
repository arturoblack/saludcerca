import { useEffect, useState } from 'react';
import { api, Usuario } from '../api';
import { AUTH_MODE, iniciarSesion, iniciarSesionDev } from '../auth';

const etiqueta: Record<string, string> = { paciente: 'Paciente', medico: 'Médico', admin: 'Coordinación' };

export function Login({ onLogin }: { onLogin: () => void }) {
  const [usuarios, setUsuarios] = useState<Usuario[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    if (AUTH_MODE !== 'entra') api.devUsuarios().then(setUsuarios).catch((e) => setError(e.message));
  }, []);

  if (AUTH_MODE !== 'dev') {
    return (
      <section className="card center">
        <h1>Bienvenido a SaludCerca</h1>
        <p className="muted">Consultas médicas a distancia para su comunidad.</p>
        <button className="primary" onClick={() => iniciarSesion()}>Ingresar</button>
        {AUTH_MODE === 'oidc' ? (
          <div className="small muted">
            <p>Proveedor de identidad de pruebas: en su pantalla escriba como <em>username</em> el usuario con el que quiere entrar.</p>
            <p>{usuarios.map((u) => u.id).join(' · ')}</p>
          </div>
        ) : <p className="small muted">Le enviaremos un código por SMS o correo para confirmar que es usted.</p>}
      </section>
    );
  }

  return (
    <section>
      <h1>Ingresar</h1>
      <p className="muted">En la demo, elija con qué usuario ficticio entrar. En Azure este paso lo hace Microsoft Entra External ID con verificación en dos pasos.</p>
      {error && <p className="error">{error}</p>}
      <div className="list">
        {usuarios.map((u) => (
          <button key={u.id} className="row-button" onClick={async () => { await iniciarSesionDev(u.id); onLogin(); }}>
            <span className={`pill ${u.rol}`}>{etiqueta[u.rol]}</span>
            <span className="grow">
              <strong>{u.nombre}</strong>
              <span className="small muted">
                {u.especialidad ?? u.establecimiento ?? ''}
                {u.rol === 'paciente' && ` · avisos por ${u.canal_preferido === 'sms' ? 'SMS (teléfono básico)' : 'la app'}`}
              </span>
            </span>
            <span aria-hidden>›</span>
          </button>
        ))}
      </div>
    </section>
  );
}
