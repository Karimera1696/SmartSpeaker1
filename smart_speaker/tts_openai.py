from openai import AsyncOpenAI
_openai = AsyncOpenAI()

async def text_to_speech(text: str) -> bytes:
    # Streaming response を手動で読み取る
    async with _openai.audio.speech.with_streaming_response.create(
        model="gpt-4o-mini-tts",
        voice="coral",
        input=text,
        response_format="pcm") as resp:
        return await resp.read()        # bytes をそのまま返す
