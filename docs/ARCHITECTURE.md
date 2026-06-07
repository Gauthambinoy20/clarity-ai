# ClarityAI Architecture

How the system fits together, derived from the code in this repository.
Each diagram names real modules, routes and tables — if it's in a box here,
you can find it in the tree.

ClarityAI reports probabilistic writing signals. It is designed for portfolio
demonstration, editorial triage, and NLP experimentation, not definitive
authorship attribution.

## 1. System architecture

All components and how they connect. The frontend is a static React build
served by nginx; the backend is a single FastAPI service that owns the ML
pipeline, the database and the websocket.

```mermaid
flowchart LR
    subgraph Client
        B[Browser]
    end

    subgraph Frontend["frontend/ (React 18 + MUI, nginx)"]
        UI["8 pages<br/>Detect · Analytics · Plagiarism · Humanize<br/>Batch · Compare · History · Dashboard"]
        API["src/utils/api.ts<br/>axios client"]
    end

    subgraph Backend["backend/app (FastAPI)"]
        RT["api/routes/*<br/>detection · analytics · dashboard · plagiarism<br/>humanization · export · advanced · realtime · health"]
        RL[core/rate_limiter.py]
        WS[core/websocket.py]
        subgraph ML["app/ml"]
            DET["detectors/ — 19 signals"]
            ENS[ensemble/meta_learner.py]
            ANA["analyzers/ — 17 modules"]
            HUM[humanizer/ pipeline]
            PLAG[plagiarism/ pipeline]
            REG[models/model_registry.py]
        end
        DB[("SQLite via<br/>SQLAlchemy async")]
    end

    HF[("Hugging Face hub<br/>gpt2 · distilgpt2 · gpt2-medium<br/>RoBERTa detector heads")]
    OL["Ollama — optional<br/>local rewrite model"]

    B --> UI --> API --> RT
    B -. "ws /ws/detect" .-> WS
    RT --> RL
    RT --> DET & ANA & HUM & PLAG
    DET --> ENS
    DET & ANA --> REG
    REG -. "first use, then cached" .-> HF
    HUM -. http .-> OL
    RT --> DB
```

## 2. Data flow (DFD)

Where a piece of user text travels, from input to stored result.

```mermaid
flowchart TD
    SRC([User text / file upload]) --> VAL{"Validation<br/>pydantic schema +<br/>MIN_WORDS/MAX_WORDS"}
    VAL -- reject --> ERR([422 with clear message])
    VAL -- accept --> RLIM{Rate limiter}
    RLIM -- over budget --> R429([429])
    RLIM -- ok --> FAN["Detector fan-out<br/>asyncio.gather over roster"]
    FAN --> BRIDGE["_bridge_signals<br/>name translation"]
    BRIDGE --> META["EnsembleMetaLearner.predict<br/>weighted features + watermark override"]
    META --> CLS[classification + confidence]
    FAN --> VIZ["per-signal details<br/>GLTR token_data · heatmap · attribution"]
    CLS --> STORE[(analyses table)]
    VIZ --> STORE
    STORE --> RESP([JSON response])
    STORE --> EXP["export/ PDF · JSON · CSV · share links"]
    STORE --> DASH["dashboard/ stats · trends · top signals"]
```

## 3. Sequence — the /detect request lifecycle

The core path of the product, as implemented in
`api/routes/detection.py::_run_full_detection`.

```mermaid
sequenceDiagram
    participant C as Client
    participant R as detection.py
    participant Reg as ModelRegistry
    participant D as 14 detectors
    participant E as EnsembleMetaLearner
    participant DB as SQLite

    C->>R: POST /api/v1/detect {text, mode, options}
    R->>R: word-count guard (422 if out of range)
    R->>D: asyncio.gather(_run_detector × roster)
    D->>Reg: get_model("gpt2" / roberta heads)
    Reg-->>D: cached model (downloads once)
    Note over D: a failing detector degrades to a<br/>flagged neutral result, never raises
    D-->>R: signal results
    R->>E: predict(_bridge_signals(results))
    E-->>R: overall_score + interpretation
    R->>DB: INSERT analyses row (signals as JSON)
    R-->>C: score, classification, signals,<br/>sentence heatmap, GLTR tokens, attribution
```

## 4. Sequence — humanize and plagiarism (compact)

