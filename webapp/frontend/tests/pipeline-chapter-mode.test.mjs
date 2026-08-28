/**
 * The web board must speak in chapters, like the mobile app does.
 *
 * The two clients diverged on the unit the author is asked for:
 *
 * - mobile sends `{chapters: N}` to `/run-async` and shows "Số chương cần viết"
 *   (manuscript_screen.dart), so the server decides how many steps that costs;
 * - the web board asked for a number of *steps* and never sent it anywhere — it
 *   was purely a client-side `for` bound around `/run-step`.
 *
 * "Step" is an internal unit: a clean chapter costs ~5 and a hard one ~11
 * (service.py `_STEPS_PER_CHAPTER_CEILING` comment), so the default of 1 step
 * wrote one fifth of a chapter. Chapter mode already exists end to end in the
 * backend (`RunRequest.chapters` → `stop_after_chapters` → `max_chapters`); the
 * web simply did not use it.
 *
 * Chapter mode is the default here, and the per-step driver stays available in
 * the Advanced panel so step-level debugging is not lost.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const board = readFileSync(
  new URL("../src/components/PipelineBoard.tsx", import.meta.url),
  "utf8",
);
const client = readFileSync(
  new URL("../../../packages/api-client/src/client.ts", import.meta.url),
  "utf8",
);
const messages = readFileSync(
  new URL("../src/i18n/messages.ts", import.meta.url),
  "utf8",
);

function translated(key) {
  const at = messages.indexOf(`"${key}":`);
  assert.notEqual(at, -1, `${key} is not defined`);
  const body = messages.slice(at, messages.indexOf("},", at));
  for (const lang of ["vi", "en", "ko", "ja", "zh", "pt", "fr"]) {
    assert.match(body, new RegExp(`\\b${lang}:`), `${key} is missing ${lang}`);
  }
}

// --- the api client must be able to express chapter mode -------------------- //

test("runAsync can request a chapter count, not only a step budget", () => {
  const at = client.indexOf("runAsync:");
  assert.notEqual(at, -1, "runAsync disappeared from the api client");
  const fn = client.slice(at, client.indexOf("runStatus:", at));
  assert.match(fn, /chapters/, "runAsync cannot express chapter mode");
});

// --- the board asks for chapters by default -------------------------------- //

test("the primary control is a chapter count", () => {
  assert.match(board, /useState\(1\)/);
  assert.match(
    board,
    /chapterCount|targetChapters/,
    "the board still only tracks a step budget",
  );
});

test("the chapter label is translated in all seven languages", () => {
  translated("pipeline.chapterCount");
});

test("chapter mode drives the server job, not a client-side step loop", () => {
  // Follow the primary button's own onClick rather than a function name: which
  // handler is "the default driver" is exactly what this change moves, so
  // pinning the name would assert the old design.
  const at = board.indexOf('className="btn run-btn"');
  assert.notEqual(at, -1, "the primary run button lost its run-btn class");
  const handler = board.slice(at, board.indexOf(">", board.indexOf("title=", at)));
  const onClick = handler.match(/onClick=\{(\w+)\}/);
  assert.ok(onClick, "the primary button has no named click handler");

  const fnAt = board.indexOf(`async function ${onClick[1]}`);
  assert.notEqual(fnAt, -1, `${onClick[1]} is not a function on the board`);
  const body = board.slice(fnAt, board.indexOf("\n  async function", fnAt + 10));
  assert.match(
    body,
    /runAsync\(/,
    "one click still walks /run-step from the browser, so closing the tab loses the run",
  );
  assert.doesNotMatch(
    body,
    /api\.runStep\(/,
    "the default driver must not loop /run-step inside the tab",
  );
});

test("the board polls run-status while a job is in flight", () => {
  assert.match(board, /runStatus\(/);
});

// --- step mode survives, but only under Advanced ---------------------------- //

test("the per-step driver is kept for debugging", () => {
  assert.match(
    board,
    /runSteps|stepMode/,
    "step-by-step driving was removed rather than moved",
  );
});

test("the step control is rendered inside the Advanced panel", () => {
  const at = board.indexOf('className="advanced"');
  assert.notEqual(at, -1, "the Advanced panel disappeared");
  const panel = board.slice(at);
  assert.match(
    panel,
    /pipeline\.maxSteps/,
    "the step budget input must live under Advanced, not in the main run bar",
  );
});

test("the main run bar no longer exposes raw steps", () => {
  const bar = board.slice(
    board.indexOf('className="run-bar"'),
    board.indexOf('className="advanced"'),
  );
  assert.doesNotMatch(
    bar,
    /pipeline\.maxSteps/,
    "the end-user run bar still asks for an internal step count",
  );
});
