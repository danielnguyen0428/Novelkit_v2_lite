# NovelKit V2 Lite：AI 长篇小说创作工具

**语言：** [Tiếng Việt](README.md) · [English](README.en.md) ·
**简体中文** · [한국어](README.ko.md) · [日本語](README.ja.md)

**用 AI 创作长篇连载小说，同时守住设定一致性与创作主导权。**

NovelKit V2 Lite 将故事创意转化为结构化的创作流程：建立故事正典
（canon）、规划情节、逐章写作、质量审查、一致性检查，并把通过审核的
变化同步回项目记忆。

它不是一个只会“续写”的聊天框。NovelKit 把 AI 组织成可观察、可控制的
内容生产流水线。即使章节、人物和事件线不断增加，作者仍然掌握故事方向。

**正典一致 · 按章流水线 · 数据本地保存 · 模型自由选择**

你决定故事。NovelKit 负责背后的复杂运行工作。

> **个人、教育、研究、评估及非商业用途可免费使用。** AI provider 由你
> 自行选择并直接承担模型费用。商业使用以及任何修改版或衍生版，都必须事先
> 获得书面许可。

| 核心能力 | 关键依据 |
| --- | --- |
| 类型配置 | 6 个 genre canon pack + 明确的 hybrid routing |
| 长期记忆 | A–E 五层 · 8 个数据 category · 受控 rotation |
| Quality Gate | 85 分通过 · 70 分 soft-fail/revise · 仅接受后的 canon 才会晋级 |
| 创作经验 | 3 年实际写作 · 真实项目 · 已出版书籍 |
| 运营能力 | 面向 local-first、单 operator 的 Production-ready |

## 为什么需要 NovelKit？

LLM 可以写出精彩的单个场景，但长篇小说需要的不只是一个好 prompt。在普通
聊天流程中，作者往往需要不断重复背景、手动维护 canon、检查矛盾，并管理散落
在不同位置的资料。

NovelKit 把这些工作集中到一个 Studio 中：

| 长篇创作难题 | NovelKit V2 Lite 的解决方式 |
| --- | --- |
| 模型在多章后遗忘细节 | 维护 canon、memory、summaries 与 knowledge graph |
| 人物状态或时间线发生漂移 | 执行 diagnostics、review gate 与一致性检查 |
| Prompt 和策划资料分散 | 将 DNA、大纲、世界观、章节与 review 放进同一 workspace |
| 不清楚下一步该做什么 | 通过确定性 pipeline 标记可执行 task 与章节状态 |
| 被单一模型供应商绑定 | 使用用户自行配置的 OpenAI-compatible endpoint |
| 担心稿件被托管平台控制 | 将运行数据与小说 workspace 保存在本机 |

## 产品优势

### 1. 项目越长，故事脉络仍然清晰

NovelKit 将“故事记忆”从模型短暂的对话窗口中分离出来。系统持续维护
`PROJECT_DNA`、人物、世界规则、时间线、大纲、章节摘要、curated memory
与 narrative graph，为每个 task 提供针对性的 context。

**业务价值：**减少手动重复 prompt，并在设定偏差扩散到后续章节前更早发现
问题。

### 2. 用可控流程生产章节，而不是依赖一次生成

每个章节都经过清晰可见的流程：

```mermaid
flowchart LR
    DNA["Project DNA"] --> World["世界观构建"]
    World --> Outline["章节大纲"]
    Outline --> Draft["初稿"]
    Draft --> Check["自检"]
    Check --> Review["质量审查"]
    Review --> Gate{"通过 Gate？"}
    Gate -- 是 --> Sync["同步至 canon"]
    Gate -- 尚未 --> Revise["修改初稿"]
    Revise --> Draft
    Sync --> Next["下一章"]
```

Pipeline 会跟踪 task、版本、checkpoint 和 review 结果。作者可以查看、干预、
继续或恢复流程，而不是在一次 provider 调用失败后丢失整次进度。

