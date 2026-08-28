import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowCounterClockwise,
  Buildings,
  Check,
  CircleNotch,
  Dna,
  FolderOpen,
  GearSix,
  Lifebuoy,
  MagnifyingGlass,
  MapTrifold,
  PenNib,
  Play,
  PushPin,
  Stop,
  WarningCircle,
} from "@phosphor-icons/react";
import { api } from "../api";
import { useT } from "../i18n/I18nProvider";
import { BOOTSTRAP_KEYS, STAGE_DESC_KEYS } from "../i18n/messages";
import type { NovelDetail, RunStep, Task } from "../types";

interface Props {
  novel: NovelDetail;
  onChange: () => void;
  llmConfigured: boolean;
  onOpenSettings: () => void;
  showSettingsLink?: boolean;
  advanced: boolean;
  /** True while another AI task (e.g. DNA enrichment) is running elsewhere in
   *  the studio, so the run controls stay inactive to avoid overlapping runs. */
  aiBusy?: boolean;
  /** False while PROJECT_DNA still carries unfilled "tự sinh" placeholders.
   *
   *  Distinct from ``novel.dna_ready``, which only checks that the logline is
   *  filled in. A novel can therefore be "ready" with most of its DNA still
   *  unwritten — 360 of 503 real workspaces are in exactly that state — and the
   *  write button used to be enabled while the DNA tab told the author to finish
   *  step 1 first. Writing from a placeholder DNA is what produces the generic
   *  chapters, so the run is gated on this instead. */
  dnaComplete?: boolean;
  /** Focus the "finish the DNA" action, which lives on the other side of the
   *  studio layout, when that is the real next step. */
  onFinishDna?: () => void;
  onViewArtifact: (path: string, allPaths: string[]) => void;
}

const RESULTS = ["done", "soft_fail", "hard_fail", "blocked", "skipped"];

/** Backoff between retries while the server-side run lock is held. */
const BUSY_RETRY_MS = 1500;

/** Ceiling for one "write N chapters" request. Matches the server's own
 *  ``RunRequest.chapters`` bound (schemas.py: ge=1, le=20), so the UI can never
 *  submit a value the API rejects with a 422. */
const MAX_CHAPTERS_PER_RUN = 20;

/** Gap between ``/run-status`` polls while a server job is in flight. A chapter
 *  takes minutes, so a tighter interval only adds request noise. */
const JOB_POLL_MS = 4000;

/** How many busy retries before giving the user back control. A step can hold the
 *  lock for minutes, so retrying forever is just a slower frozen UI. */
const BUSY_MAX_WAITS = 4;

const STAGE_META = [
  { id: "dna", icon: Dna, titleKey: "pipeline.stage.dna.title" },
  { id: "setup", icon: Buildings, titleKey: "pipeline.stage.setup.title" },
  { id: "outline", icon: MapTrifold, titleKey: "pipeline.stage.outline.title" },
  { id: "write", icon: PenNib, titleKey: "pipeline.stage.write.title" },
  { id: "review", icon: MagnifyingGlass, titleKey: "pipeline.stage.review.title" },
  { id: "sync", icon: PushPin, titleKey: "pipeline.stage.sync.title" },
] as const;

function stageOf(task: Task | null): string | null {
  if (!task) return null;
  if (task.task_key.startsWith("bootstrap") || task.phase === "state") return "setup";
  return { "2": "outline", "3": "write", "4": "review", sync: "sync" }[task.phase] ?? "setup";
}

