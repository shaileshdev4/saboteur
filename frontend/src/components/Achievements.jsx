import React, { useEffect, useState } from 'react';
import { api } from '../api.js';
import Card from './ui/Card.jsx';
import { AchievementIcon } from './ui/StatusIcon.jsx';

const ALL_ACHIEVEMENT_META = [
  { id: 'first_catch', tier: 'bronze' },
  { id: 'ten_rounds', tier: 'bronze' },
  { id: 'fifty_rounds', tier: 'silver' },
  { id: 'no_over_trust_streak_10', tier: 'silver' },
  { id: 'score_80', tier: 'silver' },
  { id: 'score_95', tier: 'gold' },
  { id: 'four_domains', tier: 'silver' },
  { id: 'rating_1300', tier: 'gold' },
  { id: 'all_domains_score_70', tier: 'gold' },
  { id: 'catch_all_misconceptions_once', tier: 'gold' },
];

const TIER_RING = {
  bronze: 'border-ink-500/50 opacity-60',
  silver: 'border-ink-200/40 opacity-80',
  gold: 'border-warn/50',
};

export default function Achievements({ sessionId, unlocked = [] }) {
  const [list, setList] = useState(unlocked);
  const [loading, setLoading] = useState(!unlocked.length && !!sessionId);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    api.achievements(sessionId)
      .then(setList)
      .catch(() => setList([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

  const unlockedIds = new Set(list.map((a) => a.id));

  if (loading) {
    return <p className="text-ink-400 text-sm">Loading achievements…</p>;
  }

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
      {list.map((a) => (
        <AchievementCard key={a.id} achievement={a} locked={false} />
      ))}
      {ALL_ACHIEVEMENT_META.filter((m) => !unlockedIds.has(m.id)).map((m) => (
        <AchievementCard
          key={m.id}
          achievement={{ id: m.id, name: '???', description: 'Keep playing to unlock.', icon: 'help', tier: m.tier }}
          locked
        />
      ))}
    </div>
  );
}

function AchievementCard({ achievement, locked }) {
  const ring = TIER_RING[achievement.tier] || TIER_RING.bronze;
  return (
    <Card
      variant="default"
      className={`p-3 text-center border ${ring} ${locked ? 'grayscale' : ''}`}
    >
      <div className="w-10 h-10 mx-auto rounded-lg bg-surface border border-line grid place-items-center mb-2">
        <AchievementIcon name={achievement.icon} className={locked ? 'text-ink-500' : 'text-accent-foreground'} />
      </div>
      <p className="text-xs font-semibold text-ink-100 truncate">{achievement.name}</p>
      {!locked && (
        <p className="text-[10px] text-ink-500 mt-1 line-clamp-2">{achievement.description}</p>
      )}
    </Card>
  );
}

export function RecentUnlocks({ achievements }) {
  if (!achievements?.length) return null;
  const recent = achievements.slice(-3).reverse();
  return (
    <section className="mt-8">
      <h3 className="text-caption mb-3">Recent unlocks</h3>
      <div className="flex flex-wrap gap-2">
        {recent.map((a) => (
          <Card key={a.id} variant="default" className="px-3 py-2 flex items-center gap-2 border-warn/30">
            <AchievementIcon name={a.icon} className="text-warn-foreground" />
            <span className="text-sm font-medium">{a.name}</span>
          </Card>
        ))}
      </div>
    </section>
  );
}
