import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const modalSource = readFileSync(
  new URL("../src/components/CreateNovelModal.tsx", import.meta.url),
  "utf8",
);

test("the secondary author dropdown follows the selected secondary genre", () => {
  assert.match(
    modalSource,
    /f\.id === "style_secondary"\s*\? fields\.genre_secondary\s*:\s*genre/,
  );
  assert.match(modalSource, /genre_styles\[styleGenre\]/);
});

test("changing the secondary genre clears an author code from the old pack", () => {
  assert.match(
    modalSource,
    /if \(id === "genre_secondary"\)\s*\{\s*next\.style_secondary = "";/,
  );
});
