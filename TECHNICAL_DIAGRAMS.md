# NovelKit V2 Lite — Technical diagrams

[← README](README.md) · [Architecture](ARCHITECTURE.md) ·
[Knowledge graph](KNOWLEDGE_GRAPH.md)

Các nhãn kỹ thuật trong tài liệu này dùng English để làm điểm tham chiếu chung
cho toàn bộ README đã bản địa hóa. Sơ đồ phản ánh runtime Lite hiện tại, không mô
tả kiến trúc của bản full hoặc một SaaS giả định.

## 1. Product operating loop

Sơ đồ này cho thấy giá trị cốt lõi: mỗi chương mới làm giàu canon, rồi canon cập
nhật quay lại cung cấp context cho chương kế tiếp.

```mermaid
flowchart LR
    Intent["Writer intent"] --> DNA["Project DNA"]
    DNA --> Plan["World + plot planning"]
    Plan --> Produce["Chapter production"]
    Produce --> Verify["Review + consistency gates"]
    Verify --> Canon["Accepted canon"]
    Canon --> Memory["Memory + summaries + graph"]
    Memory --> Context["Context for the next task"]
    Context --> Produce
    Verify -->|"needs revision"| Produce
```

## 2. System context

Mọi thành phần trừ AI provider đều chạy trên máy của operator. Prompt và context
cần cho inference rời máy qua HTTPS tới provider do operator cấu hình.

```mermaid
flowchart TB
    Writer["Local operator"] --> Browser["Browser"]

    subgraph Machine["Local machine"]
        Browser --> Studio["React Studio"]
        Studio -->|"JSON / same origin"| API["FastAPI"]
        API --> Service["NovelKitService"]
        API --> Jobs["Persistent run jobs"]
        Jobs --> Service
        Service --> Runtime["Pipeline + creative tools"]
        Runtime --> DB[("SQLite")]
        Runtime --> Workspace[("File-first workspaces")]
        API --> Assets["Built frontend assets"]
    end

    Runtime -->|"HTTPS · prompt/context"| Provider["OpenAI-compatible provider"]
    Provider -->|"model output"| Runtime
```

## 3. Background run sequence

API trả `job_id` ngay sau khi persist request. Studio poll trạng thái trong khi
daemon thread thực thi pipeline; vì metadata nằm trong SQLite, reload tab không
làm mất khả năng theo dõi job.

```mermaid
sequenceDiagram
    actor Writer
    participant UI as React Studio
    participant API as FastAPI
    participant DB as SQLite
    participant Worker as Daemon thread
    participant Pipe as Pipeline
    participant LLM as AI provider
    participant Files as Novel workspace

    Writer->>UI: Run N chapters
    UI->>API: POST /run-async
    API->>DB: Insert queued job
    API-->>UI: job_id + queued
    API->>Worker: Start background execution

    par Background execution
        Worker->>DB: Mark running
        loop Each ready task
            Worker->>Pipe: Load state and plan next task
            Pipe->>Files: Read scoped canon/context
            Pipe->>LLM: Send prompt/context
            LLM-->>Pipe: Return model output
            Pipe->>Files: Write draft/review/sync artifacts
            Pipe->>DB: Record redacted usage metadata
        end
        Worker->>DB: Mark completed or failed
    and Status polling
        loop While job is active
            UI->>API: GET /run-status
            API->>DB: Read latest job
            API-->>UI: Persisted status
        end
    end
```

## 4. Long-form chapter pipeline

Mỗi outline chờ state barrier của chương trước. Draft chỉ trở thành canonical
chapter sau self-check, quality review và sync gate.

```mermaid
flowchart LR
    Bootstrap["Bootstrap canon"] --> Outline["Outline chapter N"]
    Prev["Chapter N-1 state barrier"] --> Outline
    Outline --> Write["Write draft"]
    Write --> SelfCheck["Deterministic self-check"]
    SelfCheck --> Review["Quality review"]
    Review --> Gate{"Review gate"}
    Gate -->|"pass"| Sync["Sync state"]
    Gate -->|"revise"| Rewrite["Bounded rewrite cycle"]
    Rewrite --> Review
    Sync --> Chapter["Canonical chapter N"]
    Sync --> Memory["Memory + summaries"]
    Sync --> Graph["Narrative graph projection"]
    Sync --> Next["Chapter N+1 barrier"]
```

