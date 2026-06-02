import React, { useState } from 'react';
import { ScanLine } from 'lucide-react';
import StepCard from './StepCard.jsx';
import HintButton from './HintButton.jsx';
import Button from './ui/Button.jsx';
import Card from './ui/Card.jsx';
import Chip from './ui/Chip.jsx';

export default function PlayScreen({
  round,
  sessionId,
  onSubmit,
  isSubmitting,
  domains,
  roundNumber = 1,
}) {
  const [flaggedIndex, setFlaggedIndex] = useState(null);
  const [hintsUsed, setHintsUsed] = useState(0);

  if (!round) return null;

  const domain = (domains || []).find((d) => d.id === round.domain_id);
  const kind = domain?.problem_kinds.find((k) => k.id === round.problem_type);
  const subtitle = kind ? kind.label : round.problem_type;
  const selectableSteps = round.steps.filter((s) => s.operation !== 'initial');

  const handleTrust = () => onSubmit({ decision: 'trust' });
  const handleFlag = () => {
    if (flaggedIndex === null) return;
    onSubmit({ decision: 'flag', flagged_step_index: flaggedIndex });
  };

  const toggleFlag = (index) => {
    setFlaggedIndex((prev) => (prev === index ? null : index));
  };

  return (
    <div className="layout-shell py-4 sm:py-6 pb-6">
      <header className="mb-3 sm:mb-4 step-in">
        <div className="flex items-center justify-between gap-2 mb-2 flex-wrap">
          <div className="flex items-center gap-2 text-caption">
            <ScanLine size={14} className="text-accent-foreground" aria-hidden />
            <span>Round {roundNumber}</span>
          </div>
          <Chip variant="muted">
            {selectableSteps.length} auditable step{selectableSteps.length !== 1 ? 's' : ''}
          </Chip>
        </div>
        <h2 className="text-xl sm:text-2xl">Audit this AI solution</h2>
        <p className="text-sm text-ink-400 mt-1">
          Read top to bottom. Flag one step or trust the full pipeline.
        </p>
        <div className="flex flex-wrap gap-2 mt-3">
          <Chip variant="muted">{domain?.label || round.domain_id}</Chip>
          <Chip variant="muted">{subtitle}</Chip>
          <Chip variant="accent-soft">Difficulty {round.difficulty}</Chip>
          {hintsUsed > 0 && (
            <Chip variant="warn" className="chip-pulse">
              {hintsUsed}/3 hints
            </Chip>
          )}
        </div>
      </header>

      {/* Game HUD: hints before the work (not after steps) */}
      <HintButton
        layout="hud"
        sessionId={sessionId}
        roundId={round.round_id}
        onHintUsed={(hints) => setHintsUsed(hints.length)}
      />

      <div className="space-y-3 mb-2">
        {round.steps.map((step) => (
          <StepCard
            key={step.index}
            step={step}
            index={step.index}
            selectable={step.operation !== 'initial'}
            flaggedIndex={flaggedIndex}
            onSelect={toggleFlag}
          />
        ))}
      </div>

      <div className="action-bar-sticky">
        <Card
          variant="glass"
          className="p-3 sm:p-4 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 shadow-card"
        >
          <p className="text-xs sm:text-sm text-ink-300">
            {flaggedIndex === null
              ? 'Tap a step to flag it, or trust the whole solution.'
              : (
                <>
                  Flagging{' '}
                  <Chip variant="accent" className="inline-flex ml-1">
                    Step {flaggedIndex}
                  </Chip>
                  <span className="text-ink-500"> · tap again to clear</span>
                </>
              )}
          </p>
          <div className="flex items-center gap-2 sm:ml-auto w-full sm:w-auto shrink-0">
            <Button
              variant="secondary"
              size="md"
              onClick={handleTrust}
              disabled={isSubmitting}
              className="flex-1 sm:flex-none btn-press"
            >
              Trust
            </Button>
            <Button
              variant="primary"
              size="md"
              onClick={handleFlag}
              disabled={flaggedIndex === null || isSubmitting}
              className="flex-1 sm:flex-none btn-press"
            >
              {flaggedIndex !== null ? `Flag step ${flaggedIndex}` : 'Flag step…'}
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
