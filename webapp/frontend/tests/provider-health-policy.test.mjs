import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

const providerStatusSource = readFileSync(
  new URL("../src/components/ProviderStatusPill.tsx", import.meta.url),
  "utf8",
);
const settingsModalSource = readFileSync(
  new URL("../src/components/SettingsModal.tsx", import.meta.url),
  "utf8",
);
const messagesSource = readFileSync(
  new URL("../src/i18n/messages.ts", import.meta.url),
  "utf8",
);
const stylesSource = readFileSync(
  new URL("../src/styles.css", import.meta.url),
  "utf8",
);

test("the topbar provider status never spends tokens on automatic live checks", () => {
  assert.doesNotMatch(providerStatusSource, /api\.testSettings\(/);
  assert.doesNotMatch(providerStatusSource, /setInterval\(/);
});

test("settings only tests the provider after an explicit user action", () => {
  const testCalls = settingsModalSource.match(/api\.testSettings\(/g) ?? [];
  assert.equal(testCalls.length, 1);
  assert.doesNotMatch(settingsModalSource, /probeHealth/);
});

test("custom API mode uses one OpenAI-compatible form with gateway presets", () => {
  assert.doesNotMatch(settingsModalSource, /aria-label="LLM provider"/);
  assert.doesNotMatch(settingsModalSource, /function GatewayPanel/);
  assert.match(settingsModalSource, /customProviderPresets/);
  assert.match(settingsModalSource, /provider:\s*"other"/);
});

test("custom API security notice has clear spacing and modal headers have no divider", () => {
  assert.match(settingsModalSource, /className="muted small custom-provider-hint"/);
  assert.match(messagesSource, /mã hóa API key của bạn bằng Fernet/);
  const modalHeadRule = stylesSource.match(/\.modal-head\s*\{([^}]*)\}/)?.[1] ?? "";
  assert.doesNotMatch(modalHeadRule, /border-bottom/);
  assert.doesNotMatch(stylesSource, /\.modal-settings \.modal-head/);
  assert.match(
    stylesSource,
    /\.custom-provider-hint\s*\{[^}]*padding-top:\s*24px/,
  );
});
