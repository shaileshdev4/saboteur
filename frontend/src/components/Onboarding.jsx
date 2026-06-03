import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import Button from "./ui/Button.jsx";
import Card from "./ui/Card.jsx";
import BrandMark from "./ui/BrandMark.jsx";
import { ChevronRight, OnboardingIcon } from "./ui/StatusIcon.jsx";

const ONBOARDING_KEY = "saboteur:onboarded";

const STEPS = [
  {
    title: "One error -or none",
    body:
      "Each round shows an AI worked solution. It is either fully correct, " +
      "or exactly one step is wrong. Your job: decide which.",
    icon: "target",
  },
  {
    title: "Trust or flag",
    body:
      "Tap Trust if every step checks out. Tap a step, then Flag, if you " +
      "spot the break. Over-trust -trusting a bad solution -hurts your " +
      "calibration score the most.",
    icon: "scale",
  },
  {
    title: "Your calibration score",
    body:
      "SymPy verifies every step; the LLM only explains after the reveal. " +
      "Play rounds to build your trust calibration. Algebra, geometry, and " +
      "calculus, and statistics track separately.",
    icon: "flask",
  },
  {
    title: "Leaderboards & ranks",
    body:
      "Want to compare with others? Open the Ranks tab and opt in with a " +
      "nickname. Until you do, your stats stay private.",
    icon: "trophy",
  },
];

export default function Onboarding({ onStartPractice }) {
  const [visible, setVisible] = useState(false);
  const [step, setStep] = useState(0);

  useEffect(() => {
    try {
      if (!localStorage.getItem(ONBOARDING_KEY)) {
        const t = setTimeout(() => setVisible(true), 600);
        return () => clearTimeout(t);
      }
    } catch {}
  }, []);

  const finish = (startPractice = false) => {
    try {
      localStorage.setItem(ONBOARDING_KEY, "1");
    } catch {}
    setVisible(false);
    if (startPractice && onStartPractice) onStartPractice();
  };

  if (!visible) return null;
  const card = STEPS[step];
  const isLast = step === STEPS.length - 1;

  const overlay = (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="onboarding-title"
      className="onboarding-overlay fixed inset-0 z-[100] flex items-center justify-center bg-black/75 backdrop-blur-sm px-4 py-8"
      onClick={() => finish(false)}
    >
      <Card
        variant="elevated"
        className="max-w-md w-full p-6 shadow-2xl step-in border-accent/20 mx-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center gap-3 mb-4">
          <BrandMark />
          <div>
            <p className="text-caption text-accent-soft">The Saboteur</p>
            <p className="text-xs text-ink-500">
              Audit lens · step {step + 1} of {STEPS.length}
            </p>
          </div>
        </div>

        <div className="mb-4 w-12 h-12 rounded-xl bg-accent/15 border border-accent/30 grid place-items-center">
          <OnboardingIcon name={card.icon} />
        </div>
        <h3 id="onboarding-title" className="text-xl font-semibold mb-2">
          {card.title}
        </h3>
        <p className="text-sm text-ink-200 leading-relaxed">{card.body}</p>

        <div className="flex items-center gap-1.5 mt-5">
          {STEPS.map((_, i) => (
            <span
              key={i}
              className={`h-1.5 rounded-full transition-all ${
                i === step ? "w-6 bg-accent" : "w-1.5 bg-ink-600"
              }`}
            />
          ))}
        </div>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between mt-5 gap-2">
          <Button variant="ghost" size="sm" onClick={() => finish(false)}>
            Skip intro
          </Button>
          <div className="flex flex-col sm:flex-row gap-2 sm:ml-auto">
            {!isLast ? (
              <Button
                variant="primary"
                size="md"
                onClick={() => setStep(step + 1)}
                className="inline-flex items-center justify-center gap-1.5 btn-press"
              >
                Next
                <ChevronRight size={16} aria-hidden />
              </Button>
            ) : (
              <>
                <Button
                  variant="secondary"
                  size="md"
                  onClick={() => finish(true)}
                  className="btn-press"
                >
                  Try a practice round
                </Button>
                <Button
                  variant="primary"
                  size="md"
                  onClick={() => finish(false)}
                  className="btn-press"
                >
                  Start playing
                </Button>
              </>
            )}
          </div>
        </div>
      </Card>
    </div>
  );

  return createPortal(overlay, document.body);
}