**业务价值：**让 AI 从一次性文字生成器变成可观察、可管理的内容生产流程。

### 3. 数据留在本机，模型由你决定

- Studio 默认只绑定 `127.0.0.1`。
- 稿件和 canon 保存在本地 workspace。
- API key 写入 SQLite 前会先加密。
- NovelKit 没有 telemetry，也没有接收你稿件的 NovelKit server。
- 只有 inference 必需的 prompt 与 context 会发送到你选择的 provider。
- 支持 OpenAI-compatible 的 base URL、model ID 与 API key。

**业务价值：**自行控制数据存储位置、模型选择和 inference 成本。

### 4. 专为长篇连载叙事设计

NovelKit 不会把通用内容 workflow 套用到所有作品。系统包含 genre canon、
hybrid genre、long-form compass、strand tracking、recall、language guard 与
narrative continuity gate。

Author reference 仅作为中性的身份 metadata。Runtime 不模仿真实作者的节奏、
词汇、结构或个人“禁忌”。

**业务价值：**让模型遵守项目与类型约束，同时避免把产品变成个人文风复制工具。

### 5. 比单一写作脚本更可靠

- Background job 会持久化到 database，UI reload 后仍能继续查看。
- 同一时间只有一个 run 可以写入某部小说。
- File lock 与 optimistic version 降低 state 被覆盖的风险。
- Service restart 时会处理遗留的 orphaned job。
- Review 与 sync 将 draft 和已接受 canon 分开管理。

**业务价值：**降低长项目运行或 provider 故障时 state 损坏的风险。

### 6. 有真实创作经验支撑的类型配置

NovelKit 提供六个核心 genre canon pack：仙侠、都市、言情、科幻、穿越和 Meta
Genre。类型配置不只是替换 prompt 关键词，还会路由世界规则、人物状态、情节线、
language guard、专业角色和 review checklist。Hybrid genre 也有明确的 primary
genre、secondary genre 与混合比例。

这套配置来自真实的小说创作实践。作者拥有**3 年写作经验**，有**实际小说项目**
和**已经出版的书籍**。这些经验被沉淀到 DNA 表单、模板、canon pack 和可重复运行
的检查中，而不是依赖一次聊天的直觉。

**业务价值：**按类型快速启动，同时保留长篇连载所需的研究深度与制作纪律。

### 7. 长期记忆是一套运行系统，而不是便签框

Memory 按 novel 隔离，并以结构化 item 存储在八个 category 中，包括
`character_state`、`story_facts`、`world_rules`、`timeline`、`open_loops`、
`reader_promises`、`relationships` 和 `minor_cast`。

五层 A–E 用来区分 canon、episode/context、summary 与 curated memory。Active memory
约限制在 3,500 个词以内；较旧内容会受控地 rotation 到 archive，而不是静默丢弃。
Context engine 会优先使用权威 canon，而不是 derivative index 或 cache。

**业务价值：**系列越写越长，也不会因 context 稀释或不同 novel 串数据而失控。

### 8. 从初稿到 canon 之间的严格 Quality Gate

NovelKit 不会把模型第一次输出直接当作正式章节。每章都必须经过 self-check、review
与 sync gate；参考阈值是**85 分通过**、**70 分 soft-fail/revise**。低于阈值或发生
hard fail 时，初稿会回到有边界的修改循环。只有通过 gate 的章节才能进入 canon。

Quality Auditor 与 Sync 会生成可检查的交付记录。相较于只聊天或自由调用 model 的
工具，这是结构上的优势：确定性 DAG 维护 task 顺序，model 不能跳过 gate，缺陷也会
在进入下一章前被拦截。

**业务价值：**质量有标准、有停止条件，也有恢复路径，适合 editorial review、联合
制作与连载 catalog。

### 9. 面向 local-first 运营模型的 Production-ready

