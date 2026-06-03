import React, { useEffect, useRef, useState } from 'react';
import { Users } from 'lucide-react';
import katex from 'katex';
import StepCard from './StepCard.jsx';
import Button from './ui/Button.jsx';
import Card from './ui/Card.jsx';
import Chip from './ui/Chip.jsx';
import { Check, ChevronRight } from './ui/StatusIcon.jsx';

import { api, getErrorMessage } from '../api.js';

function LaTeXBlock({ tex, displayMode = false }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current && tex) {
      try {
        katex.render(tex, ref.current, { throwOnError: false, displayMode });
      } catch {
        ref.current.textContent = tex;
      }
    }
  }, [tex, displayMode]);
  return <span ref={ref} />;
}

export default function MultiplayerMode({ sessionId }) {
  const [view, setView] = useState('hub');     // hub | lobby | playing | finished
  const [nickname, setNickname] = useState('');
  const [joinCode, setJoinCode] = useState('');
  const [match, setMatch] = useState(null);
  const [round, setRound] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Poll the match while waiting for the other player or for them to answer.
  useEffect(() => {
    if (!match) return;
    if (match.state === 'finished') return;
    // Only poll when there's something to wait for:
    //   - lobby: waiting for player 2 to join
    //   - in_progress with no current_round_id: waiting for next round
    //   - in_progress with both not answered: race underway
    const interval = setInterval(async () => {
      try {
        const m = await api.matchGet(match.match_id);
        setMatch(m);
        if (m.state === 'in_progress' && view === 'lobby') {
          setView('playing');
        }
        if (m.state === 'finished') {
          setView('finished');
        }
      } catch {}
    }, 1500);
    return () => clearInterval(interval);
  }, [match, view]);

  // When a new round_id appears, fetch the round payload.
  useEffect(() => {
    if (!match) return;
    if (!match.current_round_id) {
      setRound(null);
      return;
    }
    // The round was created via /match/.../next-round; the round_id is reused.
    // We need to display the round, but we don't have direct access to the
    // RoundOut schema via match. Hit /round on the match's session.
    // Actually: the simplest path is to make next-round return the round
    // payload. For now, we GET /session/.../round won't work for the opponent.
    // We'll display steps fetched via a dedicated multiplayer round payload.
    // For V3 simplicity, the round payload is reconstructed by parsing the
    // truth_steps via a separate endpoint — but since that's not built, we
    // call /match/.../next-round (idempotent — returns existing match) and
    // fetch the actual round from the backend with /round/{round_id} if it
    // existed. Workaround: re-fetch by calling next-round which is idempotent.
  }, [match]);

  const createMatch = async () => {
    if (!nickname.trim()) {
      setError('Pick a nickname first.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const m = await api.matchCreate({
        session_id: sessionId,
        nickname: nickname.trim(),
      });
      setMatch(m);
      setView('lobby');
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const joinMatch = async () => {
    if (!nickname.trim() || !joinCode.trim()) {
      setError('Nickname and code required.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const m = await api.matchJoin({
        session_id: sessionId,
        nickname: nickname.trim(),
        join_code: joinCode.trim().toUpperCase(),
      });
      setMatch(m);
      setView('lobby');
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const startMatch = async () => {
    setLoading(true);
    setError('');
    try {
      const m = await api.matchStart(match.match_id, { session_id: sessionId });
      setMatch(m);
      await nextRound();
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const nextRound = async () => {
    try {
      const m = await api.matchNextRound(match.match_id, { session_id: sessionId });
      setMatch(m);
      setView('playing');
    } catch (e) {
      setError(getErrorMessage(e));
    }
  };

  if (!sessionId) {
    return (
      <div className="layout-shell py-8 text-center text-sm text-ink-400">
        Connect to the API from the Play tab first (or use Retry in the banner).
      </div>
    );
  }

  if (view === 'hub') {
    return (
      <Hub
        sessionId={sessionId}
        nickname={nickname}
        setNickname={setNickname}
        joinCode={joinCode}
        setJoinCode={setJoinCode}
        onCreate={createMatch}
        onJoin={joinMatch}
        loading={loading}
        error={error}
      />
    );
  }

  if (!match) return null;

  return (
    <div className="layout-shell py-4 sm:py-6 space-y-5">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <div>
          <p className="text-caption text-accent-soft mb-0.5">Head-to-head audit</p>
          <h2 className="text-xl sm:text-2xl font-semibold tracking-tight">
            Multiplayer
          </h2>
          <p className="text-sm text-ink-400 mt-1">
            Round {match.current_round_number} / {match.total_rounds} · {match.state}
          </p>
        </div>
        <ScoreBoard match={match} sessionId={sessionId} />
      </header>

      {match.state === 'lobby' && (
        <Lobby
          match={match}
          isHost={match.players[0]?.session_id === sessionId}
          onStart={startMatch}
          loading={loading}
        />
      )}

      {match.state === 'in_progress' && (
        <PlayingView
          match={match}
          sessionId={sessionId}
          onNextRound={nextRound}
        />
      )}

      {match.state === 'finished' && (
        <FinishedView match={match} sessionId={sessionId} onPlayAgain={() => {
          setMatch(null); setView('hub');
        }} />
      )}

      {error && <p className="text-sm text-bad-foreground">{error}</p>}
    </div>
  );
}

function Hub({ nickname, setNickname, joinCode, setJoinCode, onCreate, onJoin, loading, error }) {
  return (
    <div className="layout-shell py-4 sm:py-6 space-y-5">
      <header>
        <h2 className="text-xl sm:text-2xl font-semibold tracking-tight">
          Multiplayer
        </h2>
        <p className="text-sm text-ink-400 mt-1">
          Two players race on the same round. First to correctly catch wins
          the round. 5 rounds per match.
        </p>
      </header>

      <div>
        <label className="text-xs uppercase tracking-wider text-ink-400 block mb-1">
          Your nickname
        </label>
        <input
          type="text"
          value={nickname}
          onChange={(e) => setNickname(e.target.value)}
          placeholder="e.g. you"
          maxLength={24}
          className="w-full px-4 py-3 rounded-lg bg-ink-800 border border-ink-700 text-ink-50 focus:border-accent"
        />
      </div>

      <div className="grid sm:grid-cols-2 gap-3">
        <div className="rounded-2xl border border-ink-700 bg-ink-800/40 p-5">
          <div className="text-lg font-semibold mb-2">Start a new match</div>
          <p className="text-sm text-ink-400 mb-3">
            You'll get a code to share with your opponent.
          </p>
          <button
            onClick={onCreate}
            disabled={loading || !nickname.trim()}
            className="px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 font-semibold w-full disabled:opacity-50"
          >
            {loading ? '…' : 'Create match'}
          </button>
        </div>
        <div className="rounded-2xl border border-ink-700 bg-ink-800/40 p-5">
          <div className="text-lg font-semibold mb-2">Join a match</div>
          <input
            type="text"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            placeholder="ABCD"
            maxLength={6}
            className="w-full px-3 py-2 rounded-lg bg-ink-800 border border-ink-700 font-mono uppercase mb-2 focus:border-accent"
          />
          <button
            onClick={onJoin}
            disabled={loading || !nickname.trim() || !joinCode.trim()}
            className="px-4 py-2 rounded-lg bg-ink-700 hover:bg-ink-600 font-semibold w-full disabled:opacity-50"
          >
            {loading ? '…' : 'Join'}
          </button>
        </div>
      </div>

      {error && <p className="text-sm text-bad-foreground">{error}</p>}
    </div>
  );
}

function ScoreBoard({ match, sessionId }) {
  return (
    <div className="flex items-center gap-2 text-sm">
      {match.players.map((p, i) => {
        const isYou = p.session_id === sessionId;
        return (
          <div
            key={p.session_id}
            className={`px-3 py-1.5 rounded-lg ${
              isYou ? 'bg-accent/20 text-accent-soft' : 'bg-ink-800'
            }`}
          >
            <span className="font-medium">{p.nickname}</span>
            <span className="ml-2 font-mono">{p.score}</span>
          </div>
        );
      })}
    </div>
  );
}

function Lobby({ match, isHost, onStart, loading }) {
  return (
    <div className="rounded-2xl border border-ink-700 bg-ink-800/40 p-5 step-in">
      <div className="text-xs uppercase tracking-wider text-ink-400">
        Share this code
      </div>
      <div className="text-3xl font-mono font-bold text-accent mt-1">
        {match.join_code}
      </div>
      <p className="text-sm text-ink-400 mt-3">
        Waiting for {match.players.length === 1
          ? 'an opponent to join…'
          : 'host to start the match…'}
      </p>
      {isHost && match.players.length >= 2 && (
        <button
          onClick={onStart}
          disabled={loading}
          className="mt-4 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 font-semibold disabled:opacity-50"
        >
          {loading ? '…' : 'Start match'}
        </button>
      )}
    </div>
  );
}

function PlayingView({ match, sessionId, onNextRound }) {
  const [round, setRound] = useState(null);
  const [loadingRound, setLoadingRound] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [flaggedIndex, setFlaggedIndex] = useState(null);
  const [error, setError] = useState('');
  const me = match.players.find((p) => p.session_id === sessionId);
  const answered = me?.answered_this_round;

  // Fetch the round payload whenever current_round_id changes.
  useEffect(() => {
    if (!match.current_round_id) {
      setRound(null);
      return;
    }
    setLoadingRound(true);
    setFlaggedIndex(null);
    api.roundPublic(match.current_round_id, sessionId)
      .then((r) => setRound(r))
      .catch((e) => setError(getErrorMessage(e)))
      .finally(() => setLoadingRound(false));
  }, [match.current_round_id, sessionId]);

  const submit = async (decision) => {
    setSubmitting(true);
    setError('');
    try {
      const body = {
        session_id: sessionId,
        round_id: match.current_round_id,
        decision,
      };
      if (decision === 'flag') {
        if (flaggedIndex === null) {
          setError('Tap a step to flag first.');
          setSubmitting(false);
          return;
        }
        body.flagged_step_index = flaggedIndex;
      }
      await api.matchSubmit(match.match_id, body);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  // No active round → between rounds.
  if (!match.current_round_id) {
    return (
      <Card variant="default" className="p-5 text-center step-in">
        <p className="text-ink-400 mb-3">
          Round {match.current_round_number} ended. Ready for the next?
        </p>
        <Button
          variant="primary"
          size="md"
          onClick={onNextRound}
          className="inline-flex items-center gap-1.5 btn-press"
        >
          Next round
          <ChevronRight size={16} aria-hidden />
        </Button>
      </Card>
    );
  }

  if (loadingRound || !round) {
    return <div className="text-ink-400 py-8 text-center text-sm">Loading round…</div>;
  }

  return (
    <div className="space-y-3 step-in pb-4">
      <div className="flex flex-wrap items-center gap-2">
        <Chip variant="muted" className="inline-flex items-center gap-1">
          <Users size={12} aria-hidden />
          Head-to-head
        </Chip>
        <Chip variant="accent">Round {match.current_round_number}</Chip>
      </div>
      <p className="text-sm text-ink-400">
        Race: first correct trust or flag wins this round.
      </p>

      <div className="space-y-3">
        {round.steps.map((step) => (
          <StepCard
            key={step.index}
            step={step}
            index={step.index}
            selectable={!answered && step.operation !== 'initial'}
            flaggedIndex={flaggedIndex}
            onSelect={setFlaggedIndex}
          />
        ))}
      </div>

      {answered ? (
        <Card variant="default" className="p-3 panel-good">
          <p className="text-good-foreground text-sm inline-flex items-center gap-2">
            <Check size={16} aria-hidden />
            You submitted. Waiting for opponent…
          </p>
        </Card>
      ) : (
        <div className="action-bar-sticky">
            <Card variant="glass" className="p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 shadow-card">
              <p className="text-xs text-ink-400">
                {flaggedIndex === null
                  ? 'Tap a step to flag, or trust.'
                  : `Flagging step ${flaggedIndex}`}
              </p>
              <div className="flex items-center gap-2 justify-end shrink-0">
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => submit('trust')}
                  disabled={submitting}
                  className="btn-press"
                >
                  Trust
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => submit('flag')}
                  disabled={submitting || flaggedIndex === null}
                  className="btn-press"
                >
                  {flaggedIndex !== null ? `Flag step ${flaggedIndex}` : 'Flag step…'}
                </Button>
              </div>
            </Card>
        </div>
      )}
      {error && <p className="text-sm text-bad-foreground">{error}</p>}
    </div>
  );
}

function FinishedView({ match, sessionId, onPlayAgain }) {
  const sorted = [...match.players].sort((a, b) => b.score - a.score);
  const me = match.players.find((p) => p.session_id === sessionId);
  const won = sorted[0]?.session_id === sessionId && sorted[0]?.score > (sorted[1]?.score || -1);
  const tied = sorted[0]?.score === sorted[1]?.score;

  return (
    <div className={`rounded-2xl border p-5 step-in text-center ${
      won ? 'panel-good' : tied ? 'panel-warn' : 'panel-bad'
    }`}>
      <div className="text-2xl font-bold mb-2 text-ink-50">
        {tied ? 'Tied!' : won ? 'You won!' : 'You lost.'}
      </div>
      <div className="text-sm text-ink-300">
        Final: {sorted.map((p) => `${p.nickname} ${p.score}`).join(' · ')}
      </div>
      <button
        onClick={onPlayAgain}
        className="mt-4 px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 font-semibold"
      >
        Play again
      </button>
    </div>
  );
}
