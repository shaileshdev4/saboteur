import React, { useEffect, useRef } from 'react';
import katex from 'katex';
import Card from './ui/Card.jsx';
import Chip from './ui/Chip.jsx';

const OP_LABELS = {
  initial: 'Original equation',
  simplify: 'Simplify',
  transpose: 'Move terms across =',
  multiply_both_sides: 'Multiply both sides',
  divide_both_sides: 'Divide both sides',
  expand: 'Distribute',
  factor: 'Factor',
  square_root: 'Take square root',
  substitute: 'Substitute',
  final: 'Result',
};

export default function StepCard({
  step,
  index,
  selectable,
  onSelect,
  flaggedIndex,
  revealCorruptIndex,
  narration,
}) {
  const mathRef = useRef(null);
  useEffect(() => {
    if (mathRef.current && step?.latex) {
      try {
        katex.render(step.latex, mathRef.current, {
          throwOnError: false,
          displayMode: true,
        });
      } catch {
        mathRef.current.textContent = step.latex;
      }
    }
  }, [step?.latex]);

  const isFlagged = flaggedIndex === index;
  const isCorrupt = revealCorruptIndex === index;

  let stateClass = '';
  if (isCorrupt) {
    stateClass = '!border-bad !bg-bad-muted ring-1 ring-bad/40';
  } else if (isFlagged) {
    stateClass = '!border-accent !bg-accent-muted ring-2 ring-accent/50';
  }

  return (
    <Card
      as="button"
      type="button"
      variant="interactive"
      onClick={() => selectable && onSelect?.(index)}
      disabled={!selectable}
      aria-pressed={isFlagged}
      className={[
        'w-full text-left px-5 py-4 step-in',
        selectable
          ? 'cursor-pointer hover:border-line-subtle'
          : 'cursor-default',
        stateClass,
      ].join(' ')}
    >
      <div className="flex items-baseline justify-between gap-3 mb-2 flex-wrap">
        <span className="text-caption text-ink-400">
          Step {index} · {OP_LABELS[step.operation] || step.operation}
        </span>
        {isFlagged && !revealCorruptIndex && (
          <Chip variant="accent-soft">Flagged</Chip>
        )}
        {isCorrupt && (
          <Chip variant="bad">Break</Chip>
        )}
      </div>
      <div ref={mathRef} className="text-ink-50 text-lg leading-snug" />
      {narration && (
        <p className="text-xs text-ink-300 mt-2 italic">{narration}</p>
      )}
    </Card>
  );
}