Lite 的目标是真实运行单 operator 的工作流，而不只是 demo：

- 使用 `temp + fsync + rename` 的原子写入；
- 通过 digest、optimistic version 和 transaction manifest 支持 sync/recovery；
- per-novel thread/file lock，避免并发写入；
- persistent background jobs、status polling 与 startup recovery；
- 加密 provider key、脱敏 error code 和本地 backup 边界；
- source 中包含 backend、frontend 与 property-based tests。

这里的“production-ready”限定为可靠的本地创作流程。Multi-user、billing、public
catalog 与 cloud deployment 属于 Full NovelKit 或单独的实施项目。

### 10. 可复制到整个内容 catalog 的基础

File-first canon、genre routing、memory isolation 和 chapter pipeline 让流程可以
复制到多部小说。Editorial 团队可以用同一套方式保存 story bible、review record、
handoff artifact 与 series 状态。

**业务价值：**从单一写作 prototype 走向可控制、可交接的内容 line-up。

## 在 Studio 中可以做什么？

- 根据 premise、类型、人物和目标章节数创建小说。
- 从简短 brief 出发，使用 AI 完成 `PROJECT_DNA`。
- 按章节数规划并运行 pipeline。
- 阅读章节、策划文档和 worldbuilding artifacts。
- 查看 run status、usage metadata 与可恢复错误。
- 使用 Doctor 和 Diagnostics 检查故事结构。
- 在 narrative graph 中查看人物、地点与事件关系。
- 分析 language guard 与机器化文本信号。
- 通过 steer、advanced controls 和 NovelCLI 干预 pipeline 方向。

## Demo 界面

Studio 中的两个代表性界面：

<p align="center">
  <img src="docs/screenshots/quick-setup-ai-story.png" alt="Quick Setup — AI 创建小说" width="49%" />
  <img src="docs/screenshots/studio-project-dna-pipeline.png" alt="Studio — PROJECT_DNA 与写作 pipeline" width="49%" />
</p>
<p align="center"><em>用 Quick Setup 创建 PROJECT_DNA &nbsp;•&nbsp; 在 Studio 跟踪 canon 与写作 pipeline</em></p>

## 合作与 Full NovelKit

