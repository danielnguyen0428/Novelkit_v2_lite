import { GearSix } from "@phosphor-icons/react";
import { useT } from "../i18n/I18nProvider";
import type { ProviderSettings } from "../types";

type HealthState = "checking" | "ok" | "error" | "configured" | "unconfigured";

interface Props {
  settings: ProviderSettings | null;
  onOpenSettings: () => void;
}

export function ProviderStatusPill({ settings, onOpenSettings }: Props) {
  const t = useT();

  const dotClass = settings?.configured
    ? "provider-status-dot configured"
    : "provider-status-dot warn";

  const modelText = settings?.configured ? settings.model : t("topbar.llmNotConfigured");

  return (
    <div className="provider-status-pill">
      <span className={dotClass} aria-hidden="true" />
      <span className="provider-status-text">
        <span className="provider-status-label">Provider:</span>{" "}
        <span className="provider-status-model">{modelText}</span>
      </span>
      <button
        type="button"
        className="btn-icon provider-status-gear"
        onClick={onOpenSettings}
        aria-label={t("topbar.settings")}
        title={t("topbar.settings")}
      >
        <GearSix size={15} weight="light" />
      </button>
    </div>
  );
}

export function ProviderStatusLine({
  settings,
  health,
}: {
  settings: ProviderSettings | null;
  health: HealthState;
}) {
  const t = useT();
  const dotClass =
    health === "ok"
      ? "provider-status-dot ok"
      : health === "error"
        ? "provider-status-dot err"
        : health === "configured"
          ? "provider-status-dot configured"
          : "provider-status-dot warn";

  const modelText = settings?.configured
    ? settings.model
    : t("topbar.llmNotConfigured");

  return (
    <div className="provider-status-line">
      <span className={dotClass} aria-hidden="true" />
      <span>
        Provider: {modelText}
      </span>
    </div>
  );
}

export type { HealthState };
