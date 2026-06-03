import React, { useEffect, useRef } from "react";
import katex from "katex";
import { AlertOctagon, BarChart3 } from "lucide-react";
import StepCard from "./StepCard.jsx";
import Button from "./ui/Button.jsx";
import Card from "./ui/Card.jsx";
import { ChevronRight, StatusIcon } from "./ui/StatusIcon.jsx";

const OUTCOME_COPY = {
  correct_trust: {
    label: "Correct trust",
    color: "good",
    status: "good",
    subtitle: "The solution was clean -good calibration.",
  },
  correct_catch: {
    label: "You caught it",
    color: "good",
    status: "good",
    subtitle: "You found the planted break.",
  },
  over_trust: {
    label: "Over-trust",
    color: "bad",
    status: "bad",
    subtitle: "There was an error -trusting it is the dangerous miss.",
  },
  over_suspicion: {
    label: "Over-suspicion",
    color: "warn",
    status: "warn",
    subtitle: "The solution was actually clean.",
  },
  wrong_step_catch: {
    label: "Wrong step flagged",
    color: "warn",
    status: "warn",
    subtitle: "There was an error, but not on the step you picked.",
  },
};

function LaTeXLine({ tex }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current && tex) {
      try {
        katex.render(tex, ref.current, {
          throwOnError: false,
          displayMode: false,
        });
      } catch {
        ref.current.textContent = tex;
      }
    }
  }, [tex]);
  return <span ref={ref} />;
}

export default function RevealScreen({ round, grade, onNext, onDashboard }) {
  if (!grade || !round) return null;
  const o = OUTCOME_COPY[grade.outcome] || {
    label: grade.outcome,
    color: "warn",
    status: "warn",
    subtitle: "",
  };
  const panelMap = {
    good: "panel-good",
    bad: "panel-bad",
    warn: "panel-warn",
  };
  const iconBg = {
    good: "bg-good-muted border-good/50",
    bad: "bg-bad-muted border-bad/50",
    warn: "bg-warn-muted border-warn/50",
  };
  const signPts = grade.points >= 0 ? `+${grade.points}` : `${grade.points}`;
  const ptsClass =
    grade.points >= 0 ? "text-good-foreground" : "text-bad-foreground";

  return (
    <div className="layout-shell py-4 sm:py-6 pb-6">
      <Card
        variant="elevated"
        className={`p-5 mb-6 step-in border-2 ${panelMap[o.color]}`}
      >
        <p className="text-caption mb-2">Audit complete</p>
        <div className="flex items-start justify-between gap-4">
          <div className="flex items-start gap-3 min-w-0">
            <div
              className={`flex-shrink-0 w-10 h-10 rounded-xl grid place-items-center border ${iconBg[o.color]}`}
            >
              <StatusIcon status={o.status} size="lg" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl sm:text-2xl font-semibold">{o.label}</h2>
              {o.subtitle && (
                <p className="text-sm text-ink-300 mt-1">{o.subtitle}</p>
              )}
            </div>
          </div>
          <div className={`text-right flex-shrink-0 points-pop ${ptsClass}`}>
            <div className="text-caption">Points</div>
            <div className="font-mono text-2xl sm:text-3xl font-bold">
              {signPts}
            </div>
          </div>
        </div>
      </Card>

      {!grade.is_clean && (
        <section className="mb-6 step-in">
          <div className="flex items-center gap-2 mb-3">
            <AlertOctagon
              size={18}
              className="text-bad-foreground"
              aria-hidden
            />
            <h3 className="text-sm font-semibold text-ink-100">
              Break detected at Step {grade.corrupted_step_index}
            </h3>
          </div>
          <Card variant="default" className="p-5 overflow-hidden">
            <div className="grid sm:grid-cols-2 gap-4">
              <div className="rounded-xl border-l-4 border-good panel-good p-4">
                <div className="label-good mb-2">Truth</div>
                <div className="text-ink-50 text-lg">
                  <LaTeXLine tex={grade.truth_step_latex} />
                </div>
              </div>
              <div className="rounded-xl border-l-4 border-bad panel-bad p-4">
                <div className="label-bad mb-2">What was shown</div>
                <div className="text-ink-50 text-lg">
                  <LaTeXLine tex={grade.shown_step_latex} />
                </div>
              </div>
            </div>
            <div className="border-t border-line mt-4 pt-4">
              <div className="text-caption mb-1">Misconception</div>
              <p className="text-accent-foreground font-medium">
                {grade.misconception_name}
              </p>
              <p className="text-ink-200 leading-relaxed text-sm mt-2">
                {grade.misconception_explanation}
              </p>
            </div>
          </Card>
        </section>
      )}

      {grade.is_clean && (
        <Card variant="default" className="p-4 mb-6 step-in">
          <p className="text-ink-200 text-sm">
            This round was clean -every step followed correctly from the
            previous.
          </p>
        </Card>
      )}

      <section className="mb-6">
        <h3 className="text-caption mb-3">Full solution</h3>
        <div className="space-y-3">
          {round.steps.map((step, i) => (
            <StepCard
              key={step.index}
              step={step}
              index={step.index}
              selectable={false}
              revealCorruptIndex={grade.corrupted_step_index}
              narration={grade.step_narration?.[i]}
            />
          ))}
        </div>
      </section>

      <div className="action-bar-sticky">
        <Card
          variant="glass"
          className="p-3 sm:p-4 flex justify-end gap-2 shadow-card"
        >
          <Button
            variant="secondary"
            size="md"
            onClick={onDashboard}
            className="inline-flex items-center gap-1.5 btn-press"
          >
            <BarChart3 size={16} aria-hidden />
            Stats
          </Button>
          <Button
            variant="primary"
            size="md"
            onClick={onNext}
            className="inline-flex items-center gap-1.5 btn-press"
          >
            Next round
            <ChevronRight size={16} aria-hidden />
          </Button>
        </Card>
      </div>
    </div>
  );
}
