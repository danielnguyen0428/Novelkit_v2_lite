# Migration Inventory — Phase 0

> Sinh tự động bởi `migration/inventory.py` lúc 2026-06-29T16:47:13.331840+00:00.
> Nguồn: `/Users/meow/Novelkitv2/_novelkit_source`

## Tổng quan

- Tổng số file kiểm kê: **1070**
- Số file **bắt buộc-giữ** (creative-knowledge + creative-config): **339**
- File mồ côi (must-keep thiếu đích): **0**
- Độ phủ ánh xạ must-keep: **✅ ĐẠT 100%**
- Mục cần review thủ công: **20**

### Phân loại theo category

| category | số file |
|---|---|
| creative-knowledge | 326 |
| creative-config | 13 |
| business-logic | 76 |
| legacy-infra | 655 |

### Phân loại theo mapping status

| mapping status | số file |
|---|---|
| kept | 339 |
| extracted | 76 |
| removed-legacy | 655 |

## 🔎 Cần review thủ công

- `.seo-cache/audit-scores.json`
- `.seo-cache/pages/homepage/geo.json`
- `.seo-cache/plan.json`
- `.seo-cache/site-meta.json`
- `.seo-cache/sitemap.json`
- `.well-known/jwks.json`
- `.well-known/mcp/server-card.json`
- `.well-known/oauth-authorization-server`
- `.well-known/oauth-protected-resource`
- `.well-known/openid-configuration`
- `_headers`
- `_worker.js`
- `agent-ready/README.md`
- `agent-ready/dns-aid.zone`
- `auth.md`
- `index.md`
- `seo-reports/ACTION-PLAN.md`
- `seo-reports/FULL-AUDIT-REPORT.md`
- `seo-reports/GEO-ANALYSIS.md`
- `seo-reports/VALIDATION-REPORT.md`

## Danh sách bắt buộc-giữ (must-keep → đích)