```mermaid
sequenceDiagram
    participant C as Client
    participant H as humanization.py
    participant P as plagiarism.py
    participant OL as Ollama (optional)
    participant DB as SQLite

    C->>H: POST /api/v1/humanize
    H->>H: rule-based stages (lexical → structural → targeted)
    H->>OL: rewrite request (if configured)
    OL-->>H: rewritten text (or unavailable → rule-based only)
    H->>DB: humanization_results row
    H-->>C: before/after + score delta

    C->>P: POST /api/v1/plagiarism
    P->>P: exact n-gram match (cheap, first)
    P->>P: semantic embedding match (gated)
    P->>P: source discovery (network, last)
    P->>DB: plagiarism_results rows
    P-->>C: matches + sources
```

## 5. Entity-relationship

Six tables; JSON payloads live in TEXT columns because SQLite has no native
JSON type.

```mermaid
erDiagram
    analyses ||--o{ plagiarism_results : "analysis_id (CASCADE)"
    analyses ||--o{ humanization_results : "analysis_id (CASCADE)"

    analyses {
        string id PK
        text input_text
        int word_count
        float overall_ai_score
        string classification
        float confidence
        text signals_json
        text sentence_scores_json
        text gltr_data_json
        string attribution_model
        int processing_time_ms
        string model_version
        datetime created_at
    }
    plagiarism_results {
        string id PK
        string analysis_id FK
        text source_url
        string source_title
        text matched_text
        float similarity_score
        string method
        text details_json
        datetime created_at
    }
    humanization_results {
        string id PK
        string analysis_id FK
        text original_text
        text humanized_text
        float original_ai_score
        float humanized_ai_score
        int iterations_used
        string strategy
        int processing_time_ms
        datetime created_at
    }
    batch_jobs {
        string id PK
        string status
        int total_files
        int processed_files
        int failed_files
        text results_json
        text error_message
        datetime started_at
        datetime completed_at
        datetime created_at
    }
    analytics_results {
        string id PK
        string analysis_type
        text input_text
        text results_json
        int processing_time_ms
        datetime created_at
    }
    api_usage {
        int id PK
        string client_ip
        string endpoint
        string method
        int status_code
        int response_time_ms
        int request_size_bytes
        string api_key_hash
        datetime created_at
    }
```

## 6. Module map (backend)

Internal dependency direction — routes orchestrate, ml computes, core and db
support. Nothing in `ml/` imports from `api/`.

```mermaid
flowchart TD
    MAIN[app/main.py] --> ROUTES[api/routes/*]
    MAIN --> CFG[core/config.py]
    ROUTES --> CFG
    ROUTES --> RL[core/rate_limiter.py]
    ROUTES --> WSM[core/websocket.py]
    ROUTES --> DBM[db/database.py + db/models.py]
    ROUTES --> DET[ml/detectors/*]
    ROUTES --> ANA[ml/analyzers/*]
    ROUTES --> HUM[ml/humanizer/*]
    ROUTES --> PLG[ml/plagiarism/*]
    ROUTES --> ENS[ml/ensemble/meta_learner.py]
    DET --> BASE[ml/detectors/base.py]
    DET --> REG[ml/models/model_registry.py]
    ANA --> REG
    REG --> CFG
```

## 7. State machine — batch jobs

From `db/models.py::BatchJob` and the batch path in
`api/routes/detection.py`.

```mermaid
stateDiagram-v2
    [*] --> pending : POST /detect/batch
    pending --> processing : background task starts (started_at set)
    processing --> processing : per-item result appended
    processing --> completed : all items done (completed_at set)
    processing --> failed : unrecoverable error (error_message set)
    completed --> [*]
    failed --> [*]
```

## 8. Trust boundaries

Where untrusted input is validated and what the service trusts.

```mermaid
flowchart LR
    subgraph Untrusted
        U1[User text]
        U2["File uploads<br/>PDF · DOCX · TXT"]
        U3[Share tokens from URLs]
        U4[Websocket messages]
    end

    subgraph Validation["Validation layer"]
        V1["pydantic schemas<br/>length + type bounds"]
        V2["upload type/size limits"]
        V3["token lookup — 404 on miss"]
        V4["JSON parse with error reply"]
        RL2[rate limiter per client]
    end

    subgraph Trusted["Trusted internals"]
        T1[ML pipeline]
        T2[(SQLite)]
    end

    subgraph External["External (supply chain)"]
        E1["Hugging Face model downloads<br/>pinned ids in core/config.py"]
        E2[Ollama on localhost]
    end

    U1 --> V1 --> RL2 --> T1
    U2 --> V2 --> T1
    U3 --> V3 --> T2
    U4 --> V4 --> T1
    T1 --> T2
    T1 -. model load .-> E1
    T1 -. rewrite .-> E2
```

> The deployment/infrastructure diagram is added alongside the Terraform
> code in `infra/` so it documents what is actually provisioned.
