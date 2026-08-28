import { useEffect, useState } from "react";
import { CheckCircle, Plug, X } from "@phosphor-icons/react";
import { api } from "../api";
import { useT } from "../i18n/I18nProvider";
import { ProviderStatusLine, type HealthState } from "./ProviderStatusPill";
import type { ProviderCatalog, ProviderSettings } from "../types";

interface Props {
  open: boolean;
  onClose: () => void;
  onSaved: (s: ProviderSettings) => void;
}

type CustomProviderPreset = ProviderCatalog["other_presets"][number];

function customProviderPresets(catalog: ProviderCatalog | null): CustomProviderPreset[] {
  const gatewayPresets = (catalog?.gateways ?? []).flatMap((provider) => {
    const baseUrl =
      provider.base_urls?.[0] ??
      provider.endpoints.find((endpoint) => endpoint.url.endsWith("/chat/completions"))?.url;

    if (!baseUrl) return [];
    return [{ id: `gateway-${provider.id}`, label: provider.label, base_url: baseUrl, model: provider.default_model }];
  });

  return [...gatewayPresets, ...(catalog?.other_presets ?? [])];
}

/** Provider settings for the single-operator local runtime. */
export function SettingsModal({ open, onClose, onSaved }: Props) {
  const t = useT();
  const [settings, setSettings] = useState<ProviderSettings | null>(null);
  const [catalog, setCatalog] = useState<ProviderCatalog | null>(null);
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthState>("unconfigured");

  useEffect(() => {
    if (!open) return;
    Promise.all([api.getSettings(), api.getProviderCatalog()])
      .then(([s, c]) => {
        setSettings(s);
        setCatalog(c);
        setBaseUrl(s.base_url);
        setModel(s.model);
        setApiKey("");
        setMsg(null);
        setHealth(s.configured ? "configured" : "unconfigured");
      })
      .catch((e) => setMsg(`Error: ${(e as Error).message}`));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  const presets = customProviderPresets(catalog);

  async function save() {
    setBusy(true);
    setMsg(null);
    try {
      const body: { provider: "other"; base_url: string; model: string; api_key?: string } = {
        provider: "other",
        base_url: baseUrl,
        model,
      };
      if (apiKey) body.api_key = apiKey;
      const saved = await api.saveSettings(body);
      setSettings(saved);
      setApiKey("");
      onSaved(saved);
      setMsg(t("settings.saved"));
      setHealth(saved.configured ? "configured" : "unconfigured");
    } catch (e) {
      setMsg(`Error: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  async function test() {
    setBusy(true);
    setMsg(t("settings.testing"));
    try {
      const body: { base_url: string; model: string; api_key?: string } = { base_url: baseUrl, model };
      if (apiKey) body.api_key = apiKey;
      const result = await api.testSettings(body);
      setHealth(result.ok ? "ok" : "error");
      setMsg(result.ok ? `Connected: ${result.detail}` : `Connection failed: ${result.detail}`);
    } catch (e) {
      setHealth("error");
      setMsg(`Connection failed: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop">
      <div className="modal modal-settings" role="dialog" aria-modal="true" aria-labelledby="settings-title">
        <div className="modal-head">
          <div>
            <h2 id="settings-title">Kết nối model local</h2>
            <ProviderStatusLine settings={settings} health={health} />
          </div>
          <button className="btn-mini" onClick={onClose} aria-label={t("settings.closeAria")}>
            <X size={15} weight="light" />
          </button>
        </div>

        <p className="muted small custom-provider-hint">
          NovelKit V2-lite chạy bằng API key của bạn. Key được mã hóa trong database local; khóa mã hóa nằm trong `.secrets`.
        </p>

        <div className="provider-section">
          <div className="provider-section-head">
            <span className="section-title">OpenAI-compatible</span>
          </div>

          <label className="field">
            Preset
            <div className="presets">
              {presets.map((preset) => (
                <button
                  key={preset.id}
                  type="button"
                  className={`btn-mini ${baseUrl === preset.base_url ? "active" : ""}`}
                  onClick={() => {
                    setBaseUrl(preset.base_url);
                    if (preset.model) setModel(preset.model);
                  }}
                >
                  {preset.label}
                </button>
              ))}
            </div>
          </label>

          <label className="field">
            Endpoint / Base URL
            <input value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
          </label>

          <label className="field">
            Model
            <input
              value={model}
              onChange={(e) => setModel(e.target.value)}
              placeholder="gpt-4o-mini / openai/gpt-4o / gemini-2.0-flash …"
            />
          </label>
        </div>

        <label className="field">
          API key {settings?.api_key_set && <span className="muted small">{t("settings.apiKeySet", { fingerprint: settings.api_key_fingerprint })}</span>}
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={settings?.api_key_set ? t("settings.apiKeyPlaceholderKeep") : "sk-…"}
          />
        </label>

        <div className="modal-actions">
          <button className="btn ghost" disabled={busy} onClick={test}>
            <Plug size={15} weight="light" /> {t("settings.testConnection")}
          </button>
          <button className="btn" disabled={busy} onClick={save}>
            <CheckCircle size={15} weight="light" /> {t("settings.save")}
          </button>
        </div>
        {msg && <div className="modal-msg">{msg}</div>}
      </div>
    </div>
  );
}
