import React, { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";
import {
  AlertTriangle,
  ChevronRight,
  Target,
  TrendingDown,
  Trophy,
} from "lucide-react";
import Button from "./ui/Button.jsx";
import Card from "./ui/Card.jsx";
import Chip from "./ui/Chip.jsx";
import { buildOverTrustTrend } from "../utils/sessionAnalytics.js";
import Achievements, { RecentUnlocks } from "./Achievements.jsx";

const CAT_COLOR = {
  sign: "#a193ff",
  distribution: "#2ec27e",
  coefficient: "#e5a52b",
  cancellation: "#e5484d",
  operation_one_side: "#5cbdff",
  calculus_basic: "#a193ff",
  calculus_power_rule: "#e5a52b",
  calculus_chain_rule: "#2ec27e",
  calculus_product_rule: "#5cbdff",
  calculus_integration: "#e5484d",
  geometry_pythagoras: "#a193ff",
  geometry_area: "#2ec27e",
  geometry_formulas: "#5cbdff",
};

const DOMAIN_COLORS = {
  algebra: "#7c5cff",
  geometry: "#2ec27e",
  calculus: "#e5a52b",
};

function computeInsights(data, domains, sessionId) {
  const c = data.counts || {};
  const total = c.total || 0;
  const catchRate =
    total > 0 ? Math.round(((c.correct_catch || 0) / total) * 100) : 0;

  const domainList = Object.entries(data.per_domain || {});
  let bestDomain = null;
  let bestScore = -1;
  for (const [did, info] of domainList) {
    const s = info.score ?? 0;
    if (s > bestScore) {
      bestScore = s;
      bestDomain = domains?.find((d) => d.id === did)?.label || did;
    }
  }

  const misconceptions = Object.entries(data.per_misconception || {})
    .filter(([, e]) => (e.seen || 0) >= 2)
    .map(([id, e]) => ({
      id,
      name: e.name || id,
      category: e.category,
      rate: e.seen ? e.caught / e.seen : 0,
      seen: e.seen,
      caught: e.caught,
    }))
    .sort((a, b) => a.rate - b.rate);

  const weakest = misconceptions[0] || null;

  return {
    catchRate,
    overTrust: c.over_trust || 0,
    bestDomain: bestDomain || "-",
    weakest,
    scoreSeries: (data.score_history || []).map((v, i) => ({
      round: i + 1,
      score: v,
    })),
    riskSeries: buildOverTrustTrend(sessionId),
  };
}

export default function Dashboard({
  data,
  loading,
  loadError = "",
  onPlay,
  domains,
  sessionId,
  recentAchievements = [],
}) {
  const insights = useMemo(
    () => (data ? computeInsights(data, domains, sessionId) : null),
    [data, domains, sessionId],
  );

  if (loading) {
    return (
      <div className="text-ink-400 py-10 text-center">Loading calibration…</div>
    );
  }
  if (loadError) {
    return (
      <div className="text-center py-12 px-4 max-w-md mx-auto">
        <p className="text-sm text-bad-foreground leading-relaxed">
          {loadError}
        </p>
        <p className="text-xs text-ink-500 mt-2">
          Use Retry in the banner above or play a round first.
        </p>
      </div>
    );
  }
  if (!data || !insights) {
    return (
      <div className="text-center py-12 px-4">
        <Target size={32} className="mx-auto text-ink-600 mb-3" aria-hidden />
        <p className="text-ink-400">
          Play a round to see your trust calibration profile.
        </p>
        <Button
          variant="primary"
          size="md"
          onClick={onPlay}
          className="mt-4 btn-press"
        >
          Start auditing
        </Button>
      </div>
    );
  }

  const c = data.counts;
  const score = (data.score ?? 0).toFixed(1);
  const domainList = Object.entries(data.per_domain || {});
  const misconceptions = Object.entries(data.per_misconception || {});

  return (
    <div className="layout-shell py-4 sm:py-6 space-y-5 sm:space-y-6">
      <header className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-3">
        <div>
          <p className="text-caption text-accent-soft mb-1">
            Trust calibration
          </p>
          <h2 className="text-xl sm:text-2xl">Your audit record</h2>
          <p className="text-sm text-ink-400 mt-1">
            Measurable learning -catches vs dangerous over-trust.
          </p>
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={onPlay}
          className="w-full sm:w-auto inline-flex items-center gap-1.5 btn-press"
        >
          Audit another round
          <ChevronRight size={16} aria-hidden />
        </Button>
      </header>

      {/* Phase 3: story cards */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-2 sm:gap-3">
        <InsightCard
          icon={Trophy}
          label="Calibration"
          value={score}
          suffix="/ 100"
          highlight
        />
        <InsightCard
          icon={Target}
          label="Catch rate"
          value={`${insights.catchRate}%`}
          sub="correct catches / rounds"
        />
        <InsightCard
          icon={TrendingDown}
          label="Over-trusts"
          value={insights.overTrust}
          sub="dangerous misses"
          warn={insights.overTrust > 0}
        />
        <InsightCard
          icon={AlertTriangle}
          label="Top weakness"
          value={
            insights.weakest
              ? `${Math.round(insights.weakest.rate * 100)}%`
              : "-"
          }
          sub={insights.weakest?.name?.slice(0, 28) || "play more rounds"}
          warn={insights.weakest && insights.weakest.rate < 0.5}
        />
      </section>

      <section className="grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
        <MiniStat label="Total points" value={data.total_points} />
        <MiniStat label="Rating" value={Math.round(data.rating)} />
        <MiniStat
          label="Difficulty"
          value={data.suggested_difficulty}
          suffix="/ 5"
        />
        <MiniStat label="Best domain" value={insights.bestDomain} small />
      </section>

      {/* Outcomes: cards on mobile, table on md+ */}
      <section>
        <h3 className="text-caption mb-3">Outcome matrix</h3>
        <div className="grid sm:grid-cols-2 gap-2 md:hidden">
          <OutcomeCard
            title="Clean solution"
            trustLabel="Correct trust"
            trustValue={c.correct_trust}
            trustTone="good"
            flagLabel="Over-suspicion"
            flagValue={c.over_suspicion}
            flagTone="warn"
          />
          <OutcomeCard
            title="Flawed solution"
            trustLabel="Over-trust"
            trustValue={c.over_trust}
            trustTone="bad"
            warnTrust
            flagLabel="Correct catch"
            flagValue={c.correct_catch}
            flagTone="good"
            flagExtra={`+${c.wrong_step_catch} wrong step`}
          />
        </div>
        <Card variant="default" className="overflow-hidden hidden md:block">
          <table className="w-full text-sm">
            <thead className="bg-surface-elevated/80 text-ink-400">
              <tr>
                <th className="px-4 py-2 text-left font-medium" />
                <th className="px-4 py-2 text-center font-medium">Trusted</th>
                <th className="px-4 py-2 text-center font-medium">Flagged</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-t border-line">
                <td className="px-4 py-3 text-ink-300">Solution was correct</td>
                <td className="px-4 py-3 text-center font-mono text-good-foreground">
                  {c.correct_trust}
                </td>
                <td className="px-4 py-3 text-center font-mono text-warn-foreground">
                  {c.over_suspicion}
                </td>
              </tr>
              <tr className="border-t border-line">
                <td className="px-4 py-3 text-ink-300">Solution was wrong</td>
                <td className="px-4 py-3 text-center font-mono text-bad-foreground">
                  <span className="inline-flex items-center justify-center gap-1">
                    {c.over_trust}
                    {c.over_trust > 0 && (
                      <AlertTriangle size={14} aria-hidden />
                    )}
                  </span>
                </td>
                <td className="px-4 py-3 text-center font-mono text-good-foreground">
                  {c.correct_catch}
                  <span className="text-ink-500 text-xs ml-1">
                    (+{c.wrong_step_catch} wrong step)
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </Card>
        {c.over_trust > 0 && (
          <p className="text-xs text-bad-foreground mt-2 inline-flex items-start gap-1.5">
            <AlertTriangle
              size={14}
              className="flex-shrink-0 mt-0.5"
              aria-hidden
            />
            Over-trust is weighted heaviest in your calibration score.
          </p>
        )}
      </section>

      {/* Charts */}
      <section className="grid md:grid-cols-2 gap-4">
        {insights.scoreSeries.length > 1 && (
          <ChartPanel title="Score across rounds">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={insights.scoreSeries}>
                <CartesianGrid stroke="#33353c" strokeDasharray="3 3" />
                <XAxis
                  dataKey="round"
                  stroke="#888a96"
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  stroke="#888a96"
                  domain={[0, 100]}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Line
                  type="monotone"
                  dataKey="score"
                  stroke="#7c5cff"
                  strokeWidth={2}
                  dot={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartPanel>
        )}
        {insights.riskSeries.length > 1 ? (
          <ChartPanel title="Over-trust rate (cumulative)">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={insights.riskSeries}>
                <CartesianGrid stroke="#33353c" strokeDasharray="3 3" />
                <XAxis
                  dataKey="round"
                  stroke="#888a96"
                  tick={{ fontSize: 11 }}
                />
                <YAxis
                  stroke="#888a96"
                  domain={[0, 100]}
                  tick={{ fontSize: 11 }}
                  unit="%"
                />
                <Tooltip contentStyle={chartTooltipStyle} />
                <Line
                  type="monotone"
                  dataKey="rate"
                  stroke="#e5484d"
                  strokeWidth={2}
                  dot={{ r: 2, fill: "#e5484d" }}
                />
              </LineChart>
            </ResponsiveContainer>
          </ChartPanel>
        ) : (
          <ChartPanel title="Over-trust trend">
            <div className="h-full grid place-items-center text-center px-4">
              <p className="text-xs text-ink-500">
                Play more rounds to see your cumulative over-trust rate. Each
                grade updates this chart in your browser.
              </p>
            </div>
          </ChartPanel>
        )}
      </section>

      {domainList.length > 0 && (
        <section>
          <h3 className="text-caption mb-3">By domain</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3">
            {domainList.map(([did, info]) => {
              const dom = (domains || []).find((d) => d.id === did);
              const counts = info.counts || {};
              return (
                <Card key={did} variant="default" className="p-3">
                  <div className="flex items-baseline justify-between mb-1">
                    <span
                      className="inline-flex items-center gap-2 font-medium text-sm"
                      style={{ color: DOMAIN_COLORS[did] || "#fff" }}
                    >
                      <span
                        className="w-2 h-2 rounded-full"
                        style={{
                          backgroundColor: DOMAIN_COLORS[did] || "#888",
                        }}
                      />
                      {dom?.label || did}
                    </span>
                    <span className="font-mono text-sm text-ink-300">
                      {(info.score ?? 0).toFixed(0)}
                    </span>
                  </div>
                  <p className="text-xs text-ink-500">
                    {counts.total || 0} rounds · rating{" "}
                    {Math.round(info.rating || 1000)}
                  </p>
                </Card>
              );
            })}
          </div>
        </section>
      )}

      {misconceptions.length > 0 && (
        <section>
          <h3 className="text-caption mb-3">Misconception catch rates</h3>
          <div className="space-y-2">
            {misconceptions
              .map(([id, entry]) => {
                const rate = entry.seen ? entry.caught / entry.seen : 0;
                return { id, entry, pct: Math.round(rate * 100), rate };
              })
              .sort((a, b) => a.rate - b.rate)
              .map(({ id, entry, pct }) => (
                <Card key={id} variant="default" className="p-3">
                  <div className="flex items-baseline justify-between gap-3 mb-1 flex-wrap">
                    <div className="flex items-baseline gap-2 min-w-0">
                      <span
                        className="inline-block w-2 h-2 rounded-full flex-shrink-0"
                        style={{
                          backgroundColor: CAT_COLOR[entry.category] || "#888",
                        }}
                      />
                      <span className="text-ink-100 font-medium text-sm truncate">
                        {entry.name || id}
                      </span>
                      {pct < 50 && entry.seen >= 2 && (
                        <Chip variant="bad" className="hidden sm:inline-flex">
                          weakness
                        </Chip>
                      )}
                    </div>
                    <span className="font-mono text-xs text-ink-300">
                      {entry.caught}/{entry.seen}
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-ink-700 overflow-hidden">
                    <div
                      className="h-full transition-all"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: CAT_COLOR[entry.category] || "#888",
                      }}
                    />
                  </div>
                </Card>
              ))}
          </div>
        </section>
      )}

      <RecentUnlocks achievements={recentAchievements} />

      {sessionId && (
        <section>
          <h3 className="text-caption mb-3">Achievements</h3>
          <Achievements sessionId={sessionId} />
        </section>
      )}
    </div>
  );
}

const chartTooltipStyle = {
  backgroundColor: "#1f2126",
  border: "1px solid #33353c",
  borderRadius: "12px",
};

function ChartPanel({ title, children }) {
  return (
    <div>
      <h3 className="text-caption mb-2">{title}</h3>
      <Card variant="default" className="p-2 sm:p-3 h-44 sm:h-52">
        {children}
      </Card>
    </div>
  );
}

function InsightCard({
  icon: Icon,
  label,
  value,
  suffix,
  sub,
  highlight,
  warn,
}) {
  return (
    <Card
      variant={highlight ? "elevated" : "default"}
      className={`p-3 ${highlight ? "border-accent/40 bg-accent/10" : ""} ${warn ? "border-bad/30" : ""}`}
    >
      <div className="flex items-center gap-1.5 text-caption mb-1">
        <Icon
          size={12}
          className={warn ? "text-bad-foreground" : "text-accent-foreground"}
          aria-hidden
        />
        {label}
      </div>
      <div className="text-xl sm:text-2xl font-semibold font-mono">
        {value}
        {suffix && (
          <span className="text-sm text-ink-500 font-sans ml-0.5">
            {suffix}
          </span>
        )}
      </div>
      {sub && <p className="text-xs text-ink-500 mt-1 truncate">{sub}</p>}
    </Card>
  );
}

function MiniStat({ label, value, suffix, small }) {
  return (
    <Card variant="default" className="px-3 py-2">
      <div className="text-caption">{label}</div>
      <div
        className={`font-semibold mt-0.5 ${small ? "text-sm truncate" : "text-lg"}`}
      >
        {value}
        {suffix && <span className="text-xs text-ink-500 ml-1">{suffix}</span>}
      </div>
    </Card>
  );
}

function OutcomeCard({
  title,
  trustLabel,
  trustValue,
  trustTone,
  flagLabel,
  flagValue,
  flagTone,
  flagExtra,
  warnTrust,
}) {
  const tone = (t) =>
    t === "good"
      ? "text-good-foreground"
      : t === "bad"
        ? "text-bad-foreground"
        : "text-warn-foreground";
  return (
    <Card variant="default" className="p-3">
      <div className="text-xs font-medium text-ink-300 mb-2">{title}</div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-ink-500">{trustLabel}</span>
        <span
          className={`font-mono ${tone(trustTone)} inline-flex items-center gap-1`}
        >
          {trustValue}
          {warnTrust && trustValue > 0 && (
            <AlertTriangle size={12} aria-hidden />
          )}
        </span>
      </div>
      <div className="flex justify-between text-sm">
        <span className="text-ink-500">{flagLabel}</span>
        <span className={`font-mono ${tone(flagTone)}`}>
          {flagValue}
          {flagExtra && (
            <span className="text-ink-500 text-xs block text-right">
              {flagExtra}
            </span>
          )}
        </span>
      </div>
    </Card>
  );
}
