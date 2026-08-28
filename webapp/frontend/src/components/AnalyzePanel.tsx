import { useState } from "react";
import { CheckCircle, MagnifyingGlass, WarningCircle, XCircle } from "@phosphor-icons/react";
import { api } from "../api";
import type { AiFlavorResult, LanguageGuardResult } from "../types";

const GENRES = ["xianxia", "urban", "romance", "scifi", "time_travel", "meta_genre"];

export function AnalyzePanel() {
  const [text, setText] = useState("");
  const [genre, setGenre] = useState("xianxia");
  const [secondary, setSecondary] = useState("");
  const [ai, setAi] = useState<AiFlavorResult | null>(null);
  const [guard, setGuard] = useState<LanguageGuardResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function analyze() {
    setBusy(true);
    setErr(null);
    try {
      const [a, g] = await Promise.all([
        api.aiFlavor(text),
        api.languageGuard(text, genre, secondary || undefined),
      ]);
      setAi(a);
      setGuard(g);
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="section-title icon-label"><MagnifyingGlass size={16} weight="light" /> Prose check · voice & language guard</div>
      <textarea
        className="editor"
        rows={10}
        placeholder="Dán đoạn văn cần kiểm tra…"
        value={text}
        onChange={(e) => setText(e.target.value)}
      />
      <div className="analyze-bar">
        <label className="inline">
          Genre
          <select value={genre} onChange={(e) => setGenre(e.target.value)}>
            {GENRES.map((g) => (
              <option key={g}>{g}</option>
            ))}
          </select>
        </label>
        <label className="inline">
          Hybrid +
          <select value={secondary} onChange={(e) => setSecondary(e.target.value)}>
            <option value="">none</option>
            {GENRES.map((g) => (
              <option key={g}>{g}</option>
            ))}
          </select>
        </label>
        <button className="btn" disabled={busy || !text.trim()} onClick={analyze}>
          <MagnifyingGlass size={15} weight="light" /> {busy ? "Đang phân tích…" : "Phân tích"}
        </button>
      </div>

      {err && <div className="error">{err}</div>}

      <div className="analyze-results">
        {ai && (
          <div className={`result-card ${ai.requires_fix ? "bad" : "good"}`}>
            <div className="result-head">
              AI-flavor risk: <strong>{ai.risk_score}</strong> / {ai.threshold}{" "}
              {ai.requires_fix
                ? <><WarningCircle size={15} weight="light" /> cần chỉnh</>
                : <><CheckCircle size={15} weight="light" /> đạt</>}
            </div>
            {ai.violations.length > 0 && (
              <div className="tags">
                {ai.violations.map((v, i) => (
                  <span key={i} className="tag">
                    {v.pattern}
                  </span>
                ))}
              </div>
            )}
            {ai.fix_hints.length > 0 && (
              <ul className="hints">
                {ai.fix_hints.slice(0, 4).map((h, i) => (
                  <li key={i}>{h}</li>
                ))}
              </ul>
            )}
          </div>
        )}
        {guard && (
          <div className={`result-card ${guard.passed ? "good" : "bad"}`}>
            <div className="result-head">
              Language guard: {guard.passed
                ? <><CheckCircle size={15} weight="light" /> sạch</>
                : <><XCircle size={15} weight="light" /> {guard.total_hits} hit(s)</>}
            </div>
            {guard.violations.length > 0 && (
              <div className="tags">
                {guard.violations.map((v, i) => (
                  <span key={i} className={`tag tag-${v.severity}`}>
                    {v.term} ×{v.count}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
