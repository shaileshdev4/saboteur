import React, { useCallback, useEffect, useState } from 'react';
import { Trophy } from 'lucide-react';
import { api } from '../api.js';
import Button from './ui/Button.jsx';
import Card from './ui/Card.jsx';
import Chip from './ui/Chip.jsx';
import Input from './ui/Input.jsx';

const PERIODS = [
  { id: 'daily', label: 'Daily' },
  { id: 'weekly', label: 'Weekly' },
  { id: 'all_time', label: 'All-time' },
];

export default function Leaderboard({ sessionId, domains = [] }) {
  const [period, setPeriod] = useState('weekly');
  const [domainId, setDomainId] = useState('');
  const [classId, setClassId] = useState('');
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [display, setDisplay] = useState({ nickname: '', opted_in: false });
  const [modalOpen, setModalOpen] = useState(false);
  const [nickname, setNickname] = useState('');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const loadBoard = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.leaderboard({
        period,
        domainId: domainId || undefined,
        classId: classId.trim() || undefined,
      });
      setEntries(data.entries || []);
    } catch (e) {
      setError(e.message || String(e));
      setEntries([]);
    } finally {
      setLoading(false);
    }
  }, [period, domainId, classId]);

  useEffect(() => {
    loadBoard();
  }, [loadBoard]);

  useEffect(() => {
    if (!sessionId) return;
    api.getDisplay(sessionId).then(setDisplay).catch(() => {});
  }, [sessionId]);

  const saveDisplay = async (optedIn) => {
    if (!sessionId) return;
    setSaving(true);
    setError('');
    try {
      await api.setDisplay(sessionId, {
        nickname: nickname.trim(),
        opted_in: optedIn,
      });
      setDisplay({ nickname: nickname.trim(), opted_in: optedIn });
      setModalOpen(false);
      loadBoard();
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="layout-shell py-6 pb-10">
      <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Trophy size={20} className="text-warn-foreground" aria-hidden />
            <h2 className="text-xl font-semibold">Ranks</h2>
          </div>
          <p className="text-sm text-ink-400 max-w-lg">
            Opt in with a nickname to appear on public leaderboards. Until you do, your stats stay private.
          </p>
        </div>
        {sessionId && (
          <Button
            variant={display.opted_in ? 'secondary' : 'primary'}
            size="sm"
            onClick={() => {
              setNickname(display.nickname || '');
              setModalOpen(true);
            }}
          >
            {display.opted_in ? 'Update nickname' : 'Join leaderboard'}
          </Button>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {PERIODS.map((p) => (
          <button
            key={p.id}
            type="button"
            onClick={() => setPeriod(p.id)}
            className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
              period === p.id
                ? 'bg-accent text-white'
                : 'bg-surface text-ink-300 hover:text-ink-100 border border-line'
            }`}
          >
            {p.label}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap gap-2 mb-4 items-center">
        <span className="text-caption">Domain</span>
        <Chip
          variant={domainId === '' ? 'accent-soft' : 'default'}
          onClick={() => setDomainId('')}
          className="cursor-pointer"
        >
          Combined
        </Chip>
        {domains.map((d) => (
          <Chip
            key={d.id}
            variant={domainId === d.id ? 'accent-soft' : 'default'}
            onClick={() => setDomainId(d.id)}
            className="cursor-pointer"
          >
            {d.label}
          </Chip>
        ))}
      </div>

      <div className="mb-4 max-w-xs">
        <Input
          label="Class ID (optional)"
          value={classId}
          onChange={(e) => setClassId(e.target.value)}
          placeholder="Per-class board"
        />
      </div>

      {error && (
        <p className="text-sm text-bad-foreground mb-4">{error}</p>
      )}

      {loading ? (
        <p className="text-ink-400 text-center py-12">Loading ranks…</p>
      ) : entries.length === 0 ? (
        <Card variant="default" className="p-8 text-center text-ink-400">
          No ranked players yet for this filter. Be the first to opt in.
        </Card>
      ) : (
        <Card variant="default" className="overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-caption">
                  <th className="px-4 py-3 w-12">#</th>
                  <th className="px-4 py-3">Player</th>
                  <th className="px-4 py-3 text-right">Score</th>
                  <th className="px-4 py-3 text-right hidden sm:table-cell">Rounds</th>
                  <th className="px-4 py-3 text-right hidden sm:table-cell">Rating</th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e, i) => (
                  <tr
                    key={e.session_id}
                    className={`border-b border-line/60 ${
                      e.session_id === sessionId ? 'bg-accent-muted/40' : ''
                    }`}
                  >
                    <td className="px-4 py-3 font-mono text-ink-500">{i + 1}</td>
                    <td className="px-4 py-3 font-medium text-ink-100">
                      {e.nickname}
                      {e.session_id === sessionId && (
                        <span className="text-xs text-accent-foreground ml-2">(you)</span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right font-mono text-good-foreground">
                      {Math.round(e.score)}
                    </td>
                    <td className="px-4 py-3 text-right font-mono hidden sm:table-cell">
                      {e.rounds}
                    </td>
                    <td className="px-4 py-3 text-right font-mono hidden sm:table-cell">
                      {Math.round(e.rating)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {modalOpen && (
        <div
          className="fixed inset-0 z-50 grid place-items-center bg-black/70 px-4"
          onClick={() => setModalOpen(false)}
        >
          <Card
            variant="elevated"
            className="max-w-sm w-full p-5 step-in"
            onClick={(ev) => ev.stopPropagation()}
          >
            <h3 className="font-semibold mb-2">Join public ranks</h3>
            <p className="text-xs text-ink-400 mb-4">
              Your calibration score and round count will be visible. You can opt out anytime.
            </p>
            <Input
              label="Nickname"
              value={nickname}
              onChange={(e) => setNickname(e.target.value)}
              maxLength={24}
              placeholder="Auditor42"
            />
            <div className="flex gap-2 mt-4">
              <Button
                variant="primary"
                disabled={saving || !nickname.trim()}
                onClick={() => saveDisplay(true)}
              >
                Opt in
              </Button>
              {display.opted_in && (
                <Button
                  variant="ghost"
                  disabled={saving}
                  onClick={() => saveDisplay(false)}
                >
                  Opt out
                </Button>
              )}
              <Button variant="ghost" onClick={() => setModalOpen(false)}>
                Cancel
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
