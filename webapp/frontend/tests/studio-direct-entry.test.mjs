import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const studioSource = readFileSync(
  new URL("../src/pages/StudioPage.tsx", import.meta.url),
  "utf8",
);

test("Studio opens the first novel instead of showing the old landing", () => {
  assert.match(
    studioSource,
    /selected === null \|\| !novels\.some[\s\S]*setSelected\(novels\[0\]\.name\)/,
  );
  assert.doesNotMatch(studioSource, /welcome-workbench|chapter-01-draft\.webp/);
});

test("an empty library stays inside Studio with a create action", () => {
  assert.match(studioSource, /className="studio-empty"/);
  assert.match(studioSource, /onClick=\{openCreate\}/);
});
