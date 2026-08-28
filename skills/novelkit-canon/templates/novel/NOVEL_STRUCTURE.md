# Novel Workspace Template

Khi khởi tạo novel mới, tạo cấu trúc sau:

```
novels/[novel_name]/
├── PROJECT_DNA.md          ← Studio render từ templates/genres/PROJECT_DNA_<GENRE>.md
│                             (đơn genre) hoặc templates/PROJECT_DNA_TEMPLATE.md (hybrid)
├── PLAN.md                 ← Copy từ templates/PLAN_TEMPLATE.md  
├── GOAL_TRACKER.md         ← Copy từ templates/GOAL_TRACKER_TEMPLATE.md
├── memory/
│   └── Memory.md           ← Bộ nhớ dài hạn tác phẩm
├── logs/
│   └── pipeline_log.md     ← Token usage, agent calls, timing
│   └── pipeline_status.json ← Runtime status / breaker state
├── database/
│   ├── characters/
│   │   ├── _template.md    ← Character template
│   │   └── relationship_map.md
│   ├── worldbuilding/
│   │   ├── geography.md
│   │   ├── history.md
│   │   ├── politics.md
│   │   ├── economy.md
│   │   ├── culture.md
│   │   └── factions/
│   ├── systems/            ← Tùy genre
│   │   ├── magic.md (hoặc cultivation.md, tech.md)
│   │   ├── xianxia_world_operating_config.md (nếu genre = Xianxia)
│   │   ├── sci_fi_world_operating_config.md (nếu genre = Sci-fi)
│   │   ├── time_travel_causality_config.md (nếu genre = Time Travel)
│   │   ├── meta_system_operating_config.md (nếu genre = Meta Genre / System)
│   │   ├── artifacts.md
│   │   ├── creatures.md
│   │   └── organizations.md
│   ├── plot_threads/
│   │   ├── seeds_tracker.md
│   │   └── threads_master.md
│   └── timeline/
│       └── master_timeline.md
├── style_vault/
│   └── [genre]_examples.md ← Few-shot examples (max 50/genre)
├── outlines/
│   ├── master_outline.md   ← Three-Act Eight-Sequence overview
│   ├── arc_1/
│   │   ├── arc_1_overview.md
│   │   ├── chapter_001_outline.md
│   │   └── ...
│   └── arc_2/
│       └── ...
├── chapters/
│   ├── chapter_001.md
│   └── ...
└── reviews/
    ├── chapter_001_review.md
    └── ...
```

## PROJECT_DNA — chọn template theo genre

| Thể loại (slug) | File nguồn |
|---|---|
| `xianxia` | `templates/genres/PROJECT_DNA_XIANXIA.md` |
| `urban` | `templates/genres/PROJECT_DNA_URBAN.md` |
| `romance` | `templates/genres/PROJECT_DNA_ROMANCE.md` |
| `scifi` | `templates/genres/PROJECT_DNA_SCIFI.md` |
| `time_travel` | `templates/genres/PROJECT_DNA_TIME_TRAVEL.md` |
| `meta_genre` | `templates/genres/PROJECT_DNA_META_GENRE.md` |
| Hybrid (có `genre_secondary`) | `templates/PROJECT_DNA_TEMPLATE.md` |

Studio (`webapp/api/dna_form.py`) load file tương ứng, điền form fields, ghi `PROJECT_DNA.md`.
Frontmatter ghi `template_source:` để trace nguồn template.

Ghi chú canon v1.5:
- Dùng `chapters/`, không dùng `drafts/`
- Dùng `database/plot_threads/`, không dùng `database/plot_arcs/`
- Dùng `outlines/master_outline.md`, không để `master_outline.md` ở root