| source | category | target |
|---|---|---|
| .creative_refs/ta_de_van_tam/bootstrap.characters/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.characters/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.characters/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.characters/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.characters/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.characters/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.characters/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.characters/task_runner_result.json |
| .creative_refs/ta_de_van_tam/bootstrap.master_outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.master_outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.master_outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.master_outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.master_outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.master_outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.master_outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.master_outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/bootstrap.plot_threads/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.plot_threads/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.plot_threads/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.plot_threads/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.plot_threads/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.plot_threads/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.plot_threads/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.plot_threads/task_runner_result.json |
| .creative_refs/ta_de_van_tam/bootstrap.timeline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.timeline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.timeline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.timeline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.timeline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.timeline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.timeline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.timeline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.world/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.world/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.world/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.world/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0001.outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0001.outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0001.outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0001.outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0001.review/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0001.review/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0001.sync/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0001.sync/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0001.sync/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0001.sync/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0001.write/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0001.write/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0001.write/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0001.write/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.write/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0002.outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0002.outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0002.outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0002.outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0002.review/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0002.review/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0002.sync/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0002.sync/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0002.sync/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0002.sync/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0002.write/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0002.write/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0002.write/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0002.write/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.write/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0003.outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0003.outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0003.outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0003.outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0003.review/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0003.review/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0003.sync/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0003.sync/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0003.sync/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0003.sync/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0003.write/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0003.write/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0003.write/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0003.write/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.write/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0004.outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0004.outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0004.outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0004.outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0004.review/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0004.review/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0004.sync/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0004.sync/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0004.sync/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0004.sync/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0004.write/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0004.write/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0004.write/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0004.write/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.write/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0005.outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0005.outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0005.outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0005.outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0005.review/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0005.review/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0005.sync/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0005.sync/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0005.sync/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0005.sync/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0005.write/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0005.write/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0005.write/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0005.write/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.write/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.characters/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.characters/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.characters/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.characters/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.characters/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.characters/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.characters/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.characters/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.master_outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.master_outline/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.master_outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.master_outline/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.master_outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.master_outline/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.master_outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.master_outline/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.plot_threads/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.plot_threads/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.plot_threads/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.plot_threads/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.plot_threads/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.plot_threads/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.plot_threads/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.plot_threads/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.timeline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.timeline/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.timeline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.timeline/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.timeline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.timeline/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.timeline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.timeline/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.world/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.world/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.world/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.world/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.world/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.world/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.world/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.world/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.outline/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.outline/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.outline/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.outline/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.review/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.review/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.review/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.review/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.sync/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.sync/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.sync/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.sync/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.sync/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.sync/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.sync/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.sync/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.write/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.write/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.write/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.write/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.write/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.write/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.write/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.write/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.outline/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.outline/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.outline/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.outline/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.outline/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.outline/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.outline/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.outline/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.review/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.review/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.review/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.review/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.write/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.write/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.write/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.write/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.write/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.write/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.write/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.write/task_runner_result.json |
| .creative_refs/truong_sinh_do/bootstrap.characters/creative_input_bundle.md | creative-knowledge | skills/novelkit-canon/creative_refs/truong_sinh_do/bootstrap.characters/creative_input_bundle.md |
| .creative_refs/truong_sinh_do/bootstrap.characters/creative_input_bundle.meta.json | creative-knowledge | skills/novelkit-canon/creative_refs/truong_sinh_do/bootstrap.characters/creative_input_bundle.meta.json |
| .creative_refs/truong_sinh_do/bootstrap.characters/task_runner_prompt.md | creative-knowledge | skills/novelkit-canon/creative_refs/truong_sinh_do/bootstrap.characters/task_runner_prompt.md |
| .creative_refs/truong_sinh_do/bootstrap.characters/task_runner_result.json | creative-knowledge | skills/novelkit-canon/creative_refs/truong_sinh_do/bootstrap.characters/task_runner_result.json |
| API.md | creative-knowledge | skills/novelkit-canon/docs/API.md |
| CONTRACTS.md | creative-knowledge | skills/novelkit-canon/docs/CONTRACTS.md |
| IDENTITY.md | creative-knowledge | skills/novelkit-canon/docs/IDENTITY.md |
| RUNBOOK.md | creative-knowledge | skills/novelkit-canon/docs/RUNBOOK.md |
| SKILL/agent-team-orchestration-1.0.0/SKILL.md | creative-config | skills/agent-team-orchestration-1.0.0/SKILL.md |
| SKILL/agent-team-orchestration-1.0.0/_meta.json | creative-config | skills/agent-team-orchestration-1.0.0/_meta.json |
| SKILL/agent-team-orchestration-1.0.0/references/communication.md | creative-knowledge | skills/agent-team-orchestration-1.0.0/references/communication.md |
| SKILL/agent-team-orchestration-1.0.0/references/patterns.md | creative-knowledge | skills/agent-team-orchestration-1.0.0/references/patterns.md |
| SKILL/agent-team-orchestration-1.0.0/references/task-lifecycle.md | creative-knowledge | skills/agent-team-orchestration-1.0.0/references/task-lifecycle.md |
| SKILL/agent-team-orchestration-1.0.0/references/team-setup.md | creative-knowledge | skills/agent-team-orchestration-1.0.0/references/team-setup.md |
| SKILL/elite-longterm-memory-1.2.3/README.md | creative-knowledge | skills/elite-longterm-memory-1.2.3/README.md |
| SKILL/elite-longterm-memory-1.2.3/SKILL.md | creative-config | skills/elite-longterm-memory-1.2.3/SKILL.md |
| SKILL/elite-longterm-memory-1.2.3/_meta.json | creative-config | skills/elite-longterm-memory-1.2.3/_meta.json |
| SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | creative-knowledge | skills/elite-longterm-memory-1.2.3/bin/elite-memory.js |
| SKILL/elite-longterm-memory-1.2.3/package.json | creative-knowledge | skills/elite-longterm-memory-1.2.3/package.json |
| SKILL/fix-issues-1.0.0/SKILL.md | creative-config | skills/fix-issues-1.0.0/SKILL.md |
| SKILL/self-improving-agent-3.0.11/SKILL.md | creative-config | skills/self-improving-agent-3.0.11/SKILL.md |
| SKILL/self-improving-agent-3.0.11/_meta.json | creative-config | skills/self-improving-agent-3.0.11/_meta.json |
| SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | creative-knowledge | skills/self-improving-agent-3.0.11/assets/ERRORS.md |
| SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | creative-knowledge | skills/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md |
| SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | creative-knowledge | skills/self-improving-agent-3.0.11/assets/LEARNINGS.md |
| SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | creative-knowledge | skills/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md |
| SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | creative-knowledge | skills/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md |
| SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | creative-knowledge | skills/self-improving-agent-3.0.11/hooks/openclaw/handler.js |
| SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | creative-knowledge | skills/self-improving-agent-3.0.11/hooks/openclaw/handler.ts |
| SKILL/self-improving-agent-3.0.11/references/examples.md | creative-knowledge | skills/self-improving-agent-3.0.11/references/examples.md |
| SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | creative-knowledge | skills/self-improving-agent-3.0.11/references/hooks-setup.md |
| SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | creative-knowledge | skills/self-improving-agent-3.0.11/references/openclaw-integration.md |
| SKILL/self-improving-agent-3.0.11/scripts/activator.sh | creative-knowledge | skills/self-improving-agent-3.0.11/scripts/activator.sh |
| SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | creative-knowledge | skills/self-improving-agent-3.0.11/scripts/error-detector.sh |
| SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | creative-knowledge | skills/self-improving-agent-3.0.11/scripts/extract-skill.sh |
| SKILL/telemetry-guardian-v1.0/SKILL.md | creative-config | skills/telemetry-guardian-v1.0/SKILL.md |
| SOUL.md | creative-knowledge | subagents/orchestrator/SOUL.md |
| STYLE_GUIDE.md | creative-knowledge | skills/novelkit-canon/docs/STYLE_GUIDE.md |
| config/ai_flavor_patterns.json | creative-config | config/ai_flavor_patterns.json |
| config/cool_point_markers.json | creative-config | config/cool_point_markers.json |
| config/genre_aliases.json | creative-config | config/genre_aliases.json |
| config/strand_keywords.json | creative-config | config/strand_keywords.json |
| config/xianxia_language_guard.json | creative-config | config/language_guard/xianxia.json |
| sub_agents/chan_nhan/SOUL.md | creative-knowledge | subagents/sub_agents/chan_nhan/SOUL.md |
| sub_agents/dong_tu/SOUL.md | creative-knowledge | subagents/sub_agents/dong_tu/SOUL.md |
| sub_agents/huyet_thu/SOUL.md | creative-knowledge | subagents/sub_agents/huyet_thu/SOUL.md |
| sub_agents/mong_yem/SOUL.md | creative-knowledge | subagents/sub_agents/mong_yem/SOUL.md |
| sub_agents/thien_co_tu/SOUL.md | creative-knowledge | subagents/sub_agents/thien_co_tu/SOUL.md |
| sub_agents_do_thi/bo_cuc/SOUL.md | creative-knowledge | subagents/sub_agents_do_thi/bo_cuc/SOUL.md |
| sub_agents_do_thi/but_gia/SOUL.md | creative-knowledge | subagents/sub_agents_do_thi/but_gia/SOUL.md |
| sub_agents_do_thi/kien_truc_su/SOUL.md | creative-knowledge | subagents/sub_agents_do_thi/kien_truc_su/SOUL.md |
| sub_agents_do_thi/nhan_sinh/SOUL.md | creative-knowledge | subagents/sub_agents_do_thi/nhan_sinh/SOUL.md |
| sub_agents_do_thi/tham_phan/SOUL.md | creative-knowledge | subagents/sub_agents_do_thi/tham_phan/SOUL.md |
| sub_agents_he_thong/chu_than/SOUL.md | creative-knowledge | subagents/sub_agents_he_thong/chu_than/SOUL.md |
| sub_agents_he_thong/giam_sat/SOUL.md | creative-knowledge | subagents/sub_agents_he_thong/giam_sat/SOUL.md |
| sub_agents_he_thong/giao_dien/SOUL.md | creative-knowledge | subagents/sub_agents_he_thong/giao_dien/SOUL.md |
| sub_agents_he_thong/ky_chu/SOUL.md | creative-knowledge | subagents/sub_agents_he_thong/ky_chu/SOUL.md |
| sub_agents_he_thong/nhiem_vu/SOUL.md | creative-knowledge | subagents/sub_agents_he_thong/nhiem_vu/SOUL.md |
| sub_agents_khoa_huyen/ban_the/SOUL.md | creative-knowledge | subagents/sub_agents_khoa_huyen/ban_the/SOUL.md |
| sub_agents_khoa_huyen/ky_di/SOUL.md | creative-knowledge | subagents/sub_agents_khoa_huyen/ky_di/SOUL.md |
| sub_agents_khoa_huyen/luong_tu/SOUL.md | creative-knowledge | subagents/sub_agents_khoa_huyen/luong_tu/SOUL.md |
| sub_agents_khoa_huyen/ma_tran/SOUL.md | creative-knowledge | subagents/sub_agents_khoa_huyen/ma_tran/SOUL.md |
| sub_agents_khoa_huyen/oracle/SOUL.md | creative-knowledge | subagents/sub_agents_khoa_huyen/oracle/SOUL.md |
| sub_agents_ngon_tinh/cam_sat/SOUL.md | creative-knowledge | subagents/sub_agents_ngon_tinh/cam_sat/SOUL.md |
| sub_agents_ngon_tinh/hong_nhan/SOUL.md | creative-knowledge | subagents/sub_agents_ngon_tinh/hong_nhan/SOUL.md |
| sub_agents_ngon_tinh/minh_kinh/SOUL.md | creative-knowledge | subagents/sub_agents_ngon_tinh/minh_kinh/SOUL.md |
| sub_agents_ngon_tinh/nguyet_lao/SOUL.md | creative-knowledge | subagents/sub_agents_ngon_tinh/nguyet_lao/SOUL.md |
| sub_agents_ngon_tinh/tinh_kiep/SOUL.md | creative-knowledge | subagents/sub_agents_ngon_tinh/tinh_kiep/SOUL.md |
| sub_agents_xuyen_khong/ban_do/SOUL.md | creative-knowledge | subagents/sub_agents_xuyen_khong/ban_do/SOUL.md |
| sub_agents_xuyen_khong/luan_hoi/SOUL.md | creative-knowledge | subagents/sub_agents_xuyen_khong/luan_hoi/SOUL.md |
| sub_agents_xuyen_khong/menh_chu/SOUL.md | creative-knowledge | subagents/sub_agents_xuyen_khong/menh_chu/SOUL.md |
| sub_agents_xuyen_khong/su_quan/SOUL.md | creative-knowledge | subagents/sub_agents_xuyen_khong/su_quan/SOUL.md |
| sub_agents_xuyen_khong/thien_dao/SOUL.md | creative-knowledge | subagents/sub_agents_xuyen_khong/thien_dao/SOUL.md |
| system/Apocalypse/Depth/Apocalypse_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Apocalypse/Depth/Apocalypse_Depth_Contract.md |
| system/Apocalypse/Genre Operating/Apocalypse_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Apocalypse/Genre Operating/Apocalypse_Operating_Guide.md |
| system/Apocalypse/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/Apocalypse/vocabulary.txt |
| system/Cthulhu/Depth/Cthulhu_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Cthulhu/Depth/Cthulhu_Depth_Contract.md |
| system/Cthulhu/Genre Operating/Cthulhu_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Cthulhu/Genre Operating/Cthulhu_Operating_Guide.md |
| system/Cthulhu/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/Cthulhu/vocabulary.txt |
| system/Dark Theme/Depth/DarkTheme_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Dark Theme/Depth/DarkTheme_Depth_Contract.md |
| system/Dark Theme/Genre Operating/DarkTheme_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Dark Theme/Genre Operating/DarkTheme_Operating_Guide.md |
| system/Dark Theme/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/Dark Theme/vocabulary.txt |
| system/Many Children/Depth/ManyChildren_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Many Children/Depth/ManyChildren_Depth_Contract.md |
| system/Many Children/Genre Operating/ManyChildren_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Many Children/Genre Operating/ManyChildren_Operating_Guide.md |
| system/Many Children/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/Many Children/vocabulary.txt |
| system/Meta Genre/Author Style/giang-ho-tai-kien-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/Author Style/giang-ho-tai-kien-style-profile.md |
| system/Meta Genre/Author Style/mac-huong-dong-khuu-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/Author Style/mac-huong-dong-khuu-style-profile.md |
| system/Meta Genre/Author Style/mac-vu-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/Author Style/mac-vu-style-profile.md |
| system/Meta Genre/Author Style/tan-phong-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/Author Style/tan-phong-style-profile.md |
| system/Meta Genre/Author Style/thanh-sam-thu-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/Author Style/thanh-sam-thu-style-profile.md |
| system/Meta Genre/Depth/MetaGenre_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/Depth/MetaGenre_Depth_Contract.md |
| system/Meta Genre/Genre Operating/MetaGenre_System_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/Genre Operating/MetaGenre_System_Operating_Guide.md |
| system/Meta Genre/MetaGenre_consistency_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/MetaGenre_consistency_rules.md |
| system/Meta Genre/MetaGenre_style.md | creative-knowledge | skills/novelkit-canon/canon/system/Meta Genre/MetaGenre_style.md |
| system/Romance/Author Style/[CM] CoMan_GuMan_romance_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Romance/Author Style/[CM] CoMan_GuMan_romance_rules.md |
| system/Romance/Author Style/[DH] DongHoa_TongHua_romance_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Romance/Author Style/[DH] DongHoa_TongHua_romance_rules.md |
| system/Romance/Author Style/[DM] DinhMac_DingMo_romance_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Romance/Author Style/[DM] DinhMac_DingMo_romance_rules.md |
| system/Romance/Author Style/[PNTT] PhiNgaTuTon_FeiWoSiCun_romance_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Romance/Author Style/[PNTT] PhiNgaTuTon_FeiWoSiCun_romance_rules.md |
| system/Romance/Author Style/[TDO] TanDiO_XinYiWu_romance_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Romance/Author Style/[TDO] TanDiO_XinYiWu_romance_rules.md |
| system/Romance/Depth/Romance_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Romance/Depth/Romance_Depth_Contract.md |
| system/Romance/Romance_consistency_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Romance/Romance_consistency_rules.md |
| system/Romance/Romance_style.md | creative-knowledge | skills/novelkit-canon/canon/system/Romance/Romance_style.md |
| system/Rules Horror/Depth/RulesHorror_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Rules Horror/Depth/RulesHorror_Depth_Contract.md |
| system/Rules Horror/Genre Operating/RulesHorror_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Rules Horror/Genre Operating/RulesHorror_Operating_Guide.md |
| system/Rules Horror/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/Rules Horror/vocabulary.txt |
| system/Sci-fi/Author Style/luu-tu-han-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Author Style/luu-tu-han-style-profile.md |
| system/Sci-fi/Author Style/thai-hong-chi-mon-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Author Style/thai-hong-chi-mon-style-profile.md |
| system/Sci-fi/Author Style/thap-nien-that-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Author Style/thap-nien-that-style-profile.md |
| system/Sci-fi/Author Style/that-thap-nhi-bien-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Author Style/that-thap-nhi-bien-style-profile.md |
| system/Sci-fi/Author Style/vien-dong-style-profile.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Author Style/vien-dong-style-profile.md |
| system/Sci-fi/Depth/SciFi_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Depth/SciFi_Depth_Contract.md |
| system/Sci-fi/Genre Operating/SciFi_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Genre Operating/SciFi_Operating_Guide.md |
| system/Sci-fi/Sci-fi_consistency_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Sci-fi_consistency_rules.md |
| system/Sci-fi/Sci-fi_style.md | creative-knowledge | skills/novelkit-canon/canon/system/Sci-fi/Sci-fi_style.md |
| system/Short Form/Depth/ShortForm_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Short Form/Depth/ShortForm_Depth_Contract.md |
| system/Short Form/Genre Operating/ShortForm_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Short Form/Genre Operating/ShortForm_Operating_Guide.md |
| system/Short Form/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/Short Form/vocabulary.txt |
| system/StoryDepth/CREATE_NOVEL_FIELD_EXECUTION.md | creative-knowledge | skills/novelkit-canon/canon/system/StoryDepth/CREATE_NOVEL_FIELD_EXECUTION.md |
| system/Streaming/Depth/Streaming_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Streaming/Depth/Streaming_Depth_Contract.md |
| system/Streaming/Genre Operating/Streaming_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Streaming/Genre Operating/Streaming_Operating_Guide.md |
| system/Streaming/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/Streaming/vocabulary.txt |
| system/Substitute/Depth/Substitute_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Substitute/Depth/Substitute_Depth_Contract.md |
| system/Substitute/Genre Operating/Substitute_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Substitute/Genre Operating/Substitute_Operating_Guide.md |
| system/Substitute/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/Substitute/vocabulary.txt |
| system/Time Travel/Author Style/[AV] AViet_AYue_xuyenkhong_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[AV] AViet_AYue_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[BD] BuiDoCau_PeiTuGou_chuthien_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[BD] BuiDoCau_PeiTuGou_chuthien_rules.md |
| system/Time Travel/Author Style/[HT] PhanNoHuongTieu_AngryBanana_xuyenkhong_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[HT] PhanNoHuongTieu_AngryBanana_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[LU] LaoUngTieuKe_VanTocChiKiep_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[LU] LaoUngTieuKe_VanTocChiKiep_rules.md |
| system/Time Travel/Author Style/[MB] MaiBaoTieuLangQuan_DaiPhung_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[MB] MaiBaoTieuLangQuan_DaiPhung_rules.md |
| system/Time Travel/Author Style/[MN] MaoNi_CatNi_xuyenkhong_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[MN] MaoNi_CatNi_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[NQ] NguyetQuan_YueGuan_xuyenkhong_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[NQ] NguyetQuan_YueGuan_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[TG] TamGioiDaiSu_SanJieDaShi_xuyenkhong_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[TG] TamGioiDaiSu_SanJieDaShi_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[TT] TruuTu_HuiShuoHua_hethong_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[TT] TruuTu_HuiShuoHua_hethong_rules.md |
| system/Time Travel/Author Style/[ZT] Zhttty_TruongHang_vohankhungbo_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Author Style/[ZT] Zhttty_TruongHang_vohankhungbo_rules.md |
| system/Time Travel/Depth/TimeTravel_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Depth/TimeTravel_Depth_Contract.md |
| system/Time Travel/Genre Operating/TimeTravel_Causality_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/Genre Operating/TimeTravel_Causality_Guide.md |
| system/Time Travel/TimeTravel_consistency_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/TimeTravel_consistency_rules.md |
| system/Time Travel/TimeTravel_style.md | creative-knowledge | skills/novelkit-canon/canon/system/Time Travel/TimeTravel_style.md |
| system/Urban/Author Style/[KV] KhieuVu_Dancing_urban_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Author Style/[KV] KhieuVu_Dancing_urban_rules.md |
| system/Urban/Author Style/[LHH] LieuHaHue_LiuXiaHui_urban_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Author Style/[LHH] LieuHaHue_LiuXiaHui_urban_rules.md |
| system/Urban/Author Style/[LUAG] LaoUngAnGa_EagleEatsChicken_urban_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Author Style/[LUAG] LaoUngAnGa_EagleEatsChicken_urban_rules.md |
| system/Urban/Author Style/[NNND] NguNhanNhiDai_FishmanII_urban_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Author Style/[NNND] NguNhanNhiDai_FishmanII_urban_rules.md |
| system/Urban/Author Style/[PHHCH] PhongHoaHiChuHau_FengHuo_urban_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Author Style/[PHHCH] PhongHoaHiChuHau_FengHuo_urban_rules.md |
| system/Urban/Depth/Urban_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Depth/Urban_Depth_Contract.md |
| system/Urban/Genre Operating/Urban_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Genre Operating/Urban_Operating_Guide.md |
| system/Urban/Urban_consistency_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Urban_consistency_rules.md |
| system/Urban/Urban_style.md | creative-knowledge | skills/novelkit-canon/canon/system/Urban/Urban_style.md |
| system/War Espionage/Depth/WarEspionage_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/War Espionage/Depth/WarEspionage_Depth_Contract.md |
| system/War Espionage/Genre Operating/WarEspionage_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/War Espionage/Genre Operating/WarEspionage_Operating_Guide.md |
| system/War Espionage/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/War Espionage/vocabulary.txt |
| system/Xianxia/Author Style/[CD] ThanDong_ChenDong_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[CD] ThanDong_ChenDong_xianxia_rules.md |
| system/Xianxia/Author Style/[DG] DuongGiaTamThieu_TangJiaSanShao_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[DG] DuongGiaTamThieu_TangJiaSanShao_xianxia_rules.md |
| system/Xianxia/Author Style/[NC] NhiCan_ErGen_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[NC] NhiCan_ErGen_xianxia_rules.md |
| system/Xianxia/Author Style/[OT] MucThichLanNuoc_Cuttlefish_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[OT] MucThichLanNuoc_Cuttlefish_xianxia_rules.md |
| system/Xianxia/Author Style/[PL] PhongLangThienHa_FengLingTianXia_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[PL] PhongLangThienHa_FengLingTianXia_xianxia_rules.md |
| system/Xianxia/Author Style/[PT] PhuongTuong_FangXiang_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[PT] PhuongTuong_FangXiang_xianxia_rules.md |
| system/Xianxia/Author Style/[TD] TieuDinh_XiaoDing_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[TD] TieuDinh_XiaoDing_xianxia_rules.md |
| system/Xianxia/Author Style/[TH] NgaCatTayHongThi_IEatTomatoes_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[TH] NgaCatTayHongThi_IEatTomatoes_xianxia_rules.md |
| system/Xianxia/Author Style/[TT] ThienTamThoDau_SilkwormPotato_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[TT] ThienTamThoDau_SilkwormPotato_xianxia_rules.md |
| system/Xianxia/Author Style/[VN] VongNgu_WangYu_xianxia_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Author Style/[VN] VongNgu_WangYu_xianxia_rules.md |
| system/Xianxia/Depth/Xianxia_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Depth/Xianxia_Depth_Contract.md |
| system/Xianxia/Progression/Cultivation_Progression_System.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Progression/Cultivation_Progression_System.md |
| system/Xianxia/Texture/Tu_Tien_Texture_Floor.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Texture/Tu_Tien_Texture_Floor.md |
| system/Xianxia/World/Xianxia_World_Operating_System.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/World/Xianxia_World_Operating_System.md |
| system/Xianxia/Worldbuilding guide/ThanDong_Worldbuilding_Complete.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/ThanDong_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[DG] DuongGiaTamThieu_Worldbuilding_Complete.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[DG] DuongGiaTamThieu_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[NC] NhiCan_Worldbuilding_Complete.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[NC] NhiCan_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[PL] PhongLangThienHa_Worldbuilding_Complete.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[PL] PhongLangThienHa_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[TD] TieuDinh_Worldbuilding_Complete.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[TD] TieuDinh_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[TH] NgaCatTayHongThi_Worldbuilding_Complete.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[TH] NgaCatTayHongThi_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[TT] ThienTamThoDau_Worldbuilding_Complete.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[TT] ThienTamThoDau_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[VN] VongNgu_Worldbuilding_Complete.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[VN] VongNgu_Worldbuilding_Complete.md |
| system/Xianxia/Xianxia_consistency_rules.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Xianxia_consistency_rules.md |
| system/Xianxia/Xianxia_style.md | creative-knowledge | skills/novelkit-canon/canon/system/Xianxia/Xianxia_style.md |
| system/eSports/Depth/eSports_Depth_Contract.md | creative-knowledge | skills/novelkit-canon/canon/system/eSports/Depth/eSports_Depth_Contract.md |
| system/eSports/Genre Operating/eSports_Operating_Guide.md | creative-knowledge | skills/novelkit-canon/canon/system/eSports/Genre Operating/eSports_Operating_Guide.md |
| system/eSports/vocabulary.txt | creative-knowledge | skills/novelkit-canon/canon/system/eSports/vocabulary.txt |
| templates/AUTHOR_STYLE_CATALOG.md | creative-knowledge | skills/novelkit-canon/templates/AUTHOR_STYLE_CATALOG.md |
| templates/GOAL_TRACKER_TEMPLATE.md | creative-knowledge | skills/novelkit-canon/templates/GOAL_TRACKER_TEMPLATE.md |
| templates/HYBRID_GENRE_GUIDE.md | creative-knowledge | skills/novelkit-canon/templates/HYBRID_GENRE_GUIDE.md |
| templates/PLAN_TEMPLATE.md | creative-knowledge | skills/novelkit-canon/templates/PLAN_TEMPLATE.md |
| templates/PROJECT_DNA_FILLABLE.md | creative-knowledge | skills/novelkit-canon/templates/PROJECT_DNA_FILLABLE.md |
| templates/PROJECT_DNA_TEMPLATE.md | creative-knowledge | skills/novelkit-canon/templates/PROJECT_DNA_TEMPLATE.md |
| templates/WORKFLOW_TEMPLATE.md | creative-knowledge | skills/novelkit-canon/templates/WORKFLOW_TEMPLATE.md |
| templates/database/master_timeline_template.md | creative-knowledge | skills/novelkit-canon/templates/database/master_timeline_template.md |
| templates/database/meta_system_operating_config_template.md | creative-knowledge | skills/novelkit-canon/templates/database/meta_system_operating_config_template.md |
| templates/database/sci_fi_world_operating_config_template.md | creative-knowledge | skills/novelkit-canon/templates/database/sci_fi_world_operating_config_template.md |
| templates/database/seeds_tracker_template.md | creative-knowledge | skills/novelkit-canon/templates/database/seeds_tracker_template.md |
| templates/database/style_vault_template.md | creative-knowledge | skills/novelkit-canon/templates/database/style_vault_template.md |
| templates/database/threads_master_template.md | creative-knowledge | skills/novelkit-canon/templates/database/threads_master_template.md |
| templates/database/time_travel_causality_config_template.md | creative-knowledge | skills/novelkit-canon/templates/database/time_travel_causality_config_template.md |
| templates/database/xianxia_character_template.md | creative-knowledge | skills/novelkit-canon/templates/database/xianxia_character_template.md |
| templates/database/xianxia_world_operating_config_template.md | creative-knowledge | skills/novelkit-canon/templates/database/xianxia_world_operating_config_template.md |
| templates/examples/PROJECT_DNA_SAMPLE_XIANXIA.md | creative-knowledge | skills/novelkit-canon/templates/examples/PROJECT_DNA_SAMPLE_XIANXIA.md |
| templates/genres/PROJECT_DNA_META_GENRE.md | creative-knowledge | skills/novelkit-canon/templates/genres/PROJECT_DNA_META_GENRE.md |
| templates/genres/PROJECT_DNA_ROMANCE.md | creative-knowledge | skills/novelkit-canon/templates/genres/PROJECT_DNA_ROMANCE.md |
| templates/genres/PROJECT_DNA_SCIFI.md | creative-knowledge | skills/novelkit-canon/templates/genres/PROJECT_DNA_SCIFI.md |
| templates/genres/PROJECT_DNA_TIME_TRAVEL.md | creative-knowledge | skills/novelkit-canon/templates/genres/PROJECT_DNA_TIME_TRAVEL.md |
| templates/genres/PROJECT_DNA_URBAN.md | creative-knowledge | skills/novelkit-canon/templates/genres/PROJECT_DNA_URBAN.md |
| templates/genres/PROJECT_DNA_XIANXIA.md | creative-knowledge | skills/novelkit-canon/templates/genres/PROJECT_DNA_XIANXIA.md |
| templates/novel/Memory_template.md | creative-knowledge | skills/novelkit-canon/templates/novel/Memory_template.md |
| templates/novel/NOVEL_STRUCTURE.md | creative-knowledge | skills/novelkit-canon/templates/novel/NOVEL_STRUCTURE.md |
| templates/novel/master_outline_template.md | creative-knowledge | skills/novelkit-canon/templates/novel/master_outline_template.md |
| templates/novel/pipeline_log_template.md | creative-knowledge | skills/novelkit-canon/templates/novel/pipeline_log_template.md |
| templates/novel/pipeline_status_template.json | creative-knowledge | skills/novelkit-canon/templates/novel/pipeline_status_template.json |

