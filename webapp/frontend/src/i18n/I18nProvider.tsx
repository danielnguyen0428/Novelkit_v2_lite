import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import {
  DEFAULT_LANG,
  HTML_LANG,
  LANG_STORAGE_KEY,
  LANGUAGES,
} from "./languages";
import { detectLangFromLocation } from "./geoLocale";
import { translate } from "./messages";
import type { LangCode } from "./types";
import { LANG_CODES } from "./types";

interface I18nContextValue {
  lang: LangCode;
  setLang: (lang: LangCode) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
  languages: typeof LANGUAGES;
}

const I18nContext = createContext<I18nContextValue | null>(null);

function resolveInitialLang(): LangCode {
  if (typeof window === "undefined") return DEFAULT_LANG;

  const params = new URLSearchParams(window.location.search);
  const fromUrl = params.get("lang");
  if (fromUrl && (LANG_CODES as readonly string[]).includes(fromUrl)) {
    return fromUrl as LangCode;
  }

  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    if (saved && (LANG_CODES as readonly string[]).includes(saved)) {
      return saved as LangCode;
    }
  } catch {
    /* ignore */
  }

  return DEFAULT_LANG;
}

function shouldAutoDetectLang(): boolean {
  if (typeof window === "undefined") return false;
  const params = new URLSearchParams(window.location.search);
  if (params.get("lang")) return false;
  try {
    return !localStorage.getItem(LANG_STORAGE_KEY);
  } catch {
    return true;
  }
}

export function I18nProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<LangCode>(resolveInitialLang);

  const setLang = useCallback((next: LangCode) => {
    setLangState(next);
    try {
      localStorage.setItem(LANG_STORAGE_KEY, next);
    } catch {
      /* ignore */
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = HTML_LANG[lang];
  }, [lang]);

  useEffect(() => {
    if (!shouldAutoDetectLang()) return;
    detectLangFromLocation(setLang);
  }, [setLang]);

  const t = useCallback(
    (key: string, vars?: Record<string, string | number>) => translate(lang, key, vars),
    [lang],
  );

  const value = useMemo(
    () => ({ lang, setLang, t, languages: LANGUAGES }),
    [lang, setLang, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export function useT() {
  return useI18n().t;
}
