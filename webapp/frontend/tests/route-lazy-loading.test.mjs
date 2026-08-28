import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const routerSource = readFileSync(
  new URL("../src/router.tsx", import.meta.url),
  "utf8",
);

test("the root route redirects to the lazily loaded Studio", () => {
  assert.doesNotMatch(routerSource, /import\s+\{[^}]*Page[^}]*\}\s+from\s+"\.\/pages\//);

  const lazyPageImports =
    routerSource.match(/import\("\.\/pages\/[^"]+"\)/g) ?? [];
  assert.equal(lazyPageImports.length, 1);
  assert.match(routerSource, /path:\s*"\/"[\s\S]*redirect\("\/studio"\)/);
  assert.doesNotMatch(routerSource, /browse|reader|login|billing|account/);
});