## Toàn bộ kiểm kê

| source | category | status | target |
|---|---|---|---|
| .creative_refs/ta_de_van_tam/bootstrap.characters/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.characters/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.characters/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.characters/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.characters/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.characters/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.characters/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.characters/task_runner_result.json |
| .creative_refs/ta_de_van_tam/bootstrap.master_outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.master_outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.master_outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.master_outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.master_outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.master_outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.master_outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.master_outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/bootstrap.plot_threads/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.plot_threads/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.plot_threads/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.plot_threads/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.plot_threads/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.plot_threads/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.plot_threads/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.plot_threads/task_runner_result.json |
| .creative_refs/ta_de_van_tam/bootstrap.timeline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.timeline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.timeline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.timeline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.timeline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.timeline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.timeline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.timeline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.world/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/bootstrap.world/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.world/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/bootstrap.world/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/bootstrap.world/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0001.outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0001.outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0001.outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0001.outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0001.review/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0001.review/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0001.sync/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0001.sync/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0001.sync/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0001.sync/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0001.write/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0001.write/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0001.write/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0001.write/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0001.write/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0002.outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0002.outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0002.outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0002.outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0002.review/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0002.review/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0002.sync/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0002.sync/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0002.sync/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0002.sync/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0002.write/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0002.write/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0002.write/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0002.write/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0002.write/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0003.outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0003.outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0003.outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0003.outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0003.review/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0003.review/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0003.sync/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0003.sync/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0003.sync/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0003.sync/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0003.write/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0003.write/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0003.write/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0003.write/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0003.write/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0004.outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0004.outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0004.outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0004.outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0004.review/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0004.review/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0004.sync/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0004.sync/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0004.sync/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0004.sync/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0004.write/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0004.write/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0004.write/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0004.write/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0004.write/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0005.outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.outline/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0005.outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.outline/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0005.outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.outline/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0005.outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.outline/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0005.review/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.review/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0005.review/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.review/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0005.sync/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.sync/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0005.sync/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.sync/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0005.sync/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.sync/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0005.sync/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.sync/task_runner_result.json |
| .creative_refs/ta_de_van_tam/chapter.0005.write/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.write/creative_input_bundle.md |
| .creative_refs/ta_de_van_tam/chapter.0005.write/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.write/creative_input_bundle.meta.json |
| .creative_refs/ta_de_van_tam/chapter.0005.write/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.write/task_runner_prompt.md |
| .creative_refs/ta_de_van_tam/chapter.0005.write/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/ta_de_van_tam/chapter.0005.write/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.characters/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.characters/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.characters/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.characters/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.characters/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.characters/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.characters/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.characters/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.master_outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.master_outline/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.master_outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.master_outline/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.master_outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.master_outline/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.master_outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.master_outline/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.plot_threads/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.plot_threads/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.plot_threads/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.plot_threads/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.plot_threads/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.plot_threads/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.plot_threads/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.plot_threads/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.timeline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.timeline/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.timeline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.timeline/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.timeline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.timeline/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.timeline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.timeline/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/bootstrap.world/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.world/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/bootstrap.world/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.world/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/bootstrap.world/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.world/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/bootstrap.world/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/bootstrap.world/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.outline/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.outline/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.outline/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.outline/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.review/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.review/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.review/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.review/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.sync/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.sync/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.sync/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.sync/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.sync/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.sync/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.sync/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.sync/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.write/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.write/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.write/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.write/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0001.write/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.write/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0001.write/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0001.write/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.outline/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.outline/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.outline/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.outline/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.outline/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.outline/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.outline/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.outline/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.review/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.review/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.review/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.review/task_runner_result.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.write/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.write/creative_input_bundle.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.write/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.write/creative_input_bundle.meta.json |
| .creative_refs/tan_dang_van_dao/chapter.0002.write/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.write/task_runner_prompt.md |
| .creative_refs/tan_dang_van_dao/chapter.0002.write/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/tan_dang_van_dao/chapter.0002.write/task_runner_result.json |
| .creative_refs/tmp6ov9ek3f/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmp6ov9ek3f/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmp6ov9ek3f/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmp718nhgjy/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmp718nhgjy/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmp718nhgjy/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmp91ag2175/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmp91ag2175/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmp91ag2175/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpeodd032u/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpeodd032u/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmpeodd032u/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmph0m1sqth/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmph0m1sqth/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmph0m1sqth/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpjt3hg5nb/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpjt3hg5nb/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmpjt3hg5nb/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmplbk2q9ot/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmplbk2q9ot/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmplbk2q9ot/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpm6cr2eua/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpm6cr2eua/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmpm6cr2eua/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpr8wm9sk1/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpr8wm9sk1/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmpr8wm9sk1/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpsjh444ly/chapter.0001.write/creative_input_bundle.md | legacy-infra | removed-legacy | — |
| .creative_refs/tmpsjh444ly/chapter.0001.write/creative_input_bundle.meta.json | legacy-infra | removed-legacy | — |
| .creative_refs/tmpsjh444ly/chapter.0001.write/task_runner_prompt.md | legacy-infra | removed-legacy | — |
| .creative_refs/truong_sinh_do/bootstrap.characters/creative_input_bundle.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/truong_sinh_do/bootstrap.characters/creative_input_bundle.md |
| .creative_refs/truong_sinh_do/bootstrap.characters/creative_input_bundle.meta.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/truong_sinh_do/bootstrap.characters/creative_input_bundle.meta.json |
| .creative_refs/truong_sinh_do/bootstrap.characters/task_runner_prompt.md | creative-knowledge | kept | skills/novelkit-canon/creative_refs/truong_sinh_do/bootstrap.characters/task_runner_prompt.md |
| .creative_refs/truong_sinh_do/bootstrap.characters/task_runner_result.json | creative-knowledge | kept | skills/novelkit-canon/creative_refs/truong_sinh_do/bootstrap.characters/task_runner_result.json |
| .env.example | legacy-infra | removed-legacy | — |
| .gitignore | legacy-infra | removed-legacy | — |
| .openclaw/workspace-state.json | legacy-infra | removed-legacy | — |
| .rag/narrative.sqlite3 | legacy-infra | removed-legacy | — |
| .rag/operational.sqlite3 | legacy-infra | removed-legacy | — |
| .seo-cache/audit-scores.json | legacy-infra | removed-legacy | — |
| .seo-cache/pages/homepage/geo.json | legacy-infra | removed-legacy | — |
| .seo-cache/plan.json | legacy-infra | removed-legacy | — |
| .seo-cache/site-meta.json | legacy-infra | removed-legacy | — |
| .seo-cache/sitemap.json | legacy-infra | removed-legacy | — |
| .test_artifacts/create_novel_payload.json | legacy-infra | removed-legacy | — |
| .test_artifacts/fix_mojibake.py | legacy-infra | removed-legacy | — |
| .test_artifacts/run_pipeline.sh | legacy-infra | removed-legacy | — |
| .well-known/jwks.json | legacy-infra | removed-legacy | — |
| .well-known/mcp/server-card.json | legacy-infra | removed-legacy | — |
| .well-known/oauth-authorization-server | legacy-infra | removed-legacy | — |
| .well-known/oauth-protected-resource | legacy-infra | removed-legacy | — |
| .well-known/openid-configuration | legacy-infra | removed-legacy | — |
| AGENTS.md | legacy-infra | removed-legacy | — |
| API.md | creative-knowledge | kept | skills/novelkit-canon/docs/API.md |
| ARCHITECTURE.md | legacy-infra | removed-legacy | — |
| CHANGELOG.md | legacy-infra | removed-legacy | — |
| CONTRACTS.md | creative-knowledge | kept | skills/novelkit-canon/docs/CONTRACTS.md |
| DEPLOYMENT.md | legacy-infra | removed-legacy | — |
| Dockerfile | legacy-infra | removed-legacy | — |
| HEARTBEAT.md | legacy-infra | removed-legacy | — |
| HUONG_DAN_SU_DUNG.md | legacy-infra | removed-legacy | — |
| IDENTITY.md | creative-knowledge | kept | skills/novelkit-canon/docs/IDENTITY.md |
| MEMORY.md | legacy-infra | removed-legacy | — |
| MIGRATION_OPENCLAW_TO_NOVELKIT.md | legacy-infra | removed-legacy | — |
| PIPELINE.md | legacy-infra | removed-legacy | — |
| README.md | legacy-infra | removed-legacy | — |
| README.vi.md | legacy-infra | removed-legacy | — |
| RELEASE_NOTES_P0_P2.md | legacy-infra | removed-legacy | — |
| RELEASE_SIGNOFF.md | legacy-infra | removed-legacy | — |
| RUNBOOK.md | creative-knowledge | kept | skills/novelkit-canon/docs/RUNBOOK.md |
| RUNBOOK_ACCOUNT_TIERS.md | legacy-infra | removed-legacy | — |
| SKILL/agent-team-orchestration-1.0.0/SKILL.md | creative-config | kept | skills/agent-team-orchestration-1.0.0/SKILL.md |
| SKILL/agent-team-orchestration-1.0.0/_meta.json | creative-config | kept | skills/agent-team-orchestration-1.0.0/_meta.json |
| SKILL/agent-team-orchestration-1.0.0/references/communication.md | creative-knowledge | kept | skills/agent-team-orchestration-1.0.0/references/communication.md |
| SKILL/agent-team-orchestration-1.0.0/references/patterns.md | creative-knowledge | kept | skills/agent-team-orchestration-1.0.0/references/patterns.md |
| SKILL/agent-team-orchestration-1.0.0/references/task-lifecycle.md | creative-knowledge | kept | skills/agent-team-orchestration-1.0.0/references/task-lifecycle.md |
| SKILL/agent-team-orchestration-1.0.0/references/team-setup.md | creative-knowledge | kept | skills/agent-team-orchestration-1.0.0/references/team-setup.md |
| SKILL/elite-longterm-memory-1.2.3/README.md | creative-knowledge | kept | skills/elite-longterm-memory-1.2.3/README.md |
| SKILL/elite-longterm-memory-1.2.3/SKILL.md | creative-config | kept | skills/elite-longterm-memory-1.2.3/SKILL.md |
| SKILL/elite-longterm-memory-1.2.3/_meta.json | creative-config | kept | skills/elite-longterm-memory-1.2.3/_meta.json |
| SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | creative-knowledge | kept | skills/elite-longterm-memory-1.2.3/bin/elite-memory.js |
| SKILL/elite-longterm-memory-1.2.3/package.json | creative-knowledge | kept | skills/elite-longterm-memory-1.2.3/package.json |
| SKILL/fix-issues-1.0.0/SKILL.md | creative-config | kept | skills/fix-issues-1.0.0/SKILL.md |
| SKILL/self-improving-agent-3.0.11/SKILL.md | creative-config | kept | skills/self-improving-agent-3.0.11/SKILL.md |
| SKILL/self-improving-agent-3.0.11/_meta.json | creative-config | kept | skills/self-improving-agent-3.0.11/_meta.json |
| SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | creative-knowledge | kept | skills/self-improving-agent-3.0.11/assets/ERRORS.md |
| SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | creative-knowledge | kept | skills/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md |
| SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | creative-knowledge | kept | skills/self-improving-agent-3.0.11/assets/LEARNINGS.md |
| SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | creative-knowledge | kept | skills/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md |
| SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | creative-knowledge | kept | skills/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md |
| SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | creative-knowledge | kept | skills/self-improving-agent-3.0.11/hooks/openclaw/handler.js |
| SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | creative-knowledge | kept | skills/self-improving-agent-3.0.11/hooks/openclaw/handler.ts |
| SKILL/self-improving-agent-3.0.11/references/examples.md | creative-knowledge | kept | skills/self-improving-agent-3.0.11/references/examples.md |
| SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | creative-knowledge | kept | skills/self-improving-agent-3.0.11/references/hooks-setup.md |
| SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | creative-knowledge | kept | skills/self-improving-agent-3.0.11/references/openclaw-integration.md |
| SKILL/self-improving-agent-3.0.11/scripts/activator.sh | creative-knowledge | kept | skills/self-improving-agent-3.0.11/scripts/activator.sh |
| SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | creative-knowledge | kept | skills/self-improving-agent-3.0.11/scripts/error-detector.sh |
| SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | creative-knowledge | kept | skills/self-improving-agent-3.0.11/scripts/extract-skill.sh |
| SKILL/telemetry-guardian-v1.0/SKILL.md | creative-config | kept | skills/telemetry-guardian-v1.0/SKILL.md |
| SOUL.md | creative-knowledge | kept | subagents/orchestrator/SOUL.md |
| STYLE_GUIDE.md | creative-knowledge | kept | skills/novelkit-canon/docs/STYLE_GUIDE.md |
| TOOLS.md | legacy-infra | removed-legacy | — |
| UPGRADE_PLAN.md | legacy-infra | removed-legacy | — |
| USER.md | legacy-infra | removed-legacy | — |
| _headers | legacy-infra | removed-legacy | — |
| _worker.js | legacy-infra | removed-legacy | — |
| agent-ready/README.md | legacy-infra | removed-legacy | — |
| agent-ready/dns-aid.zone | legacy-infra | removed-legacy | — |
| app.js | legacy-infra | removed-legacy | — |
| auth.md | legacy-infra | removed-legacy | — |
| config/account_tiers.example.json | legacy-infra | removed-legacy | — |
| config/account_tiers.json | legacy-infra | removed-legacy | — |
| config/ai_flavor_patterns.json | creative-config | kept | config/ai_flavor_patterns.json |
| config/cool_point_markers.json | creative-config | kept | config/cool_point_markers.json |
| config/genre_aliases.json | creative-config | kept | config/genre_aliases.json |
| config/strand_keywords.json | creative-config | kept | config/strand_keywords.json |
| config/xianxia_language_guard.json | creative-config | kept | config/language_guard/xianxia.json |
| database/events_registry.json | legacy-infra | removed-legacy | — |
| docker-compose.yml | legacy-infra | removed-legacy | — |
| docs/superpowers/plans/2026-06-04-iflas-v2-unified-review-gate.md | legacy-infra | removed-legacy | — |
| index.html | legacy-infra | removed-legacy | — |
| index.md | legacy-infra | removed-legacy | — |
| logs/ui_events.sqlite3 | legacy-infra | removed-legacy | — |
| memory/.gitkeep | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/.controlplane.sqlite3 | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/GOAL_TRACKER.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/PLAN.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/PROJECT_DNA.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/PROJECT_DNA.meta.json | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/database/characters/LucTruongSinhMotTuSiPhamCanPhiThangTuHaGioiVeNgoaiBinhThuongTinhTinhKinDaoGioiAnNhanLuonChuanBiDuongLuiTruocKhiRaTay.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/database/characters/_template.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/database/characters/relationship_map.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/database/plot_threads/seeds_tracker.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/database/plot_threads/threads_master.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/database/systems/xianxia_world_operating_config.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/database/timeline/master_timeline.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/database/worldbuilding/_seed_brief.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/logs/.pipeline_status.lock | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/logs/pipeline_log.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/logs/pipeline_status.json | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/memory/Memory.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/outlines/master_outline.md | legacy-infra | removed-legacy | — |
| novels/pham_tam_dao_to/style_vault/examples.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.controlplane.sqlite3 | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.creative_refs/bootstrap.characters/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.creative_refs/bootstrap.master_outline/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.creative_refs/bootstrap.plot_threads/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.creative_refs/bootstrap.timeline/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.creative_refs/bootstrap.world/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.mem0/fallback.sqlite3 | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.mem0/history.db | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.mem0/qdrant/.lock | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.mem0/qdrant/.process.lock | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.mem0/qdrant/collection/agent_memory/storage.sqlite | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.mem0/qdrant/meta.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.metrics.sqlite3 | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.rag/narrative.sqlite3 | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.rag/operational.sqlite3 | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.vector_db/.lock | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.vector_db/.process.lock | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.vector_db/collection/novel_db/storage.sqlite | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.vector_db/index_meta.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/.vector_db/meta.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/GOAL_TRACKER.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/PLAN.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/PROJECT_DNA.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/PROJECT_DNA.meta.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/chapters/chapter_001.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/chapters/chapter_002.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/chapters/chapter_003.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/chapters/chapter_004.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/chapters/chapter_005.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/characters/TaVoNhaiThieuNienBiCaTongMonXemLaMaChungSoHuuTaAnVanTuongCoTheDuaThanHonVaoCacTieuGioiDeHocDaoPhapCamKy.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/characters/_template.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/characters/co_thien_khuyet.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/characters/huyen_nha.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/characters/lam_tich_nguyet.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/characters/relationship_map.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/characters/ta_vo_nhai.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/characters/tich_diet_dao_nhan.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/plot_threads/seeds_tracker.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/plot_threads/threads_master.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/systems/cultivation.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/systems/meta_system_operating_config.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/systems/world_rules.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/systems/xianxia_world_operating_config.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/timeline/master_timeline.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/worldbuilding/WorldOverview.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/worldbuilding/_seed_brief.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/worldbuilding/factions.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/database/worldbuilding/geography.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/.pipeline_log.lock | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/.pipeline_status.lock | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_bootstrap_characters_20260531T150736033Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_bootstrap_master_outline_20260531T163248277Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_bootstrap_plot_threads_20260531T152347182Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_bootstrap_timeline_20260531T152937256Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_bootstrap_world_20260531T151753313Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0001_outline_20260531T165027215Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0001_outline_20260531T173622922Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0001_review_20260601T000501151Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0001_sync_20260601T000657942Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0001_sync_20260601T001017304Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0001_write_20260531T180940520Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0002_outline_20260601T014333548Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0002_review_20260601T040618318Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0002_sync_20260601T040759326Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0002_sync_20260601T041213680Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0002_write_20260601T032612403Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0003_outline_20260601T041643864Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0003_review_20260601T042420111Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0003_sync_20260601T042616143Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0003_write_20260601T041835855Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0004_outline_20260601T043135515Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0004_review_20260601T045512225Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0004_sync_20260601T045655165Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0004_write_20260601T043703311Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0005_outline_20260601T052942792Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0005_review_20260601T145136729Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0005_sync_20260601T145320835Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0005_sync_20260601T145948778Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/agent_chapter_0005_write_20260601T053127686Z.log | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/pipeline_log.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/logs/pipeline_status.json | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/memory/Memory.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/outlines/arc_1/chapter_001_outline.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/outlines/arc_1/chapter_002_outline.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/outlines/arc_1/chapter_003_outline.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/outlines/arc_1/chapter_004_outline.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/outlines/arc_1/chapter_005_outline.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/outlines/master_outline.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/reviews/chapter_001_review.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/reviews/chapter_002_review.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/reviews/chapter_003_review.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/reviews/chapter_004_review.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/reviews/chapter_005_review.md | legacy-infra | removed-legacy | — |
| novels/ta_de_van_tam/style_vault/examples.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.controlplane.sqlite3 | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.creative_refs/bootstrap.characters/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.creative_refs/bootstrap.master_outline/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.creative_refs/bootstrap.plot_threads/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.creative_refs/bootstrap.timeline/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.creative_refs/bootstrap.world/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.creative_refs/chapter.0002.review/quality_verdict.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.mem0/fallback.sqlite3 | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.mem0/history.db | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.mem0/qdrant/.lock | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.mem0/qdrant/.process.lock | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.mem0/qdrant/collection/agent_memory/storage.sqlite | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.mem0/qdrant/meta.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.metrics.sqlite3 | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.rag/narrative.sqlite3 | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.rag/operational.sqlite3 | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.vector_db/.lock | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.vector_db/.process.lock | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.vector_db/collection/novel_db/storage.sqlite | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.vector_db/index_meta.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/.vector_db/meta.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/GOAL_TRACKER.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/PLAN.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/PROJECT_DNA.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/PROJECT_DNA.meta.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/chapters/chapter_001.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/chapters/chapter_002.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/LucTruongSinhThieuNienGiuDenMoOTranVoThuyTinhTramMacNhanNaiMangCanCotTamThuongNhungCoTamVanDaoBenBiDenDangSo.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/_template.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/bach_tu_yen.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/co_son_lao_nhan.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/do_tam.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/hac_nha_tang_nguyet.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/luc_muoi.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/luc_truong_sinh.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/mo_thanh_han.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/relationship_map.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/characters/ta_vo_nhai.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/plot_threads/seeds_tracker.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/plot_threads/threads_master.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/systems/cultivation.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/systems/world_rules.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/systems/xianxia_world_operating_config.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/timeline/master_timeline.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/worldbuilding/WorldOverview.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/worldbuilding/_seed_brief.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/worldbuilding/factions.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/database/worldbuilding/geography.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/.pipeline_log.lock | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/.pipeline_status.lock | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_bootstrap_characters_20260530T150235350Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_bootstrap_master_outline_20260530T153426297Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_bootstrap_plot_threads_20260530T152811932Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_bootstrap_timeline_20260530T153112968Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_bootstrap_world_20260530T151802086Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_bootstrap_world_20260530T152434792Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0001_outline_20260530T153912545Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0001_review_20260530T154836079Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0001_sync_20260530T155001521Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0001_sync_20260530T155244441Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0001_write_20260530T154113697Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_outline_20260603T070607083Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_outline_20260603T143638571Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_outline_20260604T064637690Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_outline_20260604T064813340Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_outline_20260604T065026487Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_review_20260604T073556371Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_review_20260604T073919359Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_review_20260604T080044704Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/agent_chapter_0002_write_20260604T071658524Z.log | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/pipeline_log.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/logs/pipeline_status.json | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/memory/Memory.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/outlines/arc_1/chapter_001_outline.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/outlines/arc_1/chapter_002_outline.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/outlines/master_outline.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/reviews/chapter_001_review.md | legacy-infra | removed-legacy | — |
| novels/tan_dang_van_dao/style_vault/examples.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/.controlplane.sqlite3 | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/.rag/narrative.sqlite3 | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/.rag/operational.sqlite3 | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/GOAL_TRACKER.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/PLAN.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/PROJECT_DNA.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/PROJECT_DNA.meta.json | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/database/characters/LucTranThieuNienKienNhanHamHocHoiXuatThanBinhThuongNhungCoCanCotAnGiau.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/database/characters/_template.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/database/characters/relationship_map.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/database/plot_threads/seeds_tracker.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/database/plot_threads/threads_master.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/database/systems/xianxia_world_operating_config.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/database/timeline/master_timeline.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/database/worldbuilding/_seed_brief.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/logs/.pipeline_status.lock | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/logs/agent_bootstrap_characters_20260603T031210280Z.log | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/logs/pipeline_log.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/logs/pipeline_status.json | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/memory/Memory.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/outlines/master_outline.md | legacy-infra | removed-legacy | — |
| novels/truong_sinh_do/style_vault/examples.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/.controlplane.sqlite3 | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/GOAL_TRACKER.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/PLAN.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/PROJECT_DNA.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/PROJECT_DNA.meta.json | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/database/characters/LyVanPhongChangThieuNienMangHuyetThuyetBiAnKhatKhaoBaoThuNhungLaiBiCuonVaoVongXoayGiangHo.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/database/characters/_template.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/database/characters/relationship_map.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/database/plot_threads/seeds_tracker.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/database/plot_threads/threads_master.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/database/systems/xianxia_world_operating_config.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/database/timeline/master_timeline.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/database/worldbuilding/_seed_brief.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/logs/.pipeline_status.lock | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/logs/pipeline_log.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/logs/pipeline_status.json | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/memory/Memory.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/outlines/master_outline.md | legacy-infra | removed-legacy | — |
| novels/tuyet_the_hao_tinh/style_vault/examples.md | legacy-infra | removed-legacy | — |
| requirements.txt | legacy-infra | removed-legacy | — |
| scripts/MULTI_PROVIDER.md | legacy-infra | removed-legacy | — |
| scripts/README.md | legacy-infra | removed-legacy | — |
| scripts/account_tiers/__init__.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/account_snapshot.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/account_tiers_config.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/account_tiers_constants.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/account_tiers_db.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/audit_logger.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/cli.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/migration.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/novel_lifecycle.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/quota_manager.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/startup_validator.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/subscription_service.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/sweepers.py | legacy-infra | removed-legacy | — |
| scripts/account_tiers/user_service.py | legacy-infra | removed-legacy | — |
| scripts/adaptive_context.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/agent_memory.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/ai_flavor_detector.py | business-logic | extracted | tools/novelkit_ai_flavor_tool.py |
| scripts/batch_operations.py | legacy-infra | removed-legacy | — |
| scripts/bootstrap_planning_docs.py | business-logic | extracted | tools/novelkit_dna_tool.py |
| scripts/chapter_commit.py | business-logic | extracted | tools/novelkit_sync_tool.py |
| scripts/chapter_diff.py | business-logic | extracted | tools/novelkit_sync_tool.py |
| scripts/compare_signoff_golden.py | business-logic | extracted | tests/ |
| scripts/control_plane.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/cool_point_analyzer.py | business-logic | extracted | tools/novelkit_cool_point_tool.py |
| scripts/cp_cli.py | legacy-infra | removed-legacy | — |
| scripts/cp_constants.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/cp_db.py | legacy-infra | removed-legacy | — |
| scripts/cp_genre.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/cp_recovery.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/cp_status.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/cp_sync.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/cp_verify.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/dispatcher_adapter.py | legacy-infra | removed-legacy | — |
| scripts/enrich_dna.py | business-logic | extracted | tools/novelkit_dna_tool.py |
| scripts/feedback_loop.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gate_registry.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gates/__init__.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gates/common.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gates/meta_genre.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gates/romance.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gates/scifi.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gates/time_travel.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gates/urban.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gates/xianxia.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/gemini_key_pool.py | legacy-infra | removed-legacy | — |
| scripts/gemini_pool_status.py | legacy-infra | removed-legacy | — |
| scripts/generate_novel_from_prompt.py | business-logic | extracted | tools/novelkit_dna_tool.py |
| scripts/genre_language_guard.py | business-logic | extracted | tools/novelkit_language_guard_tool.py |
| scripts/google_genai_compat.py | legacy-infra | removed-legacy | — |
| scripts/graph_index.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/hook_tracker.py | legacy-infra | removed-legacy | — |
| scripts/llm_config.py | legacy-infra | removed-legacy | — |
| scripts/memory_bootstrap.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_cli.py | legacy-infra | removed-legacy | — |
| scripts/memory_compactor.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_importance.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_item.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_pack.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_render.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_resilience.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_rotation.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_store.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/memory_writer_v2.py | business-logic | extracted | plugins/memory/novelkit_memory.py |
| scripts/migrate_plot_threads_to_loops.py | business-logic | extracted | tools/novelkit_strand_tool.py |
| scripts/namespace_guard.py | legacy-infra | removed-legacy | — |
| scripts/observability.py | legacy-infra | removed-legacy | — |
| scripts/observability_cli.py | legacy-infra | removed-legacy | — |
| scripts/open_loops.py | business-logic | extracted | tools/novelkit_strand_tool.py |
| scripts/project_dna_metadata.py | business-logic | extracted | tools/novelkit_dna_tool.py |
| scripts/projection_runner.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/__init__.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/graph_writer.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/map_writer.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/mem0_writer.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/memory_writer.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/pipeline_status_writer.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/progression_writer.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/rag_writer.py | legacy-infra | removed-legacy | — |
| scripts/projection_writers/vector_writer.py | legacy-infra | removed-legacy | — |
| scripts/quality_feedback.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/rag_context.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/rag_sanitizer.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/recovery_orchestrator.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/reference_deconstructor.py | business-logic | extracted | tools/novelkit_reference_tool.py |
| scripts/reference_deconstructor_cli.py | business-logic | extracted | tools/novelkit_reference_tool.py |
| scripts/release_signoff.py | business-logic | extracted | tests/ |
| scripts/replay_command.py | legacy-infra | removed-legacy | — |
| scripts/reranker.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/reranker_doctor.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/reranker_providers/__init__.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/reranker_providers/cohere.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/reranker_providers/jina.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/reranker_providers/noop.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/reranker_providers/voyage.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/rrf.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/runtime_guards.py | legacy-infra | removed-legacy | — |
| scripts/scaffold.sh | legacy-infra | removed-legacy | — |
| scripts/semantic_gates/__init__.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/budget.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/circuit_breaker.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/common.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/policy.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/prompts.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/runner.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/verdict.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/verdict_cache.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/verify_llm.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/semantic_gates/xianxia.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/signoff.sh | legacy-infra | removed-legacy | — |
| scripts/strand_weaver.py | business-logic | extracted | tools/novelkit_strand_tool.py |
| scripts/style_coherence.py | business-logic | extracted | tools/novelkit_style_coherence_tool.py |
| scripts/sync_stages.py | business-logic | extracted | tools/novelkit_sync_tool.py |
| scripts/task_output_contracts.py | business-logic | extracted | tools/novelkit_pipeline_tool.py |
| scripts/task_runner.py | legacy-infra | removed-legacy | — |
| scripts/update_golden_baselines.py | business-logic | extracted | tests/ |
| scripts/validators.py | business-logic | extracted | tools/novelkit_gate_tool.py |
| scripts/vector_db.py | business-logic | extracted | plugins/context_engine/novelkit_context.py |
| scripts/write_next.py | legacy-infra | removed-legacy | — |
| scripts/write_next.sh | legacy-infra | removed-legacy | — |
| scripts/xianxia_language_guard.py | business-logic | extracted | tools/novelkit_language_guard_tool.py |
| seo-reports/ACTION-PLAN.md | legacy-infra | removed-legacy | — |
| seo-reports/FULL-AUDIT-REPORT.md | legacy-infra | removed-legacy | — |
| seo-reports/GEO-ANALYSIS.md | legacy-infra | removed-legacy | — |
| seo-reports/VALIDATION-REPORT.md | legacy-infra | removed-legacy | — |
| state/account_tiers.sqlite3 | legacy-infra | removed-legacy | — |
| styles.css | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/HEARTBEAT.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents/chan_nhan/SOUL.md | creative-knowledge | kept | subagents/sub_agents/chan_nhan/SOUL.md |
| sub_agents/chan_nhan/TOOLS.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/HEARTBEAT.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents/dong_tu/SOUL.md | creative-knowledge | kept | subagents/sub_agents/dong_tu/SOUL.md |
| sub_agents/dong_tu/TOOLS.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/HEARTBEAT.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents/huyet_thu/SOUL.md | creative-knowledge | kept | subagents/sub_agents/huyet_thu/SOUL.md |
| sub_agents/huyet_thu/TOOLS.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/HEARTBEAT.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/SKILL_CLEANUP.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents/mong_yem/SOUL.md | creative-knowledge | kept | subagents/sub_agents/mong_yem/SOUL.md |
| sub_agents/mong_yem/TOOLS.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/HEARTBEAT.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents/thien_co_tu/SOUL.md | creative-knowledge | kept | subagents/sub_agents/thien_co_tu/SOUL.md |
| sub_agents/thien_co_tu/TOOLS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/bo_cuc/SOUL.md | creative-knowledge | kept | subagents/sub_agents_do_thi/bo_cuc/SOUL.md |
| sub_agents_do_thi/but_gia/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/but_gia/SOUL.md | creative-knowledge | kept | subagents/sub_agents_do_thi/but_gia/SOUL.md |
| sub_agents_do_thi/kien_truc_su/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/kien_truc_su/SOUL.md | creative-knowledge | kept | subagents/sub_agents_do_thi/kien_truc_su/SOUL.md |
| sub_agents_do_thi/nhan_sinh/SKILL/elite-longterm-memory-1.2.3/README.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/elite-longterm-memory-1.2.3/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/elite-longterm-memory-1.2.3/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/elite-longterm-memory-1.2.3/bin/elite-memory.js | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/elite-longterm-memory-1.2.3/package.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/SKILL.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/_meta.json | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/assets/ERRORS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/assets/FEATURE_REQUESTS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/assets/LEARNINGS.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/assets/SKILL-TEMPLATE.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/hooks/openclaw/HOOK.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.js | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/hooks/openclaw/handler.ts | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/references/examples.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/references/hooks-setup.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/references/openclaw-integration.md | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/scripts/activator.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/scripts/error-detector.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SKILL/self-improving-agent-3.0.11/scripts/extract-skill.sh | legacy-infra | removed-legacy | — |
| sub_agents_do_thi/nhan_sinh/SOUL.md | creative-knowledge | kept | subagents/sub_agents_do_thi/nhan_sinh/SOUL.md |
| sub_agents_do_thi/tham_phan/SOUL.md | creative-knowledge | kept | subagents/sub_agents_do_thi/tham_phan/SOUL.md |
| sub_agents_he_thong/chu_than/SOUL.md | creative-knowledge | kept | subagents/sub_agents_he_thong/chu_than/SOUL.md |
| sub_agents_he_thong/giam_sat/SOUL.md | creative-knowledge | kept | subagents/sub_agents_he_thong/giam_sat/SOUL.md |
| sub_agents_he_thong/giao_dien/SOUL.md | creative-knowledge | kept | subagents/sub_agents_he_thong/giao_dien/SOUL.md |
| sub_agents_he_thong/ky_chu/SOUL.md | creative-knowledge | kept | subagents/sub_agents_he_thong/ky_chu/SOUL.md |
| sub_agents_he_thong/nhiem_vu/SOUL.md | creative-knowledge | kept | subagents/sub_agents_he_thong/nhiem_vu/SOUL.md |
| sub_agents_khoa_huyen/ban_the/SOUL.md | creative-knowledge | kept | subagents/sub_agents_khoa_huyen/ban_the/SOUL.md |
| sub_agents_khoa_huyen/ky_di/SOUL.md | creative-knowledge | kept | subagents/sub_agents_khoa_huyen/ky_di/SOUL.md |
| sub_agents_khoa_huyen/luong_tu/SOUL.md | creative-knowledge | kept | subagents/sub_agents_khoa_huyen/luong_tu/SOUL.md |
| sub_agents_khoa_huyen/ma_tran/SOUL.md | creative-knowledge | kept | subagents/sub_agents_khoa_huyen/ma_tran/SOUL.md |
| sub_agents_khoa_huyen/oracle/SOUL.md | creative-knowledge | kept | subagents/sub_agents_khoa_huyen/oracle/SOUL.md |
| sub_agents_ngon_tinh/cam_sat/SOUL.md | creative-knowledge | kept | subagents/sub_agents_ngon_tinh/cam_sat/SOUL.md |
| sub_agents_ngon_tinh/hong_nhan/SOUL.md | creative-knowledge | kept | subagents/sub_agents_ngon_tinh/hong_nhan/SOUL.md |
| sub_agents_ngon_tinh/minh_kinh/SOUL.md | creative-knowledge | kept | subagents/sub_agents_ngon_tinh/minh_kinh/SOUL.md |
| sub_agents_ngon_tinh/nguyet_lao/SOUL.md | creative-knowledge | kept | subagents/sub_agents_ngon_tinh/nguyet_lao/SOUL.md |
| sub_agents_ngon_tinh/tinh_kiep/SOUL.md | creative-knowledge | kept | subagents/sub_agents_ngon_tinh/tinh_kiep/SOUL.md |
| sub_agents_xuyen_khong/ban_do/SOUL.md | creative-knowledge | kept | subagents/sub_agents_xuyen_khong/ban_do/SOUL.md |
| sub_agents_xuyen_khong/luan_hoi/SOUL.md | creative-knowledge | kept | subagents/sub_agents_xuyen_khong/luan_hoi/SOUL.md |
| sub_agents_xuyen_khong/menh_chu/SOUL.md | creative-knowledge | kept | subagents/sub_agents_xuyen_khong/menh_chu/SOUL.md |
| sub_agents_xuyen_khong/su_quan/SOUL.md | creative-knowledge | kept | subagents/sub_agents_xuyen_khong/su_quan/SOUL.md |
| sub_agents_xuyen_khong/thien_dao/SOUL.md | creative-knowledge | kept | subagents/sub_agents_xuyen_khong/thien_dao/SOUL.md |
| system/Apocalypse/Depth/Apocalypse_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Apocalypse/Depth/Apocalypse_Depth_Contract.md |
| system/Apocalypse/Genre Operating/Apocalypse_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Apocalypse/Genre Operating/Apocalypse_Operating_Guide.md |
| system/Apocalypse/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/Apocalypse/vocabulary.txt |
| system/Cthulhu/Depth/Cthulhu_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Cthulhu/Depth/Cthulhu_Depth_Contract.md |
| system/Cthulhu/Genre Operating/Cthulhu_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Cthulhu/Genre Operating/Cthulhu_Operating_Guide.md |
| system/Cthulhu/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/Cthulhu/vocabulary.txt |
| system/Dark Theme/Depth/DarkTheme_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Dark Theme/Depth/DarkTheme_Depth_Contract.md |
| system/Dark Theme/Genre Operating/DarkTheme_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Dark Theme/Genre Operating/DarkTheme_Operating_Guide.md |
| system/Dark Theme/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/Dark Theme/vocabulary.txt |
| system/Many Children/Depth/ManyChildren_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Many Children/Depth/ManyChildren_Depth_Contract.md |
| system/Many Children/Genre Operating/ManyChildren_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Many Children/Genre Operating/ManyChildren_Operating_Guide.md |
| system/Many Children/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/Many Children/vocabulary.txt |
| system/Meta Genre/Author Style/giang-ho-tai-kien-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/Author Style/giang-ho-tai-kien-style-profile.md |
| system/Meta Genre/Author Style/mac-huong-dong-khuu-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/Author Style/mac-huong-dong-khuu-style-profile.md |
| system/Meta Genre/Author Style/mac-vu-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/Author Style/mac-vu-style-profile.md |
| system/Meta Genre/Author Style/tan-phong-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/Author Style/tan-phong-style-profile.md |
| system/Meta Genre/Author Style/thanh-sam-thu-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/Author Style/thanh-sam-thu-style-profile.md |
| system/Meta Genre/Depth/MetaGenre_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/Depth/MetaGenre_Depth_Contract.md |
| system/Meta Genre/Genre Operating/MetaGenre_System_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/Genre Operating/MetaGenre_System_Operating_Guide.md |
| system/Meta Genre/MetaGenre_consistency_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/MetaGenre_consistency_rules.md |
| system/Meta Genre/MetaGenre_style.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Meta Genre/MetaGenre_style.md |
| system/Romance/Author Style/[CM] CoMan_GuMan_romance_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Romance/Author Style/[CM] CoMan_GuMan_romance_rules.md |
| system/Romance/Author Style/[DH] DongHoa_TongHua_romance_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Romance/Author Style/[DH] DongHoa_TongHua_romance_rules.md |
| system/Romance/Author Style/[DM] DinhMac_DingMo_romance_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Romance/Author Style/[DM] DinhMac_DingMo_romance_rules.md |
| system/Romance/Author Style/[PNTT] PhiNgaTuTon_FeiWoSiCun_romance_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Romance/Author Style/[PNTT] PhiNgaTuTon_FeiWoSiCun_romance_rules.md |
| system/Romance/Author Style/[TDO] TanDiO_XinYiWu_romance_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Romance/Author Style/[TDO] TanDiO_XinYiWu_romance_rules.md |
| system/Romance/Depth/Romance_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Romance/Depth/Romance_Depth_Contract.md |
| system/Romance/Romance_consistency_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Romance/Romance_consistency_rules.md |
| system/Romance/Romance_style.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Romance/Romance_style.md |
| system/Rules Horror/Depth/RulesHorror_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Rules Horror/Depth/RulesHorror_Depth_Contract.md |
| system/Rules Horror/Genre Operating/RulesHorror_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Rules Horror/Genre Operating/RulesHorror_Operating_Guide.md |
| system/Rules Horror/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/Rules Horror/vocabulary.txt |
| system/Sci-fi/Author Style/luu-tu-han-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Author Style/luu-tu-han-style-profile.md |
| system/Sci-fi/Author Style/thai-hong-chi-mon-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Author Style/thai-hong-chi-mon-style-profile.md |
| system/Sci-fi/Author Style/thap-nien-that-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Author Style/thap-nien-that-style-profile.md |
| system/Sci-fi/Author Style/that-thap-nhi-bien-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Author Style/that-thap-nhi-bien-style-profile.md |
| system/Sci-fi/Author Style/vien-dong-style-profile.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Author Style/vien-dong-style-profile.md |
| system/Sci-fi/Depth/SciFi_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Depth/SciFi_Depth_Contract.md |
| system/Sci-fi/Genre Operating/SciFi_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Genre Operating/SciFi_Operating_Guide.md |
| system/Sci-fi/Sci-fi_consistency_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Sci-fi_consistency_rules.md |
| system/Sci-fi/Sci-fi_style.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Sci-fi/Sci-fi_style.md |
| system/Short Form/Depth/ShortForm_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Short Form/Depth/ShortForm_Depth_Contract.md |
| system/Short Form/Genre Operating/ShortForm_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Short Form/Genre Operating/ShortForm_Operating_Guide.md |
| system/Short Form/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/Short Form/vocabulary.txt |
| system/StoryDepth/CREATE_NOVEL_FIELD_EXECUTION.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/StoryDepth/CREATE_NOVEL_FIELD_EXECUTION.md |
| system/Streaming/Depth/Streaming_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Streaming/Depth/Streaming_Depth_Contract.md |
| system/Streaming/Genre Operating/Streaming_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Streaming/Genre Operating/Streaming_Operating_Guide.md |
| system/Streaming/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/Streaming/vocabulary.txt |
| system/Substitute/Depth/Substitute_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Substitute/Depth/Substitute_Depth_Contract.md |
| system/Substitute/Genre Operating/Substitute_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Substitute/Genre Operating/Substitute_Operating_Guide.md |
| system/Substitute/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/Substitute/vocabulary.txt |
| system/Time Travel/Author Style/[AV] AViet_AYue_xuyenkhong_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[AV] AViet_AYue_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[BD] BuiDoCau_PeiTuGou_chuthien_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[BD] BuiDoCau_PeiTuGou_chuthien_rules.md |
| system/Time Travel/Author Style/[HT] PhanNoHuongTieu_AngryBanana_xuyenkhong_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[HT] PhanNoHuongTieu_AngryBanana_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[LU] LaoUngTieuKe_VanTocChiKiep_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[LU] LaoUngTieuKe_VanTocChiKiep_rules.md |
| system/Time Travel/Author Style/[MB] MaiBaoTieuLangQuan_DaiPhung_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[MB] MaiBaoTieuLangQuan_DaiPhung_rules.md |
| system/Time Travel/Author Style/[MN] MaoNi_CatNi_xuyenkhong_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[MN] MaoNi_CatNi_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[NQ] NguyetQuan_YueGuan_xuyenkhong_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[NQ] NguyetQuan_YueGuan_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[TG] TamGioiDaiSu_SanJieDaShi_xuyenkhong_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[TG] TamGioiDaiSu_SanJieDaShi_xuyenkhong_rules.md |
| system/Time Travel/Author Style/[TT] TruuTu_HuiShuoHua_hethong_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[TT] TruuTu_HuiShuoHua_hethong_rules.md |
| system/Time Travel/Author Style/[ZT] Zhttty_TruongHang_vohankhungbo_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Author Style/[ZT] Zhttty_TruongHang_vohankhungbo_rules.md |
| system/Time Travel/Depth/TimeTravel_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Depth/TimeTravel_Depth_Contract.md |
| system/Time Travel/Genre Operating/TimeTravel_Causality_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/Genre Operating/TimeTravel_Causality_Guide.md |
| system/Time Travel/TimeTravel_consistency_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/TimeTravel_consistency_rules.md |
| system/Time Travel/TimeTravel_style.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Time Travel/TimeTravel_style.md |
| system/Urban/Author Style/[KV] KhieuVu_Dancing_urban_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Author Style/[KV] KhieuVu_Dancing_urban_rules.md |
| system/Urban/Author Style/[LHH] LieuHaHue_LiuXiaHui_urban_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Author Style/[LHH] LieuHaHue_LiuXiaHui_urban_rules.md |
| system/Urban/Author Style/[LUAG] LaoUngAnGa_EagleEatsChicken_urban_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Author Style/[LUAG] LaoUngAnGa_EagleEatsChicken_urban_rules.md |
| system/Urban/Author Style/[NNND] NguNhanNhiDai_FishmanII_urban_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Author Style/[NNND] NguNhanNhiDai_FishmanII_urban_rules.md |
| system/Urban/Author Style/[PHHCH] PhongHoaHiChuHau_FengHuo_urban_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Author Style/[PHHCH] PhongHoaHiChuHau_FengHuo_urban_rules.md |
| system/Urban/Depth/Urban_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Depth/Urban_Depth_Contract.md |
| system/Urban/Genre Operating/Urban_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Genre Operating/Urban_Operating_Guide.md |
| system/Urban/Urban_consistency_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Urban_consistency_rules.md |
| system/Urban/Urban_style.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Urban/Urban_style.md |
| system/War Espionage/Depth/WarEspionage_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/War Espionage/Depth/WarEspionage_Depth_Contract.md |
| system/War Espionage/Genre Operating/WarEspionage_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/War Espionage/Genre Operating/WarEspionage_Operating_Guide.md |
| system/War Espionage/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/War Espionage/vocabulary.txt |
| system/Xianxia/Author Style/[CD] ThanDong_ChenDong_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[CD] ThanDong_ChenDong_xianxia_rules.md |
| system/Xianxia/Author Style/[DG] DuongGiaTamThieu_TangJiaSanShao_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[DG] DuongGiaTamThieu_TangJiaSanShao_xianxia_rules.md |
| system/Xianxia/Author Style/[NC] NhiCan_ErGen_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[NC] NhiCan_ErGen_xianxia_rules.md |
| system/Xianxia/Author Style/[OT] MucThichLanNuoc_Cuttlefish_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[OT] MucThichLanNuoc_Cuttlefish_xianxia_rules.md |
| system/Xianxia/Author Style/[PL] PhongLangThienHa_FengLingTianXia_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[PL] PhongLangThienHa_FengLingTianXia_xianxia_rules.md |
| system/Xianxia/Author Style/[PT] PhuongTuong_FangXiang_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[PT] PhuongTuong_FangXiang_xianxia_rules.md |
| system/Xianxia/Author Style/[TD] TieuDinh_XiaoDing_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[TD] TieuDinh_XiaoDing_xianxia_rules.md |
| system/Xianxia/Author Style/[TH] NgaCatTayHongThi_IEatTomatoes_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[TH] NgaCatTayHongThi_IEatTomatoes_xianxia_rules.md |
| system/Xianxia/Author Style/[TT] ThienTamThoDau_SilkwormPotato_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[TT] ThienTamThoDau_SilkwormPotato_xianxia_rules.md |
| system/Xianxia/Author Style/[VN] VongNgu_WangYu_xianxia_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Author Style/[VN] VongNgu_WangYu_xianxia_rules.md |
| system/Xianxia/Depth/Xianxia_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Depth/Xianxia_Depth_Contract.md |
| system/Xianxia/Progression/Cultivation_Progression_System.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Progression/Cultivation_Progression_System.md |
| system/Xianxia/Texture/Tu_Tien_Texture_Floor.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Texture/Tu_Tien_Texture_Floor.md |
| system/Xianxia/World/Xianxia_World_Operating_System.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/World/Xianxia_World_Operating_System.md |
| system/Xianxia/Worldbuilding guide/ThanDong_Worldbuilding_Complete.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/ThanDong_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[DG] DuongGiaTamThieu_Worldbuilding_Complete.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[DG] DuongGiaTamThieu_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[NC] NhiCan_Worldbuilding_Complete.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[NC] NhiCan_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[PL] PhongLangThienHa_Worldbuilding_Complete.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[PL] PhongLangThienHa_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[TD] TieuDinh_Worldbuilding_Complete.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[TD] TieuDinh_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[TH] NgaCatTayHongThi_Worldbuilding_Complete.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[TH] NgaCatTayHongThi_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[TT] ThienTamThoDau_Worldbuilding_Complete.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[TT] ThienTamThoDau_Worldbuilding_Complete.md |
| system/Xianxia/Worldbuilding guide/[VN] VongNgu_Worldbuilding_Complete.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Worldbuilding guide/[VN] VongNgu_Worldbuilding_Complete.md |
| system/Xianxia/Xianxia_consistency_rules.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Xianxia_consistency_rules.md |
| system/Xianxia/Xianxia_style.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/Xianxia/Xianxia_style.md |
| system/eSports/Depth/eSports_Depth_Contract.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/eSports/Depth/eSports_Depth_Contract.md |
| system/eSports/Genre Operating/eSports_Operating_Guide.md | creative-knowledge | kept | skills/novelkit-canon/canon/system/eSports/Genre Operating/eSports_Operating_Guide.md |
| system/eSports/vocabulary.txt | creative-knowledge | kept | skills/novelkit-canon/canon/system/eSports/vocabulary.txt |
| templates/AUTHOR_STYLE_CATALOG.md | creative-knowledge | kept | skills/novelkit-canon/templates/AUTHOR_STYLE_CATALOG.md |
| templates/GOAL_TRACKER_TEMPLATE.md | creative-knowledge | kept | skills/novelkit-canon/templates/GOAL_TRACKER_TEMPLATE.md |
| templates/HYBRID_GENRE_GUIDE.md | creative-knowledge | kept | skills/novelkit-canon/templates/HYBRID_GENRE_GUIDE.md |
| templates/PLAN_TEMPLATE.md | creative-knowledge | kept | skills/novelkit-canon/templates/PLAN_TEMPLATE.md |
| templates/PROJECT_DNA_FILLABLE.md | creative-knowledge | kept | skills/novelkit-canon/templates/PROJECT_DNA_FILLABLE.md |
| templates/PROJECT_DNA_TEMPLATE.md | creative-knowledge | kept | skills/novelkit-canon/templates/PROJECT_DNA_TEMPLATE.md |
| templates/WORKFLOW_TEMPLATE.md | creative-knowledge | kept | skills/novelkit-canon/templates/WORKFLOW_TEMPLATE.md |
| templates/database/master_timeline_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/master_timeline_template.md |
| templates/database/meta_system_operating_config_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/meta_system_operating_config_template.md |
| templates/database/sci_fi_world_operating_config_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/sci_fi_world_operating_config_template.md |
| templates/database/seeds_tracker_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/seeds_tracker_template.md |
| templates/database/style_vault_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/style_vault_template.md |
| templates/database/threads_master_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/threads_master_template.md |
| templates/database/time_travel_causality_config_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/time_travel_causality_config_template.md |
| templates/database/xianxia_character_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/xianxia_character_template.md |
| templates/database/xianxia_world_operating_config_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/database/xianxia_world_operating_config_template.md |
| templates/examples/PROJECT_DNA_SAMPLE_XIANXIA.md | creative-knowledge | kept | skills/novelkit-canon/templates/examples/PROJECT_DNA_SAMPLE_XIANXIA.md |
| templates/genres/PROJECT_DNA_META_GENRE.md | creative-knowledge | kept | skills/novelkit-canon/templates/genres/PROJECT_DNA_META_GENRE.md |
| templates/genres/PROJECT_DNA_ROMANCE.md | creative-knowledge | kept | skills/novelkit-canon/templates/genres/PROJECT_DNA_ROMANCE.md |
| templates/genres/PROJECT_DNA_SCIFI.md | creative-knowledge | kept | skills/novelkit-canon/templates/genres/PROJECT_DNA_SCIFI.md |
| templates/genres/PROJECT_DNA_TIME_TRAVEL.md | creative-knowledge | kept | skills/novelkit-canon/templates/genres/PROJECT_DNA_TIME_TRAVEL.md |
| templates/genres/PROJECT_DNA_URBAN.md | creative-knowledge | kept | skills/novelkit-canon/templates/genres/PROJECT_DNA_URBAN.md |
| templates/genres/PROJECT_DNA_XIANXIA.md | creative-knowledge | kept | skills/novelkit-canon/templates/genres/PROJECT_DNA_XIANXIA.md |
| templates/novel/Memory_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/novel/Memory_template.md |
| templates/novel/NOVEL_STRUCTURE.md | creative-knowledge | kept | skills/novelkit-canon/templates/novel/NOVEL_STRUCTURE.md |
| templates/novel/master_outline_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/novel/master_outline_template.md |
| templates/novel/pipeline_log_template.md | creative-knowledge | kept | skills/novelkit-canon/templates/novel/pipeline_log_template.md |
| templates/novel/pipeline_status_template.json | creative-knowledge | kept | skills/novelkit-canon/templates/novel/pipeline_status_template.json |
| tests/_tmp_test_writers.py | legacy-infra | removed-legacy | — |
| tests/fixtures/reference_excerpts/romance_excerpt.md | legacy-infra | removed-legacy | — |
| tests/fixtures/reference_excerpts/urban_excerpt.md | legacy-infra | removed-legacy | — |
| tests/fixtures/reference_excerpts/xianxia_excerpt.md | legacy-infra | removed-legacy | — |
| tests/fixtures/signoff_golden_xuyen_khong.json | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/.controlplane.sqlite3 | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/.semantic_gates/cache.sqlite3 | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/PROJECT_DNA.md | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/chapters/chapter_001.expected.json | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/chapters/chapter_001.md | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/expected_ai_flavor_report.json | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/expected_cool_point_report.json | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/expected_hook_metadata.json | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/expected_open_loops.json | legacy-infra | removed-legacy | — |
| tests/golden/xianxia/expected_strands.json | legacy-infra | removed-legacy | — |
| tests/test_accept_commit.py | legacy-infra | removed-legacy | — |
| tests/test_account_snapshot.py | legacy-infra | removed-legacy | — |
| tests/test_account_tiers_cli.py | legacy-infra | removed-legacy | — |
| tests/test_account_tiers_config.py | legacy-infra | removed-legacy | — |
| tests/test_account_tiers_db.py | legacy-infra | removed-legacy | — |
| tests/test_ai_flavor_detector.py | legacy-infra | removed-legacy | — |
| tests/test_audit_logger.py | legacy-infra | removed-legacy | — |
| tests/test_chapter_commit.py | legacy-infra | removed-legacy | — |
| tests/test_chapter_commit_reopen.py | legacy-infra | removed-legacy | — |
| tests/test_chapter_cycle_integration.py | legacy-infra | removed-legacy | — |
| tests/test_commit_projection_integration.py | legacy-infra | removed-legacy | — |
| tests/test_commit_projection_seeding.py | legacy-infra | removed-legacy | — |
| tests/test_composite_genre.py | legacy-infra | removed-legacy | — |
| tests/test_cool_point_analyzer.py | legacy-infra | removed-legacy | — |
| tests/test_correctness_property_10_boundary_time.py | legacy-infra | removed-legacy | — |
| tests/test_correctness_property_1_non_invasion.py | legacy-infra | removed-legacy | — |
| tests/test_correctness_property_3_atomic_slot.py | legacy-infra | removed-legacy | — |
| tests/test_correctness_property_5_audit_atomicity.py | legacy-infra | removed-legacy | — |
| tests/test_correctness_property_6_first_login_race.py | legacy-infra | removed-legacy | — |
| tests/test_correctness_property_7_workspace_preservation.py | legacy-infra | removed-legacy | — |
| tests/test_cp_cli.py | legacy-infra | removed-legacy | — |
| tests/test_feature_flag.py | legacy-infra | removed-legacy | — |
| tests/test_gate_registry_keyword_precondition.py | legacy-infra | removed-legacy | — |
| tests/test_gates_semantic_registration.py | legacy-infra | removed-legacy | — |
| tests/test_genre_pack_expansion.py | legacy-infra | removed-legacy | — |
| tests/test_graph_doctor.py | legacy-infra | removed-legacy | — |
| tests/test_graph_index.py | legacy-infra | removed-legacy | — |
| tests/test_graph_integration.py | legacy-infra | removed-legacy | — |
| tests/test_graph_writer.py | legacy-infra | removed-legacy | — |
| tests/test_hook_tracker.py | legacy-infra | removed-legacy | — |
| tests/test_infra.py | legacy-infra | removed-legacy | — |
| tests/test_ingress_matrix_18_3.py | legacy-infra | removed-legacy | — |
| tests/test_ingress_matrix_verification.py | legacy-infra | removed-legacy | — |
| tests/test_map_writer.py | legacy-infra | removed-legacy | — |
| tests/test_mem0_writer.py | legacy-infra | removed-legacy | — |
| tests/test_memory_bootstrap.py | legacy-infra | removed-legacy | — |
| tests/test_memory_cli.py | legacy-infra | removed-legacy | — |
| tests/test_memory_compactor.py | legacy-infra | removed-legacy | — |
| tests/test_memory_integration.py | legacy-infra | removed-legacy | — |
| tests/test_memory_item.py | legacy-infra | removed-legacy | — |
| tests/test_memory_pack.py | legacy-infra | removed-legacy | — |
| tests/test_memory_render.py | legacy-infra | removed-legacy | — |
| tests/test_memory_store.py | legacy-infra | removed-legacy | — |
| tests/test_memory_writer_v2.py | legacy-infra | removed-legacy | — |
| tests/test_memory_writer_v2_smoke.py | legacy-infra | removed-legacy | — |
| tests/test_migration.py | legacy-infra | removed-legacy | — |
| tests/test_novel_lifecycle.py | legacy-infra | removed-legacy | — |
| tests/test_open_loops.py | legacy-infra | removed-legacy | — |
| tests/test_phase2_hardening.py | legacy-infra | removed-legacy | — |
| tests/test_pipeline_resilience.py | legacy-infra | removed-legacy | — |
| tests/test_pipeline_status_writer.py | legacy-infra | removed-legacy | — |
| tests/test_progression_writer.py | legacy-infra | removed-legacy | — |
| tests/test_projection_runner.py | legacy-infra | removed-legacy | — |
| tests/test_quota_gate_claim.py | legacy-infra | removed-legacy | — |
| tests/test_quota_gate_sync.py | legacy-infra | removed-legacy | — |
| tests/test_quota_manager.py | legacy-infra | removed-legacy | — |
| tests/test_rag_router.py | legacy-infra | removed-legacy | — |
| tests/test_rag_writer.py | legacy-infra | removed-legacy | — |
| tests/test_reference_deconstructor.py | legacy-infra | removed-legacy | — |
| tests/test_replay_command.py | legacy-infra | removed-legacy | — |
| tests/test_reranker.py | legacy-infra | removed-legacy | — |
| tests/test_rrf.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_budget.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_circuit_breaker.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_common.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_doctor_status.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_observability.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_policy.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_prompts.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_runner.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_verdict.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_verdict_cache.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_verify_llm.py | legacy-infra | removed-legacy | — |
| tests/test_semantic_gates_xianxia.py | legacy-infra | removed-legacy | — |
| tests/test_startup_validator.py | legacy-infra | removed-legacy | — |
| tests/test_status_retrieval.py | legacy-infra | removed-legacy | — |
| tests/test_strand_weaver.py | legacy-infra | removed-legacy | — |
| tests/test_subscription_service.py | legacy-infra | removed-legacy | — |
| tests/test_sweepers.py | legacy-infra | removed-legacy | — |
| tests/test_user_service.py | legacy-infra | removed-legacy | — |
| tests/test_vector_writer.py | legacy-infra | removed-legacy | — |
| tests/test_write_next.py | legacy-infra | removed-legacy | — |
