/**
 * A busy server must never look like a dead button.
 *
 * `run_step` holds a per-novel lock for the whole request. A click arriving while
 * a previous run is still in flight is answered with HTTP 200 and
 * `alreadyRunning: true` — not an error. The board used to `continue` on that
 * flag without recording a message, incrementing progress, or waiting, so with
 * the default `maxSteps` of 1 the loop finished in one silent pass: the user saw
 * nothing at all and reported "the next-step button does not work".
 *
 * These assertions pin the contract on the source, since the board needs a live
 * React tree to execute.
 */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const board = readFileSync(
  new URL("../src/components/PipelineBoard.tsx", import.meta.url),
  "utf8",
);
const messages = readFileSync(
  new URL("../src/i18n/messages.ts", import.meta.url),
  "utf8",
);

/** The `if (r.alreadyRunning) { … }` body in runAI. */
function busyBranch() {
  const start = board.indexOf("if (r.alreadyRunning)");
  assert.notEqual(start, -1, "runAI no longer handles alreadyRunning");
  let depth = 0;
  for (let i = board.indexOf("{", start); i < board.length; i += 1) {
    if (board[i] === "{") depth += 1;
    if (board[i] === "}") {
      depth -= 1;
      if (depth === 0) return board.slice(start, i + 1);
    }
  }
  throw new Error("unbalanced braces in the alreadyRunning branch");
}

test("a busy server produces a visible message instead of silence", () => {
  assert.match(busyBranch(), /setMsg\(/);
});

test("the busy message is translated in all seven languages", () => {
  const key = busyBranch().match(/t\("(pipeline\.msg\.[A-Za-z]+)"/);
  assert.ok(key, "the busy branch must report a translated message");
  const entry = messages.slice(messages.indexOf(`"${key[1]}":`));
  const body = entry.slice(0, entry.indexOf("},"));
  for (const lang of ["vi", "en", "ko", "ja", "zh", "pt", "fr"]) {
    assert.match(body, new RegExp(`\\b${lang}:`), `${key[1]} is missing ${lang}`);
  }
});

test("a busy retry waits, so the loop cannot spin the server", () => {
  assert.match(
    busyBranch(),
    /await\s+(?:sleep|delay|wait)\(|setTimeout/,
    "retrying a held lock with no delay hammers the endpoint",
  );
});

test("a busy pass does not consume the step budget silently", () => {
  // With maxSteps=1 the old code exited after one rejected attempt having done
  // nothing and said nothing. The branch must either break out (so the outer
  // code reports a message) or not spend an iteration.
  const branch = busyBranch();
  assert.ok(
    /break/.test(branch) || /i\s*-=\s*1/.test(branch),
    "a rejected attempt must not silently burn the only iteration",
  );
});
