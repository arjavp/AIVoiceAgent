# Voice Agent — System Design Document

---

## 1. Setup Instructions (from scratch)

### Prerequisites

| Dependency       | Version  | Purpose                          |
|------------------|----------|----------------------------------|
| Python           | 3.11+    | Runtime                          |
| PostgreSQL       | 14+      | Primary database + pgvector      |
| Redis            | 7+       | Celery broker / Channels backend |
| LiveKit Server   | latest   | WebRTC media server              |

### Step-by-step

```bash
# 1. Clone the repository
git clone <repo-url>
cd voice-agent

# 2. Create and activate a virtual environment
python3.11 -m venv venv
source venv/bin/activate

# 3. Install Python dependencies
pip install -r requirements.txt        # see "Dependencies" section below

# 4. Enable the pgvector extension in PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE voice_agent;"
sudo -u postgres psql -d voice_agent -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 5. Configure environment variables (create a .env file in the project root)
cat > .env <<EOF
GROQ_API_KEY=<your-groq-api-key>
ELEVEN_API_KEY=<your-elevenlabs-api-key>
DEEPGRAM_API_KEY=<your-deepgram-api-key>

LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=<your-livekit-api-key>
LIVEKIT_API_SECRET=<your-livekit-api-secret>

DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=voice_agent
EOF

# 6. Run Django migrations
cd config
python manage.py migrate
cd ..

# 7. Start the LiveKit agent
python agent.py dev
```

---

## 2. Dependencies Installation

### Core Framework

```
Django==5.2.12
djangorestframework==3.16.1
djangorestframework_simplejwt==5.5.1
drf-spectacular==0.29.0
django-cors-headers==4.9.0
```

### Real-time Voice Pipeline (LiveKit)

```
livekit==1.1.2
livekit-agents==1.4.6
livekit-api==1.1.0
livekit-plugins-deepgram==1.4.5        # STT
livekit-plugins-elevenlabs==1.4.6      # TTS
livekit-plugins-openai==1.4.5          # LLM bridge (Groq-compatible)
livekit-plugins-silero==1.4.5          # VAD
```

### LLM / RAG / LangGraph

```
langchain==1.2.12
langchain-core==1.2.19
langchain-community==0.4.1
langchain-groq==1.1.2
langchain-huggingface==1.2.1
langchain-postgres==0.0.17
langchain-text-splitters==1.1.1
langgraph==1.1.2
langgraph-checkpoint==4.0.1
langgraph-prebuilt==1.0.8
openai==2.28.0
sentence-transformers==5.3.0
```

### Database / Task Queue

```
psycopg2-binary==2.9.11
psycopg-binary==3.3.3
pgvector==0.3.6
celery==5.6.2
redis==7.3.0
```

### Other

```
PyPDF2==3.0.1                          # PDF text extraction for document upload
torch==2.10.0                          # Embedding model runtime
python-dotenv                          # .env loading
bcrypt==5.0.0                          # Password hashing
```

Install everything at once:

```bash
pip install django==5.2.12 djangorestframework djangorestframework_simplejwt \
    drf-spectacular django-cors-headers \
    livekit livekit-agents livekit-api \
    livekit-plugins-deepgram livekit-plugins-elevenlabs \
    livekit-plugins-openai livekit-plugins-silero \
    langchain langchain-community langchain-groq langchain-huggingface \
    langchain-postgres langchain-text-splitters langgraph \
    openai sentence-transformers psycopg2-binary pgvector \
    celery redis PyPDF2 python-dotenv bcrypt
```

---

## 3. Overall Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                        LiveKit Server (WebRTC)                     │
│   Handles real-time audio transport between user and agent         │
└──────────────┬─────────────────────────────────┬───────────────────┘
               │  audio frames                   │  audio frames
               ▼                                 ▲
┌──────────────────────────────────────────────────────────────────┐
│                     agent.py  (LiveKit Agent)                     │
│                                                                   │
│  ┌──────────┐   ┌───────────┐   ┌───────────┐   ┌────────────┐  │
│  │  Silero   │──▶│  Deepgram │──▶│  Groq LLM │──▶│ ElevenLabs │  │
│  │   VAD     │   │   STT     │   │ llama-3.1 │   │    TTS     │  │
│  └──────────┘   └───────────┘   └─────┬─────┘   └────────────┘  │
│                                       │                           │
│                          function_tool calls                      │
│                    ┌──────────┼──────────┐                        │
│                    ▼          ▼          ▼                         │
│             ┌──────────┐ ┌────────┐ ┌────────┐                    │
│             │   RAG    │ │ Ticket │ │ Email  │   LangGraph        │
│             │ Workflow │ │Workflow│ │Workflow│   Workflows         │
│             └────┬─────┘ └───┬────┘ └───┬────┘                    │
│                  │           │          │                          │
└──────────────────┼───────────┼──────────┼─────────────────────────┘
                   │           │          │
                   ▼           ▼          ▼
