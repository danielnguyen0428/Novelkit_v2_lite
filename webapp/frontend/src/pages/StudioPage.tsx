import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpenText,
  BracketsCurly,
  CircleNotch,
  Command,
  FileText,
  FirstAid,
  FolderOpen,
  GearSix,
  Graph,
  MagicWand,
  PencilSimple,
  Plus,
  SlidersHorizontal,
  Sparkle,
  WarningCircle,
  X,
} from "@phosphor-icons/react";
import { api } from "../api";
import { Sidebar } from "../components/Sidebar";
import { PipelineBoard } from "../components/PipelineBoard";
import { ChaptersPanel } from "../components/ChaptersPanel";
import { DocsPanel } from "../components/DocsPanel";
import { DoctorPanel } from "../components/DoctorPanel";
import { AnalyzePanel } from "../components/AnalyzePanel";
import { NovelCliPanel } from "../components/NovelCliPanel";
import { GraphPanel } from "../components/GraphPanel";
import { SettingsModal } from "../components/SettingsModal";
import { ProviderStatusPill } from "../components/ProviderStatusPill";
import { CreateNovelModal } from "../components/CreateNovelModal";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { useT } from "../i18n/I18nProvider";
import { useDocumentMeta } from "../lib/seo";
import type { NovelBrief, NovelDetail, ProviderSettings } from "../types";

type Tab = "dna" | "chapters" | "docs" | "doctor" | "analyze" | "novelcli" | "graph";

const TAB_ICONS = {
  dna: BracketsCurly,
  chapters: BookOpenText,
  docs: FileText,
  doctor: FirstAid,
  analyze: Sparkle,
  novelcli: Command,
  graph: Graph,
};

// Persist the open novel/tab across a browser refresh so F5 resumes the run.
const SELECTED_NOVEL_KEY = "novelkit.studio.selectedNovel";
const SELECTED_TAB_KEY = "novelkit.studio.selectedTab";

