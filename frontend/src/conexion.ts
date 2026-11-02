import { useEffect, useState } from 'react';
import { API_BASE } from './api';

/*
 * Medición real de la conexión: mediana de 3 viajes de ida y vuelta a /api/health,
 * combinada con la pista del navegador (navigator.connection) donde exista.
 * navigator.connection no existe en Safari ni Firefox; la medición sí funciona en todos.
 */
export interface Conexion { ms: number; lenta: boolean }

const UMBRAL_MS = 700;

export async function medirConexion(intentos = 3): Promise<Conexion> {
  const tiempos: number[] = [];
  for (let i = 0; i < intentos; i++) {
    const ctrl = new AbortController();
    const t = setTimeout(() => ctrl.abort(), 5000);
    const inicio = performance.now();
    try {
      await fetch(`${API_BASE}/api/health`, { cache: 'no-store', signal: ctrl.signal });
      tiempos.push(performance.now() - inicio);
    } catch {
      tiempos.push(5000);
    } finally {
      clearTimeout(t);
    }
  }
  tiempos.sort((a, b) => a - b);
  const ms = Math.round(tiempos[Math.floor(tiempos.length / 2)]);
  const tipo = (navigator as any).connection?.effectiveType as string | undefined;
  const pistaLenta = tipo === 'slow-2g' || tipo === '2g' || tipo === '3g';
  return { ms, lenta: ms > UMBRAL_MS || pistaLenta };
}

export function useConexion(): Conexion | null {
  const [c, setC] = useState<Conexion | null>(null);
  useEffect(() => {
    let vivo = true;
    medirConexion().then((r) => vivo && setC(r));
    return () => { vivo = false; };
  }, []);
  return c;
}
