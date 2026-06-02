import React, { useState } from 'react';
import { Lightbulb } from 'lucide-react';
import { api } from '../api.js';
import Button from './ui/Button.jsx';
import Card from './ui/Card.jsx';
import Chip from './ui/Chip.jsx';

const HINT_LABELS = {
  1: 'Something off?',
  2: 'Narrow it down',
  3: 'What kind of error?',
};

const TIER_COST = { 1: 1, 2: 2, 3: 3 };

export default function HintButton({
  sessionId,
  roundId,
  onHintUsed,
  layout = 'hud',
}) {
  const [hints, setHints] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const nextTier = hints.length === 0 ? 1 : hints[hints.length - 1].tier + 1;
  const isTerminal =
    hints.length > 0 && hints[hints.length - 1].is_terminal;
  const cumulative =
    hints.length > 0 ? hints[hints.length - 1].cumulative_cost : 0;

  const requestHint = async () => {
    if (isTerminal || nextTier > 3) return;
    setError('');
    try {
      setLoading(true);
      const h = await api.hint(sessionId, roundId, nextTier);
      const updated = [...hints, h];
      setHints(updated);
      if (onHintUsed) onHintUsed(updated);
    } catch (e) {
      setError(e.message || 'Failed to fetch hint');
    } finally {
      setLoading(false);
    }
  };

  const tierDots = (
    <div className="flex items-center gap-1.5" aria-label={`${hints.length} of 3 hints used`}>
      {[1, 2, 3].map((t) => (
        <span
          key={t}
          className={`w-2.5 h-2.5 rounded-full transition-colors border ${
            hints.length >= t
              ? 'bg-warn border-warn-foreground'
              : 'bg-ink-800 border-line'
          }`}
        />
      ))}
    </div>
  );

  const hintMessages = hints.length > 0 && (
    <div className="mt-2 pt-2 border-t border-warn/30 space-y-1.5">
      {hints.map((h) => (
        <div
          key={h.tier}
          className="text-sm text-ink-100 pl-2 border-l-2 border-warn"
        >
          <Chip variant="warn" className="inline-flex mr-2 text-[10px] py-0 px-1.5">
            T{h.tier}
          </Chip>
          {h.message}
        </div>
      ))}
    </div>
  );

  if (layout === 'hud') {
    return (
      <div className="mb-4 step-in">
        <Card variant="default" className="p-2.5 sm:p-3 panel-hint">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <span className="label-hint inline-flex items-center gap-1.5">
              <Lightbulb size={14} className="text-warn-foreground" aria-hidden />
              Hints
            </span>
            {tierDots}
            {!isTerminal && nextTier <= 3 && (
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={requestHint}
                disabled={loading}
                className="btn-press border-warn/40 bg-ink-800 text-warn-foreground hover:bg-ink-700"
              >
                {loading
                  ? '…'
                  : `Hint ${nextTier} (−${TIER_COST[nextTier]} pt)`}
              </Button>
            )}
            {isTerminal && (
              <span className="text-xs text-warn-foreground/80">All hints used</span>
            )}
            {cumulative > 0 && (
              <span className="text-xs font-mono text-warn-foreground ml-auto">
                −{cumulative} pts on grade
              </span>
            )}
          </div>
          {hintMessages}
          {error && <p className="text-xs text-bad-foreground mt-2">{error}</p>}
        </Card>
      </div>
    );
  }

  return (
    <Card variant="default" className="p-3 panel-hint">
      <div className="flex items-center justify-between gap-3 mb-2 flex-wrap">
        <span className="label-hint inline-flex items-center gap-1.5">
          <Lightbulb size={14} aria-hidden />
          Hints {hints.length}/3
        </span>
        {tierDots}
        {cumulative > 0 && (
          <span className="text-xs font-mono text-warn-foreground">
            −{cumulative} pts when graded
          </span>
        )}
      </div>
      {hintMessages}
      {!isTerminal && nextTier <= 3 && (
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={requestHint}
          disabled={loading}
          className="mt-1 btn-press"
        >
          {loading
            ? 'Loading…'
            : `Get hint ${nextTier} — ${HINT_LABELS[nextTier]} (−${nextTier} pts)`}
        </Button>
      )}
      {error && <p className="text-xs text-bad-foreground mt-2">{error}</p>}
    </Card>
  );
}
