import os
import sys
import asyncio

dummy_lib_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'dummy_lib')
current_ld = os.environ.get('LD_LIBRARY_PATH', '')

if dummy_lib_dir not in current_ld:
    print(f"Injecting dummy libva-drm.so.2 into LD_LIBRARY_PATH...")
    os.environ['LD_LIBRARY_PATH'] = dummy_lib_dir + (os.pathsep + current_ld if current_ld else '')
    os.execv(sys.executable, [sys.executable] + sys.argv)

from dotenv import load_dotenv

from livekit.agents import (
    Agent,
    AgentSession,
    AutoSubscribe,
    JobContext,
    JobExecutorType,
    WorkerOptions,
    cli,
    function_tool,
    RunContext,
)
from livekit.plugins import deepgram, openai, silero, elevenlabs

load_dotenv()

# Set up Django path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'config'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# ── Ensure Django is set up once ──
_django_ready = False


def ensure_django():
    global _django_ready
    if not _django_ready:
        import django
        django.setup()
        _django_ready = True


# ── Cached LangGraph workflows (singletons) ──
_workflows_ready = False


def _init_workflows():
    """Initialise all three LangGraph workflows once."""
    global _workflows_ready
    if not _workflows_ready:
        ensure_django()
        from apps.ai.services.graph_service import (
            get_rag_workflow,
            get_ticket_workflow,
            get_email_workflow,
        )
        # Touch each singleton so they are warm
        get_rag_workflow()
        get_ticket_workflow()
        get_email_workflow()
        _workflows_ready = True
        print("✅ All LangGraph workflows initialized")


def _sync_rag_retrieve(query: str) -> str:
    """Run RAG LangGraph workflow (sync) — call via asyncio.to_thread()."""
    _init_workflows()
    from apps.ai.services.graph_service import get_rag_workflow
    return get_rag_workflow().run(query)


def _sync_create_ticket(title: str, description: str, priority: str) -> str:
    """Run Ticket LangGraph workflow (sync) — call via asyncio.to_thread()."""
    _init_workflows()
    from apps.ai.services.graph_service import get_ticket_workflow
    return get_ticket_workflow().run(title, description, priority)


def _sync_draft_email(subject: str, body: str, recipient: str) -> str:
    """Run Email LangGraph workflow (sync) — call via asyncio.to_thread()."""
    _init_workflows()
    from apps.ai.services.graph_service import get_email_workflow
    return get_email_workflow().run(subject, body, recipient)


class VoiceAssistant(Agent):
    """Voice AI Agent with RAG knowledge base, ticket creation, draft email, and general Q&A."""

    def __init__(self) -> None:
        super().__init__(
            instructions=(
                "You are a helpful voice assistant. Keep answers brief (2-3 sentences). "
                "Topic questions → use query_knowledge_base, then summarize the result to the user. "
                "Issue/bug reports → use create_ticket, then confirm to the user. "
                "Email requests → use draft_email, then confirm to the user. "
                "Greetings → answer directly. "
                "After any tool returns, speak the result to the user immediately. "
                "Do NOT chain tools. One tool per question. Never repeat tool calls."
            ),
        )

    @function_tool()
    async def query_knowledge_base(self, context: RunContext, user_inquiry: str) -> str:
        """Search documents for a topic. Use for factual questions only."""
        print(f"🔧 Tool Called → query_knowledge_base: {user_inquiry}")
        try:
            raw_context = await asyncio.to_thread(_sync_rag_retrieve, user_inquiry)

            if not raw_context or raw_context == "No relevant documents found.":
                print("📭 No relevant docs found")
                return "No docs found. Answer from general knowledge."

            # Trim to keep tokens low for Groq free tier (6000 TPM)
            if len(raw_context) > 400:
                raw_context = raw_context[:400].rsplit(' ', 1)[0]

            print(f"✅ RAG context ({len(raw_context)} chars) returned to agent")
            return f"Found: {raw_context}\nSummarize this to the user."

        except Exception as e:
            print(f"❌ RAG Error: {e}")
            import traceback; traceback.print_exc()
            return "Knowledge base search failed. Try again."

    @function_tool()
    async def create_ticket(
        self,
        context: RunContext,
        title: str,
        description: str,
        priority: str = "medium",
    ) -> str:
        """Create a support ticket. Priority: low/medium/high/urgent."""
        print(f"🎫 Tool Called → create_ticket: {title} | priority={priority}")
        try:
            result = await asyncio.to_thread(_sync_create_ticket, title, description, priority)
            return result
        except Exception as e:
            print(f"❌ Ticket creation error: {e}")
            import traceback; traceback.print_exc()
            return f"Error creating ticket '{title}'. Try again."

    @function_tool()
    async def draft_email(
        self,
        context: RunContext,
        subject: str,
        body: str,
        recipient: str = "",
    ) -> str:
        """Draft and save an email."""
        print(f"📧 Tool Called → draft_email: subject='{subject}', to='{recipient}'")
        try:
            result = await asyncio.to_thread(_sync_draft_email, subject, body, recipient)
            return result
        except Exception as e:
            print(f"❌ Draft email error: {e}")
            import traceback; traceback.print_exc()
            return f"Error saving email '{subject}'. Try again."


async def entrypoint(ctx: JobContext):
    # ── Pre-warm all LangGraph workflows in background thread ──
    # (eliminates 5-10s first-call lag from loading embeddings model)
    asyncio.create_task(asyncio.to_thread(_init_workflows))

    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)

    groq_api_key = os.environ.get("GROQ_API_KEY")
    eleven_api_key = os.environ.get("ELEVEN_API_KEY")
    deepgram_api_key = os.environ.get("DEEPGRAM_API_KEY")

    # ── STT: Prefer Deepgram (real-time optimized), fallback to Groq Whisper ──
    if deepgram_api_key:
        stt = deepgram.STT(
            api_key=deepgram_api_key,
            language="en",
        )
        print("🎙️ STT: Deepgram (real-time optimized)")
    else:
        stt = openai.STT.with_groq(
            language="en",
            api_key=groq_api_key,
        )
        print("🎙️ STT: Groq Whisper")

    # ── LLM: Groq (fast inference) ──
    llm = openai.LLM(
        base_url="https://api.groq.com/openai/v1",
        api_key=groq_api_key,
        model="llama-3.1-8b-instant",
    )

    # ── TTS: ElevenLabs ──
    if eleven_api_key:
        tts = elevenlabs.TTS(
            voice_id="EXAVITQu4vr4xnSDxMaL",
            api_key=eleven_api_key,
            model="eleven_turbo_v2",
        )
        print("🔊 TTS: ElevenLabs (turbo_v2)")
    else:
        print("⚠️ No ELEVEN_API_KEY found, TTS may not work")
        tts = elevenlabs.TTS(voice_id="EXAVITQu4vr4xnSDxMaL")

    # ── VAD: Silero ──
    vad = silero.VAD.load()

    session = AgentSession(
        stt=stt,
        llm=llm,
        tts=tts,
        vad=vad,
        max_tool_steps=1,  # limit to 1 tool call per turn to save Groq TPM
    )

    await session.start(
        room=ctx.room,
        agent=VoiceAssistant(),
    )

    await session.say("Hello! How can I help you?")


if __name__ == "__main__":
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            job_executor_type=JobExecutorType.THREAD,
            load_fnc=lambda: 0.0,
            load_threshold=0.95,
            initialize_process_timeout=60.0,
        )
    )