export function StudioPage() {
  const t = useT();

  const TAB_LABELS: Record<Tab, string> = useMemo(
    () => ({
      dna: t("tab.dna"),
      chapters: t("tab.chapters"),
      docs: t("tab.docs"),
      doctor: t("tab.doctor"),
      analyze: t("tab.analyze"),
      novelcli: t("tab.novelcli"),
      graph: t("tab.graph"),
    }),
    [t],
  );

  useDocumentMeta({
    title: "NovelKit V2-lite — Studio local",
    description: "Studio viết tiểu thuyết chạy hoàn toàn trên máy cá nhân.",
    noindex: true,
  });

  const [novels, setNovels] = useState<NovelBrief[]>([]);
  // Persist the open novel/tab so a browser refresh (F5) resumes where the user
  // was instead of selecting another manuscript.
  const [selected, setSelected] = useState<string | null>(
    () => {
      try {
        return localStorage.getItem(SELECTED_NOVEL_KEY) || null;
      } catch {
        return null;
      }
    },
  );
  // Mirror of ``selected`` for async callbacks (enrich) that must not capture a
  // stale value — right after create, ``selected`` is briefly null.
  const selectedRef = useRef<string | null>(null);
  useEffect(() => {
    selectedRef.current = selected;
  }, [selected]);
  const [detail, setDetail] = useState<NovelDetail | null>(null);
  const [tab, setTab] = useState<Tab>(() => {
    try {
      return (localStorage.getItem(SELECTED_TAB_KEY) as Tab) || "dna";
    } catch {
      return "dna";
    }
  });
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [advanced, setAdvanced] = useState(false);
  const [enriching, setEnriching] = useState(false);
  const [booting, setBooting] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [viewingArtifacts, setViewingArtifacts] = useState<{
    paths: string[];
    selectedPath: string;
    text: string;
  } | null>(null);
  // Documents open in read-only mode by default; the user must press "Sửa" to
  // edit. ``artifactOriginal`` keeps the loaded text so "Hủy" can discard edits.
  const [artifactEditing, setArtifactEditing] = useState(false);
  const [artifactOriginal, setArtifactOriginal] = useState("");

  const viewArtifact = useCallback(
    async (path: string, allPaths: string[] = [path]) => {
      if (!selected) return;
      try {
        const a = await api.artifact(selected, path);
        setViewingArtifacts({
          paths: allPaths,
          selectedPath: path,
          text: a.text,
        });
        // Always open a freshly loaded / switched file in view mode.
        setArtifactEditing(false);
        setArtifactOriginal(a.text);
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [selected],
  );

  const refreshSettings = useCallback(async () => {
    try {
      setSettings(await api.getSettings());
    } catch {
      /* settings endpoint optional */
    }
  }, []);

  const openCreate = useCallback(() => {
    setCreateOpen(true);
  }, []);

  const openSettings = useCallback(() => {
    setSettingsOpen(true);
  }, []);

  const refreshNovels = useCallback(async () => {
    try {
      setNovels(await api.listNovels());
    } catch (e) {
      const message = (e as Error).message;
      setError(message);
    }
  }, []);

  const refreshDetail = useCallback(async (options?: { silent?: boolean }) => {
    if (!selected) {
      setDetail(null);
      setDetailLoading(false);
      return;
    }
    const silent = options?.silent ?? false;
    if (!silent) setDetailLoading(true);
    try {
      setDetail(await api.novel(selected));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      if (!silent) setDetailLoading(false);
    }
  }, [selected]);

  useEffect(() => {
    (async () => {
      await Promise.all([refreshNovels(), refreshSettings()]);
      setBooting(false);
    })();
  }, [refreshNovels, refreshSettings]);

  useEffect(() => {
    refreshDetail();
  }, [refreshDetail]);

  // Persist the open novel + tab so an F5 resumes the same view.
  useEffect(() => {
    try {
      if (selected) localStorage.setItem(SELECTED_NOVEL_KEY, selected);
      else localStorage.removeItem(SELECTED_NOVEL_KEY);
    } catch {
      /* storage unavailable (private mode) — persistence is best-effort */
    }
  }, [selected]);

  useEffect(() => {
    try {
      localStorage.setItem(SELECTED_TAB_KEY, tab);
    } catch {
      /* best-effort */
    }
  }, [tab]);

  // Enter the working surface immediately: keep a valid restored selection, or
  // open the first manuscript. The empty state is reserved for an empty library.
  useEffect(() => {
    if (booting) return;
    if (novels.length === 0) {
      if (selected !== null) setSelected(null);
      return;
    }
    if (selected === null || !novels.some((n) => n.name === selected)) {
      setSelected(novels[0].name);
    }
  }, [booting, novels, selected]);

  const onChange = useCallback(() => {
    refreshDetail({ silent: true });
    refreshNovels();
  }, [refreshDetail, refreshNovels]);

  const onDelete = useCallback(
    async (name: string) => {
      if (!window.confirm(t("confirm.deleteNovel", { name }))) {
        return;
      }
      try {
        await api.deleteNovel(name);
        const remaining = novels.filter((novel) => novel.name !== name);
        setNovels(remaining);
        if (selected === name) setSelected(remaining[0]?.name ?? null);
        void refreshNovels();
      } catch (e) {
        setError((e as Error).message);
      }
    },
    [novels, selected, refreshNovels, t],
  );

  const enrichNovel = useCallback(
    async (novelName: string) => {
      setEnriching(true);
      setError(null);
      try {
        const res = await api.enrichDnaAll(novelName);
        // Refresh THIS novel's detail directly. Using the selected-bound
        // refreshDetail here would capture a stale ``selected`` (null right
        // after create) and wipe the detail back to the empty state. Only
        // apply if the user is still viewing this novel.
        if (selectedRef.current === novelName) {
          try {
            setDetail(await api.novel(novelName));
          } catch {
            /* detail refresh is best-effort; enrich already persisted */
          }
        }
        const missing = res.missing_count ?? 0;
        if (missing > 0) {
          const batches = res.batches_failed
            ? t("dna.batchesFailed", { count: res.batches_failed })
            : "";
          setError(t("dna.enrichPartial", { missing, batches }));
        }
      } catch (e) {
        setError((e as Error).message);
      } finally {
        setEnriching(false);
      }
    },
    [t],
  );

  const onEnrich = useCallback(async () => {
    if (!selected) return;
    await enrichNovel(selected);
  }, [selected, enrichNovel]);

  // The DNA still has unfilled slots when a "tự sinh" placeholder remains
  // (either the "_(tự sinh)_" bullet form or the "[Tự sinh]" pacing form). Once
  // none are left the enrich button is hidden — the DNA is complete.
  const dnaHasPlaceholders = useMemo(() => {
    const dna = detail?.dna ?? "";
    return dna.includes("(tự sinh") || dna.includes("[Tự sinh]");
  }, [detail?.dna]);

  return (
    <div className="app">
      <Sidebar
        novels={novels}
        selected={selected}
        onSelect={setSelected}
        onHome={() => setSelected(novels[0]?.name ?? null)}
        onNew={openCreate}
        onDelete={onDelete}
      />

      <main className="main">
        <div className="topbar">
          <div className="topbar-context">
            <span className="live-dot" aria-hidden="true" />
            <span>{t("topbar.creativeRuntime")}</span>
          </div>
          <div className="topbar-actions">
            <ProviderStatusPill settings={settings} onOpenSettings={openSettings} />
            <LanguageSwitcher />
          </div>
        </div>

        {!settings?.configured && (
          <div className="onboard-nudge top-notice" role="status">
            <GearSix size={17} weight="light" />
            <span>
              Kết nối model để bắt đầu bằng API key của bạn. Cấu hình được lưu
              riêng trong máy local này.
            </span>
            <button className="btn btn--sm" onClick={openSettings}>
              Kết nối model
            </button>
          </div>
        )}

        {error && (
          <div className="error banner" onClick={() => setError(null)}>
            {error} {t("topbar.errorDismiss")}
          </div>
        )}

        {booting || detailLoading || (!selected && novels.length > 0) ? (
          <div className="studio-skeleton" aria-label={t("studio.loadingAria")}>
            <div className="skeleton-line short" />
            <div className="skeleton-line title" />
            <div className="skeleton-grid">
              <div className="skeleton-sheet" />
              <div className="skeleton-rail" />
            </div>
          </div>
        ) : !detail ? (
          <section className="studio-empty" aria-labelledby="studio-empty-title">
            <div className="kicker">
              <span /> Studio
            </div>
            <h1 id="studio-empty-title">{t("nav.noNovels")}</h1>
            <button type="button" className="btn btn-primary" onClick={openCreate}>
              <Plus size={16} weight="light" />
              {t("studio.createWork")}
            </button>
          </section>
        ) : (
          <>
            <header className="main-head">
              <div>
                <div className="kicker">
                  <span /> {t("studio.activeManuscript")}
                </div>
                <h1>{detail.title || detail.name}</h1>
                <div className="manuscript-meta">
                  <span className={`status-mark status-${detail.status}`} />
                  <span>{detail.status}</span>
                  <span className="meta-divider" />
                  <span>
                    {detail.chapters_written}
                    {detail.target_chapters ? `/${detail.target_chapters}` : ""} {t("studio.chapters")}
                  </span>
                  {detail.doctor.blocking_issues.length > 0 && (
                    <span className="pill bad">
                      <WarningCircle size={13} weight="light" />
                      {detail.doctor.blocking_issues.length} {t("studio.blocking")}
                    </span>
                  )}
                </div>
              </div>
              <button
                className={advanced ? "btn ghost btn-adv on" : "btn ghost btn-adv"}
                onClick={() => setAdvanced((a) => !a)}
              >
                <SlidersHorizontal size={16} weight="light" />
                {t("studio.advancedControls")}
              </button>
            </header>

            <div className="studio">
              <section className="studio-mid">
                <nav className="tabs">
                  {(["dna", "chapters", "docs", "doctor", "analyze", "novelcli", "graph"] as Tab[]).map((t) =>
                    (() => {
                      const TabIcon = TAB_ICONS[t];
                      return (
                        <button
                          key={t}
                          className={tab === t && !viewingArtifacts ? "tab active" : "tab"}
                          onClick={() => {
                            setTab(t);
                            setViewingArtifacts(null);
                          }}
                        >
                          <TabIcon size={15} weight="light" />
                          {TAB_LABELS[t]}
                        </button>
                      );
                    })(),
                  )}
                </nav>

                {viewingArtifacts && (
                  <div className="panel artifact-editor">
                    <div className="spread artifact-editor-head">
                      <span className="section-title icon-label">
                        <FolderOpen size={16} weight="light" /> {t("artifact.docTitle")}{" "}
                        <code>{viewingArtifacts.selectedPath}</code>
                      </span>
                      <div className="row-mini">
                        {!artifactEditing ? (
                          <button
                            className="btn btn-mini"
                            onClick={() => setArtifactEditing(true)}
                          >
                            <PencilSimple size={14} weight="light" /> {t("artifact.edit")}
                          </button>
                        ) : (
                          <button
                            className="btn btn-mini"
                            onClick={() => {
                              // Discard edits and return to view mode.
                              setViewingArtifacts({
                                ...viewingArtifacts,
                                text: artifactOriginal,
                              });
                              setArtifactEditing(false);
                            }}
                          >
                            <X size={14} weight="light" /> {t("artifact.cancel")}
                          </button>
                        )}
                        <button className="btn btn-mini" onClick={() => setViewingArtifacts(null)}>
                          <X size={14} weight="light" /> {t("artifact.close")}
                        </button>
                      </div>
                    </div>

                    {viewingArtifacts.paths.length > 1 && (
                      <div className="tabs artifact-tabs">
                        {viewingArtifacts.paths.map((p) => (
                          <button
                            key={p}
                            className={`tab ${viewingArtifacts.selectedPath === p ? "active" : ""}`}
                            onClick={() => viewArtifact(p, viewingArtifacts.paths)}
                          >
                            {p.split("/").pop()}
                          </button>
                        ))}
                      </div>
                    )}

                    <textarea
                      className={`artifact-textarea${artifactEditing ? "" : " readonly"}`}
                      value={viewingArtifacts.text}
                      readOnly={!artifactEditing}
                      onChange={(e) =>
                        setViewingArtifacts({ ...viewingArtifacts, text: e.target.value })
                      }
                      style={{
                        resize: "vertical",
                      }}
                    />

                    {artifactEditing && (
                      <div className="artifact-actions">
                        {detail.chapters_written > 0 && (
                          <span className="muted small warning-copy">
                            <WarningCircle size={15} weight="light" /> {t("artifact.editWarning")}
                          </span>
                        )}
                        <button
                          className="btn"
                          onClick={async () => {
                            try {
                              await api.writeArtifact(
                                detail.name,
                                viewingArtifacts.selectedPath,
                                viewingArtifacts.text,
                              );
                              // Persist the saved text as the new baseline and
                              // return to read-only view mode.
                              setArtifactOriginal(viewingArtifacts.text);
                              setArtifactEditing(false);
                              alert(t("artifact.saved"));
                            } catch (e) {
                              alert(t("artifact.saveError", { message: (e as Error).message }));
                            }
                          }}
                        >
                          {t("artifact.save")}
                        </button>
                      </div>
                    )}
                  </div>
                )}

                {!viewingArtifacts && tab === "chapters" && (
                  <ChaptersPanel novel={detail.name} onChange={onChange} />
                )}
                {!viewingArtifacts && tab === "docs" && (
                  <DocsPanel novel={detail.name} onViewArtifact={(path, all) => viewArtifact(path, all)} />
                )}
                {!viewingArtifacts && tab === "dna" && (
                  <div className="panel">
                    <div className="spread">
                      <div className="section-title">PROJECT_DNA.md</div>
                      {/* Hide the enrich button once the DNA is complete (no
                          placeholder left). While enriching, the button is
                          replaced by the "Writing" status pill below. */}
                      {!enriching && dnaHasPlaceholders && (
                        <button
                          // While placeholders remain this is the ONLY action that
                          // moves the novel forward — the write button in the right
                          // column is disabled until it completes. Draw the eye here
                          // so the disabled control does not read as a broken one.
                          className={`btn btn--sm${
                            settings?.configured ? " btn--attention" : ""
                          }`}
                          disabled={!settings?.configured}
                          onClick={onEnrich}
                          title={
                            settings?.configured
                              ? t("dna.enrichTitle")
                              : t("dna.configureApiFirst")
                          }
                        >
                          <MagicWand size={16} weight="light" />
                          {t("dna.enrichButton")}
                        </button>
                      )}
                    </div>
                    {enriching && (
                      <div className="dna-writing" role="status" aria-live="polite">
                        <span className="dna-writing-orb" aria-hidden="true">
                          <CircleNotch className="spin" size={16} weight="light" />
                        </span>
                        <div>
                          <div className="dna-writing-title">{t("dna.writingTitle")}</div>
                          <div className="dna-writing-sub">{t("dna.writingSub")}</div>
                        </div>
                        <span className="dna-writing-dots" aria-hidden="true">
                          <i /><i /><i />
                        </span>
                      </div>
                    )}
                    {!enriching && dnaHasPlaceholders && detail.chapters_written === 0 && (
                      <div className="dna-steps-hint muted small">
                        Còn 2 bước tới chương đầu: <strong>1)</strong> Hoàn thiện PROJECT_DNA
                        (nút bên trên) → <strong>2)</strong> Bấm "Để AI viết" ở cột phải.
                      </div>
                    )}
                    {detail.dna ? (
                      <pre className="prose">{detail.dna}</pre>
                    ) : enriching ? null : (
                      <div className="muted">{t("dna.missing")}</div>
                    )}
                  </div>
                )}
                {!viewingArtifacts && tab === "doctor" && <DoctorPanel doctor={detail.doctor} />}
                {!viewingArtifacts && tab === "analyze" && <AnalyzePanel />}
                {!viewingArtifacts && tab === "novelcli" && (
                  <NovelCliPanel novel={detail.name} onChange={onChange} />
                )}
                {!viewingArtifacts && tab === "graph" && <GraphPanel novel={detail.name} />}
              </section>

              <aside className="studio-right">
                <div className="studio-right-head">
                  <SlidersHorizontal size={15} weight="light" /> {t("studio.progressTitle")}
                </div>
                <PipelineBoard
                  novel={detail}
                  onChange={onChange}
                  llmConfigured={!!settings?.configured}
                  onOpenSettings={openSettings}
                  showSettingsLink
                  advanced={advanced}
                  aiBusy={enriching}
                  dnaComplete={!dnaHasPlaceholders}
                  onViewArtifact={(path, all) => viewArtifact(path, all)}
                />
              </aside>
            </div>
          </>
        )}
      </main>

      <SettingsModal
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        onSaved={(s) => setSettings(s)}
      />

      <CreateNovelModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        existingNames={novels.map((n) => n.name)}
        llmConfigured={!!settings?.configured}
        onOpenSettings={() => {
          setCreateOpen(false);
          openSettings();
        }}
        onCreated={(name, opts) => {
          refreshNovels();
          setSelected(name);
          setTab("dna");
          if (opts?.autoEnrich) {
            // Enrichment is the slow multi-batch LLM pass. Run it here (not in
            // the modal) so the author lands on the manuscript and watches the
            // PROJECT_DNA tab show a "Writing" state instead of waiting behind a
            // modal spinner.
            void enrichNovel(name);
          }
        }}
      />
    </div>
  );
}
