import React, { useEffect, useState } from "react";
import { ArrowLeft, GraduationCap, Users } from "lucide-react";
import Button from "./ui/Button.jsx";
import Card from "./ui/Card.jsx";
import Input from "./ui/Input.jsx";
import Chip from "./ui/Chip.jsx";

import { api, getErrorMessage, ApiError } from "../api.js";

const TEACHER_TOKEN_KEY = "saboteur:teacher_token";

export default function ClassroomMode({ sessionId }) {
  const [view, setView] = useState("hub"); // hub | student | teacher
  const [classInfo, setClassInfo] = useState(null); // student's current class
  const [teacherToken, setTeacherToken] = useState(
    () => localStorage.getItem(TEACHER_TOKEN_KEY) || "",
  );

  // Check whether session is already in a class.
  useEffect(() => {
    if (!sessionId) return;
    api
      .classBySession(sessionId)
      .then((d) => {
        if (d) {
          setClassInfo(d);
          setView("student");
        }
      })
      .catch(() => {});
  }, [sessionId]);

  if (!sessionId) {
    return (
      <div className="layout-shell py-8 text-center text-sm text-ink-400">
        Start a session from the Play tab (or Retry in the banner) before using
        Classroom mode.
      </div>
    );
  }

  return (
    <div className="layout-shell py-4 sm:py-6 space-y-6">
      <header>
        <p className="text-caption text-accent-soft mb-1 inline-flex items-center gap-1.5">
          <GraduationCap size={14} aria-hidden />
          Classroom mode
        </p>
        <h2 className="text-xl sm:text-2xl">Teacher & student hub</h2>
        <p className="text-sm text-ink-400 mt-1">
          Teachers see aggregate calibration. Students join with a code -no
          accounts.
        </p>
      </header>

      {view === "hub" && (
        <HubView
          onStudent={() => setView("student")}
          onTeacher={() => setView("teacher")}
          hasTeacherToken={!!teacherToken}
        />
      )}

      {view === "student" && (
        <StudentView
          sessionId={sessionId}
          classInfo={classInfo}
          onClassChange={setClassInfo}
          onBack={() => setView("hub")}
        />
      )}

      {view === "teacher" && (
        <TeacherView
          teacherToken={teacherToken}
          onTokenChange={(t) => {
            setTeacherToken(t);
            if (t) localStorage.setItem(TEACHER_TOKEN_KEY, t);
            else localStorage.removeItem(TEACHER_TOKEN_KEY);
          }}
          onBack={() => setView("hub")}
        />
      )}
    </div>
  );
}

function HubView({ onStudent, onTeacher, hasTeacherToken }) {
  return (
    <div className="grid sm:grid-cols-2 gap-3">
      <Card
        as="button"
        type="button"
        variant="interactive"
        onClick={onStudent}
        className="text-left p-5 w-full"
      >
        <Users size={20} className="text-accent-soft mb-2" aria-hidden />
        <div className="text-lg font-semibold mb-1">I'm a student</div>
        <p className="text-sm text-ink-400">
          Join with a teacher's code. Your calibration aggregates to the class
          -not other students.
        </p>
      </Card>
      <Card
        as="button"
        type="button"
        variant="interactive"
        onClick={onTeacher}
        className="text-left p-5 w-full"
      >
        <GraduationCap
          size={20}
          className="text-accent-soft mb-2"
          aria-hidden
        />
        <div className="text-lg font-semibold mb-1 flex items-center gap-2 flex-wrap">
          I'm a teacher
          {hasTeacherToken && <Chip variant="accent">saved</Chip>}
        </div>
        <p className="text-sm text-ink-400">
          Create a class, share a join code, view class-wide misconception
          heatmaps.
        </p>
      </Card>
    </div>
  );
}

