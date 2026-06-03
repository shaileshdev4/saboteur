import React, { useEffect, useRef, useState } from "react";
import { FileText, Scan, Sparkles } from "lucide-react";
import katex from "katex";
import Button from "./ui/Button.jsx";
import Card from "./ui/Card.jsx";
import Chip from "./ui/Chip.jsx";
import Textarea from "./ui/Textarea.jsx";
import { Camera, StatusIcon } from "./ui/StatusIcon.jsx";

import { api, getErrorMessage } from "../api.js";

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

/** Demo-ready samples - one equation per line; SymPy-friendly. */
const SAMPLES = [
  {
    label: "Algebra (broken)",
    blob: `Solve: 2x + 6 = 10

2x = 16
x = 8`,
  },
  {
    label: "Algebra (correct)",
    blob: `Solve: 2x + 6 = 10

2x = 4
x = 2`,
  },
  {
    label: "Geometry (correct)",
    blob: `Right triangle: legs 3 and 4, find c.

c^2 = 3^2 + 4^2
c^2 = 9 + 16
c^2 = 25
c = 5`,
  },
  {
    label: "Calculus (broken)",
    blob: `Derivative of (2x + 3)^2:

y = 2*(2*x + 3)*2
y = 4*x + 3`,
  },
  {
    label: "Statistics (broken)",
    blob: `Scores: 2, 4, 4, 5, 7

Mean = (2+4+4+5+7)/4 = 5.5`,
  },
];

export default function UniversalAuditor() {
  const [blob, setBlob] = useState(SAMPLES[0].blob);
  const [forceDomain, setForceDomain] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [imageEnabled, setImageEnabled] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef(null);

  useEffect(() => {
    api
      .imageConfigured()
      .then((d) => setImageEnabled(!!d.configured))
      .catch(() => setImageEnabled(false));
  }, []);

  const submit = async () => {
    setError("");
    setResult(null);
    if (!blob.trim()) {
      setError(
        "Paste a chatbot response first - include the problem and each step.",
      );
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
    setError("");
    setUploading(true);
    try {
      const data = await api.imageTranscribe(file);
      if (!data.ok) {
        setError(data.error || "Transcription failed.");
        return;
      }
      setBlob(data.text);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const loadSample = (s) => {
    setBlob(s.blob);
    setResult(null);
    setError("");
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
          Paste messy chatbot output. SymPy checks each step - one equation per
          line works best.
        </p>
      </header>

      <Card variant="default" className="p-4 space-y-3">
        <label className="text-caption block">Pasted response</label>
        <Textarea
          value={blob}
          onChange={(e) => setBlob(e.target.value)}
          rows={10}
          className="font-mono text-sm"
          placeholder="Problem on its own line, then one step per line…"
        />
        <div className="flex flex-wrap gap-2 items-center">
          <Button
            variant="primary"
            size="md"
            onClick={submit}
            disabled={loading}
            className="inline-flex items-center gap-1.5 btn-press"
          >
            <Sparkles size={16} aria-hidden />
            {loading ? "Auditing…" : "Run audit"}
          </Button>
          <select
            value={forceDomain}
            onChange={(e) => setForceDomain(e.target.value)}
            className="text-sm rounded-lg border border-line bg-surface px-3 py-2 text-ink-200"
          >
            <option value="">Auto-detect domain</option>
            <option value="algebra">Algebra</option>
            <option value="geometry">Geometry</option>
            <option value="calculus">Calculus</option>
            <option value="statistics">Statistics</option>
          </select>
          {imageEnabled && (
            <>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={onImageSelect}
              />
              <Button
                variant="secondary"
                size="md"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
                className="inline-flex items-center gap-1.5"
              >
                <Camera size={16} aria-hidden />
                {uploading ? "Reading…" : "From image"}
              </Button>
            </>
          )}
        </div>
        <div className="flex flex-wrap gap-1.5">
          <span className="text-caption mr-1">Samples</span>
          {SAMPLES.map((s) => (
            <Chip
              key={s.label}
              variant="muted"
              as="button"
              type="button"
              onClick={() => loadSample(s)}
              className="cursor-pointer hover:border-accent/40"
            >
              {s.label}
            </Chip>
          ))}
        </div>
      </Card>

      {error && (
        <Card variant="default" className="p-4 panel-bad">
          <p className="text-sm text-bad-foreground">{error}</p>
        </Card>
      )}

      {result && (
        <div className="space-y-4 step-in">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-caption">Detected domain</span>
            <Chip variant="accent-soft">{result.detected_domain}</Chip>
          </div>

          {breakIndex != null && (
            <Card variant="default" className="p-4 panel-bad">
              <p className="text-sm font-medium text-bad-foreground">
                First break at step {breakIndex}
              </p>
              <p className="text-xs text-ink-400 mt-1">
                Scroll to the highlighted step for the symbolic mismatch.
              </p>
            </Card>
          )}

          {result.problem_latex && (
            <Card variant="default" className="p-4">
              <p className="text-caption mb-2">Problem</p>
              <LaTeXBlock tex={result.problem_latex} displayMode />
            </Card>
          )}

          {result.steps?.map((s) => (
            <Card
              key={s.index}
              variant="default"
              className={`p-4 ${
                s.index === breakIndex
                  ? "border-bad/50 panel-bad"
                  : s.is_valid
                    ? "border-good/30"
                    : ""
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <p className="text-caption">
                  Step {s.index}
                  {s.index === breakIndex ? " · break" : ""}
                </p>
                <StatusIcon status={s.is_valid ? "good" : "bad"} size="sm" />
              </div>
              {s.expression_latex && (
                <LaTeXBlock tex={s.expression_latex} displayMode />
              )}
              {s.error_message && (
                <p className="text-sm text-bad-foreground mt-2">
                  {s.error_message}
                </p>
              )}
              {s.expected_latex && (
                <p className="text-xs text-ink-400 mt-1">
                  Expected from prior line:{" "}
                  <LaTeXBlock tex={s.expected_latex} />
                </p>
              )}
            </Card>
          ))}

          <Card variant="default" className="p-4 text-sm text-ink-300">
            {result.summary}
            {result.final_answer_correct === false && (
              <p className="text-bad-foreground mt-2 text-xs">
                Final answer does not satisfy the original problem.
              </p>
            )}
            {result.final_answer_correct === true && (
              <p className="text-good-foreground mt-2 text-xs">
                Final answer satisfies the original problem.
              </p>
            )}
          </Card>
        </div>
      )}

      {!imageEnabled && (
        <p className="text-xs text-ink-500">
          Image upload needs{" "}
          <code className="text-meta">MULTIMODAL_API_KEY</code> on the server.
        </p>
      )}
    </div>
  );
}
