/**
 * User-facing API errors. Never expose raw stack traces or HTTP bodies in the UI.
 */

export class ApiError extends Error {
  constructor(kind, message, { status, cause, resource } = {}) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind; // network | http | config | parse
    this.status = status;
    this.cause = cause;
    /** 'session' | 'round' | null - parsed from 404 bodies */
    this.resource = resource ?? null;
  }
}

function isNetworkFailure(err) {
  if (err instanceof ApiError && err.kind === 'network') return true;
  if (err?.name === 'TypeError' && /fetch|network|Failed/i.test(String(err.message))) {
    return true;
  }
  return false;
}

function parseApiDetail(bodySnippet) {
  const t = (bodySnippet || '').trim();
  if -t) return '';
  try {
    const j = JSON.parse(t);
    const d = j.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) {
      return d.map((x) => (typeof x === 'string' ? x : x.msg || '')).filter(Boolean).join('; ');
    }
  } catch {
    /* plain text body */
  }
  return t.slice(0, 200);
}

/** @param {unknown} err */
export function isSessionLostError(err) {
  return err instanceof ApiError && err.status === 404 && err.resource === 'session';
}

/** Short hint for developers running locally. */
export function getDevBackendHint() {
  return (
    'Start the API from the repo root: uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001 ' +
    '- then run the UI with npm run dev (proxies /api).'
  );
}

/**
 * @param {unknown} err
 * @param {{ context?: string }} [opts]
 */
export function getErrorMessage(err, { context } = {}) {
  if (err instanceof ApiError) {
    return err.message;
  }

  if (isNetworkFailure(err)) {
    if (import.meta.env.DEV) {
      return `Can't reach the API. ${getDevBackendHint()}`;
    }
    return (
      "Can't reach the server. Check your internet connection, or try again in a moment. " +
      'If you deployed the app, confirm the API is running and VITE_API_BASE points to it.'
    );
  }

  const msg = err?.message || '';
  if (/^HTTP \d+/.test(msg)) {
    const status = parseInt(msg.match(/^HTTP (\d+)/)?.[1] || '0', 10);
    if (status === 401 || status === 403) return "You don't have permission for that action.";
    if (status === 404) {
      if (context === 'session') {
        return 'Could not connect to the game server. Check VITE_API_BASE on Vercel or use Reset session.';
      }-
      return 'That resource was not found. Try Reset session or refresh the page.';
    }
    if (status === 429) return 'Too many requests. Wait a minute and try again.';
    if (status === 503) return 'That feature is not available on the server right now.';
    if (status >= 500) return 'Server error. Try again in a moment.';
    if (status >= 400) return 'Request could not be completed. Check your input and try again.';
  }

  if (msg && msg.length < 200 && !msg.includes('Unexpected token')) {
    return msg;
  }

  return 'Something went wrong. Try again.';
}

export function networkApiError(cause) {
  const message = import.meta.env.DEV
    ? `Can't reach the API. ${getDevBackendHint()}`
    : "Can't reach the server. Check your connection or try again shortly.";
  return new ApiError('network', message, { cause });
}

export function configApiError(message) {
  return new ApiError('config', message);
}

export function httpApiError(status, bodySnippet = '', { apiBase = '' } = {}) {
  const detail = parseApiDetail(bodySnippet).toLowerCase();
  let message;
  let resource = null;

  if (status === 404) {
    if (detail.includes('session')) {
      resource = 'session';
      message =
        'Your saved session is not on the server anymore (normal after a Railway redeploy). ' +
        'Tap Reset session or wait - we will start a new one automatically.';
    } else if (detail.includes('round')) {
      resource = 'round';
      message = 'That round is no longer available. Start a new round.';
    } else if (import.meta.env.PROD && !apiBase) {
      message =
        'The app is not linked to the API. In Vercel, set VITE_API_BASE to your Railway URL and redeploy.';
    } else {
      message =
        'API returned not found. Confirm VITE_API_BASE is your Railway backend URL (no trailing slash).';
    }
  } else if (status === 429) {
    message = 'Too many requests. Wait a minute and try again.';
  } else if (status === 503) {
    message = 'Service unavailable. Try again later.';
  } else if (status >= 500) {
    message = `Server error (${status}). Try again shortly.`;
  } else if (status >= 400) {
    const snippet = parseApiDetail(bodySnippet).trim();
    message = snippet
      ? `Request failed (${status}): ${snippet.slice(0, 100)}`
      : `Request failed (${status}). Check your input and try again.`;
  } else {
    message = `Unexpected response (${status}).`;
  }

  return new ApiError('http', message, { status, resource });
}
