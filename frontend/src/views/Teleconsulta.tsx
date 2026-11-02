import { ReactNode, useEffect, useRef, useState } from 'react';
import { api, Cita, Sala } from '../api';
import { useConexion } from '../conexion';

/*
 * Sala de teleconsulta.
 * El backend emite el token de Azure Communication Services (ACS) para la sala de la cita.
 * - Modo "azure": aquí se conectaría el SDK @azure/communication-calling con ese token (ver README).
 * - Modo "simulado": se usa la cámara y el micrófono del equipo para mostrar la experiencia
 *   (solo audio, silenciar, colgar) sin conectar a una segunda persona.
 */
export function Teleconsulta({ cita, rol, onSalir, panel }: {
  cita: Cita; rol: 'paciente' | 'medico'; onSalir: (atendida?: boolean) => void;
  panel?: (segundos: number) => ReactNode; // notas e historia del paciente (solo médico)
}) {
  const video = useRef<HTMLVideoElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const [sala, setSala] = useState<Sala | null>(null);
  const [error, setError] = useState('');
  const [soloAudio, setSoloAudio] = useState(cita.modalidad === 'audio');
  const [mic, setMic] = useState(true);
  const [conectado, setConectado] = useState(false);
  const [segundos, setSegundos] = useState(0);
  const [verPanel, setVerPanel] = useState(true);
  const conexion = useConexion();
  const senalDebil = !!conexion?.lenta;

  useEffect(() => {
    let vivo = true;
    api.videoconsulta(cita.id).then((s) => vivo && setSala(s)).catch((e) => setError(e.message));
    navigator.mediaDevices?.getUserMedia({ audio: true, video: cita.modalidad === 'video' })
      .then((s) => {
        if (!vivo) { s.getTracks().forEach((t) => t.stop()); return; }
        stream.current = s;
        if (video.current) video.current.srcObject = s;
      })
      .catch(() => setError('No se pudo acceder a la cámara o al micrófono. Revise los permisos del navegador.'));
    const t = setTimeout(() => vivo && setConectado(true), 2500);
    return () => { vivo = false; clearTimeout(t); stream.current?.getTracks().forEach((tr) => tr.stop()); };
  }, [cita.id, cita.modalidad]);

  useEffect(() => {
    if (!conectado) return;
    const i = setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => clearInterval(i);
  }, [conectado]);

  useEffect(() => { if (senalDebil) setSoloAudio(true); }, [senalDebil]);
  useEffect(() => { stream.current?.getVideoTracks().forEach((t) => (t.enabled = !soloAudio)); }, [soloAudio]);
  useEffect(() => { stream.current?.getAudioTracks().forEach((t) => (t.enabled = mic)); }, [mic]);

  const otro = rol === 'paciente' ? cita.medico_nombre : cita.paciente_nombre;
  const iniciales = (otro ?? '?').replace(/^(Dr|Dra)\.\s*/, '').split(' ').slice(0, 2).map((p) => p[0]).join('');
  const mmss = `${String(Math.floor(segundos / 60)).padStart(2, '0')}:${String(segundos % 60).padStart(2, '0')}`;

  return (
    <div className={panel && verPanel ? 'call-layout con-panel' : 'call-layout'}>
    <section className="call">
      <div className="stage">
        <div className="remote">
          <div className="avatar">{iniciales}</div>
          <p>{conectado ? otro : `Esperando a ${otro}…`}</p>
          {conectado && <p className="small">{mmss}</p>}
        </div>
        <video ref={video} className={`self ${soloAudio ? 'hidden' : ''}`} autoPlay playsInline muted />
        {soloAudio && <div className="self audio-only">Solo audio</div>}
      </div>

      {(senalDebil || soloAudio) && (
        <p className="notice">{senalDebil ? `Señal débil (${conexion?.ms} ms): la consulta continúa solo con audio.` : 'Video desactivado para ahorrar datos.'}</p>
      )}
      {error && <p className="error">{error}</p>}

      <div className="controls">
        <button className={mic ? 'ctrl' : 'ctrl off'} onClick={() => setMic(!mic)}>{mic ? 'Silenciar' : 'Activar micrófono'}</button>
        <button className={soloAudio ? 'ctrl off' : 'ctrl'} onClick={() => setSoloAudio(!soloAudio)} disabled={cita.modalidad === 'audio'}>
          {soloAudio ? 'Activar video' : 'Solo audio'}
        </button>
        {panel && (
          <button className={verPanel ? 'ctrl activo' : 'ctrl'} aria-pressed={verPanel} onClick={() => setVerPanel(!verPanel)}>
            {verPanel ? 'Ocultar notas' : 'Notas e historia'}
          </button>
        )}
        <button className="ctrl hangup" onClick={() => onSalir(rol === 'medico' && conectado)}>Colgar</button>
      </div>

      {sala && (
        <p className="small muted center">
          Sala {sala.sala} · token de Communication Services {sala.modo === 'simulado' ? '(simulado en la demo)' : 'emitido'} · vence {new Date(sala.expira).toLocaleTimeString('es-PE', { hour: '2-digit', minute: '2-digit' })}
        </p>
      )}
    </section>
    {panel && verPanel && panel(segundos)}
    </div>
  );
}
