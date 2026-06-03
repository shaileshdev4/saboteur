import React, { useEffect, useRef, useState } from 'react';
import { FileText, Scan, Sparkles } from 'lucide-react';
import katex from 'katex';
import Button from './ui/Button.jsx';
import Card from './ui/Card.jsx';
import Chip from './ui/Chip.jsx';
import Textarea from './ui/Textarea.jsx';
import { Camera, StatusIcon } from './ui/StatusIcon.jsx';

import { api, getErrorMessage } from '../api.js';

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

const SAMPLES = [
  {
    label: 'ChatGPT algebra (broken)',
    blob: `Sure! Let's solve 2x + 6 = 10.

Step 1: Subtract 6 from both sides:
2x = 16

Step 2: Divide both sides by 2:
x = 8`,
  },
  {
    label: 'Claude calculus',
    blob: `To find the derivative of f(x) = (2x + 3)^2:

f'(x) = 2(2x + 3) · 2
f'(x) = 4(2x + 3)
f'(x) = 8x + 12`,
  },
  {
    label: 'Gemini geometry',
    blob: `Find the hypotenuse of a right triangle with legs 3 and 4.

c^2 = a^2 + b^2
c^2 = 9 + 16
c^2 = 25
c = 5`,
  },
];

export default function UniversalAuditor() {
  const [blob, setBlob] = useState(SAMPLES[0].blob);
  const [forceDomain, setForceDomain] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [imageEnabled, setImageEnabled] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    api.imageConfigured()
      .then((d) => setImageEnabled(!!d.configured))
      .catch(() => setImageEnabled(false));
  }, []);

  const submit = async () => {
    setError('');
    setResult(null);
    if (!blob.trim()) {
      setError('Paste a chatbot response first — include the problem and each step.');
      return;
    }
    try {
      setLoading(true);
      const r = await api.audit({
        blob,
        domain_id: forceDomain || null,
      });
      setResult(r);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  const onImageSelect = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError('');
    setUploading(true);
    try {
      const data = await api.imageTranscribe(file);
      if (!data.ok) {
        setError(data.error || 'Transcription failed.');
        return;
      }
      setBlob(data.text);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const loadSample = (s) => {
    setBlob(s.blob);
    setResult(null);
    setError('');
  };

  const breakIndex = result?.first_error_index;

  return (
    <div className="layout-shell py-4 sm:py-6 space-y-5">
      <header>
        <p className="text-caption text-accent-soft mb-1 inline-flex items-center gap-1.5">
          <Scan size={14} aria-hidden />
          External work import
        </p>
        <h2 className="text-xl sm:text-2xl">Audit a real AI answer</h2>
        <p className="text-sm text-ink-400 mt-1">
          Paste messy chatbot output. We extract steps, detect the domain, and verify symbolically.
        </p>
      </header>

      <Card variant="default" className="p-4 border-accent/20 bg-accent/5">
        <div className="flex gap-2">
          <FileText size={18} className="text-accent-soft flex-shrink-0 mt-0.5" aria-hidden />
          <div className="text-sm text-ink-300 space-y-1">
            <p className="font-medium text-ink-100">Parser tips</p>
            <ul className="list-disc list-inside text-xs text-ink-400 space-y-0.5">
              <li>Put the problem on its own line (with an equals sign).</li>
              <li>One step per line works best; numbered steps are fine.</li>
              <li>Code fences and markdown are OK — we strip them.</li>
            </ul>
          </div>
        </div>
      </Card>

      <section className="space-y-3">
        <label className="text-caption block">Pasted response</label>
        <Textarea
          value={blob}
          onChange={(e) => setBlob(e.target.value)}
          rows={10}
          className="px-4 py-3 min-h-[12rem]"
          placeholder="Paste the full chatbot reply here…"
        />

        <div className="flex flex-wrap items-center gap-2">
          <Button
            variant="primary"
            size="md"
            onClick={submit}
            disabled={loading}
            className="inline-flex items-center gap-1.5 btn-press"
          >
            <Sparkles size={16} aria-hidden />
            {loading ? 'Auditing…' : 'Run audit'}
          </Button>

          <select
            value={forceDomain}
            onChange={(e) => setForceDomain(e.target.value)}
            className="px-3 py-2 rounded-xl border border-line bg-surface text-sm text-ink-100 hover:border-line-subtle focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent focus-visible:border-accent/60"
          >
            <option value="">Auto-detect domain</option>
            <option value="algebra">Force: Algebra</option>
            <option value="geometry">Force: Geometry</option>
            <option value="calculus">Force: Calculus</option>
          </select>

          {imageEnabled && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                onChange={onImageSelect}
                className="hidden"
              />
              <Button
                type="button"
                variant="secondary"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="inline-flex items-center gap-1.5"
              >
                <Camera size={16} aria-hidden />
                {uploading ? 'Transcribing…' : 'From image'}
              </Button>
            </>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-caption">Samples</span>
          {SAMPLES.map((s) => (
            <Chip
              key={s.label}
              as="button"
              type="button"
              variant="muted"
              onClick={() => loadSample(s)}
              className="cursor-pointer hover:border-accent/50"
            >
              {s.label}
            </Chip>
          ))}
        </div>

        {!imageEnabled && (
          <p className="text-xs text-ink-500">
            Image upload needs <code className="text-meta">MULTIMODAL_API_KEY</code> or{' '}
            <code className="text-meta">MATHPIX_APP_KEY</code> on the server.
          </p>
        )}

        {error && (
          <Card variant="default" className="p-3 panel-bad">
            <p className="text-sm text-bad-foreground">{error}</p>
          </Card>
        )}
      </section>

      {result && (
        <section className="space-y-4 step-in">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-caption">Detected domain</span>
            <Chip variant="accent">{result.detected_domain}</Chip>
          </div>

          {breakIndex != null && (
            <Card variant="default" className="p-4 panel-bad">
              <p className="text-sm text-bad-foreground font-medium">
                First break at step {breakIndex}
              </p>
              <p className="text-xs text-ink-400 mt-1">
                Scroll to the highlighted step below for the symbolic mismatch.
              </p>
            </Card>
          )}

          <Card variant="default" className="p-5">
            <div className="text-caption mb-1">Problem</div>
            <div className="text-lg">
              <LaTeXBlock tex={result.problem_latex} displayMode />
            </div>
          </Card>

          <div className="space-y-2">
            {result.steps.map((s, i) => {
              const broke = !s.is_valid;
              const isFirstBreak = breakIndex === s.index || breakIndex === i;
              return (
                <Card
                  key={i}
                  variant="default"
                  className={`px-4 sm:px-5 py-4 step-in ${
                    isFirstBreak
                      ? 'border-bad ring-1 ring-bad/40 panel-bad'
                      : broke
                        ? 'panel-bad'
                        : 'panel-good'
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-3 mb-1">
                    <span className="text-caption">
                      Step {s.index} {broke ? '· break' : '· verified'}
                    </span>
                    <StatusIcon status={broke ? 'bad' : 'good'} size="sm" />
                  </div>
                  <div className="text-lg">
                    <LaTeXBlock tex={s.expression_latex} displayMode />
                  </div>
                  {broke && s.error_message && (
                    <p className="text-sm text-bad-foreground mt-2">{s.error_message}</p>
                  )}
                  {broke && s.expected_latex && (
                    <p className="text-xs text-ink-400 mt-1">
                      Expected from prior line:{' '}
                      <LaTeXBlock tex={s.expected_latex} />
                    </p>
                  )}
                </Card>
              );
            })}
          </div>

          <Card variant="default" className="p-4">
            <div className="text-sm text-ink-200">{result.summary}</div>
            {result.final_answer_correct !== null && (
              <div className="text-xs text-ink-400 mt-2">
                Final answer:{' '}
                {result.final_answer_correct ? (
                  <span className="text-good-foreground inline-flex items-center gap-1">
                    <StatusIcon status="good" size="xs" />
                    satisfies the original
                  </span>
                ) : (
                  <span className="text-bad-foreground inline-flex items-center gap-1">
                    <StatusIcon status="bad" size="xs" />
                    does not satisfy the original
                  </span>
                )}
              </div>
            )}
          </Card>
        </section>
      )}
    </div>
  );
}
