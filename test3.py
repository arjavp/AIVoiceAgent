from dotenv import load_dotenv
load_dotenv()

import asyncio
from livekit.plugins import deepgram, openai, silero
from livekit.agents import AgentSession
import os
import faulthandler
faulthandler.enable()

async def main():
    print("creating session...", flush=True)
    try:
        session = AgentSession(
            stt=deepgram.STT(),
            llm=openai.LLM(
                base_url="https://api.groq.com/openai/v1",
                api_key="123",
                model="llama-3.1-8b-instant",
            ),
            tts=deepgram.TTS(),
            vad=silero.VAD.load(),
        )
        print("session created!", flush=True)
        # Attempt to trigger what happens when a track starts
        import sys
        print("done", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(main())