┌──────────────────────────────────────────────────────────────────┐
│              PostgreSQL  (Django ORM + pgvector)                   │
│                                                                   │
│  ┌─────────────────┐  ┌──────────┐  ┌─────────────┐              │
│  │ knowledge_base   │  │ Ticket   │  │ DraftEmail  │              │
│  │ (pgvector store) │  │          │  │             │              │
│  └─────────────────┘  └──────────┘  └─────────────┘              │
└──────────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component             | Role                                                                            |
|-----------------------|---------------------------------------------------------------------------------|
| **LiveKit Server**    | WebRTC media routing — low-latency, bidirectional audio between user and agent.  |
| **Silero VAD**        | Voice Activity Detection — determines when the user starts/stops speaking.      |
| **Deepgram STT**      | Speech-to-Text — real-time streaming transcription of user audio.               |
| **Groq LLM**          | Language model inference (llama-3.1-8b-instant) via OpenAI-compatible API.      |
| **ElevenLabs TTS**    | Text-to-Speech — converts agent text responses into natural-sounding audio.     |
| **LangGraph Workflows**| Stateful, graph-based orchestration for RAG, ticket creation, and email drafts.|
| **Django + DRF**      | REST API layer — document upload, ticket/email CRUD, user auth, Swagger docs.   |
| **PostgreSQL + pgvector** | Relational storage for Django models **and** vector similarity search for RAG.|
| **Redis + Celery**    | Background task execution and channel layers (available but not heavily used).   |

### Data Flow (voice query example)

1. **User speaks** → LiveKit captures audio frames.
2. **Silero VAD** detects speech boundaries → frames are forwarded.
3. **Deepgram STT** transcribes audio → text query.
4. **Groq LLM** receives text + system instructions → decides to call a `function_tool`.
5. **LangGraph workflow** executes (e.g. RAG retrieval from pgvector) in a background thread via `asyncio.to_thread`.
6. Tool result returns to the LLM → LLM generates a spoken summary.
7. **ElevenLabs TTS** converts summary → audio frames.
8. **LiveKit** streams audio back to the user's browser/device.

---

## 4. Key Design Decisions

### 4.1 Groq for LLM Inference

Groq's custom LPU hardware delivers sub-200 ms token-generation latency for llama-3.1-8b-instant, which is critical for a real-time voice loop where every millisecond counts. The trade-off is Groq's free-tier rate limits (6 000 TPM), mitigated by trimming RAG context to 400 chars and limiting to 1 tool call per turn (`max_tool_steps=1`).

### 4.2 LiveKit Agents Framework

LiveKit was chosen over a custom WebSocket solution because it provides:
- Production-grade WebRTC transport with built-in echo cancellation and jitter buffering.
- A pluggable `Agent` / `AgentSession` abstraction with first-class `function_tool` support.
- Automatic VAD → STT → LLM → TTS pipeline wiring.

### 4.3 LangGraph for Workflow Orchestration

Each backend action (RAG, ticket, email) is modeled as a **compiled LangGraph `StateGraph`** rather than a plain function. This was a deliberate decision to:
- Make workflows **inspectable and extensible** — adding nodes (e.g. approval steps, side-effects) requires only graph edges, not code rewrites.
- Provide a clear **typed state contract** (`TypedDict`) per workflow.
- Enable future migration to **conditional routing, cycles, and human-in-the-loop** without changing the calling code in `agent.py`.

### 4.4 Singleton Workflow & Service Instances

Both `HybridRAGService` and every `*Workflow` class are instantiated once per process and cached in module-level globals. This avoids reloading the `all-MiniLM-L6-v2` sentence-transformer model (~80 MB) on every request.

### 4.5 pgvector Inside PostgreSQL

Using `langchain-postgres` / `PGVector` keeps the vector store co-located with relational data in a single PostgreSQL instance. This simplifies deployment (no separate Pinecone / Weaviate cluster) while still supporting cosine-distance similarity search with a configurable relevance threshold (0.65).

### 4.6 Sync Workflows Wrapped with `asyncio.to_thread`

