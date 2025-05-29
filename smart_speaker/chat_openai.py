from openai import AsyncOpenAI
_openai = AsyncOpenAI()

async def chat(prompt: str) -> str:
    stream = await _openai.chat.completions.create(
        model="gpt-4o",
        messages=[{"role":"user","content":prompt}],
        stream=True)
    answer = ""
    async for chunk in stream:
        delta = chunk.choices[0].delta.content
        if delta: answer += delta
    return answer
