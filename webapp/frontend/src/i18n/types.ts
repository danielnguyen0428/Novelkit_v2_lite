export const LANG_CODES = ["vi", "en", "ko", "ja", "zh", "pt", "fr"] as const;

export type LangCode = (typeof LANG_CODES)[number];

export type MessageMap = Record<LangCode, string>;
