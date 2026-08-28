---
name: novelkit-canon
description: "Creative brain of NovelKit packaged as a Hermes skill bundle. Provides the 17 genre canon packs (consistency rules, style, Author Style, Depth, Genre Operating systems, vocabulary whitelists), StoryDepth cross-genre field execution, creative templates, reference projects, and the standard creative docs (STYLE_GUIDE/CONTRACTS/API/IDENTITY/RUNBOOK). Load the pack(s) for the running genre when bootstrapping, outlining, writing, reviewing, or syncing a chapter."
metadata:
  version: "1.0.0"
  authority: shared-canon-wins
---

# NovelKit Canon

This bundle is the **creative brain** of NovelKit — the literary domain
knowledge preserved 100% from `_novelkit_source/` during the Hermes migration
(Requirements 2, 3, 4). It is loaded by the Hermes context-engine according to
the genre declared in a novel's `PROJECT_DNA.md`.

## Layout

```text
novelkit-canon/
├── SKILL.md · _meta.json          # this manifest
├── canon/system/<pack>/           # 17 genre canon packs (incl. StoryDepth)
├── templates/                     # PROJECT_DNA, character, worldbuilding,
│                                  # plot_threads, timeline, outline, review, ...
├── creative_refs/                 # worked reference project bundles
└── docs/                          # STYLE_GUIDE, CONTRACTS, API, IDENTITY, RUNBOOK
```

## Genre packs (17)

Apocalypse · Cthulhu · Dark Theme · Many Children · Meta Genre · Romance ·
Rules Horror · Sci-fi · Short Form · **StoryDepth** · Streaming · Substitute ·
Time Travel · Urban · War Espionage · Xianxia · eSports

- **Xianxia** keeps the full module set: Cultivation Progression System,
  Xianxia World Operating System, Texture, Worldbuilding guide, Author Style,
  and the 7 baseline laws (Requirement 2.2).
- **StoryDepth/CREATE_NOVEL_FIELD_EXECUTION.md** is the cross-genre field
  execution (Core Wound, World Pressure, Scene Vitality, motif angle, reader
  loop) and applies to every genre (Requirement 2.3).
- Packs that ship a `vocabulary.txt` provide the whitelist consumed by the
  language guard (Requirement 2.5).

## How to load

1. Resolve the genre slug from `PROJECT_DNA.md` (`genre`, plus
   `genre_secondary` / `hybrid_ratio` when hybrid).
2. Ask the context-engine for the matching `canon/system/<pack>/` content
   (retrieval-first — retrieve before opening whole files).
3. For hybrid novels, load both the primary and secondary packs; the primary
   genre wins on conflict, the secondary only adds canon/whitelist/style.

## Authority rules (do not break)

- **Shared canon wins.** Content under `canon/system/*` overrides any persona
  `SOUL.md` (Requirement 3.3).
- **Disk beats chat; canon beats index.** Canon files are the source of truth;
  retrieval/index/runtime state is derivative and must never override canon
  (CONTRACTS §1, Requirement 4.3).
- Content here is preserved verbatim from the source — never summarize or trim
  canon when consuming it.
