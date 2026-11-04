import type { Sala } from './api';

export interface LlamadaAcs {
  video(activo: boolean): Promise<void>;
  microfono(activo: boolean): Promise<void>;
  colgar(): void;
}

// El SDK pesa cientos de kB: se carga solo al entrar a una consulta real, no en la demo ni en el resto de la app.
export async function unirseALlamada(sala: Sala, op: {
  conVideo: boolean; self: HTMLElement; remoto: HTMLElement; onHayOtraPersona: (hay: boolean) => void;
}): Promise<LlamadaAcs> {
  const [{ CallClient, LocalVideoStream, VideoStreamRenderer }, { AzureCommunicationTokenCredential }] =
    await Promise.all([import('@azure/communication-calling'), import('@azure/communication-common')]);
  type StreamRemoto = import('@azure/communication-calling').RemoteVideoStream;
  type Participante = import('@azure/communication-calling').RemoteParticipant;

  const cliente = new CallClient();
  const agente = await cliente.createCallAgent(new AzureCommunicationTokenCredential(sala.token));
  const dispositivos = await cliente.getDeviceManager();
  await dispositivos.askDevicePermission({ audio: true, video: op.conVideo });
  const camara = op.conVideo ? (await dispositivos.getCameras())[0] : undefined;
  const local = camara ? new LocalVideoStream(camara) : undefined;

  const llamada = agente.join({ groupId: sala.grupo },
    { audioOptions: { muted: false }, videoOptions: local ? { localVideoStreams: [local] } : undefined });

  let rendererLocal: InstanceType<typeof VideoStreamRenderer> | undefined;
  const mostrarLocal = async () => {
    if (!local || rendererLocal) return;
    rendererLocal = new VideoStreamRenderer(local);
    op.self.appendChild((await rendererLocal.createView({ scalingMode: 'Crop' })).target);
  };
  const ocultarLocal = () => { rendererLocal?.dispose(); rendererLocal = undefined; };
  await mostrarLocal();

  const vistas = new Map<number, InstanceType<typeof VideoStreamRenderer>>();
  const seguirStream = (s: StreamRemoto) => {
    const actualizar = async () => {
      if (s.isAvailable && !vistas.has(s.id)) {
        const r = new VideoStreamRenderer(s);
        vistas.set(s.id, r);
        op.remoto.appendChild((await r.createView({ scalingMode: 'Crop' })).target);
      } else if (!s.isAvailable) {
        vistas.get(s.id)?.dispose();
        vistas.delete(s.id);
      }
    };
    s.on('isAvailableChanged', actualizar);
    void actualizar();
  };
  const seguirParticipante = (p: Participante) => {
    p.videoStreams.forEach(seguirStream);
    p.on('videoStreamsUpdated', ({ added }) => added.forEach(seguirStream));
  };
  const avisar = () => op.onHayOtraPersona(llamada.remoteParticipants.length > 0);

  llamada.remoteParticipants.forEach(seguirParticipante);
  llamada.on('remoteParticipantsUpdated', ({ added }) => { added.forEach(seguirParticipante); avisar(); });
  avisar();

  let colgada = false;
  return {
    async video(activo) {
      if (!local || llamada.isLocalVideoStarted === activo) return;
      if (activo) { await llamada.startVideo(local); await mostrarLocal(); }
      else { await llamada.stopVideo(local); ocultarLocal(); }
    },
    async microfono(activo) { await (activo ? llamada.unmute() : llamada.mute()); },
    colgar() {
      if (colgada) return;
      colgada = true;
      // El SDK ya puede haber liberado las vistas al terminar la llamada.
      try { ocultarLocal(); vistas.forEach((r) => r.dispose()); } catch { /* ya liberadas */ }
      void llamada.hangUp().catch(() => undefined).finally(() => agente.dispose());
    },
  };
}
