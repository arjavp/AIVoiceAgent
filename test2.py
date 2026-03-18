import asyncio
from livekit.plugins import deepgram

def main():
    print("Instantiating deepgram STT...")
    stt = deepgram.STT()
    print("STT instantiated.")

    print("Instantiating deepgram TTS...")
    tts = deepgram.TTS()
    print("TTS instantiated.")

if __name__ == '__main__':
    main()
