import type { NovelBrief } from "../types";
import { BookOpenText, Books, Plus, Trash } from "@phosphor-icons/react";
import { useT } from "../i18n/I18nProvider";

interface Props {
  novels: NovelBrief[];
  selected: string | null;
  onSelect: (name: string) => void;
  onHome: () => void;
  onNew: () => void;
  onDelete: (name: string) => void;
}

export function Sidebar({
  novels,
  selected,
  onSelect,
  onHome,
  onNew,
  onDelete,
}: Props) {
  const t = useT();

  return (
    <aside className={novels.length === 0 ? "sidebar sidebar--empty" : "sidebar"}>
      <a
        className="brand brand-link"
        href="/studio"
        aria-label={t("nav.homeAria")}
        onClick={(e) => {
          e.preventDefault();
          onHome();
        }}
      >
        <span className="brand-mark"><BookOpenText size={20} weight="light" /></span>
        <div>
          <div className="brand-title">NovelKit</div>
        </div>
      </a>

      <div className="section-head">
        <span><Books size={14} weight="light" /> {t("nav.library")}</span>
        <button className="btn-mini" onClick={onNew}>
          <Plus size={14} weight="light" /> {t("nav.new")}
        </button>
      </div>

      <ul className="novel-list">
        {novels.length === 0 && <li className="muted">{t("nav.noNovels")}</li>}
        {novels.map((n) => (
          <li
            key={n.name}
            className={n.name === selected ? "active" : ""}
          >
            <div className="novel-row">
              <button
                type="button"
                className="novel-main novel-select"
                aria-pressed={n.name === selected}
                onClick={() => onSelect(n.name)}
              >
                <div className="novel-name">{n.title || n.name}</div>
                <div className="novel-meta">
                  <span className={`dot dot-${n.status}`} /> {n.status}
                  {" · "}
                  {n.chapters_written}
                  {n.target_chapters ? `/${n.target_chapters}` : ""} ch
                </div>
              </button>
              <button
                type="button"
                className="novel-del"
                title={t("nav.deleteNovel")}
                aria-label={t("nav.deleteNovelAria", { name: n.name })}
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(n.name);
                }}
              >
                <Trash size={15} weight="light" />
              </button>
            </div>
          </li>
        ))}
      </ul>
    </aside>
  );
}
