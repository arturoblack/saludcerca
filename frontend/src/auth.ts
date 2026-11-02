/*
 * Autenticación.
 *  - VITE_AUTH_MODE=dev   : se elige un usuario ficticio; el token es "dev:<id>" (solo demo local).
 *  - VITE_AUTH_MODE=entra : Microsoft Entra External ID con MSAL (inicio de sesión con redirección + MFA).
 *  - VITE_AUTH_MODE=oidc  : proveedor OpenID Connect genérico con Authorization Code + PKCE
 *                           (pruebas locales con mock-oauth2-server; ver docker-compose.pruebas.yml).
 */
const env: Record<string, string | undefined> = (import.meta as any).env ?? {};
export const AUTH_MODE = env.VITE_AUTH_MODE ?? 'dev';

const DEV_KEY = 'saludcerca.dev.user';

type Msal = import('@azure/msal-browser').PublicClientApplication;
let msal: Msal | null = null;

const scopes = [`api://${env.VITE_ENTRA_API_CLIENT_ID}/access_as_user`];

async function getMsal(): Promise<Msal> {
  if (msal) return msal;
  const { PublicClientApplication } = await import('@azure/msal-browser');
  msal = new PublicClientApplication({
    auth: {
      clientId: env.VITE_ENTRA_SPA_CLIENT_ID ?? '',
      authority: `https://${env.VITE_ENTRA_TENANT_SUBDOMAIN}.ciamlogin.com/`,
      redirectUri: window.location.origin,
    },
    cache: { cacheLocation: 'sessionStorage' },
  });
  await msal.initialize();
  const result = await msal.handleRedirectPromise();
  if (result?.account) msal.setActiveAccount(result.account);
  else if (!msal.getActiveAccount() && msal.getAllAccounts().length) msal.setActiveAccount(msal.getAllAccounts()[0]);
  return msal;
}

export async function iniciarSesionEntra(): Promise<void> {
  const app = await getMsal();
  await app.loginRedirect({ scopes });
}

// ---------- OIDC genérico (Authorization Code + PKCE) ----------
const OIDC_KEY = 'saludcerca.oidc';
const oidcAuthority = (env.VITE_OIDC_AUTHORITY ?? '').replace(/\/$/, '');
const oidcTokenUrl = env.VITE_OIDC_TOKEN_URL || `${oidcAuthority}/token`;
const oidcClientId = env.VITE_OIDC_CLIENT_ID ?? 'saludcerca-web';

const b64url = (bytes: Uint8Array) => btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
const aleatorio = (n = 32) => b64url(crypto.getRandomValues(new Uint8Array(n)));

async function iniciarSesionOidc(): Promise<void> {
  const verifier = aleatorio(48);
  const state = aleatorio(16);
  const challenge = b64url(new Uint8Array(await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier))));
  sessionStorage.setItem(`${OIDC_KEY}.pkce`, JSON.stringify({ verifier, state }));
  const q = new URLSearchParams({
    client_id: oidcClientId, response_type: 'code', redirect_uri: `${location.origin}/`, scope: 'openid profile',
    code_challenge: challenge, code_challenge_method: 'S256', state,
  });
  location.assign(`${oidcAuthority}/authorize?${q}`);
}

let callbackEnCurso: Promise<void> | null = null;
function procesarCallbackOidc(): Promise<void> {
  const url = new URL(location.href);
  const code = url.searchParams.get('code');
  if (!code) return Promise.resolve();
  callbackEnCurso ??= (async () => {
    const pkce = JSON.parse(sessionStorage.getItem(`${OIDC_KEY}.pkce`) ?? '{}');
    history.replaceState(null, '', url.pathname); // quitar ?code=… de la barra
    if (!pkce.verifier || pkce.state !== url.searchParams.get('state')) throw new Error('Respuesta de inicio de sesión inválida');
    const res = await fetch(oidcTokenUrl, {
      method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({ grant_type: 'authorization_code', code, redirect_uri: `${location.origin}/`,
        client_id: oidcClientId, code_verifier: pkce.verifier }),
    });
    if (!res.ok) throw new Error(`El proveedor de identidad respondió ${res.status}`);
    const t = await res.json();
    sessionStorage.setItem(`${OIDC_KEY}.token`, JSON.stringify({ token: t.access_token, exp: Date.now() + (t.expires_in ?? 3600) * 1000 }));
    sessionStorage.removeItem(`${OIDC_KEY}.pkce`);
  })();
  return callbackEnCurso;
}

function tokenOidc(): string | null {
  const t = JSON.parse(sessionStorage.getItem(`${OIDC_KEY}.token`) ?? 'null');
  return t && t.exp > Date.now() + 30_000 ? t.token : null;
}

export async function iniciarSesion(): Promise<void> {
  if (AUTH_MODE === 'oidc') return iniciarSesionOidc();
  return iniciarSesionEntra();
}

export function iniciarSesionDev(usuarioId: string): void {
  sessionStorage.setItem(DEV_KEY, usuarioId);
}

export async function haySesion(): Promise<boolean> {
  if (AUTH_MODE === 'dev') return !!sessionStorage.getItem(DEV_KEY);
  if (AUTH_MODE === 'oidc') { await procesarCallbackOidc(); return !!tokenOidc(); }
  return !!(await getMsal()).getActiveAccount();
}

export async function getToken(): Promise<string | null> {
  if (AUTH_MODE === 'dev') {
    const id = sessionStorage.getItem(DEV_KEY);
    return id ? `dev:${id}` : null;
  }
  if (AUTH_MODE === 'oidc') { await procesarCallbackOidc(); return tokenOidc(); }
  const app = await getMsal();
  const account = app.getActiveAccount();
  if (!account) return null;
  try {
    return (await app.acquireTokenSilent({ scopes, account })).accessToken;
  } catch {
    await app.acquireTokenRedirect({ scopes, account });
    return null;
  }
}

export async function cerrarSesion(): Promise<void> {
  if (AUTH_MODE === 'dev') {
    sessionStorage.removeItem(DEV_KEY);
    return;
  }
  if (AUTH_MODE === 'oidc') {
    sessionStorage.removeItem(`${OIDC_KEY}.token`);
    return;
  }
  await (await getMsal()).logoutRedirect();
}