Django's ORM is synchronous. LangGraph's `invoke()` is also synchronous. Rather than introducing async ORM wrappers, all workflow calls are dispatched via `asyncio.to_thread()`, keeping the LiveKit event loop non-blocking while reusing Django's battle-tested sync ORM.

---

## 5. Latency Bottlenecks

| Bottleneck                       | Estimated Impact | Where It Occurs                              |
|----------------------------------|------------------|----------------------------------------------|
| **Embedding model cold start**   | 5–10 s (first call) | `HybridRAGService.__init__` loads `all-MiniLM-L6-v2` into memory. |
| **STT transcription wait**       | 300–800 ms       | Deepgram/Groq Whisper must accumulate enough audio before returning a final transcript. |
| **LLM round-trip (Groq)**        | 150–400 ms       | Network hop to Groq API + token generation for tool-call decision. |
| **RAG vector search**            | 50–200 ms        | pgvector similarity search on `knowledge_base` collection; grows with corpus size. |
| **TTS synthesis**                | 200–500 ms       | ElevenLabs HTTP call to generate first audio chunk (turbo_v2 model). |
| **LLM second round-trip**        | 150–400 ms       | After tool result, the LLM must run again to produce the spoken response. |
| **`asyncio.to_thread` overhead** | 1–5 ms           | Thread pool dispatch; negligible but present. |
| **Django ORM DB writes**         | 10–50 ms         | `Ticket.objects.create()` / `DraftEmail.objects.create()` — round-trip to Postgres. |

**Total voice-to-voice latency (warm, RAG path): ~1–2.5 seconds.**

The dominant contributors are: STT accumulation + two LLM round-trips + TTS first-chunk latency.

---

## 6. How to Improve Latency

### 6.1 Streaming at Every Stage

- **Streaming STT** — Deepgram already supports interim results; feed partial transcripts to the LLM sooner (speculative processing).
- **Streaming LLM** — Use Groq's streaming endpoint so TTS can begin synthesizing the first sentence before the full response is generated.
- **Streaming TTS** — ElevenLabs supports chunked audio output; start playing as soon as the first chunk arrives instead of waiting for the full synthesis.

### 6.2 Reduce LLM Round-Trips

Currently the tool-call flow requires **two** LLM calls (decide tool → generate spoken response). This can be reduced by:
- Combining the tool result directly into a template-based spoken response, skipping the second LLM call for deterministic actions (e.g. "Ticket #abc123 created").
- Using **parallel tool calling** when multiple tools are needed.

### 6.3 Pre-warm Everything

The system already pre-warms workflows via `asyncio.create_task(asyncio.to_thread(_init_workflows))`. Further improvements:
- **Persistent workers** — keep the LiveKit agent process long-lived so the embedding model stays loaded.
- **Connection pooling** — use `psycopg_pool` or PgBouncer to avoid per-request TCP handshakes to Postgres.

### 6.4 Local / Edge Inference

- Replace Groq API calls with a **locally-hosted LLM** (e.g. llama.cpp, vLLM, or Ollama) to eliminate network latency entirely.
- Run a **local Whisper model** for STT to avoid the Deepgram network hop.
- Use a **local TTS engine** (e.g. Coqui XTTS, Piper) for zero-network speech synthesis.

### 6.5 Smarter RAG

- **Pre-compute and cache** frequent queries with a simple LRU or Redis cache in front of pgvector.
- Use **HNSW indexes** (`CREATE INDEX ... USING hnsw`) on the pgvector collection for sub-linear search time on large corpora.
- Reduce `chunk_size` or use **hypothetical document embeddings (HyDE)** to improve retrieval precision and reduce the amount of context sent to the LLM.

### 6.6 Speculative Execution

Begin TTS on the LLM's first partial sentence while the rest is still being generated. If the generation changes course, discard buffered audio. This can cut perceived latency by 200–400 ms.

---

## 7. Supporting Tool Calling

### Current Implementation

The system already supports tool calling via LiveKit Agents' `@function_tool()` decorator:

```python
class VoiceAssistant(Agent):
    @function_tool()
    async def query_knowledge_base(self, context: RunContext, user_inquiry: str) -> str:
        ...

    @function_tool()
    async def create_ticket(self, context: RunContext, title: str, description: str, priority: str = "medium") -> str:
        ...

    @function_tool()
    async def draft_email(self, context: RunContext, subject: str, body: str, recipient: str = "") -> str:
        ...
```

