import React, { Suspense, lazy, useCallback, useEffect, useState } from 'react';
import { api, getOrCreateSession, clearSession, getErrorMessage } from './api.js';
import PlayScreen from './components/PlayScreen.jsx';
import RevealScreen from './components/RevealScreen.jsx';
import UniversalAuditor from './components/UniversalAuditor.jsx';
import ClassroomMode from './components/ClassroomMode.jsx';
import MultiplayerMode from './components/MultiplayerMode.jsx';
import DomainPicker from './components/DomainPicker.jsx';
import Onboarding from './components/Onboarding.jsx';
import Leaderboard from './components/Leaderboard.jsx';
import AchievementToast from './components/AchievementToast.jsx';
import Button from './components/ui/Button.jsx';
import BrandMark from './components/ui/BrandMark.jsx';
import ErrorBanner from './components/ui/ErrorBanner.jsx';
import ConnectionProblem from './components/ui/ConnectionProblem.jsx';
import { recordRoundOutcome } from './utils/sessionAnalytics.js';

const Dashboard = lazy(() => import('./components/Dashboard.jsx'));

const TABS = [
  { id: 'play', label: 'Play' },
  { id: 'multiplayer', label: 'Multiplayer' },
  { id: 'leaderboard', label: 'Ranks' },
  { id: 'dashboard', label: 'Stats' },
  { id: 'audit', label: 'Audit AI' },
  { id: 'classroom', label: 'Class' },
];

const SHOWN_ACHIEVEMENTS_KEY = 'saboteur:achievements_shown';

const DOMAIN_KEY = 'saboteur:domain';

