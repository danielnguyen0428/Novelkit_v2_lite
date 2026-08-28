import { useEffect, useState } from "react";
import { BookOpenText, Check, Eye, X } from "@phosphor-icons/react";
import { api } from "../api";
import type { ChapterRow, SyncReport } from "../types";

interface Props {
  novel: string;
  onChange: () => void;
}

export function ChaptersPanel({ novel, onChange }: Props) {
  const [rows, setRows] = useState<ChapterRow[]>([]);
  const [open, setOpen] = useState<number | null>(null);
  const [content, setContent] = useState<{ text: string; review: string | null } | null>(
    null,
  );
  const [syncChapter, setSyncChapter] = useState(1);
  const [report, setReport] = useState<SyncReport | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function load() {
    try {
      setRows(await api.chapters(novel));
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  useEffect(() => {
    load();
    setOpen(null);
    setContent(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [novel]);

  async function view(n: number) {
    setOpen(n);
    setContent(null);
    try {
      const c = await api.chapter(novel, n);
      setContent({ text: c.text, review: c.review });
    } catch (e) {
      setErr((e as Error).message);
    }
  }

  async function doSync() {
    setBusy(true);
    setErr(null);
    setReport(null);
    try {
      const r = await api.sync(novel, syncChapter);
      setReport(r);
      await load();
      onChange();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="panel">
      <div className="sync-bar">
        <span className="section-title">Sync a chapter</span>
        <input
          type="number"
          min={1}
          value={syncChapter}
          onChange={(e) => setSyncChapter(Number(e.target.value))}
        />
        <button className="btn" disabled={busy} onClick={doSync}>
          {busy ? "Syncing…" : "Commit / sync"}
        </button>
      </div>

      {report && (
        <div className={`sync-report ${report.blocked ? "blocked" : "ok"}`}>
          <strong>
            Chapter {report.chapter}: {report.blocked ? "BLOCKED" : "synced"}
          </strong>
          {" — "}gate {report.gate_passed ? "passed" : "failed"} (
          {report.gate_outcome ?? "?"}, score {report.gate_score ?? "—"})
          {report.idempotent && " · idempotent"}
          {report.error && <div className="error">{report.error}</div>}
          {report.blocking_issues.length > 0 && (
            <ul className="issues">
              {report.blocking_issues.map((i, idx) => (
                <li key={idx}>
                  <code>{i.code}</code> {i.message}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {err && <div className="error">{err}</div>}

      <table className="chapters">
        <thead>
          <tr>
            <th>#</th>
            <th>Words</th>
            <th>Review</th>
            <th>Committed</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={5}>
                <div className="table-empty">
                  <span className="empty-icon"><BookOpenText size={21} weight="light" /></span>
                  <strong>Chưa có chương nào</strong>
                  <span>Chạy pipeline để dựng dàn ý và viết bản thảo đầu tiên.</span>
                </div>
              </td>
            </tr>
          )}
          {rows.map((r) => (
            <tr key={r.chapter}>
              <td>{r.chapter}</td>
              <td>{r.words}</td>
              <td>{r.has_review ? <Check size={15} weight="bold" /> : "—"}</td>
              <td>{r.committed ? <Check size={15} weight="bold" /> : "—"}</td>
              <td>
                <button className="btn-mini" onClick={() => view(r.chapter)}>
                  <Eye size={14} weight="light" /> xem
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {open !== null && (
        <div className="reader">
          <div className="reader-head">
            <span>Chapter {open}</span>
            <button className="btn-mini" onClick={() => setOpen(null)}>
              <X size={14} weight="light" /> đóng
            </button>
          </div>
          {content ? (
            <>
              <pre className="prose">{content.text}</pre>
              {content.review && (
                <details>
                  <summary>Review</summary>
                  <pre className="prose">{content.review}</pre>
                </details>
              )}
            </>
          ) : (
            <div className="reader-loading" aria-label="Đang tải chương">
              <span />
              <span />
              <span />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
