import asyncio, time
from . import networking, wakeword, recorder, stt_openai, chat_openai, tts_openai, config

async def main():
    ww  = wakeword.WakeWord(config.PICO_ACCESS_KEY,
                            config.PPN_PATH,
                            config.PV_MODEL)
    rec = recorder.Recorder()
    net = networking.PCMStreamServer("0.0.0.0", 50007)

    # --- 録音終了判定用タイムスタンプ ------------------------------
    import time
    last_trigger = 0.0                       # ウェイクワードを検知した時刻

    def rec_complete_condition() -> bool:
        nonlocal last_trigger
        return (time.time() - last_trigger > 1.0) and rec.size_bytes() > 16000*2
    # ---------------------------------------------------------------

    asyncio.create_task(net.start())
    print("[WAIT] client connect...")

    async for mtype, data in net.events():
        if mtype == networking.MSG_MIC:
            triggered = ww.process(data)
            rec.feed(data, triggered)

            if triggered:
                print("Wake word!")
                last_trigger = time.time()      # ★ ここで時刻を更新
                full_start = time.perf_counter()

        if rec_complete_condition():
            # STT
            stt_start = time.perf_counter()
            wav = rec.stop_and_dump()
            prompt = await stt_openai.speech_to_text(wav)
            stt_end = time.perf_counter()
            print("[STT]", prompt)

            # Chat
            chat_start = time.perf_counter()
            answer = await chat_openai.chat(prompt)
            chat_end = time.perf_counter()

            # TTS
            tts_start = time.perf_counter()
            pcm24k = await tts_openai.text_to_speech(answer)
            tts_end = time.perf_counter()

            # 結果の送信
            print("broadcast", len(pcm24k), "bytes")
            await net.broadcast_tts(pcm24k)
            full_end = time.perf_counter()

            # --- ログ出力 ---
            print(f"[TIME] STT    : {stt_end - stt_start:.2f} s")
            print(f"[TIME] Chat   : {chat_end - chat_start:.2f} s")
            print(f"[TIME] TTS    : {tts_end - tts_start:.2f} s")
            print(f"[TIME] Total  : {full_end - full_start:.2f} s")
            print(f"[TIME] STT→End: {full_end - stt_end:.2f} s")