export default function App() {
  const [tab, setTab] = useState('play');
  const [sessionId, setSessionId] = useState(null);
  const [domains, setDomains] = useState([]);
  const [activeDomain, setActiveDomain] = useState(() => {
    try { return localStorage.getItem(DOMAIN_KEY) || 'algebra'; } catch { return 'algebra'; }
  });
  const [round, setRound] = useState(null);
  const [grade, setGrade] = useState(null);
  const [phase, setPhase] = useState('play');
  const [dashboardData, setDashboardData] = useState(null);
  const [loadingRound, setLoadingRound] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [bootstrapped, setBootstrapped] = useState(false);
  const [bootRetrying, setBootRetrying] = useState(false);
  const [bannerError, setBannerError] = useState('');
  const [dashboardLoading, setDashboardLoading] = useState(false);
  const [roundNumber, setRoundNumber] = useState(0);
  const [toastQueue, setToastQueue] = useState([]);
  const [allAchievements, setAllAchievements] = useState([]);

  const bootstrap = useCallback(async () => {
    setBootRetrying(true);
    setBannerError('');
    try {
      const [sid, doms] = await Promise.all([
        getOrCreateSession(),
        api.domains(),
      ]);
      setSessionId(sid);
      setDomains(doms);
      setActiveDomain((current) =>
        doms.find((d) => d.id === current) ? current : doms[0]?.id || 'algebra',
      );
    } catch (e) {
      setSessionId(null);
      setDomains([]);
      setBannerError(getErrorMessage(e, { context: 'session' }));
    } finally {
      setBootstrapped(true);
      setBootRetrying(false);
    }
  }, []);

  useEffect(() => {
    bootstrap();
  }, [bootstrap]);

  const setDomain = (did) => {
    setActiveDomain(did);
    try { localStorage.setItem(DOMAIN_KEY, did); } catch {}
    setRound(null);
    setPhase('play');
    setGrade(null);
  };

  const fetchRound = async () => {
    if (!sessionId) return;
    try {
      setLoadingRound(true);
      setBannerError('');
      setGrade(null);
      setPhase('play');
      const r = await api.newRound(sessionId, { domainId: activeDomain });
      setRound(r);
      setRoundNumber((n) => n + 1);
    } catch (e) {
      setRound(null);
      setBannerError(getErrorMessage(e));
    } finally {
      setLoadingRound(false);
    }
  };

  useEffect(() => {
    if (sessionId && tab === 'play' && !round && !loadingRound) {
      fetchRound();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId, tab, activeDomain]);

  const handleSubmit = async (action) => {
    if (!sessionId || !round) return;
    try {
      setSubmitting(true);
      const g = await api.grade({
        session_id: sessionId,
        round_id: round.round_id,
        decision: action.decision,
        flagged_step_index: action.flagged_step_index ?? null,
      });
      setGrade(g);
      recordRoundOutcome(sessionId, g.outcome);
      if (g.achievements_unlocked?.length) {
        let shown = [];
        try {
          shown = JSON.parse(localStorage.getItem(SHOWN_ACHIEVEMENTS_KEY) || '[]');
        } catch {}
        const fresh = g.achievements_unlocked.filter((a) => !shown.includes(a.id));
        if (fresh.length) {
          setToastQueue((q) => [...q, ...fresh]);
          try {
            localStorage.setItem(
              SHOWN_ACHIEVEMENTS_KEY,
              JSON.stringify([...shown, ...fresh.map((a) => a.id)]),
            );
          } catch {}
          setAllAchievements((prev) => {
            const ids = new Set(prev.map((x) => x.id));
            return [...prev, ...fresh.filter((a) => !ids.has(a.id))];
          });
        }
      }
      setPhase('reveal');
    } catch (e) {
      setBannerError(getErrorMessage(e));
    } finally {
      setSubmitting(false);
    }
  };

  const handleNext = () => fetchRound();

  const loadDashboard = async () => {
    if (!sessionId) return;
    setDashboardLoading(true);
    try {
      const d = await api.dashboard(sessionId);
      setDashboardData(d);
    } catch (e) {
      setDashboardData(null);
      setBannerError(getErrorMessage(e));
    } finally {
      setDashboardLoading(false);
    }
  };

  const goToDashboard = async () => {
    setTab('dashboard');
    await loadDashboard();
  };

  const switchTab = async (t) => {
    setTab(t);
    if (t === 'dashboard' && sessionId) {
      await loadDashboard();
    }
  };

  const startPracticeRound = () => {
    setTab('play');
    setPhase('play');
    setRound(null);
    setGrade(null);
    if (sessionId) fetchRound();
  };

  const handleResetSession = () => {
    if (!confirm('Clear your saved session and start fresh? Your calibration history will be lost.')) return;
    clearSession();
    window.location.reload();
  };

  return (
    <div className="bg-app min-h-screen flex flex-col theme-scanlines">
      <Onboarding onStartPractice={startPracticeRound} />
      {toastQueue[0] && (
        <AchievementToast
          achievement={toastQueue[0]}
          onDone={() => setToastQueue((q) => q.slice(1))}
        />
      )}
      <Header
        tab={tab}
        onTab={switchTab}
        onResetSession={handleResetSession}
        compactFooter={tab === 'play' || tab === 'multiplayer'}
      />

      {tab === 'play' && bootstrapped && domains.length > 0 && (
        <div className="border-b border-line/80 bg-ink-900/60">
          <div className="layout-shell py-2 flex items-center justify-between gap-3">
            <DomainPicker
              domains={domains}
              selected={activeDomain}
              onChange={setDomain}
              disabled={loadingRound || submitting}
            />
            <span className="text-xs text-ink-500 hidden sm:inline max-w-[40%] truncate">
              {domains.find((d) => d.id === activeDomain)?.description}
            </span>
          </div>
        </div>
      )}

      <ErrorBanner
        message={bannerError}
        onDismiss={() => setBannerError('')}
        onRetry={!sessionId ? bootstrap : undefined}
        retryLabel={bootRetrying ? 'Connecting…' : 'Retry'}
        retrying={bootRetrying}
      />

      <main className="flex-1">
        {!bootstrapped && <Booting />}

        {bootstrapped && !sessionId && (
          <ConnectionProblem
            message={bannerError}
            onRetry={bootstrap}
            retrying={bootRetrying}
          />
        )}

        {bootstrapped && sessionId && tab === 'play' && phase === 'play' && (
          loadingRound ? (
            <div className="text-ink-400 py-16 text-center">Scanning pipeline…</div>
          ) : !round ? (
            <ConnectionProblem
              message={bannerError || "Couldn't load a round."}
              onRetry={fetchRound}
              retrying={loadingRound}
            />
          ) : (
            <PlayScreen
              round={round}
              sessionId={sessionId}
              onSubmit={handleSubmit}
              isSubmitting={submitting}
              domains={domains}
              roundNumber={roundNumber || 1}
            />
          )
        )}

        {bootstrapped && sessionId && tab === 'play' && phase === 'reveal' && (
          <RevealScreen
            round={round}
            grade={grade}
            onNext={handleNext}
            onDashboard={goToDashboard}
          />
        )}

        {bootstrapped && sessionId && tab === 'multiplayer' && (
          <MultiplayerMode sessionId={sessionId} />
        )}

        {bootstrapped && sessionId && tab === 'leaderboard' && (
          <Leaderboard sessionId={sessionId} domains={domains} />
        )}

        {bootstrapped && sessionId && tab === 'dashboard' && (
          <Suspense
            fallback={
              <div className="text-ink-400 py-10 text-center">Loading stats…</div>
            }
          >
            <Dashboard
              data={dashboardData}
              loading={dashboardLoading}
              loadError={!dashboardLoading && !dashboardData ? bannerError : ''}
              onPlay={() => switchTab('play')}
              domains={domains}
              sessionId={sessionId}
              recentAchievements={allAchievements}
            />
          </Suspense>
        )}

        {bootstrapped && sessionId && tab === 'audit' && <UniversalAuditor />}

        {bootstrapped && sessionId && tab === 'classroom' && (
          <ClassroomMode sessionId={sessionId} />
        )}
      </main>
      {tab !== 'play' && tab !== 'multiplayer' ? (
        <Footer onResetSession={handleResetSession} />
      ) : (
        <PlayTabFooter onResetSession={handleResetSession} />
      )}
    </div>
  );
}

function Header({ tab, onTab, onResetSession, compactFooter }) {
  return (
    <header className="sticky top-0 z-20 backdrop-blur bg-ink-900/90 header-glow">
      <div className="layout-shell py-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          <BrandMark />
          <div className="min-w-0">
            <h1 className="text-base sm:text-lg font-semibold tracking-tight truncate">
              The Saboteur
            </h1>
            <p className="text-caption normal-case tracking-normal text-ink-500 -mt-0.5 hidden sm:block">
              Audit the AI · calibrate your trust
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
        {compactFooter && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onResetSession}
            className="text-ink-500 shrink-0"
          >
            Reset
          </Button>
        )}
        <nav className="flex gap-1 overflow-x-auto" aria-label="Main">
          {TABS.map((t) => (
            <Button
              key={t.id}
              type="button"
              variant={tab === t.id ? 'primary' : 'ghost'}
              size="sm"
              onClick={() => onTab(t.id)}
              className="whitespace-nowrap"
              aria-current={tab === t.id ? 'page' : undefined}
            >
              {t.label}
            </Button>
          ))}
        </nav>
        </div>
      </div>
    </header>
  );
}

