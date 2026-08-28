import type {
  AiFlavorResult,
  ChapterRow,
  CompassMigrateResult,
  DiagFinding,
  DocEntry,
  DoctorReport,
  DnaSchema,
  GraphResponse,
  InventorySummary,
  LanguageGuardResult,
  LongformStatus,
  NovelBrief,
  NovelDetail,
  ProviderCatalog,
  ProviderSettings,
  RunAsyncResponse,
  RunReport,
  RunStatusResponse,
  StepResponse,
  SteerResult,
  SyncReport,
  Task,
} from "./types";

export interface ApiClientConfig {
  baseUrl: string;
  /** Return bearer token for a remote deployment; local mode leaves this unset. */
  getToken?: () => string | null | Promise<string | null>;
  /** Request credentials mode for a remote deployment. */
  credentials?: RequestCredentials;
}

export function createApiClient(config: ApiClientConfig) {
  const base = config.baseUrl.replace(/\/$/, "");
  const credentials = config.credentials ?? "include";

  async function req<T>(path: string, init?: RequestInit): Promise<T> {
    const token = config.getToken ? await config.getToken() : null;
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(init?.headers as Record<string, string> | undefined),
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const res = await fetch(`${base}${path}`, {
      credentials: token ? "omit" : credentials,
      headers,
      ...init,
    });
    if (!res.ok) {
      let detail = `${res.status} ${res.statusText}`;
      try {
        const body = await res.json();
        if (body?.detail) detail = body.detail;
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }
    if (res.status === 204) return undefined as T;
    return (await res.json()) as T;
  }

  return {
    health: () => req<{ status: string; tools: number }>("/api/health"),
    tools: () => req<string[]>("/api/tools"),
    schedule: () => req<{ jobs: { name: string; description: string }[] }>("/api/schedule"),
    inventory: () => req<InventorySummary>("/api/inventory"),
    suggestCharacters: () =>
      req<{ mc: Record<string, string>; antagonist: Record<string, string> }>(
        "/api/suggest-characters",
      ),
    suggestSeed: () =>
      req<{ logline: string; usp: string; theme: string; audience: string }>("/api/suggest-seed"),
    suggestCompanions: () =>
      req<{ artifact: string; spirit_beast: string; supporting_cast: string }>(
        "/api/suggest-companions",
      ),
    suggestCultivation: (styleModel?: string) =>
      req<{ cultivation_age_benchmarks: string }>(
        `/api/suggest-cultivation${styleModel ? "?style_model=" + encodeURIComponent(styleModel) : ""}`,
      ),

    listNovels: () => req<NovelBrief[]>("/api/novels"),
    dnaTemplate: () => req<DnaSchema>("/api/dna-template"),
    generateDna: (body: {
      brief: string;
      genre?: string;
      title?: string;
      output_language?: string;
      output_language_custom?: string;
    }) =>
      req<{ fields: Record<string, string>; genre: string }>("/api/dna-generate", {
        method: "POST",
        body: JSON.stringify(body),
      }),
    createNovel: (name: string, fields: Record<string, unknown>) =>
      req<NovelDetail>("/api/novels", {
        method: "POST",
        body: JSON.stringify({ name, fields }),
      }),
    novel: (name: string) => req<NovelDetail>(`/api/novels/${encodeURIComponent(name)}`),
    deleteNovel: (name: string) =>
      req<{ deleted: string }>(`/api/novels/${encodeURIComponent(name)}`, { method: "DELETE" }),
    chapters: (name: string) =>
      req<ChapterRow[]>(`/api/novels/${encodeURIComponent(name)}/chapters`),
    artifact: (name: string, path: string) =>
      req<{ path: string; text: string }>(
        `/api/novels/${encodeURIComponent(name)}/artifact?path=${encodeURIComponent(path)}`,
      ),
    writeArtifact: (name: string, path: string, text: string) =>
      req<{ path: string; success: boolean }>(
        `/api/novels/${encodeURIComponent(name)}/artifact`,
        { method: "POST", body: JSON.stringify({ path, text }) },
      ),
    docs: (name: string) => req<DocEntry[]>(`/api/novels/${encodeURIComponent(name)}/docs`),
    regenerateDoc: (name: string, path: string) =>
      req<{
        path: string;
        regenerated: boolean;
        is_stub: boolean;
        words: number;
        alreadyRunning?: boolean;
      }>(`/api/novels/${encodeURIComponent(name)}/docs/regenerate`, {
        method: "POST",
        body: JSON.stringify({ path }),
      }),
    enrichDna: (name: string, options?: { max_batches?: number }) => {
      const qs =
        options?.max_batches != null
          ? `?max_batches=${encodeURIComponent(String(options.max_batches))}`
          : "";
      return req<{
        enriched_fields: string[];
        count: number;
        batches_failed?: number;
        missing_fields?: string[];
        missing_count?: number;
        done?: boolean;
      }>(`/api/novels/${encodeURIComponent(name)}/enrich${qs}`, { method: "POST" });
    },
    enrichDnaAll: async (name: string) => {
      const enriched = new Set<string>();
      let last: {
        enriched_fields: string[];
        count: number;
        batches_failed?: number;
        missing_fields?: string[];
        missing_count?: number;
        done?: boolean;
      } | null = null;
      let prevMissing = Number.POSITIVE_INFINITY;
      for (let step = 0; step < 64; step += 1) {
        const batch = await req<{
          enriched_fields: string[];
          count: number;
          batches_failed?: number;
          missing_fields?: string[];
          missing_count?: number;
          done?: boolean;
        }>(`/api/novels/${encodeURIComponent(name)}/enrich?max_batches=1`, {
          method: "POST",
        });
        last = batch;
        batch.enriched_fields.forEach((field) => enriched.add(field));
        if (batch.done || batch.missing_count === 0) {
          return {
            ...batch,
            enriched_fields: [...enriched].sort(),
            count: enriched.size,
          };
        }
        // Stop instead of spinning to the 64-iteration cap: a call that fills
        // nothing new AND does not shrink the missing set means the remaining
        // fields are stuck (provider keeps omitting them), so further identical
        // calls are wasted. Surface the accurate remaining count below.
        const missingNow = batch.missing_count ?? 0;
        const stalled = batch.count === 0 && missingNow >= prevMissing;
        if (stalled || (batch.count === 0 && (batch.batches_failed ?? 0) > 0)) {
          break;
        }
        prevMissing = missingNow;
      }
      if (last && last.missing_count === 0) {
        return {
          ...last,
          enriched_fields: [...enriched].sort(),
          count: enriched.size,
        };
      }
      throw new Error(
        last?.missing_count
          ? `DNA enrich incomplete (${last.missing_count} fields remaining)`
          : "DNA enrich failed (provider did not respond)",
      );
    },
    chapter: (name: string, n: number) =>
      req<{ chapter: number; text: string; review: string | null }>(
        `/api/novels/${encodeURIComponent(name)}/chapters/${n}`,
      ),
    planNext: (name: string, claim: boolean) =>
      req<{ ready_task: Task | null }>(
        `/api/novels/${encodeURIComponent(name)}/pipeline/plan-next`,
        { method: "POST", body: JSON.stringify({ claim }) },
      ),
    recordResult: (name: string, body: { task_key: string; result: string; score?: number }) =>
      req<Record<string, unknown>>(
        `/api/novels/${encodeURIComponent(name)}/pipeline/record-result`,
        { method: "POST", body: JSON.stringify(body) },
      ),
    resume: (name: string) =>
      req<Record<string, unknown>>(`/api/novels/${encodeURIComponent(name)}/pipeline/resume`, {
        method: "POST",
      }),
    recover: (name: string) =>
      req<{
        recovered: boolean;
        breaker_was_open: boolean;
        released_tasks: number;
        next_task_key: string | null;
      }>(`/api/novels/${encodeURIComponent(name)}/pipeline/recover`, {
        method: "POST",
      }),
    approveChapter: (name: string, chapter: number) =>
      req<{
        approved: boolean;
        chapter: number;
        recover: Record<string, unknown>;
      }>(`/api/novels/${encodeURIComponent(name)}/pipeline/approve`, {
        method: "POST",
        body: JSON.stringify({ chapter }),
      }),
    rollingSeed: (name: string) =>
      req<Record<string, unknown>>(
        `/api/novels/${encodeURIComponent(name)}/pipeline/rolling-seed`,
        { method: "POST" },
      ),

    sync: (name: string, chapter: number) =>
      req<SyncReport>(`/api/novels/${encodeURIComponent(name)}/sync`, {
        method: "POST",
        body: JSON.stringify({ chapter }),
      }),
    doctor: (name: string) => req<DoctorReport>(`/api/novels/${encodeURIComponent(name)}/doctor`),
    graph: (slug: string) =>
      req<GraphResponse>(`/api/studio/novels/${encodeURIComponent(slug)}/graph`),

    // Long-form GA surface (NovelCLI): compass · steer · diagnostics · reminder.
    longformStatus: (name: string) =>
      req<LongformStatus>(`/api/novels/${encodeURIComponent(name)}/longform`),
    steer: (name: string, text: string) =>
      req<SteerResult>(`/api/novels/${encodeURIComponent(name)}/steer`, {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
    diagnostics: (name: string, redact = false) =>
      req<DiagFinding[]>(
        `/api/novels/${encodeURIComponent(name)}/diagnostics${redact ? "?redact=true" : ""}`,
      ),
    compassMigrate: (
      name: string,
      body: { current_chapter: number; target_chapters: number },
    ) =>
      req<CompassMigrateResult>(`/api/novels/${encodeURIComponent(name)}/compass/migrate`, {
        method: "POST",
        body: JSON.stringify(body),
      }),

    aiFlavor: (text: string) =>
      req<AiFlavorResult>("/api/analyze/ai-flavor", {
        method: "POST",
        body: JSON.stringify({ text }),
      }),
    languageGuard: (text: string, genre: string, secondary_genre?: string) =>
      req<LanguageGuardResult>("/api/analyze/language-guard", {
        method: "POST",
        body: JSON.stringify({ text, genre, secondary_genre }),
      }),

    getSettings: () => req<ProviderSettings>("/api/settings"),
    getProviderCatalog: () => req<ProviderCatalog>("/api/settings/providers"),
    saveSettings: (body: {
      provider?: "other";
      base_url?: string;
      model?: string;
      api_key?: string;
    }) =>
      req<ProviderSettings>("/api/settings", {
        method: "PUT",
        body: JSON.stringify(body),
      }),
    testSettings: (body?: { base_url?: string; model?: string; api_key?: string }) =>
      req<{ ok: boolean; detail: string }>("/api/settings/test", {
        method: "POST",
        body: JSON.stringify(body ?? {}),
      }),
    run: (name: string, max_steps: number) =>
      req<RunReport>(`/api/novels/${encodeURIComponent(name)}/run`, {
        method: "POST",
        body: JSON.stringify({ max_steps }),
      }),
    runStep: (name: string) =>
      req<StepResponse>(`/api/novels/${encodeURIComponent(name)}/run-step`, { method: "POST" }),
    // ``chapters`` switches the server into chapter mode: it runs until that many
    // chapters finish syncing, and derives its own step ceiling. Callers that ask
    // for chapters must NOT also try to budget steps — a chapter costs ~5 steps
    // when clean and ~11 when it needs rewrites, so any step number the UI picks
    // is either a cut-off mid-chapter or a meaningless ceiling.
    runAsync: (name: string, opts: { max_steps?: number; chapters?: number } = {}) =>
      req<RunAsyncResponse>(`/api/novels/${encodeURIComponent(name)}/run-async`, {
        method: "POST",
        body: JSON.stringify({
          max_steps: opts.max_steps ?? 12,
          ...(opts.chapters != null ? { chapters: opts.chapters } : {}),
        }),
      }),
    runStatus: (name: string) =>
      req<RunStatusResponse>(`/api/novels/${encodeURIComponent(name)}/run-status`),
  };
}

export type ApiClient = ReturnType<typeof createApiClient>;
