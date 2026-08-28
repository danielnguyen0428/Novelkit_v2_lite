// Typed API client for the NovelKit FastAPI surface.
// Re-exports shared @novelkit/api-client configured for the local-only API.

import { createApiClient } from "@novelkit/api-client";

function resolveApiBase(): string {
  const fromEnv = (import.meta.env.VITE_API_BASE ?? "").replace(/\/$/, "");
  if (fromEnv) return fromEnv;
  return "";
}

const API_BASE = resolveApiBase();

export const api = createApiClient({ baseUrl: API_BASE });

// Re-export types for backward compatibility
export type * from "@novelkit/api-client";
