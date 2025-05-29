import asyncio, io, os
from openai import AsyncOpenAI

_openai = AsyncOpenAI()

async def speech_to_text(wav_bytes: bytes) -> str:
    file_like = io.BytesIO(wav_bytes)
    file_like.name = "audio.wav"  # これが超重要！！
    stream = await _openai.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=file_like,
        response_format="text",
        stream=True)       # ストリーミングで早めに返す
    text = ""
    async for ev in stream:
        if ev.type == "transcript.text.delta":
            text += ev.delta
    return text            # :contentReference[oaicite:0]{index=0}
