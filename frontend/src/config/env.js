/**
 * Frontend configuration from Vite env (.env, .env.development, .env.production).
 * Only VITE_* variables are exposed to the browser.
 */

function requireInProd(value, name) {
  if (import.meta.env.PROD && !value) {
    console.warn(`[config] Missing ${name} in production build.`);
  }
  return value;
}

/** Strip trailing slashes from API base URL. */
function normalizeBase(url) {
  if (!url) return '';
  return url.replace(/\/+$/, '');
}

const apiBase = normalizeBase(
  import.meta.env.VITE_API_BASE ??
    (import.meta.env.DEV ? '/api' : '')
);

requireInProd(apiBase, 'VITE_API_BASE');

export const env = {
  /** Fetch prefix for all API calls (e.g. /api in dev, full URL in prod). */
  apiBase,

  /** Dev-only: Vite proxy target (not sent to browser). Documented in .env.example. */
  proxyTarget: import.meta.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8001',

  devServerPort: Number(import.meta.env.VITE_DEV_SERVER_PORT) || 5173,

  appTitle: import.meta.env.VITE_APP_TITLE || 'The Saboteur',

  sessionStorageKey:
    import.meta.env.VITE_SESSION_STORAGE_KEY || 'saboteur_session_id',

  defaultCorruptProb: Number(import.meta.env.VITE_DEFAULT_CORRUPT_PROB ?? 0.5),

  isDev: import.meta.env.DEV,
  isProd: import.meta.env.PROD,
};

export default env;
