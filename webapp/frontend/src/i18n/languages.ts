import type { LangCode } from "./types";

export interface LanguageOption {
  code: LangCode;
  label: string;
  native: string;
}

export const LANGUAGES: LanguageOption[] = [
  { code: "vi", label: "Vietnamese", native: "Tiếng Việt" },
  { code: "en", label: "English", native: "English" },
  { code: "ko", label: "Korean", native: "한국어" },
  { code: "ja", label: "Japanese", native: "日本語" },
  { code: "zh", label: "Chinese", native: "中文" },
  { code: "pt", label: "Portuguese", native: "Português" },
  { code: "fr", label: "French", native: "Français" },
];

export const DEFAULT_LANG: LangCode = "en";

export const LANG_STORAGE_KEY = "novelkit_lang";

export const HTML_LANG: Record<LangCode, string> = {
  vi: "vi",
  en: "en",
  ko: "ko",
  ja: "ja",
  zh: "zh-Hans",
  pt: "pt",
  fr: "fr",
};
