/** Shared types mirroring the FastAPI responses (webapp/api). */

export interface NovelBrief {
  name: string;
  title: string;
  status: string;
  target_chapters: number | null;
  chapters_written: number;
  dna_ready: boolean;
}

export interface DocEntry {
  path: string;
  label: string;
  group: string;
  words: number;
  /** True when the file still carries the "chờ AI bổ sung" stub (or is empty)
   *  and should offer a regenerate action. */
  is_stub?: boolean;
}

export interface Task {
  task_key: string;
  phase: string;
  agent_role: string;
  command: string;
  chapter: number | null;
  arc: number | null;
  status: string;
  score: number | null;
  depends_on: string[];
}

export interface PipelineStatus {
  novel: string;
  status: string;
  current_phase: string | null;
  current_chapter: number | null;
  circuit_breaker: Record<string, unknown>;
  stats: Record<string, unknown>;
}

export interface DoctorIssue {
  code: string;
  severity: string;
  message: string;
  path: string | null;
  suggestion: string | null;
}

export interface DoctorReport {
  issues: DoctorIssue[];
  blocking_issues: DoctorIssue[];
}

export interface NovelDetail extends NovelBrief {
  pipeline_status: PipelineStatus | null;
  ready_task: Task | null;
  doctor: DoctorReport;
  dna: string | null;
}

export interface ChapterRow {
  chapter: number;
  has_review: boolean;
  committed: boolean;
  words: number;
}

export interface SyncReport {
  chapter: number;
  gate_passed: boolean;
  blocked: boolean;
  commit_id: string | null;
  idempotent: boolean;
  gate_score: number | null;
  gate_outcome: string | null;
  updated_docs: string[];
  blocking_issues: DoctorIssue[];
  error: string | null;
}

export interface InventorySummary {
  total_files: number;
  must_keep_count: number;
  orphan_count: number;
  coverage_complete: boolean;
}

export interface Violation {
  term: string;
  severity: string;
  count: number;
  replacement?: string;
  reason?: string;
}

export interface LanguageGuardResult {
  severity: string;
  passed: boolean;
  total_hits: number;
  violations: Violation[];
}

export interface AiFlavorResult {
  risk_score: number;
  requires_fix: boolean;
  threshold: number;
  fix_hints: string[];
  violations: { dimension: string; pattern: string; severity: string }[];
}

export interface ProviderSettings {
  mode?: "custom";
  provider?: "other";
  base_url: string;
  model: string;
  api_key_set: boolean;
  api_key_fingerprint: string;
  configured: boolean;
  temperature?: number;
  max_tokens?: number;
}

export interface ProviderEndpoint {
  id: string;
  label: string;
  url: string;
}

export interface ProviderGateway {
  id: string;
  label: string;
  default_model: string;
  peak_rps?: number;
  base_urls?: string[];
  endpoints: ProviderEndpoint[];
}

export interface ProviderCatalog {
  tabs: { id: string; label: string }[];
  gateways: ProviderGateway[];
  other_presets: { id: string; label: string; base_url: string; model?: string }[];
}

export interface RunStep {
  task_key: string;
  stage: string;
  phase: string;
  chapter: number | null;
  outcome: string;
  score: number | null;
  artifacts: string[];
}

export interface RunReport {
  steps: RunStep[];
  tasks_completed: number;
  chapters_drafted: number;
  chapters_synced: number;
  blocked: boolean;
  breaker_open: boolean;
  final_status: string | null;
  stopped_reason: string | null;
  error?: string;
}

export interface StepResponse {
  step: RunStep | null;
  finished: boolean;
  blocked: boolean;
  breaker_open: boolean;
  status: string | null;
  alreadyRunning?: boolean;
}

export interface RunAsyncResponse {
  job_id: string;
  status: "queued" | "running";
  alreadyRunning?: boolean;
}

export interface RunStatusResponse {
  job_id: string | null;
  status: "idle" | "queued" | "running" | "completed" | "failed";
  steps: RunStep[];
  tasks_completed: number;
  chapters_drafted: number;
  chapters_synced: number;
  blocked: boolean;
  breaker_open: boolean;
  final_status: string | null;
  stopped_reason: string | null;
  error: string | null;
  alreadyRunning?: boolean;
}