export function PipelineBoard({
  novel,
  onChange,
  llmConfigured,
  onOpenSettings,
  showSettingsLink = true,
  advanced,
  aiBusy = false,
  dnaComplete = true,
  onViewArtifact,
}: Props) {
  const t = useT();
  const [maxSteps, setMaxSteps] = useState(1);
  // How many CHAPTERS one click should write. This is the unit an author thinks
  // in; "steps" is an internal scheduling detail (a clean chapter is ~5 steps, a
  // hard one ~11), so asking for steps made the primary control unpredictable.
  // The server has supported chapter mode all along via RunRequest.chapters.
  const [chapterCount, setChapterCount] = useState(1);
  const [running, setRunning] = useState(false);
  const [remoteRunActive, setRemoteRunActive] = useState(false);
  const [liveSteps, setLiveSteps] = useState<RunStep[]>([]);
  const [msg, setMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [recovering, setRecovering] = useState(false);
  const [approving, setApproving] = useState(false);
  const [result, setResult] = useState("done");
  const [score, setScore] = useState<number | "">(90);
  const cancelRef = useRef(false);
  const advancedRef = useRef<HTMLDivElement>(null);

  // The "Điều khiển nâng cao" toggle lives in the page header, but its panel
  // renders at the bottom of this board in the (sticky) right column — often
  // below the fold, so toggling it on looked like "nothing happened". Bring the
  // panel into view when it opens so the click has a visible effect.
  useEffect(() => {
    if (advanced && advancedRef.current) {
      advancedRef.current.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }, [advanced]);

  const stages = useMemo(
    () =>
      STAGE_META.map((s) => ({
        ...s,
        title: t(s.titleKey),
        desc: (STAGE_DESC_KEYS[s.id] ?? []).map((key) => t(key)),
      })),
    [t],
  );

  const describeTask = (task: Task | null): string => {
    if (!task) return "";
    const ch = task.chapter;
    switch (stageOf(task)) {
      case "setup": {
        const key = BOOTSTRAP_KEYS[task.command];
        const label = key ? t(key) : task.command;
        return t("pipeline.task.setup", { label });
      }
      case "outline":
        return t("pipeline.task.outline", { ch: ch ?? 0 });
      case "write":
        return t("pipeline.task.write", { ch: ch ?? 0 });
      case "review":
        return t("pipeline.task.review", { ch: ch ?? 0 });
      case "sync":
        return t("pipeline.task.sync", { ch: ch ?? 0 });
      default:
        return task.task_key;
    }
  };

  const ready = novel.ready_task;
  const dnaReady = novel.dna_ready;
  // A run started from another tab, another device, or a previous session that
  // is still in flight. `running` only knows about THIS tab, so on its own it
  // let a second tab offer a button whose every click the server rejected as
  // alreadyRunning — visible to the user as a dead control.
  const serverRunning =
    remoteRunActive || novel.pipeline_status?.status === "running";
  const anyRunning = running || serverRunning;
  // `dna_ready` only checks that the logline is filled, while the DNA tab's
  // "2 steps to your first chapter" hint keys off ANY remaining placeholder.
  // Measured on 503 real workspaces, 360 sat between the two: the hint said to
  // finish the DNA first, yet the write button was enabled. Writing from a
  // half-filled DNA is what produces chapters that contradict their own canon.
  const dnaIncomplete = dnaReady && !dnaComplete;
  const currentStage = dnaReady ? stageOf(ready) : "dna";
  const target = novel.target_chapters ?? 0;
  const written = novel.chapters_written;
  const stats = (novel.pipeline_status?.stats ?? {}) as Record<string, unknown>;
  const passed = Number(stats.total_chapters_passed ?? 0);
  const breaker = (novel.pipeline_status?.circuit_breaker ?? {}) as Record<string, number>;
  const breakerOpen =
    (breaker.hard_fail_count ?? 0) >= (breaker.max_hard_fail ?? 2) ||
    (breaker.soft_fail_count ?? 0) >= (breaker.max_soft_fail ?? 3) ||
    (breaker.total_attempts ?? 0) >= (breaker.max_total ?? 5);

  const stageOrder = ["dna", "setup", "outline", "write", "review", "sync"];
  const currentIndex = stageOrder.indexOf(currentStage ?? "");

  // Local React state disappears on reload and cannot see jobs started from a
  // different tab. Poll the persistent job record so the primary control
  // reflects the server's actual ability to accept another run.
  useEffect(() => {
    let cancelled = false;
    let timer: number | undefined;

    async function pollRunStatus() {
      try {
        const status = await api.runStatus(novel.name);
        if (!cancelled) {
          setRemoteRunActive(["queued", "running", "pausing"].includes(status.status));
        }
      } catch {
        if (!cancelled) setRemoteRunActive(false);
      }
      if (!cancelled) timer = window.setTimeout(pollRunStatus, JOB_POLL_MS);
    }

    setRemoteRunActive(false);
    void pollRunStatus();
    return () => {
      cancelled = true;
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [novel.name]);

  // Recover orphaned in-progress tasks after a browser close mid-run.
  useEffect(() => {
    if (!dnaReady) return;
    let cancelled = false;
    api
      .resume(novel.name)
      .then(() => {
        if (!cancelled) onChange();
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [novel.name, dnaReady]);

  function isStageDone(stageId: string): boolean {
    if (written >= target && target > 0) return true;
    const idx = stageOrder.indexOf(stageId);
    if (idx === -1) return false;
    return idx < currentIndex;
  }

  /** Shared preflight for both drivers. Returns false when the run must not start. */
  function canStartRun(): boolean {
    if (!dnaReady) {
      setMsg(t("pipeline.msg.noDnaRun"));
      return false;
    }
    // Starting from an unfinished DNA is not recoverable by retrying: the
    // chapters are already written against a half-filled canon.
    if (dnaIncomplete) {
      setMsg(t("pipeline.msg.finishDnaFirst"));
      return false;
    }
    if (serverRunning) {
      setMsg(t("pipeline.msg.busy"));
      return false;
    }
    return true;
  }

  /**
   * Write N chapters as a SERVER-SIDE job (the default driver).
   *
   * The per-step loop below runs inside this tab, so closing it abandoned the
   * run mid-chapter. `/run-async` hands the work to the server and we poll
   * `/run-status`, which is what the mobile app has always done — the run then
   * survives a closed tab, a lock screen or a flaky connection.
   */
  async function runChapters() {
    if (!canStartRun()) return;
    setRunning(true);
    setMsg(null);
    setLiveSteps([]);
    cancelRef.current = false;
    try {
      const started = await api.runAsync(novel.name, { chapters: chapterCount });
      if (started.alreadyRunning) {
        setMsg(t("pipeline.msg.busy"));
        return;
      }
      // Poll until the job leaves an active state. `finally` clears `running`, so
      // an early return here can never leave the button stuck.
      for (;;) {
        await new Promise((resolve) => setTimeout(resolve, JOB_POLL_MS));
        const status = await api.runStatus(novel.name);
        setLiveSteps(status.steps ?? []);
        onChange();
        if (status.status === "completed" || status.status === "failed") {
          setMsg(
            status.error
              ? t("pipeline.msg.error", { message: status.error })
              : t("pipeline.msg.chaptersDone", { count: status.chapters_synced ?? 0 }),
          );
          return;
        }
        if (cancelRef.current) {
          // The job keeps running server-side; only this view stops following it.
          setMsg(t("pipeline.msg.detached"));
          return;
        }
      }
    } catch (err) {
      setMsg(t("pipeline.msg.error", { message: (err as Error).message }));
    } finally {
      setRunning(false);
      onChange();
    }
  }

  /**
   * Drive the pipeline one step at a time from THIS tab (debugging driver).
   *
   * Kept because it is the only view that surfaces each stage as it lands, which
   * is what makes a misbehaving prompt diagnosable. It lives behind the Advanced
   * panel: the run dies with the tab, and its budget is in steps, which is an
   * internal unit an author has no way to convert into chapters.
   */
  async function runAI() {
    if (!canStartRun()) return;
    setRunning(true);
    setMsg(null);
    setLiveSteps([]);
    cancelRef.current = false;
    let done = 0;
    let busyWaits = 0;
    try {
      for (let i = 0; i < maxSteps; i++) {
        if (cancelRef.current) {
          setMsg(t("pipeline.msg.stopped", { count: done }));
          break;
        }
        const r = await api.runStep(novel.name);
        if (r.alreadyRunning) {
          // The server answers a held run lock with HTTP 200 + alreadyRunning,
          // not an error. The old code `continue`d here without a message, a
          // delay, or progress: with the default maxSteps of 1 the loop finished
          // in one silent pass and the click looked like a dead button.
          //
          // Instead: say so, back off, and do NOT spend a step on a rejected
          // attempt (`i -= 1`), so a brief overlap resolves itself. The wait is
          // capped because the lock can be held for minutes by a long step —
          // waiting forever would just be a different kind of frozen UI.
          await api.resume(novel.name);
          onChange();
          busyWaits += 1;
          setMsg(t("pipeline.msg.busy"));
          if (busyWaits > BUSY_MAX_WAITS) break;
          await new Promise((resolve) => setTimeout(resolve, BUSY_RETRY_MS));
          i -= 1;
          continue;
        }
        if (r.step) {
          setLiveSteps((prev) => [...prev, r.step!]);
          done += 1;
          onChange();
          if (r.step.artifacts && r.step.artifacts.length > 0) {
            onViewArtifact(r.step.artifacts[0], r.step.artifacts);
          }
        }
        if (cancelRef.current) {
          setMsg(t("pipeline.msg.stopped", { count: done }));
          break;
        }
        if (r.breaker_open) {
          setMsg(t("pipeline.msg.breaker"));
          break;
        }
        if (r.finished) {
          setMsg(done ? t("pipeline.msg.batchDone") : t("pipeline.msg.noWork"));
          break;
        }
      }
      if (done === maxSteps) setMsg(t("pipeline.msg.ranMax", { count: done }));
    } catch (err) {
      setMsg(t("pipeline.msg.error", { message: (err as Error).message }));
    } finally {
      setRunning(false);
      onChange();
    }
  }

  async function recoverRun() {
    setRecovering(true);
    setMsg(null);
    try {
      await api.recover(novel.name);
      setMsg(t("pipeline.msg.recovered"));
      onChange();
    } catch (err) {
      setMsg(t("pipeline.msg.error", { message: (err as Error).message }));
    } finally {
      setRecovering(false);
    }
  }

  async function approveChapter() {
    const ch = novel.pipeline_status?.current_chapter;
    if (ch == null) return;
    setApproving(true);
    setMsg(null);
    try {
      await api.approveChapter(novel.name, ch);
      setMsg(t("pipeline.msg.approved", { ch }));
      onChange();
      // Approve → continue: the sync gate now accepts the chapter, so drive the
      // run forward automatically instead of making the user press "run" again.
      // Uses the default (chapter/server-job) driver, not the per-step one:
      // recovering from a stuck chapter is exactly when the author is least
      // likely to sit and watch, so the continuation has to survive a closed tab.
      await runChapters();
    } catch (err) {
      setMsg(t("pipeline.msg.error", { message: (err as Error).message }));
    } finally {
      setApproving(false);
    }
  }

  async function run(fn: () => Promise<unknown>, label: string) {
    setBusy(true);
    setMsg(null);
    try {
      await fn();
      setMsg(label);
      onChange();
    } catch (err) {
      setMsg(t("pipeline.msg.error", { message: (err as Error).message }));
    } finally {
      setBusy(false);
    }
  }

  const progressTarget = target ? `/${target}` : "";

  return (
    <div className="panel">
      <div className="next-banner">
        <div className="next-label">
          {anyRunning || aiBusy ? t("pipeline.inProgress") : t("pipeline.nextStep")}
        </div>
        <div className="next-text">
          <span className="next-icon">
            {anyRunning || aiBusy ? (
              <CircleNotch className="spin" size={16} weight="light" />
            ) : (
              <WarningCircle size={16} weight="light" />
            )}
          </span>
          {!dnaReady
            ? t("pipeline.noDna")
            : aiBusy
              ? t("pipeline.writingDna")
              : anyRunning
                ? t("pipeline.runningNow")
                : dnaIncomplete
                  ? t("pipeline.dnaIncomplete")
                  : breakerOpen
                    ? t("pipeline.breakerPause")
                    : ready
                      ? describeTask(ready)
                      : written >= target && target > 0
                        ? t("pipeline.allDone")
                        : t("pipeline.clickAiWrite")}
        </div>
      </div>

      <div className="run-bar">
        <div className="run-left">
          <button
            className="btn run-btn"
            disabled={
              anyRunning || aiBusy || !llmConfigured || breakerOpen || !dnaReady || dnaIncomplete
            }
            onClick={runChapters}
            title={
              aiBusy
                ? t("pipeline.tooltip.aiBusy")
                : anyRunning
                  ? t("pipeline.tooltip.aiRunning")
                  : !dnaReady
                    ? t("pipeline.tooltip.createDnaFirst")
                    : dnaIncomplete
                      ? t("pipeline.tooltip.finishDnaFirst")
                      : llmConfigured
                        ? t("pipeline.tooltip.letAiRun")
                        : t("dna.configureApiFirst")
            }
          >
            {anyRunning || aiBusy ? (
              <>
                <CircleNotch className="spin" size={17} weight="light" /> {t("pipeline.aiWriting")}
              </>
            ) : (
              <>
                <Play size={17} weight="fill" /> {t("pipeline.letAiWrite")}
              </>
            )}
          </button>
          {running && (
            <button
              className="btn ghost"
              onClick={() => {
                cancelRef.current = true;
                setMsg(t("pipeline.msg.stopping"));
              }}
              title={t("pipeline.tooltip.stopAfterStep")}
            >
              <Stop size={15} weight="fill" /> {t("pipeline.stop")}
            </button>
          )}
          {/* The author asks for CHAPTERS, which is the unit they think in and the
              unit the mobile app has always used. "Steps" is an internal pipeline
              concept — a clean chapter is ~5 of them and a hard one ~11, so the
              old control asked the user to convert a number they could not know.
              The server does the conversion (stop_after_chapters), so the count
              stays honest when a chapter needs extra rewrites. */}
          <label className="inline">
            {t("pipeline.chapterCount")}
            <input
              type="number"
              min={1}
              max={MAX_CHAPTERS_PER_RUN}
              value={chapterCount}
              disabled={anyRunning || aiBusy}
              onChange={(e) =>
                setChapterCount(
                  Math.min(MAX_CHAPTERS_PER_RUN, Math.max(1, Number(e.target.value) || 1)),
                )
              }
            />
            {t("pipeline.chapters")}
          </label>
        </div>
        {!llmConfigured && showSettingsLink && (
          <button className="btn ghost" onClick={onOpenSettings}>
            <GearSix size={15} weight="light" /> {t("pipeline.configureApi")}
          </button>
        )}
      </div>

      {breakerOpen && dnaReady && (
        <div className="breaker-recover">
          <div className="breaker-recover-body">
            <span className="breaker-recover-icon">
              <Lifebuoy size={18} weight="light" />
            </span>
            <div>
              <div className="breaker-recover-title">{t("pipeline.breakerTitle")}</div>
              <p className="breaker-recover-desc">{t("pipeline.breakerDesc")}</p>
            </div>
          </div>
          <div className="breaker-recover-actions">
            <button
              className="btn breaker-recover-btn"
              disabled={recovering || approving}
              onClick={recoverRun}
              title={t("pipeline.tooltip.recover")}
            >
              {recovering ? (
                <>
                  <CircleNotch className="spin" size={16} weight="light" /> {t("pipeline.recovering")}
                </>
              ) : (
                <>
                  <ArrowCounterClockwise size={16} weight="light" /> {t("pipeline.recover")}
                  <span className="btn-orb">
                    <ArrowCounterClockwise size={13} weight="light" />
                  </span>
                </>
              )}
            </button>
            {novel.pipeline_status?.current_chapter != null && (
              <button
                className="btn ghost breaker-approve-btn"
                disabled={recovering || approving}
                onClick={approveChapter}
                title={t("pipeline.tooltip.approve")}
              >
                {approving ? (
                  <>
                    <CircleNotch className="spin" size={16} weight="light" />{" "}
                    {t("pipeline.approving")}
                  </>
                ) : (
                  <>
                    <Check size={16} weight="light" />{" "}
                    {t("pipeline.approve", {
                      ch: novel.pipeline_status.current_chapter,
                    })}
                  </>
                )}
              </button>
            )}
          </div>
        </div>
      )}

      <div className="progress-wrap">
        <div className="progress-head">
          <span>{t("pipeline.chapterProgress")}</span>
          <span className="muted">
            {t("pipeline.passedWritten", {
              passed,
              written: String(written),
              target: progressTarget,
            })}
          </span>
        </div>
        <div className="progress-bar">
          <div
            className="progress-fill"
            style={{ "--progress": target ? Math.min(1, passed / target) : 0 } as React.CSSProperties}
          />
        </div>
      </div>

      <div className="journey">
        {stages.map((s, i) => {
          const active = s.id === currentStage;
          const done = isStageDone(s.id);
          // The step immediately after the active one — labelled "next up" so
          // the flow reads clearly as doing-now → next, not a flat list.
          const isNext = !active && !done && i === currentIndex + 1 && currentIndex >= 0;
          const StageIcon = s.icon;
          return (
            <div
              key={s.id}
              className={`stage ${active ? "active" : ""} ${done ? "done" : ""} ${isNext ? "next" : ""}`}
            >
              <div className="stage-rail">
                <div className="stage-dot">{done ? <Check size={14} weight="bold" /> : i + 1}</div>
                {i < stages.length - 1 && <div className="stage-line" />}
              </div>
              <div className="stage-body">
                <div className="stage-title">
                  <StageIcon size={16} weight="light" /> {s.title}
                  {active && <span className="stage-now">{t("pipeline.hereNow")}</span>}
                  {isNext && <span className="stage-next">{t("pipeline.nextUp")}</span>}
                </div>
                <ul
                  className="stage-desc-list"
                  style={{
                    margin: "4px 0 0 0",
                    paddingLeft: "16px",
                    color: "var(--muted)",
                    listStyleType: "disc",
                  }}
                >
                  {s.desc.map((bullet, idx) => (
                    <li key={idx} style={{ marginBottom: "2px", lineHeight: "1.4" }}>
                      {bullet}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}
      </div>

      {(running || liveSteps.length > 0) && (
        <div className="run-report ok">
          <strong>
            {running ? t("pipeline.aiWriting") : t("pipeline.ranSteps", { count: liveSteps.length })}
          </strong>
          {liveSteps.length > 0 && (
            <ul className="run-steps" style={{ listStyle: "none", padding: 0, margin: "8px 0 0 0" }}>
              {liveSteps.map((s, i) => {
                const paths = s.artifacts ?? [];
                const phaseId =
                  ({ "2": "outline", "3": "write", "4": "review", sync: "sync" }[s.phase] ??
                    "setup") as (typeof STAGE_META)[number]["id"];
                const stageTitle = stages.find((x) => x.id === phaseId)?.title ?? s.stage;
                return (
                  <li
                    key={i}
                    className={`outcome-${s.outcome}`}
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      alignItems: "center",
                      gap: "6px",
                      marginBottom: "8px",
                      fontSize: "16px",
                    }}
                  >
                    <span className={`badge phase-${s.phase}`} style={{ fontSize: "14px" }}>
                      {stageTitle}
                    </span>{" "}
                    <span>
                      {s.chapter ? `${t("pipeline.chapterN", { n: s.chapter })} ` : ""}→{" "}
                      {s.outcome === "done" ? t("pipeline.completed") : s.outcome}
                      {s.score != null && ` (${s.score})`}
                    </span>
                    {paths.length > 0 && (
                      <button
                        className="link-btn"
                        style={{
                          fontSize: "14px",
                          padding: "2px 6px",
                          textDecoration: "underline",
                          color: "var(--accent)",
                        }}
                        onClick={() => onViewArtifact(paths[0], paths)}
                      >
                        <FolderOpen size={13} weight="light" /> {t("pipeline.viewInMiddle")}
                      </button>
                    )}
                  </li>
                );
              })}
              {running && (
                <li className="muted" style={{ fontSize: "16px", paddingLeft: "4px" }}>
                  {t("pipeline.writingNext")}
                </li>
              )}
            </ul>
          )}
        </div>
      )}

      {msg && <div className="toast">{msg}</div>}

      {advanced && (
        <div className="advanced" ref={advancedRef}>
          <p className="muted small">{t("pipeline.advancedHint")}</p>
          {/* The per-step driver. It stays because it is the only way to watch a
              single stage's artifact land, which is how a pipeline problem gets
              diagnosed — but it runs inside this tab (closing it abandons the
              run) and it counts in steps, an internal unit. Both make it wrong
              as the default for someone who just wants N chapters. */}
          <div className="step-driver">
            <button
              className="btn ghost"
              disabled={
                anyRunning || aiBusy || !llmConfigured || breakerOpen || !dnaReady || dnaIncomplete
              }
              onClick={runAI}
              title={t("pipeline.tooltip.stepMode")}
            >
              <Play size={15} weight="fill" /> {t("pipeline.runSteps")}
            </button>
            <label className="inline">
              {t("pipeline.maxSteps")}
              <input
                type="number"
                min={1}
                max={60}
                value={maxSteps}
                onChange={(e) => setMaxSteps(Number(e.target.value))}
              />
              {t("pipeline.steps")}
            </label>
          </div>
          <div className="actions">
            <button
              className="btn ghost"
              disabled={busy || !ready}
              onClick={() =>
                run(
                  () => api.planNext(novel.name, true),
                  t("pipeline.msg.accepted", { task: describeTask(ready) }),
                )
              }
            >
              {t("pipeline.acceptNext")}
            </button>
            <button
              className="btn ghost"
              disabled={busy}
              onClick={() => run(() => api.resume(novel.name), t("pipeline.msg.resumed"))}
            >
              {t("pipeline.resume")}
            </button>
            <button
              className="btn ghost"
              disabled={busy}
              onClick={() => run(() => api.rollingSeed(novel.name), t("pipeline.msg.seeded"))}
            >
              {t("pipeline.seedNext")}
            </button>
          </div>
          <div className="record-row">
            <span className="muted small">{t("pipeline.recordResult")}</span>
            <select value={result} onChange={(e) => setResult(e.target.value)}>
              {RESULTS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
            <input
              type="number"
              min={0}
              max={100}
              placeholder={t("pipeline.score")}
              value={score}
              onChange={(e) => setScore(e.target.value === "" ? "" : Number(e.target.value))}
            />
            <button
              className="btn ghost"
              disabled={busy || !ready}
              onClick={() =>
                run(
                  () =>
                    api.recordResult(novel.name, {
                      task_key: ready!.task_key,
                      result,
                      score: score === "" ? undefined : score,
                    }),
                  t("pipeline.msg.recorded"),
                )
              }
            >
              {t("pipeline.record")}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
