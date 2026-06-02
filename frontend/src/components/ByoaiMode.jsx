import React, { useEffect, useRef, useState } from 'react';
import katex from 'katex';
import { api } from '../api.js';
import { StatusIcon } from './ui/StatusIcon.jsx';

function LaTeXBlock({ tex, displayMode = false }) {
  const ref = useRef(null);
  useEffect(() => {
    if (ref.current && tex) {
      try {
        katex.render(tex, ref.current, { throwOnError: false, displayMode });
      } catch {
        ref.current.textContent = tex;
      }
    }
  }, [tex, displayMode]);
  return <span ref={ref} />;
}

const PLACEHOLDER_PROBLEM = '2*x + 6 = 10';
const PLACEHOLDER_STEPS = '2*x = 4\nx = 2';

const SAMPLES = [
  {
    label: 'Correct linear',
    problem: '3*x + 4 = 19',
    steps: '3*x = 15\nx = 5',
  },
  {
    label: 'Broken: sign flip',
    problem: '2*x + 6 = 10',
    steps: '2*x = 16\nx = 8',
  },
  {
    label: 'Factored quadratic',
    problem: 'x**2 - 5*x + 6 = 0',
    steps: '(x - 2)*(x - 3) = 0\nx = 2',
  },
];

export default function ByoaiMode() {
  const [problem, setProblem] = useState(PLACEHOLDER_PROBLEM);
  const [stepsText, setStepsText] = useState(PLACEHOLDER_STEPS);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const submit = async () => {
    setError('');
    setResult(null);
    const steps = stepsText
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean);
    if (!problem.trim() || steps.length === 0) {
      setError('Provide a problem and at least one step.');
      return;
    }
    try {
      setLoading(true);
      const r = await api.byoai(problem, steps);
      setResult(r);
    } catch (e) {
      setError(String(e.message || e));
    } finally {
      setLoading(false);
    }
  };

  const loadSample = (s) => {
    setProblem(s.problem);
    setStepsText(s.steps);
    setResult(null);
  };

  return (
    <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
      <header>
        <h2 className="text-2xl font-semibold tracking-tight">
          Audit a real AI answer
        </h2>
        <p className="text-sm text-ink-400 mt-1">
          Paste a step-by-step solution from any chatbot. We'll verify it symbolically.
        </p>
      </header>

      <section className="space-y-3">
        <div>
          <label className="text-xs uppercase tracking-wider text-ink-400 block mb-1">
            Original problem
          </label>
          <input
            type="text"
            value={problem}
            onChange={(e) => setProblem(e.target.value)}
            placeholder={PLACEHOLDER_PROBLEM}
            className="w-full px-4 py-3 rounded-lg bg-ink-800 border border-ink-700 font-mono text-ink-50 focus:border-accent"
          />
        </div>
        <div>
          <label className="text-xs uppercase tracking-wider text-ink-400 block mb-1">
            Steps (one per line)
          </label>
          <textarea
            value={stepsText}
            onChange={(e) => setStepsText(e.target.value)}
            placeholder={PLACEHOLDER_STEPS}
            rows={6}
            className="w-full px-4 py-3 rounded-lg bg-ink-800 border border-ink-700 font-mono text-ink-50 focus:border-accent"
          />
          <p className="text-xs text-ink-500 mt-1">
            We accept basic LaTeX (e.g., <code>\frac{'{a}'}{'{b}'}</code>,{' '}
            <code>\sqrt{'{x}'}</code>) or plain expressions (<code>2*x + 6 = 10</code>).
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={submit}
            disabled={loading}
            className="px-4 py-2 rounded-lg bg-accent text-white hover:opacity-90 font-semibold disabled:opacity-50"
          >
            {loading ? 'Verifying…' : 'Audit'}
          </button>
          <span className="text-xs text-ink-500 ml-2">Try a sample:</span>
          {SAMPLES.map((s) => (
            <button
              key={s.label}
              onClick={() => loadSample(s)}
              className="px-3 py-1 rounded-full text-xs bg-ink-800 border border-ink-700 hover:border-ink-500"
            >
              {s.label}
            </button>
          ))}
        </div>

        {error && (
          <p className="text-sm text-bad-foreground">{error}</p>
        )}
      </section>

      {result && (
        <section className="space-y-4">
          <div className="rounded-2xl border border-ink-700 bg-ink-800/40 p-5">
            <div className="text-xs uppercase tracking-wider text-ink-400 mb-1">
              Problem
            </div>
            <div className="text-lg">
              <LaTeXBlock tex={result.problem_latex} displayMode />
            </div>
          </div>

          <div className="space-y-2">
            {result.steps.map((s, i) => {
              const broke = !s.is_valid;
              return (
                <div
                  key={i}
                  className={`rounded-2xl border px-5 py-4 step-in ${
                    broke
                      ? 'panel-bad'
                      : 'panel-good'
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-3 mb-1">
                    <span className="text-xs uppercase tracking-wider text-ink-400">
                      Step {s.index} {broke ? '· break' : '· verified'}
                    </span>
                    <span className={broke ? 'text-bad-foreground' : 'text-good-foreground'}>
                      <StatusIcon status={broke ? 'bad' : 'good'} size="sm" />
                    </span>
                  </div>
                  <div className="text-lg">
                    <LaTeXBlock tex={s.expression_latex} displayMode />
                  </div>
                  {broke && s.error_message && (
                    <p className="text-sm text-bad-foreground mt-2">{s.error_message}</p>
                  )}
                  {broke && s.expected_latex && (
                    <p className="text-xs text-ink-400 mt-1">
                      Solving from the previous line gives:{' '}
                      <LaTeXBlock tex={s.expected_latex} />
                    </p>
                  )}
                </div>
              );
            })}
          </div>

          <div className="rounded-2xl border border-ink-700 bg-ink-800/60 p-4">
            <div className="text-sm text-ink-200">{result.summary}</div>
            {result.final_answer_correct !== null && (
              <div className="text-xs text-ink-400 mt-1">
                Final answer:{' '}
                {result.final_answer_correct ? (
                  <span className="text-good-foreground inline-flex items-center gap-1">
                    <StatusIcon status="good" size="xs" />
                    satisfies the original problem
                  </span>
                ) : (
                  <span className="text-bad-foreground inline-flex items-center gap-1">
                    <StatusIcon status="bad" size="xs" />
                    does not satisfy the original problem
                  </span>
                )}
              </div>
            )}
          </div>
        </section>
      )}
    </div>
  );
}
