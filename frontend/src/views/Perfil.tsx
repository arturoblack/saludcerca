import { FormEvent, useState } from 'react';
import { api, Canal, Usuario } from '../api';

/* "Mis datos": el usuario actualiza su celular, su correo y por dónde quiere recibir los avisos. */
const CANALES: { valor: Canal; titulo: string; detalle: string }[] = [
  { valor: 'sms', titulo: 'SMS al celular', detalle: 'Funciona en cualquier teléfono, aunque no tenga internet.' },
  { valor: 'email', titulo: 'Correo electrónico', detalle: 'Recibirá los avisos en su bandeja de entrada.' },
  { valor: 'app', titulo: 'Solo en la app', detalle: 'Los verá en la pestaña Avisos al abrir SaludCerca.' },
];

export function Perfil({ usuario, onGuardado, onVolver }: { usuario: Usuario; onGuardado: (u: Usuario) => void; onVolver: () => void }) {
  const [telefono, setTelefono] = useState(usuario.telefono ?? '');
  const [email, setEmail] = useState(usuario.email ?? '');
  const [canal, setCanal] = useState<Canal>(usuario.canal_preferido);
  const [error, setError] = useState('');
  const [guardando, setGuardando] = useState(false);

  const guardar = async (e: FormEvent) => {
    e.preventDefault();
    setGuardando(true); setError('');
    try {
      onGuardado(await api.actualizarPerfil({ telefono, email, canal_preferido: canal }));
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setGuardando(false);
    }
  };

  return (
    <form className="card form perfil" onSubmit={guardar}>
      <h1>Mis datos de contacto</h1>
      <p className="muted small">{usuario.nombre}{usuario.establecimiento ? ` · ${usuario.establecimiento}` : ''}</p>
      <label>Celular
        <input type="tel" inputMode="tel" autoComplete="tel" placeholder="987 654 321" value={telefono}
          onChange={(e) => setTelefono(e.target.value)} />
      </label>
      <label>Correo (opcional)
        <input type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      </label>
      <fieldset className="canales">
        <legend>¿Por dónde quiere recibir los avisos de sus citas?</legend>
        {CANALES.map((c) => (
          <label key={c.valor} className={canal === c.valor ? 'canal sel' : 'canal'}>
            <input type="radio" name="canal" checked={canal === c.valor} onChange={() => setCanal(c.valor)} />
            <span><strong>{c.titulo}</strong><span className="small muted">{c.detalle}</span></span>
          </label>
        ))}
      </fieldset>
      {error && <p className="error">{error}</p>}
      <div className="actions">
        <button className="primary" disabled={guardando}>{guardando ? 'Guardando…' : 'Guardar'}</button>
        <button type="button" className="ghost" onClick={onVolver}>Volver</button>
      </div>
    </form>
  );
}
