import { useState } from 'react';
import { api, Usuario } from '../api';

// Ley N.° 29733: consentimiento previo, informado, expreso e inequívoco para datos de salud.
export function Consentimiento({ onAceptado, onSalir }: { onAceptado: (u: Usuario) => void; onSalir: () => void }) {
  const [acepta, setAcepta] = useState(false);
  const [enviando, setEnviando] = useState(false);
  const [error, setError] = useState('');

  const aceptar = async () => {
    setEnviando(true); setError('');
    try {
      onAceptado(await api.aceptarConsentimiento());
    } catch (e) {
      setError((e as Error).message);
      setEnviando(false);
    }
  };

  return (
    <section className="card form">
      <h1>Sus datos de salud</h1>
      <p>Antes de continuar, necesitamos su autorización para usar sus datos personales.</p>
      <ul>
        <li><strong>Qué datos:</strong> identificación, contacto, citas e historia clínica.</li>
        <li><strong>Para qué:</strong> brindarle consultas a distancia, guardar su historia y enviarle avisos de sus citas.</li>
        <li><strong>Quién los ve:</strong> usted y los médicos que lo atienden. La coordinación no lee su historia clínica.</li>
        <li><strong>Dónde se guardan:</strong> cifrados, en servidores de Microsoft Azure fuera del Perú.</li>
        <li><strong>Sus derechos:</strong> puede pedir acceder, corregir o eliminar sus datos, y retirar esta autorización, en su puesto de salud.</li>
      </ul>
      <label className="check">
        <input type="checkbox" checked={acepta} onChange={(e) => setAcepta(e.target.checked)} />
        <span>He leído esta información y autorizo el uso de mis datos personales y de salud.</span>
      </label>
      {error && <p className="error">{error}</p>}
      <button className="primary" disabled={!acepta || enviando} onClick={aceptar}>{enviando ? 'Guardando…' : 'Aceptar y continuar'}</button>
      <button className="link" onClick={onSalir}>Ahora no, salir</button>
    </section>
  );
}