function StudentView({ sessionId, classInfo, onClassChange, onBack }) {
  const [joinCode, setJoinCode] = useState("");
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const join = async () => {
    if (!joinCode.trim() || !nickname.trim()) {
      setError("Join code and nickname are both required.");
      return;
    }
    setError("");
    setLoading(true);
    try {
      const data = await api.classJoin({
        join_code: joinCode.trim().toUpperCase(),
        session_id: sessionId,
        nickname: nickname.trim(),
      });
      onClassChange(data);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  if (classInfo) {
    return (
      <section>
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="mb-3 !px-0 inline-flex items-center gap-1"
        >
          <ArrowLeft size={14} aria-hidden />
          Back
        </Button>
        <Card variant="default" className="p-5 panel-good">
          <div className="text-caption mb-1">You're in</div>
          <div className="text-2xl font-semibold">{classInfo.name}</div>
          <div className="text-sm text-ink-300 mt-1">
            Join code: <span className="font-mono">{classInfo.join_code}</span>
            <span className="mx-2 text-ink-500">·</span>
            {classInfo.member_count} member
            {classInfo.member_count !== 1 ? "s" : ""}
          </div>
          <p className="text-xs text-ink-500 mt-3">
            Your calibration aggregates to the teacher. Nickname visible only in
            this class.
          </p>
        </Card>
      </section>
    );
  }

  return (
    <section>
      <Button
        variant="ghost"
        size="sm"
        onClick={onBack}
        className="mb-3 !px-0 inline-flex items-center gap-1"
      >
        <ArrowLeft size={14} aria-hidden />
        Back
      </Button>
      <div className="space-y-3">
        <div>
          <label className="text-caption block mb-1">
            Join code from your teacher
          </label>
          <Input
            type="text"
            value={joinCode}
            onChange={(e) => setJoinCode(e.target.value)}
            placeholder="RED-PI-42"
            className="font-mono uppercase"
          />
        </div>
        <div>
          <label className="text-caption block mb-1">
            Nickname (teacher view only)
          </label>
          <Input
            type="text"
            value={nickname}
            onChange={(e) => setNickname(e.target.value)}
            placeholder="e.g. Ada"
            maxLength={32}
          />
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={join}
          disabled={loading}
          className="btn-press"
        >
          {loading ? "Joining…" : "Join class"}
        </Button>
        {error && <p className="text-sm text-bad-foreground">{error}</p>}
      </div>
    </section>
  );
}

function TeacherView({ teacherToken, onTokenChange, onBack }) {
  const [name, setName] = useState("");
  const [created, setCreated] = useState(null);
  const [dashboard, setDashboard] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Auto-load dashboard if we have a stored teacher token.
  useEffect(() => {
    if (teacherToken && !dashboard) {
      loadDashboard(teacherToken);
    }
    // eslint-disable-next-line
  }, [teacherToken]);

  const loadDashboard = async (token) => {
    setLoading(true);
    setError("");
    try {
      setDashboard(await api.classDashboard(token));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        onTokenChange("");
        setDashboard(null);
        setError("Saved teacher token is invalid. Create a new class.");
      } else {
        setError(getErrorMessage(e));
      }
    } finally {
      setLoading(false);
    }
  };

  const createClass = async () => {
    if (!name.trim()) {
      setError("Class name is required.");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const data = await api.classCreate({ name: name.trim() });
      setCreated(data);
      onTokenChange(data.teacher_token);
    } catch (e) {
      setError(getErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  if (dashboard) {
    return (
      <TeacherDashboard
        dashboard={dashboard}
        onRefresh={() => loadDashboard(teacherToken)}
        onSignOut={() => {
          onTokenChange("");
          setDashboard(null);
          setCreated(null);
        }}
        loading={loading}
      />
    );
  }

  if (created) {
    return (
      <section>
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="mb-3 !px-0 inline-flex items-center gap-1"
        >
          <ArrowLeft size={14} aria-hidden />
          Back
        </Button>
        <Card variant="default" className="p-5 panel-good">
          <div className="text-caption mb-1">Class created</div>
          <div className="text-2xl font-semibold">{created.name}</div>
          <div className="mt-3 space-y-2">
            <div>
              <div className="text-xs uppercase tracking-wider text-ink-400">
                Share this with students
              </div>
              <div className="text-2xl font-mono font-bold text-accent">
                {created.join_code}
              </div>
            </div>
            <div>
              <div className="text-xs uppercase tracking-wider text-ink-400">
                Your teacher token (saved in this browser)
              </div>
              <div className="font-mono text-xs text-ink-300 break-all bg-ink-800 px-2 py-1 rounded">
                {created.teacher_token}
              </div>
              <p className="text-xs text-ink-500 mt-1">
                Keep this safe. If you lose it, you can't recover this class's
                data.
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            size="md"
            onClick={() => loadDashboard(created.teacher_token)}
            className="mt-4 btn-press"
          >
            Open dashboard
          </Button>
        </Card>
      </section>
    );
  }

  return (
    <section>
      <Button
        variant="ghost"
        size="sm"
        onClick={onBack}
        className="mb-3 !px-0 inline-flex items-center gap-1"
      >
        <ArrowLeft size={14} aria-hidden />
        Back
      </Button>
      <div className="space-y-3">
        <div>
          <label className="text-caption block mb-1">Class name</label>
          <Input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Period 3 Algebra"
            maxLength={80}
          />
        </div>
        <Button
          variant="primary"
          size="md"
          onClick={createClass}
          disabled={loading}
          className="btn-press"
        >
          {loading ? "Creating…" : "Create class"}
        </Button>
        {error && <p className="text-sm text-bad-foreground">{error}</p>}
      </div>
    </section>
  );
}

function TeacherDashboard({ dashboard, onRefresh, onSignOut, loading }) {
  const heatmap = Object.entries(dashboard.misconception_heatmap || {}).sort(
    (a, b) => b[1].seen - a[1].seen,
  );

  return (
    <section>
      <div className="flex items-baseline justify-between mb-3">
        <div>
          <div className="text-xs uppercase tracking-wider text-ink-400">
            Class
          </div>
          <h3 className="text-xl font-semibold">{dashboard.name}</h3>
        </div>
        <div className="flex gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={onRefresh}
            disabled={loading}
          >
            {loading ? "Loading…" : "Refresh"}
          </Button>
          <Button variant="ghost" size="sm" onClick={onSignOut}>
            Sign out
          </Button>
        </div>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-3 gap-2 sm:gap-3 mb-5">
        <Stat label="Students" value={dashboard.member_count} />
        <Stat
          label="Avg score"
          value={(dashboard.avg_score ?? 0).toFixed(1)}
          suffix="/ 100"
          highlight
        />
        <Stat
          label="Avg rating"
          value={Math.round(dashboard.avg_rating ?? 1000)}
        />
      </div>

      {/* Members table */}
      <div className="rounded-2xl border border-ink-700 overflow-hidden mb-5">
        <table className="w-full text-sm">
          <thead className="bg-ink-800/80 text-ink-400">
            <tr>
              <th className="px-2 sm:px-4 py-2 text-left font-medium">
                Student
              </th>
              <th className="px-2 sm:px-4 py-2 text-right font-medium">
                Score
              </th>
              <th className="px-2 sm:px-4 py-2 text-right font-medium">
                Rounds
              </th>
              <th className="px-2 sm:px-4 py-2 text-right font-medium">
                Catches
              </th>
              <th className="px-2 sm:px-4 py-2 text-right font-medium">
                Over-trust
              </th>
            </tr>
          </thead>
          <tbody className="bg-ink-800/40">
            {dashboard.members.map((m, i) => (
              <tr key={m.nickname + i} className="border-t border-ink-700">
                <td className="px-2 sm:px-4 py-2 text-ink-200">{m.nickname}</td>
                <td className="px-2 sm:px-4 py-2 text-right font-mono">
                  {(m.score ?? 0).toFixed(0)}
                </td>
                <td className="px-2 sm:px-4 py-2 text-right font-mono text-ink-400">
                  {m.total_rounds}
                </td>
                <td className="px-2 sm:px-4 py-2 text-right font-mono text-good-foreground">
                  {m.correct_catch_count}
                </td>
                <td className="px-2 sm:px-4 py-2 text-right font-mono text-bad-foreground">
                  {m.over_trust_count}
                </td>
              </tr>
            ))}
            {dashboard.members.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-4 text-center text-ink-500">
                  No students have joined yet. Share the join code.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Misconception heatmap */}
      {heatmap.length > 0 && (
        <div>
          <h4 className="text-xs uppercase tracking-wider text-ink-400 mb-2">
            Class-wide misconception heatmap
          </h4>
          <div className="space-y-2">
            {heatmap.map(([mid, agg]) => {
              const pct = Math.round((agg.catch_rate || 0) * 100);
              const trouble = pct < 50;
              return (
                <div
                  key={mid}
                  className="rounded-xl border border-ink-700 bg-ink-800/40 p-3"
                >
                  <div className="flex items-baseline justify-between mb-1 gap-2">
                    <span className="text-sm text-ink-100 truncate">
                      {agg.name || mid}
                    </span>
                    <span
                      className={`text-xs font-mono ${trouble ? "text-bad-foreground" : "text-good-foreground"}`}
                    >
                      {agg.caught}/{agg.seen} caught
                    </span>
                  </div>
                  <div className="h-1.5 rounded-full bg-ink-700 overflow-hidden">
                    <div
                      className={`h-full transition-all ${trouble ? "bg-bad" : "bg-good"}`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
          <p className="text-xs text-ink-500 mt-2">
            Misconceptions caught &lt; 50% by the class are good candidates for
            re-teaching.
          </p>
        </div>
      )}
    </section>
  );
}

function Stat({ label, value, suffix, highlight }) {
  return (
    <div
      className={`rounded-2xl border px-3 sm:px-4 py-3 ${
        highlight
          ? "border-accent/40 bg-accent/10"
          : "border-ink-700 bg-ink-800/40"
      }`}
    >
      <div className="text-xs uppercase tracking-wider text-ink-400">
        {label}
      </div>
      <div className="text-xl sm:text-2xl font-semibold mt-1">
        {value}
        {suffix && <span className="text-sm text-ink-500 ml-1">{suffix}</span>}
      </div>
    </div>
  );
}
