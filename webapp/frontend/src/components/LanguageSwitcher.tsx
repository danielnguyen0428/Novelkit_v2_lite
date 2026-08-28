import { Globe } from "@phosphor-icons/react";
import { useI18n } from "../i18n/I18nProvider";
import type { LangCode } from "../i18n/types";

export function LanguageSwitcher() {
  const { lang, setLang, languages, t } = useI18n();
  const current = languages.find((l) => l.code === lang);

  return (
    <div className="lang-switcher">
      <label className="lang-switcher-label">
        <Globe size={15} weight="light" aria-hidden="true" />
        <span className="sr-only">{t("topbar.language")}</span>
        <select
          className="lang-switcher-select"
          value={lang}
          aria-label={t("topbar.language")}
          onChange={(e) => setLang(e.target.value as LangCode)}
        >
          {languages.map((l) => (
            <option key={l.code} value={l.code}>
              {l.native}
            </option>
          ))}
        </select>
        <span className="lang-switcher-current hide-sm" aria-hidden="true">
          {current?.native ?? lang}
        </span>
      </label>
    </div>
  );
}
