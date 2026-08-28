import { useCallback, useEffect, useState } from "react";
import {
  CheckCircle,
  Command,
  Compass,
  SlidersHorizontal,
  Stethoscope,
  SteeringWheel,
  WarningCircle,
} from "@phosphor-icons/react";
import { api } from "../api";
import { useT } from "../i18n/I18nProvider";
import type { DiagFinding, LongformStatus, SteerResult } from "../types";

interface Props {
  novel: string;
  onChange?: () => void;
}

/**
 * NovelCLI — web surface for the long-form GA capabilities (compass, steer,
 * diagnostics, reminder/stop-guard, feature flags). Mirrors the `novelkit`
 * CLI's new commands. All sections degrade gracefully: reads never error on a
 * novel that hasn't opted into long-form, and each mutating action is flag-aware.
 */
export function NovelCliPanel({ novel, onChange }: Props) {
  const t = useT();

  const [status, setStatus] = useState<LongformStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState<string | null>(null);

  const [steerText, setSteerText] = useState("");
  const [steerBusy, setSteerBusy] = useState(false);
  const [steerResult, setSteerResult] = useState<SteerResult | null>(null);

  const [findings, setFindings] = useState<DiagFinding[] | null>(null);
  const [diagBusy, setDiagBusy] = useState(false);
  const [redact, setRedact] = useState(false);

  const [curChapter, setCurChapter] = useState(0);
  const [targetChapters, setTargetChapters] = useState(300);
  const [migrateBusy, setMigrateBusy] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      setStatus(await api.longformStatus(novel));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [novel]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const sendSteer = useCallback(async () => {
    const text = steerText.trim();
    if (!text) return;
    setSteerBusy(true);
    setErr(null);
    try {
      const res = await api.steer(novel, text);
      setSteerResult(res);
      setSteerText("");
      await refresh();
      onChange?.();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setSteerBusy(false);
    }
  }, [novel, steerText, refresh, onChange]);

  const runDiag = useCallback(async () => {
    setDiagBusy(true);
    setErr(null);
    try {
      setFindings(await api.diagnostics(novel, redact));
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setDiagBusy(false);
    }
  }, [novel, redact]);

  const runMigrate = useCallback(async () => {
    setMigrateBusy(true);
    setErr(null);
    try {
      await api.compassMigrate(novel, {
        current_chapter: curChapter,
        target_chapters: targetChapters,
      });
      await refresh();
      onChange?.();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setMigrateBusy(false);
    }
  }, [novel, curChapter, targetChapters, refresh, onChange]);

  if (loading && !status) {
    return (
      <div className="panel">
        <div className="muted">{t("novelcli.loading")}</div>
      </div>
    );
  }

  const flags = status?.flags ?? {};
  const compass = status?.compass ?? null;
  const arcs = status?.arc_map?.arcs ?? [];
  const stopGuard = status?.stop_guard ?? null;

  return (
    <div className="panel novelcli">
      <div className="spread">
        <span className="section-title icon-label">
          <Command size={16} weight="light" /> NovelCLI · {t("novelcli.subtitle")}
        </span>
        <button className="btn btn-mini" onClick={refresh}>
          {t("novelcli.refresh")}
        </button>
      </div>

      {err && <div className="error">{err}</div>}

      {/* Mode & feature flags */}
      <div className="novelcli-block">
        <div className="novelcli-mode">
          <span className="muted">{t("novelcli.modeLabel")}:</span>{" "}
          <code>{status?.mode ?? t("novelcli.modeLegacy")}</code>
        </div>
        <div className="section-title small icon-label">
          <SlidersHorizontal size={14} weight="light" /> {t("novelcli.flagsTitle")}
        </div>
        <div className="flag-grid">
          {Object.entries(flags).map(([name, on]) => (
            <span key={name} className={`flag-pill ${on ? "on" : "off"}`}>
              {name} · {on ? t("novelcli.on") : t("novelcli.off")}
            </span>
          ))}
        </div>
      </div>

      {/* Story compass + arc map + migrate */}
      <div className="novelcli-block">
        <div className="section-title icon-label">
          <Compass size={15} weight="light" /> {t("novelcli.compassTitle")}
        </div>
        {compass ? (
          <div className="compass-body">
            <div>
              <span className="muted">{t("novelcli.endingDirection")}:</span>{" "}
              {String(compass.ending_direction || "—")}
            </div>
            <div>
              <span className="muted">{t("novelcli.scale")}:</span>{" "}
              {compass.scale_estimate?.chapters ?? "—"}
            </div>
            <div className="section-title small">
              {t("novelcli.arcsTitle")} ({arcs.length})
            </div>
            {arcs.length === 0 ? (
              <div className="muted">{t("novelcli.noArcs")}</div>
            ) : (
              <ul className="arc-list">
                {arcs.map((a) => (
                  <li key={a.arc_id}>
                    <code>{a.arc_id}</code> · {a.arc_type} · ch {a.start_chapter}–
                    {a.end_chapter ?? "…"} <span className="badge">{a.status}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ) : (
          <div className="muted">{t("novelcli.compassNone")}</div>
        )}
        <div className="novelcli-form">
          <label className="inline">
            {t("novelcli.currentChapter")}
            <input
              type="number"
              min={0}
              value={curChapter}
              onChange={(e) => setCurChapter(Number(e.target.value))}
            />
          </label>
          <label className="inline">
            {t("novelcli.targetChapters")}
            <input
              type="number"
              min={1}
              value={targetChapters}
              onChange={(e) => setTargetChapters(Number(e.target.value))}
            />
          </label>
          <button
            className="btn btn-mini"
            disabled={migrateBusy || !targetChapters || targetChapters < 1}
            onClick={runMigrate}
          >
            <Compass size={14} weight="light" />{" "}
            {migrateBusy ? t("novelcli.working") : t("novelcli.migrate")}
          </button>
        </div>
      </div>

      {/* Realtime steer */}
      <div className="novelcli-block">
        <div className="section-title icon-label">
          <SteeringWheel size={15} weight="light" /> {t("novelcli.steerTitle")}
          {!flags.steer && <span className="pill warn">{t("novelcli.featureOff")}</span>}
        </div>
        <div className="novelcli-form">
          <input
            className="steer-input"
            type="text"
            placeholder={t("novelcli.steerPlaceholder")}
            value={steerText}
            onChange={(e) => setSteerText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") sendSteer();
            }}
          />
          <button
            className="btn"
            disabled={steerBusy || !steerText.trim()}
            onClick={sendSteer}
          >
            {steerBusy ? t("novelcli.working") : t("novelcli.steerSend")}
          </button>
        </div>
        {steerResult && (
          <div className={`result-card ${steerResult.applied ? "good" : ""}`}>
            {t("novelcli.route")}: <code>{steerResult.route}</code> ·{" "}
            {steerResult.applied ? t("novelcli.applied") : t("novelcli.notApplied")}
            {steerResult.affected_chapters.length > 0 && (
              <> · ch {steerResult.affected_chapters.join(", ")}</>
            )}
          </div>
        )}
        {status?.pending_steer && (
          <div className="muted small">
            {t("novelcli.pendingSteer")}: <code>{status.pending_steer.route}</code> —{" "}
            {status.pending_steer.raw_text}
          </div>
        )}
      </div>

      {/* Creative-health diagnostics */}
      <div className="novelcli-block">
        <div className="section-title icon-label">
          <Stethoscope size={15} weight="light" /> {t("novelcli.diagTitle")}
        </div>
        <div className="novelcli-form">
          <label className="inline checkbox">
            <input
              type="checkbox"
              checked={redact}
              onChange={(e) => setRedact(e.target.checked)}
            />{" "}
            {t("novelcli.redact")}
          </label>
          <button className="btn btn-mini" disabled={diagBusy} onClick={runDiag}>
            <Stethoscope size={14} weight="light" />{" "}
            {diagBusy ? t("novelcli.working") : t("novelcli.diagRun")}
          </button>
        </div>
        {findings !== null &&
          (findings.length === 0 ? (
            <div className="doctor-banner good">
              <CheckCircle size={16} weight="light" /> {t("novelcli.diagClean")}
            </div>
          ) : (
            <ul className="issues">
              {findings.map((f, i) => (
                <li key={i} className={`sev-${f.severity}`}>
                  <span className={`badge sev-${f.severity}`}>{f.dimension}</span>
                  <code>{f.code}</code>
                  {f.suggestion && <div className="hint">{f.suggestion}</div>}
                </li>
              ))}
            </ul>
          ))}
      </div>

      {/* Reminder + stop-guard */}
      <div className="novelcli-block">
        <div className="section-title icon-label">
          <WarningCircle size={15} weight="light" /> {t("novelcli.reminderTitle")}
        </div>
        {stopGuard && (
          <div className={`doctor-banner ${stopGuard.blocked ? "bad" : "good"}`}>
            {stopGuard.blocked ? (
              <>
                <WarningCircle size={16} weight="light" /> {t("novelcli.stopBlocked")}
              </>
            ) : (
              <>
                <CheckCircle size={16} weight="light" /> {t("novelcli.stopAllowed")}
              </>
            )}{" "}
            <code>{stopGuard.reason}</code>
          </div>
        )}
        {status?.reminder && <pre className="prose reminder-box">{status.reminder}</pre>}
      </div>
    </div>
  );
}
