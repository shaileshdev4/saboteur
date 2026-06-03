/**
 * User-facing API errors. Never expose raw stack traces or HTTP bodies in the UI.
 */

export class ApiError extends Error {
  constructor(kind, message, { status, cause } = {}) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind; // network | http | config | parse
    this.status = status;
    this.cause = cause;
  }
}

function isNetworkFailure(err) {
  if (err instanceof ApiError && err.kind === 'network') return true;
  if (err?.name === 'TypeError' && /fetch|network|Failed/i.test(String(err.message))) {
    return true;
  }
  return false;
}

/** Short hint for developers running locally. */
export function getDevBackendHint() {
  return (
    'Start the API from the repo root: uvicorn backend.main:app --reload --host 127.0.0.1 --port 8001 ' +
    '— then run the UI with npm run dev (proxies /api).'
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
      if (context === 'session') return 'Session expired. Use Reset session and try again.';
      return 'That resource was not found. Try refreshing or starting a new round.';
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

export function httpApiError(status, bodySnippet = '') {
  let message;
  if (status === 404) message = 'Not found. Your session may have expired — use Reset session.';
  else if (status === 429) message = 'Too many requests. Wait a minute and try again.';
  else if (status === 503) message = 'Service unavailable. Try again later.';
  else if (status >= 500) message = `Server error (${status}). Try again shortly.`;
  else if (status >= 400) {
    const detail = bodySnippet?.slice(0, 120)?.trim();
    message = detail
      ? `Request failed (${status}): ${detail}`
      : `Request failed (${status}). Check your input and try again.`;
  } else message = `Unexpected response (${status}).`;

  return new ApiError('http', message, { status });
}
