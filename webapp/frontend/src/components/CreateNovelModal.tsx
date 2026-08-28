import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  CaretDown,
  CaretRight,
  ChartBar,
  CircleNotch,
  DiceFive,
  GlobeHemisphereWest,
  Lightning,
  NotePencil,
  Plant,
  Sparkle,
  Sword,
  X,
} from "@phosphor-icons/react";
import { api } from "../api";
import type { DnaField, DnaOption, DnaSchema, DnaSection } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  onCreated: (name: string, opts?: { autoEnrich?: boolean }) => void;
  existingNames: string[];
  llmConfigured: boolean;
  /** Open the provider Settings modal so the user can connect a model without
   *  leaving the create flow (used when Quick Setup needs an LLM). */
  onOpenSettings?: () => void;
}

type Mode = "choose" | "quick" | "full";

function slugify(s: string): string {
  return s
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/đ/g, "d")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "")
    .slice(0, 64);
}

// Append -2, -3 … when the slug already exists (mirrors the backend rule).
function dedupeSlug(base: string, taken: string[]): string {
  if (!base || !taken.includes(base)) return base;
  let i = 2;
  while (taken.includes(`${base}-${i}`)) i += 1;
  return `${base}-${i}`;
}

export function CreateNovelModal({
  open,
  onClose,
  onCreated,
  existingNames,
  llmConfigured,
  onOpenSettings,
}: Props) {
  const [mode, setMode] = useState<Mode>("choose");
  // Full Setup keeps only the essentials (seed + genre + chapters) visible by
  // default; the detailed character/world/param sections collapse behind this
  // toggle so a new author is not overwhelmed. Nothing is removed — the fields
  // can still be filled here or later in the PROJECT_DNA tab.
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [schema, setSchema] = useState<DnaSchema | null>(null);
  const [fields, setFields] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [brief, setBrief] = useState("");

  useEffect(() => {
    if (!open) return;
    setMode("choose");
    setError(null);
    setBrief("");
    setShowAdvanced(false);
    api.dnaTemplate().then((s) => {
      setSchema(s);
      const init: Record<string, string> = {};
      s.sections.forEach((sec) =>
        sec.fields.forEach((f) => {
          if (f.default !== undefined) init[f.id] = String(f.default);
        }),
      );
      setFields(init);
    });
  }, [open]);

  const title = fields.title ?? "";
  const genre = fields.genre ?? "xianxia";
  const squad = schema?.genre_to_squad[genre] ?? "sub_agents";

  // Slug auto-derived from the title and deduped so it is unique.
  const effectiveName = useMemo(
    () => dedupeSlug(slugify(title), existingNames),
    [title, existingNames],
  );

  const genreSections = useMemo(
    () => schema?.genre_sections?.[genre] ?? [],
    [schema, genre],
  );

  // Author-reference options for the CURRENT primary genre. The stable code is
  // written to PROJECT_DNA for routing/identification only; the profile itself
  // no longer contributes prose-imitation rules.
  const genreStyles = useMemo(
    () => schema?.genre_styles?.[genre] ?? [],
    [schema, genre],
  );
  const quickStyleModel = fields.style_model || genreStyles[0]?.value || "";
  const quickWbGuide = fields.worldbuilding_guide || quickStyleModel;

  function fieldVisible(f: DnaField): boolean {
    if (f.id === "output_language_custom") {
      return (fields.output_language ?? "vi") === "custom";
    }
    return !f.genres || f.genres.includes(genre);
  }

  function optionsFor(f: DnaField): DnaOption[] {
    if (f.options_source === "genre_styles") {
      const styleGenre =
        f.id === "style_secondary" ? fields.genre_secondary : genre;
      const styles = styleGenre ? schema?.genre_styles[styleGenre] ?? [] : [];
      return [{ value: "", label: "— Chọn —" }, ...styles];
    }
    if (f.options_source === "output_languages") {
      return schema?.output_language_options ?? [];
    }
    return f.options ?? [];
  }



  function set(id: string, v: string) {
    setFields((prev) => {
      const next = { ...prev, [id]: v };
      if (id === "genre") {
        next.style_model = "";
        next.style_secondary = "";
        next.worldbuilding_guide = "";
      }
      if (id === "genre_secondary") {
        next.style_secondary = "";
      }
      return next;
    });
  }



  // Full Setup: create from the manually filled form. Enrichment (the slow,
  // multi-batch LLM step) is handed off to the Studio's PROJECT_DNA tab so the
  // modal closes immediately instead of blocking the user behind a spinner.
  async function submitFull() {
    setBusy(true);
    setError(null);
    try {
      const slug = dedupeSlug(slugify(fields.title || ""), existingNames);
      const detail = await api.createNovel(slug, fields);
      // Hand off to Studio; it shows the "Writing" state while enrich runs.
      onCreated(detail.name, { autoEnrich: llmConfigured });
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  // Quick Setup: AI fills the DNA from the brief, then create immediately. The
  // long enrichment pass runs in the Studio (background) so the user lands on
  // the manuscript with a visible "Writing" status instead of waiting here.
  async function quickCreate() {
    if (!brief.trim()) return;
    setGenerating(true);
    setError(null);
    try {
      const res = await api.generateDna({
        brief,
        genre: fields.genre || "xianxia",
        title: fields.title || undefined,
        output_language: fields.output_language || "vi",
        output_language_custom:
          fields.output_language === "custom"
            ? fields.output_language_custom
            : undefined,
      });
      const merged = { ...fields, ...res.fields };
      // A title the author typed explicitly always wins over the AI's.
      if (fields.title?.trim()) merged.title = fields.title.trim();
      // Send the style routing the author actually SAW in the dropdowns. These
      // are pre-selected rather than typed, so `fields` can still be empty while
      // the UI shows a resolved default; writing the displayed value keeps the
      // form and PROJECT_DNA in agreement and stops the enrich pass from
      // treating the field as missing and picking a master on its own.
      merged.style_model = quickStyleModel;
      merged.worldbuilding_guide = quickWbGuide;
      setGenerating(false);
      setBusy(true);
      const slug = dedupeSlug(slugify(merged.title || ""), existingNames);
      const detail = await api.createNovel(slug, merged);
      onCreated(detail.name, { autoEnrich: llmConfigured });
      onClose();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setGenerating(false);
      setBusy(false);
    }
  }

  async function handleSuggest() {
    try {
      const res = await api.suggestCharacters();
      setFields((prev) => ({
        ...prev,
        ...res.mc,
        ...res.antagonist,
      }));
    } catch (e) {
      alert("Lỗi khi lấy gợi ý: " + (e as Error).message);
    }
  }

  async function handleSuggestSeed() {
    try {
      const res = await api.suggestSeed();
      setFields((prev) => ({
        ...prev,
        logline: res.logline,
        usp: res.usp,
        theme: res.theme,
        audience: res.audience,
      }));
    } catch (e) {
      alert("Lỗi khi lấy gợi ý hạt giống: " + (e as Error).message);
    }
  }

  async function handleSuggestCompanions() {
    try {
      const res = await api.suggestCompanions();
      setFields((prev) => ({
        ...prev,
        artifact: res.artifact,
        spirit_beast: res.spirit_beast,
        supporting_cast: res.supporting_cast,
      }));
    } catch (e) {
      alert("Lỗi khi lấy gợi ý đồng hành: " + (e as Error).message);
    }
  }

  async function handleSuggestCultivation() {
    try {
      const res = await api.suggestCultivation(fields.style_model);
      setFields((prev) => ({
        ...prev,
        cultivation_age_benchmarks: res.cultivation_age_benchmarks,
      }));
    } catch (e) {
      alert("Lỗi khi lấy gợi ý mốc tuổi tu luyện: " + (e as Error).message);
    }
  }


  const sectionsMap = useMemo(() => {
    const map: Record<string, DnaSection> = {};
    if (schema) {
      schema.sections.forEach((s) => {
        map[s.section] = s;
      });
    }
    return map;
  }, [schema]);

  function renderField(f: DnaField) {
    if (!fieldVisible(f)) return null;
    return (
      <label
        className={`field ${f.type === "textarea" ? "field-wide" : ""}`}
        key={f.id}
      >
        {f.label}
        {f.required && <span className="req">*</span>}
        {f.type === "select" ? (
          <select
            value={fields[f.id] ?? ""}
            onChange={(e) => set(f.id, e.target.value)}
          >
            {optionsFor(f).map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        ) : f.type === "textarea" ? (
          <textarea
            rows={3}
            value={fields[f.id] ?? ""}
            placeholder={f.placeholder}
            onChange={(e) => set(f.id, e.target.value)}
          />
        ) : (
          <input
            type={f.type === "number" ? "number" : "text"}
            value={fields[f.id] ?? ""}
            placeholder={f.placeholder}
            onChange={(e) => set(f.id, e.target.value)}
          />
        )}
        {f.id === "title" && (
          <span className="muted small slug-hint">
            {effectiveName ? (
              <>
                Mã thư mục: <code>{effectiveName}</code> · squad:{" "}
                <code>{squad}</code>
              </>
            ) : (
              <em>Mã thư mục sẽ tự sinh khi bạn gõ tên tác phẩm.</em>
            )}
          </span>
        )}
      </label>
    );
  }

  function renderSection(sectionName: string, isHalfWidth: boolean = false) {
    const sec = sectionsMap[sectionName];
    if (!sec) return null;
    const visibleFields = sec.fields.filter(fieldVisible);
    if (visibleFields.length === 0) return null;
    return (
      <fieldset className={`dna-section ${isHalfWidth ? "dna-section-half" : ""}`} key={sec.section}>
        <legend style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
          <span>{sec.section}</span>
          {sectionName === "Đồng hành đặc biệt" && genre === "xianxia" && (
            <button
              type="button"
              className="btn ghost btn-mini"
              onClick={handleSuggestCompanions}
              title="Gợi ý đồng hành ngẫu nhiên"
              style={{
                padding: "2px 6px",
                fontSize: "15px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
                cursor: "pointer",
                border: "none",
                background: "transparent",
              }}
            >
              <DiceFive size={14} weight="light" /> Gợi ý nhanh
            </button>
          )}
          {sectionName === "Thế giới & tu luyện" && genre === "xianxia" && (
            <button
              type="button"
              className="btn ghost btn-mini"
              onClick={handleSuggestCultivation}
              title="Gợi ý mốc tuổi tu luyện"
              style={{
                padding: "2px 6px",
                fontSize: "15px",
                display: "flex",
                alignItems: "center",
                gap: "4px",
                cursor: "pointer",
                border: "none",
                background: "transparent",
              }}
            >
              <DiceFive size={14} weight="light" /> Gợi ý nhanh
            </button>
          )}

        </legend>
        <div className="dna-grid">
          {visibleFields.map((f) => renderField(f))}
        </div>
      </fieldset>
    );
  }

  function renderGenreSections() {
    if (genreSections.length === 0) return null;
    return (
      <div className="dna-group-box">
        <div className="dna-group-title">
          <Sparkle size={17} weight="light" /> Trường theo thể loại · {schema?.genre_options.find((o) => o.value === genre)?.label ?? genre}
        </div>
        {genreSections.map((sec) => (
          <fieldset className="dna-section" key={sec.section}>
            <legend>{sec.section}</legend>
            <div className="dna-grid">{sec.fields.map((f) => renderField(f))}</div>
          </fieldset>
        ))}
      </div>
    );
  }

  if (!open) return null;

  const headTitle =
    mode === "choose"
      ? "Tạo novel mới"
      : mode === "quick"
        ? "Quick Setup — AI tự dựng truyện"
        : "Full Setup — điền PROJECT_DNA";

  return (
    <div className="modal-backdrop">
      <div className="modal modal-wide" role="dialog" aria-modal="true">
        <div className="modal-head">
          <h2>{headTitle}</h2>
          <button className="btn-mini" onClick={onClose} aria-label="Đóng trình tạo novel">
            <X size={15} weight="light" />
          </button>
        </div>

        {/* ---- Step 1: choose a setup mode ---- */}
        {mode === "choose" && (
          <div className="setup-choices">
            <button
              className="setup-card"
              onClick={() => {
                // Chưa cấu hình model → mở Settings ngay trong luồng thay vì
                // khoá cứng, để người dùng kết nối rồi quay lại tạo tiếp.
                if (!llmConfigured && onOpenSettings) {
                  onOpenSettings();
                  return;
                }
                setMode("quick");
              }}
            >
              <div className="setup-ico"><Lightning size={28} weight="light" /></div>
              <div className="setup-title">Quick Setup</div>
              <div className="setup-desc">
                Chỉ cần mô tả ý tưởng — AI tự dựng toàn bộ PROJECT_DNA và tạo truyện ngay.
              </div>
              {!llmConfigured && (
                <div className="muted small">
                  Chưa kết nối model — bấm để mở Settings kết nối
                </div>
              )}
            </button>
            <button className="setup-card" onClick={() => setMode("full")}>
              <div className="setup-ico"><NotePencil size={28} weight="light" /></div>
              <div className="setup-title">Full Setup</div>
              <div className="setup-desc">
                Tự điền chi tiết từng mục của PROJECT_DNA theo template chuẩn.
              </div>
            </button>
          </div>
        )}

        {/* ---- Quick Setup screen ---- */}
        {mode === "quick" && (
          <>
            <button className="modal-back" onClick={() => setMode("choose")}>
              <ArrowLeft size={14} weight="light" /> Quay lại
            </button>
            <p className="muted small">
              Mô tả ý tưởng truyện, AI sẽ dựng PROJECT_DNA hoàn chỉnh và tạo truyện.
              Bạn có thể tinh chỉnh ở tab PROJECT_DNA sau khi tạo.
            </p>
            <label className="field field-wide">
              Ý tưởng / yêu cầu<span className="req">*</span>
              <textarea
                rows={4}
                value={brief}
                placeholder="VD: Một thiếu niên phàm nhân nhặt được mảnh hồn thượng cổ ma đầu, vừa tu tiên vừa che giấu thân phận, bi tráng kiểu Nhĩ Căn…"
                onChange={(e) => setBrief(e.target.value)}
              />
            </label>
            <div className="dna-grid">
              <label className="field">
                Tên tác phẩm (tùy chọn)
                <input
                  value={fields.title ?? ""}
                  placeholder="Để trống thì AI tự đặt"
                  onChange={(e) => set("title", e.target.value)}
                />
              </label>
              <label className="field">
                Thể loại chính
                <select value={genre} onChange={(e) => set("genre", e.target.value)}>
                  {(schema?.genre_options ?? []).map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              <label className="field">
                Tác giả tham chiếu
                <select
                  value={quickStyleModel}
                  onChange={(e) => set("style_model", e.target.value)}
                >
                  {genreStyles.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <span className="muted small">
                  Chỉ dùng để nhận diện; giọng truyện do PROJECT_DNA quyết định.
                </span>
              </label>
              <label className="field">
                Đạo thư dựng giới
                <select
                  value={quickWbGuide}
                  onChange={(e) => set("worldbuilding_guide", e.target.value)}
                >
                  {genreStyles.map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
                <span className="muted small">
                  Mặc định theo văn phong đã chọn.
                </span>
              </label>
              <label className="field">
                Ngôn ngữ output
                <select
                  value={fields.output_language ?? "vi"}
                  onChange={(e) => set("output_language", e.target.value)}
                >
                  {(schema?.output_language_options ?? []).map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              </label>
              {(fields.output_language ?? "vi") === "custom" && (
                <label className="field field-wide">
                  Ngôn ngữ tùy chỉnh
                  <input
                    value={fields.output_language_custom ?? ""}
                    placeholder="vd: Deutsch, Español, Tiếng Thái…"
                    onChange={(e) => set("output_language_custom", e.target.value)}
                  />
                </label>
              )}
              <label className="field">
                Số chương
                <input
                  type="number"
                  min={1}
                  value={fields.target_chapters ?? "30"}
                  onChange={(e) => set("target_chapters", e.target.value)}
                />
              </label>
            </div>
            {error && <div className="error">{error}</div>}
            <div className="modal-actions">
              <button className="btn ghost" onClick={() => setMode("choose")} disabled={generating || busy}>
                Quay lại
              </button>
              <button
                className="btn"
                onClick={quickCreate}
                disabled={generating || busy || !brief.trim() || !llmConfigured}
              >
                {generating
                  ? <><CircleNotch className="spin" size={15} weight="light" /> AI đang dựng ADN…</>
                  : busy
                    ? "Đang tạo…"
                    : <><Sparkle size={15} weight="light" /> AI tạo truyện</>}
              </button>
            </div>
          </>
        )}

        {/* ---- Full Setup screen ---- */}
        {mode === "full" && (
          <>
            <button className="modal-back" onClick={() => setMode("choose")}>
              <ArrowLeft size={14} weight="light" /> Quay lại
            </button>
            <p className="muted small">
              Thông tin bạn điền sẽ được ghi thẳng vào <code>PROJECT_DNA.md</code> theo
              template chuẩn, rồi mới khởi tạo pipeline. Trường để trống có thể bổ sung sau.
            </p>

            {!schema && <div className="muted">Đang tải template…</div>}

            {schema && (
              <div className="dna-form-container">
                {/* Group 1: Thông tin Hạt giống & Phong cách */}
                <div className="dna-group-box">
                  <div className="dna-group-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span><Plant size={17} weight="light" /> Hạt giống & phong cách sáng tác</span>
                    <button
                      type="button"
                      className="btn ghost btn-mini"
                      onClick={handleSuggestSeed}
                      title="Gợi ý hạt giống ngẫu nhiên"
                      style={{
                        padding: "4px 8px",
                        fontSize: "16px",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        cursor: "pointer",
                      }}
                    >
                      <DiceFive size={14} weight="light" /> Gợi ý nhanh
                    </button>
                  </div>
                  {renderSection("Hạt giống")}
                  {schema.extended_canon_genres && schema.extended_canon_genres.length > 0 && (
                    <p className="muted small" style={{ margin: "0 0 0.75rem" }}>
                      Studio hỗ trợ 6 thể loại có template PROJECT_DNA. Các canon pack khác (
                      {schema.extended_canon_genres.map((g) => g.label).join(" · ")}) dùng trong pipeline
                      nhưng chưa có form tạo novel riêng.
                    </p>
                  )}
                  {renderSection("Phong cách & giọng văn")}
                </div>

                <button
                  type="button"
                  className="dna-advanced-toggle"
                  onClick={() => setShowAdvanced((v) => !v)}
                >
                  {showAdvanced ? <CaretDown size={15} weight="light" /> : <CaretRight size={15} weight="light" />}
                  Chi tiết nâng cao (nhân vật, thế giới, thông số) — có thể bổ sung sau ở tab PROJECT_DNA
                </button>

                {showAdvanced && (
                <>
                {/* Group 2: Thiết lập Nhân vật đối trọng */}
                <div className="dna-group-box">
                  <div className="dna-group-title" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span><Sword size={17} weight="light" /> Đối trọng nhân vật · nhân vật chính / phản diện</span>
                    <button
                      type="button"
                      className="btn ghost btn-mini"
                      onClick={handleSuggest}
                      title="Gợi ý nhân vật ngẫu nhiên"
                      style={{
                        padding: "4px 8px",
                        fontSize: "16px",
                        display: "flex",
                        alignItems: "center",
                        gap: "6px",
                        cursor: "pointer",
                      }}
                    >
                      <DiceFive size={14} weight="light" /> Gợi ý nhanh
                    </button>
                  </div>
                  <div className="dna-flex-row">
                    {renderSection("Nhân vật chính", true)}
                    {renderSection("Đối trọng / Phản diện", true)}
                  </div>
                </div>

                {renderGenreSections()}

                {/* Group 3: Thiết lập thế giới & tu luyện */}
                <div className="dna-group-box">
                  <div className="dna-group-title"><GlobeHemisphereWest size={17} weight="light" /> Thế giới quan & độc giả</div>
                  {renderSection("Thế giới & tu luyện")}
                  {renderSection("Đồng hành đặc biệt")}
                  {renderSection("Thế câu dẫn độc giả")}
                </div>

                {/* Group 4: Thiết lập thông số riêng */}
                <div className="dna-group-box highlighted">
                  <div className="dna-group-title"><ChartBar size={17} weight="light" /> Thiết lập thông số riêng</div>
                  {renderSection("Thông số")}
                </div>

                {/* Dự phòng các section khác nếu có phát sinh */}
                {schema.sections
                  .filter(
                    (s) =>
                      ![
                        "Hạt giống",
                        "Phong cách & giọng văn",
                        "Nhân vật chính",
                        "Đối trọng / Phản diện",
                        "Thế giới & tu luyện",
                        "Đồng hành đặc biệt",
                        "Thế câu dẫn độc giả",
                        "Thông số",
                      ].includes(s.section)
                  )
                  .map((s) => renderSection(s.section))}
                </>
                )}
              </div>
            )}

            {error && <div className="error">{error}</div>}

            <div className="modal-actions">
              <button className="btn ghost" onClick={() => setMode("choose")} disabled={busy}>
                Quay lại
              </button>
              <button className="btn" onClick={submitFull} disabled={busy || !effectiveName}>
                {busy ? "Đang tạo…" : "Tạo & ghi PROJECT_DNA"}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
