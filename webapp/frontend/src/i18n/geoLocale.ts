import type { LangCode } from "./types";
import { LANG_CODES } from "./types";
import { LANG_STORAGE_KEY } from "./languages";

const COUNTRY_LANG: Record<string, LangCode> = {
  VN: "vi",
  KR: "ko",
  JP: "ja",
  CN: "zh",
  TW: "zh",
  HK: "zh",
  MO: "zh",
  SG: "zh",
  PT: "pt",
  BR: "pt",
  FR: "fr",
  BE: "fr",
  LU: "fr",
  MC: "fr",
};

function hasSavedLang(): boolean {
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    return !!(saved && (LANG_CODES as readonly string[]).includes(saved));
  } catch {
    return false;
  }
}

function hasUrlLang(): boolean {
  if (typeof window === "undefined") return false;
  const fromUrl = new URLSearchParams(window.location.search).get("lang");
  return !!(fromUrl && (LANG_CODES as readonly string[]).includes(fromUrl));
}

async function countryFromCoords(lat: number, lng: number): Promise<string | null> {
  try {
    const url = new URL("https://api.bigdatacloud.net/data/reverse-geocode-client");
    url.searchParams.set("latitude", String(lat));
    url.searchParams.set("longitude", String(lng));
    url.searchParams.set("localityLanguage", "en");
    const res = await fetch(url.toString(), { signal: AbortSignal.timeout(8000) });
    if (!res.ok) return null;
    const data = (await res.json()) as { countryCode?: string };
    return data.countryCode?.toUpperCase() ?? null;
  } catch {
    return null;
  }
}

function langFromCountry(code: string): LangCode | null {
  return COUNTRY_LANG[code] ?? null;
}

/** Request geolocation once and map country → UI language (skipped if user already chose). */
export function detectLangFromLocation(
  onDetected: (lang: LangCode) => void,
): void {
  if (typeof window === "undefined" || !navigator.geolocation) return;
  if (hasSavedLang() || hasUrlLang()) return;

  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      const country = await countryFromCoords(pos.coords.latitude, pos.coords.longitude);
      if (!country) return;
      const lang = langFromCountry(country);
      if (lang) onDetected(lang);
    },
    () => {
      /* permission denied — keep English default */
    },
    { maximumAge: 86_400_000, timeout: 12_000, enableHighAccuracy: false },
  );
}