## 5. Persistent job lifecycle

Job lifecycle thuộc process/SQLite. Pause, resume, steer và cancel-after-step là
commands áp dụng tại task boundary của authoritative pipeline state.

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Queued: start run
    Queued --> Running: daemon starts
    Running --> Completed: run report persisted
    Running --> Failed: busy/provider/runtime error
    Queued --> Failed: process restarted
    Running --> Failed: process restarted
    Completed --> Queued: start a new run
    Failed --> Queued: recover and retry
```

## 6. Data authority and derived views

Context retrieval ưu tiên authority trước relevance. Cache, logs và graph là
projection có thể rebuild; chúng không được ghi đè fact trong canon.

```mermaid
flowchart TB
    DNA["PROJECT_DNA + genre canon<br/>highest authority"]
    Canon["Characters · world · timeline<br/>outlines · accepted chapters · reviews"]
    Memory["Curated memory + summaries"]
    Support["Templates + operational docs"]
    Derived["Logs · status projection<br/>RAG index · narrative graph"]

    DNA --> Canon
    Canon --> Memory
    Memory --> Support
    Support --> Derived

    Canon -. "rebuild derived views" .-> Derived
```

## 7. Storage ownership graph

SQLite giữ metadata vận hành; workspace giữ narrative source of truth. Hai nhóm
dữ liệu phải được backup trong cùng snapshot với encryption key.

```mermaid
flowchart LR
    Owner["Internal local owner"] --> Novel["Novel record"]
    Owner --> Settings["Encrypted provider settings"]
    Novel --> Job["Run job + usage ledger"]
    Novel --> Workspace["Owner-scoped workspace"]

    subgraph SQLite[".data/novelkit-lite.db"]
        Owner
        Novel
        Settings
        Job
    end

    subgraph Files["storage/users/.../novels/UUID"]
        Workspace --> ProjectDNA["PROJECT_DNA"]
        Workspace --> Database["Narrative databases"]
        Workspace --> Drafts["Drafts + reviews"]
        Workspace --> Chapters["Canonical chapters"]
        Workspace --> RuntimeState["Pipeline state + indexes"]
    end

    Key[".secrets/master.key"] --> Settings
```

## 8. Narrative knowledge graph

Graph là một projection để khám phá quan hệ và contradictions. Canon trong file
workspace vẫn là nguồn có authority cao hơn.

```mermaid
graph TD
    Novel["Novel"] --> Character["Character"]
    Novel --> Location["Location"]
    Novel --> Faction["Faction"]
    Novel --> System["World system"]
    Novel --> Thread["Plot thread"]
    Novel --> Chapter["Chapter"]

    Character -->|"member of"| Faction
    Character -->|"appears in"| Chapter
    Character -->|"travels to"| Location
    Chapter -->|"advances"| Thread
    System -->|"constrains"| Character
    Chapter --> Event["Event"]
    Event -->|"changes state"| Character
    Event -->|"occurs at"| Location

    Chapter --> Summary["Summary"]
    Summary --> Memory["Curated memory"]
    Memory --> Context["Next-task context"]
```

## 9. Lite evaluation to Full NovelKit partnership

Lite và Full là hai phạm vi sản phẩm khác nhau. Repo này phù hợp để đánh giá và
phát triển workflow local; nhu cầu production catalog, licensing hoặc triển khai
cho đội ngũ được trao đổi riêng qua [novelkit.cc](https://novelkit.cc/).

```mermaid
flowchart LR
    Lite["NovelKit V2 Lite<br/>local evaluation"]
    Brief["Genre brief<br/>output target · rights model"]
    Sample["Sample delivery<br/>chapter + story bible + pipeline log"]
    Review["Joint quality + rights review"]
    Full["Full NovelKit<br/>production / licensing / deployment"]
    Catalog["Serialized catalog<br/>line-up operations"]

    Lite --> Brief
    Brief --> Sample
    Sample --> Review
    Review -->|"approved scope"| Full
    Full --> Catalog
    Review -->|"iterate"| Sample
```

## Verification anchors

- Canonical repository:
  <https://github.com/danielnguyen0428/Novelkit_v2_lite>
- Provenance ID: `NOVELKIT-V2-LITE-DN0428-20260828-12A133B9E572`
- Runtime metadata: `GET /api/provenance`
- Source manifest: [PROVENANCE.json](PROVENANCE.json)
