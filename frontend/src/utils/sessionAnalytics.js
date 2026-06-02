/** Client-side per-round outcomes for dashboard charts (no API change). */

function key(sessionId) {
  return `saboteur:outcomes:${sessionId}`;
}

export function recordRoundOutcome(sessionId, outcome) {
  if (!sessionId || !outcome) return;
  try {
    const raw = sessionStorage.getItem(key(sessionId));
    const list = raw ? JSON.parse(raw) : [];
    list.push({ outcome, at: Date.now() });
    sessionStorage.setItem(key(sessionId), JSON.stringify(list.slice(-80)));
  } catch {
    /* ignore quota errors */
  }
}

export function getRoundOutcomes(sessionId) {
  if (!sessionId) return [];
  try {
    const raw = sessionStorage.getItem(key(sessionId));
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

/** Build chart rows: rolling over-trust rate (0–100) per round index. */
export function buildOverTrustTrend(sessionId) {
  const outcomes = getRoundOutcomes(sessionId);
  if (outcomes.length === 0) return [];

  let over = 0;
  return outcomes.map((row, i) => {
    if (row.outcome === 'over_trust') over += 1;
    return {
      round: i + 1,
      rate: Math.round((over / (i + 1)) * 100),
      event: row.outcome === 'over_trust' ? 1 : 0,
    };
  });
}