NovelKit V2 Lite 是用于评估、研究和搭建 workflow 的本地版本。出版社、内容 studio、
creator network 或产品团队若需要完整的生产、授权与 catalog 能力，可通过
[novelkit.cc](https://novelkit.cc/) 了解 Full NovelKit 合作方案。

合作可以从 sample 开始：类型 brief、目标产量与版权模型 → sample chapter + story
bible + pipeline log → 联合 review → 扩展 line-up 或定制部署。双方可在签订更大合作
前，先用实际交付物确认质量与权利边界。

- [了解 Full NovelKit](https://novelkit.cc/) — 平台与 production 能力。
- [AI 小说创作方案](https://novelkit.cc/sang-tac-tieu-thuyet-ai) — 服务与 catalog 方向。
- [洽谈合作](https://novelkit.cc/#cta) — 提交 brief 或 sample 需求。

Lite repo 仍受 [LICENSE](LICENSE) 约束：商业化或创建修改版/衍生版必须获得明确许可。
购买或合作使用 Full NovelKit 属于独立的产品/服务协议。

## 适合谁？

- 网络小说与连载小说作者。
- 需要管理大量人物、情节线和 canon 文档的创作者。
- 希望使用 AI、但不想把完整稿件交给 SaaS 的作者。
- 需要可观察、可测试创作 pipeline 的 builder 与 researcher。

NovelKit V2 Lite 当前面向**单台电脑上的单一 operator**。它不是 multi-user
backend，不应直接暴露到 Internet。

## 30 秒了解架构

```mermaid
flowchart LR
    Writer["作者"] --> Studio["React Studio"]

    subgraph Local["本地电脑"]
        Studio --> API["FastAPI"]
        API --> Jobs["持久化 jobs"]
        Jobs --> Pipeline["Pipeline + creative tools"]
        Pipeline --> DB[("SQLite metadata")]
        Pipeline --> Files[("小说 workspaces")]
    end

    Pipeline -->|"HTTPS · prompt/context"| Provider["你选择的 AI provider"]
    Provider -->|"model output"| Pipeline
```

Production frontend 与 API 在同一个 Uvicorn process 中通过同源提供。Lite
不需要 Redis、Celery、PostgreSQL 或独立 worker server。

## 几分钟内开始使用

### 环境要求

- Python 3.11 或更高版本。
- Node.js 20.19+ 或 22.12+。
- npm。

### 安装与运行

```bash
git clone https://github.com/danielnguyen0428/Novelkit_v2_lite.git
cd Novelkit_v2_lite
./setup.sh
./run-local.sh
```

打开 <http://127.0.0.1:8000/studio>。

需要更换端口时：

```bash
PORT=8080 ./run-local.sh
```

### 连接 AI provider

在 Studio 中打开 **Settings**，然后填写：

- OpenAI-compatible base URL；
- model ID；
- API key。

NovelKit 不销售 token，也不要求 subscription。Inference 成本取决于你选择的
provider 和 model。

## 本地数据位置

| 路径 | 内容 |
| --- | --- |
| `.data/novelkit-lite.db` | 小说 metadata、provider settings、run jobs 与 usage ledger |
| `.secrets/master.key` | 用于解密 provider API key 的密钥 |
| `storage/users/.../novels/<uuid>/` | Studio 创建的 canon、章节与 artifacts |
| `workspaces/` | 旧 CLI/runtime 路径的 compatibility root |

这些 runtime 路径都已加入 `.gitignore`。备份时，请把 database、master key 和
`storage/` 保存在同一个 snapshot 中。

## 开发与验证

Backend：

```bash
./.venv/bin/python -m pytest \
  tests/test_lite_api.py \
  tests/test_webapi.py \
  tests/test_run_jobs.py -q
```

Frontend：

```bash
node --test webapp/frontend/tests/*.test.mjs
npm run build --prefix webapp/frontend
```

## 技术文档

- [ARCHITECTURE.md](ARCHITECTURE.md) — 系统边界与数据流。
- [RUNBOOK.md](RUNBOOK.md) — 安装、运行、备份与故障处理。
- [KNOWLEDGE_GRAPH.md](KNOWLEDGE_GRAPH.md) — 知识模型与数据归属。
- [KNOWLEDGE_GRAPH_DETAIL.md](KNOWLEDGE_GRAPH_DETAIL.md) — 模块、API 与 artifacts。
- [TECHNICAL_DIAGRAMS.md](TECHNICAL_DIAGRAMS.md) — 架构、sequence、lifecycle 与 data graphs。
- [CHANGELOG.md](CHANGELOG.md) — Lite 版本变更记录。

## 许可证与商业使用

NovelKit V2 Lite 使用 **source-available** 许可证发布，并非 open-source：

- 个人、教育、研究、评估与非商业用途免费；
- 未经许可不得修改、改编或创建衍生作品；
- 未经许可不得直接或间接用于商业目的；
- 必须保留版权声明和 provenance metadata。

许可证标识：`LicenseRef-NovelKit-V2-Lite-NC-ND-1.0`（定制的 source-available
许可证，并非 OSI 批准的 open-source 许可证）。

具体约束以 [LICENSE](LICENSE) 为准。申请商业授权或开发修改版本，请联系
**danielnguyen0428@gmail.com**。

Canonical provenance ID：

```text
NOVELKIT-V2-LITE-DN0428-20260828-12A133B9E572
```

验证信息位于 [NOTICE](NOTICE)、[PROVENANCE.json](PROVENANCE.json) 和
`GET /api/provenance`。该机制不会收集或传输用户数据。
