import { useCallback, useEffect, useState } from 'react';
import { api, Usuario } from './api';
import { AUTH_MODE, cerrarSesion, haySesion } from './auth';
import { Login } from './views/Login';
import { PacienteHome } from './views/PacienteHome';
import { MedicoHome } from './views/MedicoHome';
import { AdminHome } from './views/AdminHome';
import { Perfil } from './views/Perfil';
import { Consentimiento } from './views/Consentimiento';

function useOnline() {
  const [online, setOnline] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => setOnline(true), off = () => setOnline(false);
    window.addEventListener('online', on); window.addEventListener('offline', off);
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, []);
  return online;
}

export function App() {
  const [usuario, setUsuario] = useState<Usuario | null>(null);
  const [cargando, setCargando] = useState(true);
  const [verPerfil, setVerPerfil] = useState(false);
  const online = useOnline();

  const cargar = useCallback(async () => {
    setCargando(true);
    try {
      if (await haySesion()) setUsuario(await api.me());
    } catch {
      setUsuario(null);
    } finally {
      setCargando(false);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  const salir = async () => { await cerrarSesion(); setUsuario(null); setVerPerfil(false); };

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand"><span className="logo" aria-hidden>+</span> SaludCerca</div>
        {usuario && (
          <div className="who">
            <button className="link cuenta" onClick={() => setVerPerfil(true)} title="Mis datos de contacto">{usuario.nombre}</button>
            <button className="link" onClick={salir}>Salir</button>
          </div>
        )}
      </header>
      {!online && <div className="banner">Sin conexión: verá sus últimas citas guardadas. Los cambios se podrán hacer al volver la señal.</div>}
      {AUTH_MODE === 'dev' && <div className="banner demo">Modo demostración: datos ficticios.</div>}
      <main className="content">
        {cargando ? <p className="muted">Cargando…</p>
          : !usuario ? <Login onLogin={cargar} />
          : usuario.rol === 'paciente' && !usuario.consentimiento_en ? <Consentimiento onAceptado={setUsuario} onSalir={salir} />
          : verPerfil ? <Perfil usuario={usuario} onGuardado={(u) => { setUsuario(u); setVerPerfil(false); }} onVolver={() => setVerPerfil(false)} />
          : usuario.rol === 'paciente' ? <PacienteHome usuario={usuario} />
          : usuario.rol === 'medico' ? <MedicoHome usuario={usuario} />
          : <AdminHome />}
      </main>
    </div>
  );
}