export interface DnaOption {
  value: string;
  label: string;
}

export interface DnaField {
  id: string;
  label: string;
  type: "text" | "textarea" | "number" | "select";
  required?: boolean;
  options?: DnaOption[];
  options_source?: "genre_styles" | "output_languages";
  placeholder?: string;
  help?: string;
  default?: string | number;
  genres?: string[];
}

export interface DnaSection {
  section: string;
  fields: DnaField[];
}

export interface ExtendedCanonGenre {
  slug: string;
  label: string;
}

export interface DnaSchema {
  sections: DnaSection[];
  genre_sections?: Record<string, DnaSection[]>;
  extended_canon_genres?: ExtendedCanonGenre[];
  genres: string[];
  genre_options: DnaOption[];
  genre_to_squad: Record<string, string>;
  genre_styles: Record<string, DnaOption[]>;
  output_language_options?: DnaOption[];
  genre_template_files?: Record<string, string | null>;
}


/** Long-form GA surface (NovelCLI panel): compass · steer · diagnostics · reminder. */

export interface StoryCompass {
  ending_direction: string;
  active_long_threads: unknown[];
  scale_estimate: Record<string, number>;
  current_volume_id: string | null;
  current_arc_id: string | null;
  compass_digest?: string;
  [key: string]: unknown;
}

export interface ArcSpec {
  arc_id: string;
  start_chapter: number;
  end_chapter: number | null;
  arc_type: string;
  estimated_chapters: number;
  goal?: string;
  status: string;
  volume_id?: string | null;
}

export interface ArcMap {
  arcs: ArcSpec[];
  [key: string]: unknown;
}

export interface PendingSteer {
  steer_id: string;
  kind: string;
  route: string;
  affected_chapters: number[];
  raw_text: string;
  created_at?: string;
  executed?: Record<string, unknown>;
}

export interface StopGuardStatus {
  blocked: boolean;
  reason: string;
}

export interface LongformStatus {
  mode: string | null;
  flags: Record<string, boolean>;
  thresholds: Record<string, number>;
  compass: StoryCompass | null;
  arc_map: ArcMap | null;
  pending_steer: PendingSteer | null;
  reminder: string | null;
  stop_guard: StopGuardStatus | null;
}

export interface SteerResult {
  route: string;
  affected_chapters: number[];
  steer_id: string;
  applied: boolean;
  executed: Record<string, unknown>;
}

export interface DiagFinding {
  code: string;
  dimension: "process" | "quality" | "planning" | "context";
  severity: "error" | "warning" | "info";
  evidence: Record<string, unknown>;
  suggestion: string;
}

export interface CompassMigrateResult {
  compass_digest: string;
  expanded_through_chapter: number;
  changed: boolean;
}


/** Knowledge-graph surface (Studio graph panel). */

/**
 * A node in the node-link graph. Kept intentionally open: the backend attaches
 * kind-specific fields (name, chapter, event_type, rel_type, first_seen, …) that
 * the panel reads opportunistically via the index signature.
 */
export interface GraphNode {
  id: string;
  kind: string;
  [k: string]: unknown;
}

/** An edge in networkx node-link format (edges="links"). */
export interface GraphLink {
  source: string;
  target: string;
  label: string;
  key?: string;
  [k: string]: unknown;
}

export interface GraphContradiction {
  code: string;
  affected_chapters: number[];
  evidence: {
    entity: string;
    death_chapter?: number;
    acted_chapter?: number;
    [k: string]: unknown;
  };
  [k: string]: unknown;
}

export interface GraphResponse {
  exists: boolean;
  graph_digest: string | null;
  metadata: {
    node_count: number;
    edge_count: number;
    through_chapter: number;
  } | null;
  graph: {
    nodes: GraphNode[];
    links: GraphLink[];
  } | null;
  contradictions: {
    soft: GraphContradiction[];
    hard: GraphContradiction[];
  };
}
