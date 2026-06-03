// Single point of contact with the backend.
import { env } from './config/env.js';
import {
  ApiError,
  configApiError,
  getErrorMessage,
  httpApiError,
  isSessionLostError,
  networkApiError,
} from './utils/apiErrors.js';

export { getErrorMessage, ApiError, isSessionLostError };

const API_BASE = env.apiBase || (import.meta.env.DEV ? '/api' : '');

function sessionStorageKey() {
  return env.sessionStorageKey || 'saboteur_session_id';
}

export async function request(path, options = {}) {
  if (import.meta.env.PROD && !API_BASE) {
    throw configApiError(
      'This build has no API URL. Set VITE_API_BASE to your Railway backend in Vercel, then redeploy.',
    );
  }
  const { parseJson = true, ...fetchOptions } = options;
  const headers = { ...(fetchOptions.headers || {}) };
  if (fetchOptions.body && !(fetchOptions.body instanceof FormData)) {
    headers['Content-Type'] = headers['Content-Type'] || 'application/json';
  }

  let resp;
  try {
    resp = await fetch(`${API_BASE}${path}`, {
      ...fetchOptions,
      headers,
    });
  } catch (cause) {
    throw networkApiError(cause);
  }

  if (!resp.ok) {
    let body = '';
    try {
      body = await resp.text();
    } catch {
      /* ignore */
    }
    throw httpApiError(resp.status, body, { apiBase: API_BASE });
  }

  if (!parseJson) return resp;
  try {
    return await resp.json();
  } catch (cause) {
    throw new ApiError('parse', 'Invalid response from server.', { cause });
  }
}

export const api = {
  health: () => request('/health'),

  createSession: () => request('/session', { method: 'POST' }),
  dashboard: (sid) => request(`/session/${sid}/dashboard`),

  domains: () => request('/domains'),
  domainMisconceptions: (did) => request(`/domains/${did}/misconceptions`),

  newRound: (sid, { domainId, difficulty, problemType, corruptProb = 0.5, propagate = false } = {}) => {
    const params = new URLSearchParams();
    if (domainId) params.set('domain_id', domainId);
    if (difficulty) params.set('difficulty', difficulty);
    if (problemType) params.set('problem_type', problemType);
    params.set('corrupt_prob', corruptProb);
    if (propagate) params.set('propagate', 'true');
    return request(`/session/${sid}/round?${params.toString()}`);
  },

  grade: (payload) =>
    request('/grade', { method: 'POST', body: JSON.stringify(payload) }),

  hint: (sid, rid, tier) =>
    request('/hint', {
      method: 'POST',
      body: JSON.stringify({ session_id: sid, round_id: rid, tier }),
    }),

  misconceptions: () => request('/misconceptions'),

  byoai: (problem, steps) =>
    request('/byoai', {
      method: 'POST',
      body: JSON.stringify({ problem, steps }),
    }),

  audit: ({ blob, domain_id = null, problem_override = null }) =>
    request('/audit', {
      method: 'POST',
      body: JSON.stringify({ blob, domain_id, problem_override }),
    }),

  imageConfigured: () => request('/image/configured'),

  imageTranscribe: async (file, hint) => {
    const form = new FormData();
    form.append('file', file);
    const q = hint ? `?hint=${encodeURIComponent(hint)}` : '';
    return request(`/image/transcribe${q}`, { method: 'POST', body: form });
  },

  classBySession: (sessionId) => request(`/class/by-session/${sessionId}`),

  classJoin: (payload) =>
    request('/class/join', { method: 'POST', body: JSON.stringify(payload) }),

  classDashboard: (teacherToken) =>
    request('/class/dashboard', {
      headers: { 'X-Teacher-Token': teacherToken },
    }),

  classCreate: (payload) =>
    request('/class', { method: 'POST', body: JSON.stringify(payload) }),

  matchGet: (matchId) => request(`/match/${matchId}`),

  matchCreate: (payload) =>
    request('/match', { method: 'POST', body: JSON.stringify(payload) }),

  matchJoin: (payload) =>
    request('/match/join', { method: 'POST', body: JSON.stringify(payload) }),

  matchStart: (matchId, payload) =>
    request(`/match/${matchId}/start`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  matchNextRound: (matchId, payload) =>
    request(`/match/${matchId}/next-round`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  matchSubmit: (matchId, payload) =>
    request(`/match/${matchId}/submit`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),

  roundPublic: (roundId, sessionId) =>
    request(`/round/${roundId}/public?session_id=${encodeURIComponent(sessionId)}`),

  leaderboard: ({ period = 'all_time', domainId, classId, limit = 50 } = {}) => {
    const params = new URLSearchParams({ period, limit: String(limit) });
    if (domainId) params.set('domain_id', domainId);
    if (classId) params.set('class_id', classId);
    return request(`/leaderboard?${params.toString()}`);
  },

  setDisplay: (sessionId, { nickname, opted_in }) =>
    request('/session/display', {
      method: 'POST',
      body: JSON.stringify({ session_id: sessionId, nickname, opted_in }),
    }),

  getDisplay: (sessionId) => request(`/session/${sessionId}/display`),

  achievements: (sessionId) => request(`/session/${sessionId}/achievements`),
};

const LEGACY_SESSION_KEY = 'saboteur:session_id';

function migrateLegacySessionKey() {
  const key = sessionStorageKey();
  const legacy = localStorage.getItem(LEGACY_SESSION_KEY);
  if (legacy && !localStorage.getItem(key)) {
    localStorage.setItem(key, legacy);
  }
  localStorage.removeItem(LEGACY_SESSION_KEY);
}

export async function getOrCreateSession() {
  migrateLegacySessionKey();
  const key = sessionStorageKey();
  const stored = localStorage.getItem(key);
  if (stored) {
    try {
      await api.dashboard(stored);
      return stored;
    } catch (e) {
      if (e instanceof ApiError && e.kind === 'network') throw e;
      if (e instanceof ApiError && e.kind === 'config') throw e;
      localStorage.removeItem(key);
    }
  }
  const created = await api.createSession();
  localStorage.setItem(key, created.session_id);
  return created.session_id;
}

/** Drop cached session id and create a new server session. */
export async function refreshSession() {
  clearSession();
  return getOrCreateSession();
}

export function clearSession() {
  const key = sessionStorageKey();
  localStorage.removeItem(key);
  localStorage.removeItem(LEGACY_SESSION_KEY);
}
