/**
 * The write button must be enabled only when writing can actually start.
 *
 * Two measured gaps this pins:
 *
 * 1. `running` is local React state, so it only knows about a run this tab
 *    started. A run in flight from another tab, another device, or an async job
 *    left the button enabled and the banner reading "Bước kế tiếp" — the server
 *    then rejected the click as `alreadyRunning`. The board must also honour the
 *    server's own `pipeline_status.status`.
 *
 * 2. `dna_ready` only checks that the logline is filled, while the PROJECT_DNA
 *    tab's hint ("Còn 2 bước tới chương đầu") keys off *any* remaining
 *    placeholder. Measured on 503 real workspaces, 360 sat in between: the hint
 *    told the author to finish the DNA first, yet the write button was enabled.
 *    Writing from a placeholder DNA is what produces a chapter grounded in
 *    "[Tự sinh]".
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const board = readFileSync(
  new URL("../src/components/PipelineBoard.tsx", import.meta.url),
  "utf8",
);
const studio = readFileSync(
  new URL("../src/pages/StudioPage.tsx", import.meta.url),
  "utf8",
);
const messages = readFileSync(
  new URL("../src/i18n/messages.ts", import.meta.url),
  "utf8",
);
const styles = readFileSync(
  new URL("../src/styles.css", import.meta.url),
  "utf8",
);

/** The `disabled={…}` expression of the main run button. */
function runButtonDisabled() {
  const at = board.indexOf('className="btn run-btn"');
  assert.notEqual(at, -1, "the run button lost its run-btn class");
  const line = board.slice(at, board.indexOf("onClick", at));
  const m = line.match(/disabled=\{([^}]*)\}/);
  assert.ok(m, "the run button has no disabled expression");
  return m[1];
}

/**
 * Expand an expression by substituting the definitions of any local `const`s it
 * names, repeatedly, so an assertion can target the underlying CONDITION rather
 * than whatever intermediate variable happens to hold it. Without this the tests
 * fail the moment a correct implementation factors `serverRunning` out into
 * `anyRunning` — pinning a name, not a behaviour.
 */
function resolved(expression) {
  // Repeat to a fixed point: the gate reads through two levels
  // (`anyRunning` → `serverRunning` → `novel.pipeline_status`), so a single
  // pass would stop before reaching the actual data dependency.
  //
  // Two guards keep the substitution honest:
  //
  // * a name preceded by `.` is a PROPERTY, not a local. Without this check
  //   `pipeline_status?.status` was rewritten using the unrelated
  //   `const status = await api.runStatus(...)` inside runChapters, and the
  //   assertion failed against correct code.
  // * only component-level declarations (two-space indent) count. A `const`
  //   inside a function body is not in scope for the JSX being asserted on.
  let out = expression;
  for (let pass = 0; pass < 6; pass += 1) {
    const next = out.replace(
      /(^|[^.\w$])([A-Za-z_$][\w$]*)\b/g,
      (whole, prefix, name) => {
        const at = board.search(new RegExp(`\\n  const ${name}\\s*=`));
        if (at === -1) return whole;
        const body = board.slice(board.indexOf("=", at) + 1, board.indexOf(";", at));
        return `${prefix}(${body.trim()})`;
      },
    );
    if (next === out) break;
    out = next;
  }
  return out;
}

function translated(key) {
  const at = messages.indexOf(`"${key}":`);
  assert.notEqual(at, -1, `${key} is not defined`);
  const body = messages.slice(at, messages.indexOf("},", at));
  for (const lang of ["vi", "en", "ko", "ja", "zh", "pt", "fr"]) {
    assert.match(body, new RegExp(`\\b${lang}:`), `${key} is missing ${lang}`);
  }
}

// --- 1. a run already in flight -------------------------------------------- //

test("the run button honours a server-side run, not just this tab's state", () => {
  assert.match(
    resolved(runButtonDisabled()),
    /pipeline_status\?\.status\s*===\s*"running"/,
    "only local `running` is checked, so a run from elsewhere leaves it enabled",
  );
});

test("the board derives the running state from pipeline_status", () => {
  assert.match(board, /pipeline_status\?\.status\s*===\s*"running"/);
});

test("the board also honours the persistent background-job status", () => {
  assert.match(
    board,
    /const \[remoteRunActive, setRemoteRunActive\] = useState\(false\);/,
    "a reload loses local React state unless the board restores the active run job",
  );
  assert.match(
    board,
    /const serverRunning\s*=\s*remoteRunActive\s*\|\|/,
    "the primary run gate ignores the persistent background-job status",
  );
});

test("the next-step banner reports the in-progress state for a server run", () => {
  const at = board.indexOf('className="next-banner"');
  const banner = board.slice(at, board.indexOf('className="run-bar"', at));
  assert.match(
    resolved(banner),
    /pipeline_status\?\.status\s*===\s*"running"/,
    "the banner still says 'next step' while the server is mid-run",
  );
});

// --- 2. an unfinished PROJECT_DNA ------------------------------------------ //

test("writing is blocked while the DNA still has placeholders", () => {
  assert.match(
    resolved(runButtonDisabled()),
    /dnaComplete/,
    "an incomplete DNA must not be writable",
  );
});

test("StudioPage tells the board whether the DNA is complete", () => {
  assert.match(studio, /dnaComplete=\{!dnaHasPlaceholders\}/);
});

test("the banner explains the unfinished DNA instead of showing a generic task", () => {
  const at = board.indexOf('className="next-banner"');
  const banner = board.slice(at, board.indexOf('className="run-bar"', at));
  assert.match(banner, /pipeline\.dnaIncomplete/);
  translated("pipeline.dnaIncomplete");
});

test("the enrich button is highlighted while it is the required next action", () => {
  const at = studio.indexOf("dna.enrichButton");
  const button = studio.slice(studio.lastIndexOf("<button", at), at);
  assert.match(
    button,
    /btn--attention/,
    "the required next action carries no visual emphasis",
  );
  assert.match(styles, /\.btn--attention/);
});

test("the attention animation respects reduced-motion", () => {
  const at = styles.indexOf(".btn--attention");
  assert.notEqual(at, -1);
  assert.match(
    styles.slice(at),
    /prefers-reduced-motion/,
    "a pulsing button with no reduced-motion escape hatch is an a11y defect",
  );
});
