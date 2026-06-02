// Single point of contact with the backend.
// VITE_API_BASE in prod; Vite proxies /api/* in dev.

const API_BASE =
  import.meta.env.VITE_API_BASE ||
  (import.meta.env.DEV ? '/api' : 'http://localhost:8765');

async function request(path, options = {}) {
  const resp = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!resp.ok) {
    let body = '';
    try { body = await resp.text(); } catch {}
    const err = new Error(`HTTP ${resp.status}: ${body}`);
    err.status = resp.status;
    throw err;
  }
  return resp.json();
}

export const api = {
  health: () => request('/health'),

  // Sessions
  createSession: () => request('/session', { method: 'POST' }),
  dashboard: (sid) => request(`/session/${sid}/dashboard`),

  // Domains
  domains: () => request('/domains'),
  domainMisconceptions: (did) => request(`/domains/${did}/misconceptions`),

  // Rounds
  newRound: (sid, { domainId, difficulty, problemType, corruptProb = 0.5, propagate = false } = {}) => {
    const params = new URLSearchParams();
    if (domainId) params.set('domain_id', domainId);
    if (difficulty) params.set('difficulty', difficulty);
    if (problemType) params.set('problem_type', problemType);
    params.set('corrupt_prob', corruptProb);
    if (propagate) params.set('propagate', 'true');
    return request(`/session/${sid}/round?${params.toString()}`);
  },

  // Grade
  grade: (payload) =>
    request('/grade', { method: 'POST', body: JSON.stringify(payload) }),

  // Hints (new in V2)
  hint: (sid, rid, tier) =>
    request('/hint', {
      method: 'POST',
      body: JSON.stringify({ session_id: sid, round_id: rid, tier }),
    }),

  // Misconceptions (all domains combined)
  misconceptions: () => request('/misconceptions'),

  // BYOAI
  byoai: (problem, steps) =>
    request('/byoai', {
      method: 'POST',
      body: JSON.stringify({ problem, steps }),
    }),

  // V5: Leaderboards & achievements
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

// LocalStorage session persistence
const SESSION_KEY = 'saboteur:session_id';

export async function getOrCreateSession() {
  const stored = localStorage.getItem(SESSION_KEY);
  if (stored) {
    try {
      // Verify by hitting the dashboard endpoint.
      await api.dashboard(stored);
      return stored;
    } catch (e) {
      // Session no longer exists on backend; fall through to create a new one.
      localStorage.removeItem(SESSION_KEY);
    }
  }
  const created = await api.createSession();
  localStorage.setItem(SESSION_KEY, created.session_id);
  return created.session_id;
}

export function clearSession() {
  localStorage.removeItem(SESSION_KEY);
}
