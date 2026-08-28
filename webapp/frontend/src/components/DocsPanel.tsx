import { useCallback, useEffect, useState } from "react";
import {
  ArrowClockwise,
  BookOpenText,
  Books,
  Brain,
  CircleNotch,
  ClockCounterClockwise,
  FileText,
  GlobeHemisphereWest,
  ListBullets,
  MagnifyingGlass,
  PenNib,
  Stack,
  User,
  WarningCircle,
} from "@phosphor-icons/react";
import { api } from "../api";
import type { DocEntry } from "../types";

interface Props {
  novel: string;
  onViewArtifact: (path: string, allPaths: string[]) => void;
}

const GROUP_LABEL: Record<string, string> = {
  database: "Cơ sở dữ liệu · nhân vật / thế giới / tuyến truyện",
  outlines: "Dàn ý chương mục",
  memory: "Trí nhớ & hồi ức",
  root: "Tài liệu kế hoạch & kịch bản",
};

function getDocIcon(path: string, label: string) {
  const p = path.toLowerCase();
  const l = label.toLowerCase();
  if (p.includes("character") || l.includes("nhân vật")) return User;
  if (p.includes("world") || l.includes("thế giới") || l.includes("bối cảnh")) return GlobeHemisphereWest;
  if (p.includes("thread") || l.includes("tuyến") || l.includes("mạch")) return Stack;
  if (p.includes("timeline") || l.includes("dòng thời gian") || l.includes("mốc")) return ClockCounterClockwise;
  if (p.includes("master") || l.includes("tổng")) return BookOpenText;
  if (p.includes("outline") || l.includes("dàn ý")) return ListBullets;
  if (p.includes("memory") || l.includes("trí nhớ") || l.includes("hồi ức")) return Brain;
  if (p.includes("review") || l.includes("đánh giá") || l.includes("chấm")) return MagnifyingGlass;
  if (p.includes("chapter") || l.includes("chương")) return PenNib;
  return FileText;
}

export function DocsPanel({ novel, onViewArtifact }: Props) {
  const [docs, setDocs] = useState<DocEntry[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState<string | null>(null);

  const loadDocs = useCallback(() => {
    api
      .docs(novel)
      .then(setDocs)
      .catch((e) => setErr((e as Error).message));
  }, [novel]);

  useEffect(() => {
    loadDocs();
  }, [loadDocs]);

  async function regenerate(path: string) {
    setRegenerating(path);
    setErr(null);
    try {
      const res = await api.regenerateDoc(novel, path);
      if (res.is_stub) {
        setErr(
          `Tạo lại "${path}" chưa thành công (provider có thể đang bận). Thử lại sau giây lát.`,
        );
      }
      loadDocs();
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setRegenerating(null);
    }
  }

  // Group docs by their top-level folder.
  const groups: Record<string, DocEntry[]> = {};
  docs.forEach((d) => {
    (groups[d.group] ??= []).push(d);
  });

  return (
    <div className="panel">
      <div className="section-title icon-label">
        <Books size={16} weight="light" /> Tài liệu sáng tác · {docs.length} mục
      </div>
      {err && <div className="error">{err}</div>}
      {docs.length === 0 && (
        <div className="panel-empty">
          <span className="empty-icon"><Books size={21} weight="light" /></span>
          <strong>Kho tài liệu đang chờ nội dung</strong>
          <span>Nhân vật, thế giới và dàn ý sẽ xuất hiện sau các bước khởi tạo.</span>
        </div>
      )}

      {Object.entries(groups).map(([group, items]) => (
        <div className="doc-group" key={group}>
          <div className="doc-group-head">{GROUP_LABEL[group] ?? group}</div>
          <ul className="doc-list">
            {items.map((d) => (
              <li key={d.path}>
                {(() => {
                  const DocIcon = getDocIcon(d.path, d.label);
                  const busy = regenerating === d.path;
                  return (
                <div className={d.is_stub ? "doc-item-row is-stub" : "doc-item-row"}>
                  <button
                    className="doc-item"
                    onClick={() => onViewArtifact(d.path, [d.path])}
                  >
                    <span className="doc-icon">
                      <DocIcon size={18} weight="light" />
                    </span>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-start", flex: 1, gap: "2px" }}>
                      <span className="doc-name">
                        {d.label}
                        {d.is_stub && (
                          <span className="doc-stub-tag">
                            <WarningCircle size={12} weight="fill" /> chưa có nội dung
                          </span>
                        )}
                      </span>
                      <span className="muted small" style={{ fontSize: "14px" }}>{d.path} · {d.words} từ</span>
                    </div>
                  </button>
                  {d.is_stub && (
                    <button
                      className="btn btn--sm doc-regen-btn"
                      disabled={busy}
                      onClick={() => regenerate(d.path)}
                      title="Gọi AI tạo lại nội dung cho tệp này"
                    >
                      {busy ? (
                        <><CircleNotch className="spin" size={15} weight="light" /> Đang tạo…</>
                      ) : (
                        <><ArrowClockwise size={15} weight="light" /> Tạo lại nội dung</>
                      )}
                    </button>
                  )}
                </div>
                  );
                })()}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}
