import { ReactNode, useEffect, useRef, useState } from 'react';
import { api, Cita, hora, Sala } from '../api';
import { LlamadaAcs, unirseALlamada } from '../llamadaAcs';
import { useConexion } from '../conexion';

/*
 * Sala de teleconsulta.
 * El backend emite el token de Azure Communication Services (ACS) para la sala de la cita.
 * - Modo "azure": llamada real entre paciente y médico con el SDK de ACS.
 * - Modo "simulado" (local sin ACS): usa la cámara y el micrófono del equipo para mostrar la
 *   experiencia (solo audio, silenciar, colgar) sin conectar a una segunda persona.
 */
export function Teleconsulta({ cita, rol, onSalir, panel }: {
  cita: Cita; rol: 'paciente' | 'medico'; onSalir: (atendida?: boolean) => void;
  panel?: (segundos: number) => ReactNode; // notas e historia del paciente (solo médico)
}) {
  const video = useRef<HTMLVideoElement>(null);
  const selfAcs = useRef<HTMLDivElement>(null);
  const remotoAcs = useRef<HTMLDivElement>(null);
  const stream = useRef<MediaStream | null>(null);
  const llamada = useRef<LlamadaAcs | null>(null);
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
    let temporizador: ReturnType<typeof setTimeout> | undefined;
    const simular = () => {
      navigator.mediaDevices?.getUserMedia({ audio: true, video: cita.modalidad === 'video' })
        .then((s) => {
          if (!vivo) { s.getTracks().forEach((t) => t.stop()); return; }
          stream.current = s;
          if (video.current) video.current.srcObject = s;
        })
        .catch(() => setError('No se pudo acceder a la cámara o al micrófono. Revise los permisos del navegador.'));
      temporizador = setTimeout(() => vivo && setConectado(true), 2500);
    };
    api.videoconsulta(cita.id).then(async (s) => {
      if (!vivo) return;
      setSala(s);
      if (s.modo !== 'azure') { simular(); return; }
      const l = await unirseALlamada(s, {
        conVideo: cita.modalidad === 'video', self: selfAcs.current!, remoto: remotoAcs.current!,
        onHayOtraPersona: (hay) => { if (vivo) setConectado(hay); },
      });
      if (vivo) llamada.current = l; else l.colgar();
    }).catch((e) => setError(e.message));
    return () => {
      vivo = false;
      clearTimeout(temporizador);
      stream.current?.getTracks().forEach((tr) => tr.stop());
      llamada.current?.colgar();
      llamada.current = null;
    };
  }, [cita.id, cita.modalidad]);

  useEffect(() => {
    if (!conectado) return;
    const i = setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => clearInterval(i);
  }, [conectado]);

  useEffect(() => { if (senalDebil) setSoloAudio(true); }, [senalDebil]);
  useEffect(() => {
    stream.current?.getVideoTracks().forEach((t) => (t.enabled = !soloAudio));
    llamada.current?.video(!soloAudio).catch(() => setError('No se pudo cambiar el video.'));
  }, [soloAudio]);
  useEffect(() => {
    stream.current?.getAudioTracks().forEach((t) => (t.enabled = mic));
    llamada.current?.microfono(mic).catch(() => setError('No se pudo cambiar el micrófono.'));
  }, [mic]);

  const otro = rol === 'paciente' ? cita.medico_nombre : cita.paciente_nombre;
  const iniciales = (otro ?? '?').replace(/^(Dr|Dra)\.\s*/, '').split(' ').slice(0, 2).map((p) => p[0]).join('');
  const mmss = `${String(Math.floor(segundos / 60)).padStart(2, '0')}:${String(segundos % 60).padStart(2, '0')}`;

  return (
    <div className={panel && verPanel ? 'call-layout con-panel' : 'call-layout'}>
    <section className="call">
      <div className="stage">
        <div ref={remotoAcs} className="remoto-acs" />
        <div className="remote">
          <div className="avatar">{iniciales}</div>
          <p>{conectado ? otro : `Esperando a ${otro}…`}</p>
          {conectado && <p className="small">{mmss}</p>}
        </div>
        <video ref={video} className={`self ${soloAudio || sala?.modo === 'azure' ? 'hidden' : ''}`} autoPlay playsInline muted />
        <div ref={selfAcs} className={`self ${soloAudio || sala?.modo !== 'azure' ? 'hidden' : ''}`} />
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
          Sala {sala.sala} · token de Communication Services {sala.modo === 'simulado' ? '(simulado en la demo)' : 'emitido'} · vence {hora(sala.expira)}
        </p>
      )}
    </section>
    {panel && verPanel && panel(segundos)}
    </div>
  );
}
