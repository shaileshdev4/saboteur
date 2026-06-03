import React, { useEffect, useState } from "react";
import { Lock } from "lucide-react";
import { api } from "../api.js";
import Card from "./ui/Card.jsx";
import Chip from "./ui/Chip.jsx";
import { AchievementIcon } from "./ui/StatusIcon.jsx";
import { ACHIEVEMENTS_CATALOG } from "../data/achievementsCatalog.js";

const TIER_STYLES = {
  bronze: {
    ring: "border-amber-900/40",
    unlocked: "border-amber-700/50 bg-amber-950/20",
    icon: "text-amber-200/90",
  },
  silver: {
    ring: "border-ink-400/35",
    unlocked: "border-ink-300/40 bg-ink-800/40",
    icon: "text-ink-100",
  },
  gold: {
    ring: "border-warn/45",
    unlocked: "border-warn/40 bg-warn-muted/30",
    icon: "text-warn-foreground",
  },
};

const TIER_LABEL = { bronze: "Bronze", silver: "Silver", gold: "Gold" };

export default function Achievements({ sessionId, unlocked = [] }) {
  const [list, setList] = useState(unlocked);
  const [loading, setLoading] = useState(!unlocked.length && !!sessionId);

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    api
      .achievements(sessionId)
      .then(setList)
      .catch(() => setList([]))
      .finally(() => setLoading(false));
  }, [sessionId]);

  const unlockedById = Object.fromEntries(list.map((a) => [a.id, a]));

  if (loading) {
    return <p className="text-ink-400 text-sm">Loading achievements…</p>;
  }

  const unlockedCount = ACHIEVEMENTS_CATALOG.filter(
    (c) => unlockedById[c.id],
  ).length;

  return (
    <div className="space-y-3">
      <p className="text-xs text-ink-500">
        {unlockedCount} of {ACHIEVEMENTS_CATALOG.length} unlocked
        <span className="text-ink-600"> · hover locked badges for goals</span>
      </p>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {ACHIEVEMENTS_CATALOG.map((catalog) => {
          const live = unlockedById[catalog.id];
          return (
            <AchievementCard
              key={catalog.id}
              achievement={live || catalog}
              locked={!live}
            />
          );
        })}
      </div>
    </div>
  );
}

function AchievementCard({ achievement, locked }) {
  const tier = TIER_STYLES[achievement.tier] || TIER_STYLES.bronze;
  const hint = achievement.hint || achievement.description;

  return (
    <div className="relative group outline-none" tabIndex={0}>
      <Card
        variant="default"
        aria-disabled={locked}
        className={[
          "p-3 text-center border transition-colors duration-200",
          locked
            ? `opacity-75 cursor-default ${tier.ring} bg-surface/40`
            : `${tier.unlocked} shadow-sm`,
        ].join(" ")}
      >
        <div
          className={[
            "relative w-10 h-10 mx-auto rounded-lg border grid place-items-center mb-2",
            locked
              ? "border-line/60 bg-ink-900/50"
              : "border-line bg-surface-elevated",
          ].join(" ")}
        >
          <AchievementIcon
            name={achievement.icon}
            className={locked ? "text-ink-400" : tier.icon}
          />
          {locked && (
            <span className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-ink-800 border border-line grid place-items-center">
              <Lock size={9} className="text-ink-500" aria-hidden />
            </span>
          )}
        </div>

        <p
          className={[
            "text-xs font-semibold truncate",
            locked ? "text-ink-400" : "text-ink-50",
          ].join(" ")}
        >
          {achievement.name}
        </p>

        <Chip
          variant={locked ? "muted" : "accent"}
          className="mt-1.5 text-[9px] uppercase tracking-wide"
        >
          {TIER_LABEL[achievement.tier] || achievement.tier}
        </Chip>

        {!locked && (
          <p className="text-[10px] text-ink-500 mt-1.5 line-clamp-2 leading-snug">
            {achievement.description}
          </p>
        )}
      </Card>

      {/* Hover tooltip - locked: how to unlock; unlocked: recap */}
      <div
        role="tooltip"
        className={[
          "pointer-events-none absolute z-20 left-1/2 -translate-x-1/2 bottom-[calc(100%+6px)]",
          "w-[min(13rem,calc(100vw-2rem))] px-3 py-2.5 rounded-xl",
          "bg-ink-800/95 border border-line-subtle shadow-xl backdrop-blur-sm",
          "text-left opacity-0 scale-95 group-hover:opacity-100 group-hover:scale-100",
          "group-focus-within:opacity-100 group-focus-within:scale-100",
          "transition-all duration-150",
        ].join(" ")}
      >
        <p className="text-xs font-semibold text-ink-50 leading-tight">
          {achievement.name}
        </p>
        <p className="text-[11px] text-ink-300 mt-1 leading-snug">
          {locked ? (
            <>
              <span className="text-accent-soft font-medium">Unlock · </span>
              {hint}
            </>
          ) : (
            achievement.description
          )}
        </p>
        <span
          className="absolute left-1/2 -translate-x-1/2 -bottom-1 w-2 h-2 rotate-45 bg-ink-800/95 border-r border-b border-line-subtle"
          aria-hidden
        />
      </div>
    </div>
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
          <Card
            key={a.id}
            variant="default"
            className="px-3 py-2 flex items-center gap-2 border-warn/30"
          >
            <AchievementIcon name={a.icon} className="text-warn-foreground" />
            <span className="text-sm font-medium">{a.name}</span>
          </Card>
        ))}
      </div>
    </section>
  );
}
