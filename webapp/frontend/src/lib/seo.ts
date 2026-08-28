import { useEffect } from "react";

export type PageMeta = {
  title: string;
  description?: string;
  canonical?: string;
  noindex?: boolean;
};

const SITE = "NovelKit";
const DEFAULT_DESC =
  "NovelKit — công cụ sáng tác tiểu thuyết AI với canon, memory layer và quality gate.";

function upsertMeta(name: string, content: string, attr: "name" | "property" = "name") {
  let el = document.querySelector(`meta[${attr}="${name}"]`) as HTMLMetaElement | null;
  if (!el) {
    el = document.createElement("meta");
    el.setAttribute(attr, name);
    document.head.appendChild(el);
  }
  el.content = content;
}

function upsertCanonical(href: string) {
  let el = document.querySelector('link[rel="canonical"]') as HTMLLinkElement | null;
  if (!el) {
    el = document.createElement("link");
    el.rel = "canonical";
    document.head.appendChild(el);
  }
  el.href = href;
}

/** Sync document title and core meta tags for SPA routes. */
export function useDocumentMeta(meta: PageMeta) {
  useEffect(() => {
    const fullTitle = meta.title.includes(SITE) ? meta.title : `${meta.title} · ${SITE}`;
    document.title = fullTitle;

    upsertMeta("description", meta.description ?? DEFAULT_DESC);
    upsertMeta("og:title", fullTitle, "property");
    upsertMeta("og:description", meta.description ?? DEFAULT_DESC, "property");
    upsertMeta("twitter:title", fullTitle);
    upsertMeta("twitter:description", meta.description ?? DEFAULT_DESC);

    if (meta.canonical) {
      upsertCanonical(meta.canonical);
      upsertMeta("og:url", meta.canonical, "property");
    }

    upsertMeta("robots", meta.noindex ? "noindex, nofollow" : "index, follow");
  }, [meta.title, meta.description, meta.canonical, meta.noindex]);
}