The LLM (Groq, llama-3.1-8b-instant) natively supports OpenAI-compatible function calling. When the model decides a tool is needed, it emits a structured `function_call` JSON payload. LiveKit Agents intercepts this, invokes the matching Python method, and feeds the return value back into the LLM for response generation.

### How to Extend

To add a new tool:

1. **Define the tool** — add a new `@function_tool()` method to `VoiceAssistant`:

```python
@function_tool()
async def check_order_status(self, context: RunContext, order_id: str) -> str:
    """Look up the status of an order by its ID."""
    result = await asyncio.to_thread(_sync_check_order, order_id)
    return result
```

2. **Implement the backend** — create a new LangGraph workflow (or a plain function) in `graph_service.py`.

3. **Update system instructions** — add a routing hint so the LLM knows when to use the new tool:

```
"Order status questions → use check_order_status."
```

No changes to the pipeline wiring, LiveKit config, or STT/TTS setup are needed — tools are auto-discovered from the `Agent` class.

---

## 8. Supporting Graph-Based Conversation Workflows

### Current Graph Workflows

The system uses **LangGraph `StateGraph`** for three workflows today, each with a simple linear topology:

| Workflow        | Nodes                          | State Type    |
|-----------------|--------------------------------|---------------|
| RAG             | `retrieve`                     | `RAGState`    |
| Ticket          | `validate` → `create_ticket`   | `TicketState` |
| Email           | `validate` → `save_draft`      | `EmailState`  |

Each workflow is compiled once, cached as a singleton, and invoked synchronously via `graph.invoke()`.

### How to Add Complex Conversation Graphs

LangGraph natively supports **conditional edges, cycles, and branching** — enabling arbitrarily complex conversation flows:

#### Example: Multi-step Ticket Workflow with Approval

```python
class TicketStateV2(TypedDict):
    title: str
    description: str
    priority: str
    needs_approval: bool
    approved: bool
    ticket_id: str
    result: str

def route_after_validate(state: TicketStateV2):
    if state["needs_approval"]:
        return "request_approval"
    return "create_ticket"

wf = StateGraph(TicketStateV2)
wf.add_node("validate", validate_node)
wf.add_node("request_approval", approval_node)
wf.add_node("create_ticket", create_node)
wf.add_node("notify", notify_node)

wf.add_edge(START, "validate")
wf.add_conditional_edges("validate", route_after_validate)
wf.add_edge("request_approval", "create_ticket")
wf.add_edge("create_ticket", "notify")
wf.add_edge("notify", END)
```

#### Example: Cyclic Clarification Loop

```python
def route_after_classify(state):
    if state["intent"] == "unclear":
        return "ask_clarification"    # loop back
    return "execute_action"

wf.add_conditional_edges("classify_intent", route_after_classify)
wf.add_edge("ask_clarification", "classify_intent")  # cycle
```

### Integration Pattern

Graph-based workflows integrate with the voice agent at a single touchpoint — the `@function_tool()` methods in `agent.py`. Each tool delegates to a LangGraph workflow via `asyncio.to_thread(workflow.run, ...)`. The graphs themselves can be as simple or complex as needed without touching the voice pipeline.

To add **cross-workflow orchestration** (e.g. "create a ticket, then email the assignee"):

1. Build a **meta-workflow** whose nodes are calls to the sub-workflows.
2. Expose it as a single `@function_tool()` so the LLM triggers the entire multi-step flow with one tool call.

### Future Enhancements

- **LangGraph checkpointing** — persist workflow state across turns using `langgraph-checkpoint`, enabling conversations that span multiple voice interactions.
- **Human-in-the-loop nodes** — pause a graph at an approval node, notify the user via the voice channel, resume on confirmation.
- **Sub-graph composition** — nest workflows inside each other using LangGraph's `CompiledGraph` as a node, enabling reusable building blocks.




### Steps to run the project (after installing dependencies)

Terminal 1 — Django Server
cd /home/zt103/Documents/django-llm-2/voice-agent/config 
&& source ../venv/bin/activate 
&& python manage.py runserver

Terminal 2 — Redis (check it's running)
sudo service redis-server start && sudo service redis-server status

Terminal 3 — Celery Worker
cd /home/zt103/Documents/django-llm-2/voice-agent/config && source ../venv/bin/activate && celery -A config worker --loglevel=info

Terminal 4 — LiveKit Voice Agent
cd /home/zt103/Documents/django-llm-2/voice-agent && source venv/bin/activate && python agent.py start

if server memory overloaded
fuser -k 8081/tcp 2>/dev/null; python agent.py start

---