function Booting() {
  return (
    <div className="text-ink-400 py-16 text-center text-sm">Starting audit session…</div>
  );
}

function PlayTabFooter({ onResetSession }) {
  return (
    <div className="border-t border-line mt-4">
      <div className="layout-shell py-3 flex items-center justify-between text-xs text-ink-500 gap-2">
        <span className="inline-flex items-center gap-1.5">
          <img src="/audit-lens.svg" alt="" className="w-4 h-4 opacity-60" />
          SymPy verifies · LLM explains only
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={onResetSession}
          className="!px-2 text-ink-500 hover:text-ink-300 shrink-0"
        >
          Reset session
        </Button>
      </div>
    </div>
  );
}

function Footer({ onResetSession }) {
  return (
    <footer className="border-t border-line mt-8 mb-4">
      <div className="layout-shell py-4 flex items-center justify-between text-xs text-ink-500 flex-wrap gap-2">
        <span className="inline-flex items-center gap-1.5">
          <img src="/audit-lens.svg" alt="" className="w-4 h-4 opacity-60" />
          SymPy verifies · LLM explains only
        </span>
        <Button
          variant="ghost"
          size="sm"
          onClick={onResetSession}
          className="!px-0 !py-0 underline text-ink-500 hover:text-ink-300"
        >
          Reset session
        </Button>
      </div>
    </footer>
  );
}
