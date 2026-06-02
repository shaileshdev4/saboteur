import React, { useEffect } from 'react';
import Card from './ui/Card.jsx';
import { AchievementIcon } from './ui/StatusIcon.jsx';

const TIER_BORDER = {
  bronze: 'border-ink-500/60',
  silver: 'border-ink-300/50',
  gold: 'border-warn/50',
};

export default function AchievementToast({ achievement, onDone }) {
  useEffect(() => {
    const t = setTimeout(() => onDone(), 4000);
    return () => clearTimeout(t);
  }, [onDone]);

  if (!achievement) return null;

  return (
    <div className="fixed top-4 right-4 z-[60] max-w-xs step-in">
      <Card
        variant="elevated"
        className={`p-4 border-2 ${TIER_BORDER[achievement.tier] || TIER_BORDER.bronze} panel-accent`}
      >
        <p className="text-caption text-accent-foreground mb-1">Achievement unlocked</p>
        <div className="flex items-start gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-muted border border-accent/40 grid place-items-center flex-shrink-0">
            <AchievementIcon name={achievement.icon} />
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-ink-50">{achievement.name}</p>
            <p className="text-xs text-ink-300 mt-0.5">{achievement.description}</p>
          </div>
        </div>
      </Card>
    </div>
  );
}
