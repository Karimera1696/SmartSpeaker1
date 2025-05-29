import asyncio
import time
import queue
import numpy as np
import sounddevice as sd
import scipy.signal
import os

import wakeword, recorder, stt_openai, chat_openai, tts_openai, config

def set_volume(percent):
    os.system(f"amixer sset 'Master' {percent}%")

# ==== 設定 ====
# しきい値を仮に4000に設定
set_volume(30)  # ここで音量を50%に設定
NOISE_MARGIN = 2000
SILENCE_DURATION = 1.5  # 話し始めた後の無音継続時間
MAX_RECORD_DURATION = 10.0  # ウェイクワード検知後の最大録音時間
NOISE_MEASURE_INTERVAL = 10.0  # 10秒ごとに測定
NOISE_MEASURE_DURATION = 0.3  # 測定は0.3秒間
MIN_SPEECH_DURATION = 0.04    # 発話開始判定に必要な連続入力時間(秒)
input_sample_rate = 44100
input_device = 1  # 適宜変更
output_device = None  # Noneならデフォルトスピーカー
q = queue.Queue()

def audio_callback(indata, frames, time, status):
    if status:
        print(f"⚠️ {status}")
    q.put(indata.copy())

def play_pcm(pcm_bytes, sample_rate=24000):
    audio = np.frombuffer(pcm_bytes, dtype=np.int16)
    sd.play(audio, samplerate=sample_rate, device=output_device)
    sd.wait()

def measure_noise_level(buffer, chunk_size, ww):
    """0.5秒間ノイズレベルを測定し、その平均を返す"""
    levels = []
    start = time.time()
    while time.time() - start < NOISE_MEASURE_DURATION:
        if not q.empty():
            data = q.get().flatten()
            buffer = np.concatenate([buffer, data])
            while len(buffer) >= chunk_size:
                chunk = buffer[:chunk_size]
                buffer = buffer[chunk_size:]
                resampled = scipy.signal.resample(chunk, ww.engine.frame_length)
                resampled = np.round(resampled).astype(np.int16)
                level = np.max(np.abs(resampled))
                levels.append(level)
    if levels:
        avg = int(np.mean(levels))
    else:
        avg = 0
    return avg, buffer

def main():
    ww = wakeword.WakeWord(config.PICO_ACCESS_KEY, config.PPN_PATH, config.PV_MODEL)
    rec = recorder.Recorder()

    print("ローカルモード: マイク入力でウェイクワード検出・会話します。Ctrl+Cで終了。")

    triggered = False
    silence_start = None
    noise_level = 0
    SILENCE_THRESHOLD = 6000

    buffer = np.zeros(0, dtype='int16')
    chunk_size = int(input_sample_rate / ww.engine.sample_rate * ww.engine.frame_length)
    chunk_duration = chunk_size / input_sample_rate  # 1チャンクあたりの時間(秒)

    with sd.InputStream(
        device=input_device,
        samplerate=input_sample_rate,
        channels=1,
        dtype='int16',
        blocksize=1024,
        callback=audio_callback
    ):
        print("ノイズレベル測定中...静かにしてください")
        noise_level, buffer = measure_noise_level(buffer, chunk_size, ww)
        SILENCE_THRESHOLD = noise_level + NOISE_MARGIN
        print(f"ノイズレベル: {noise_level}, しきい値: {SILENCE_THRESHOLD}")
        last_noise_check = time.time()
        speech_buffer_accum = 0.0  # 発話開始検出用バッファ
        speech_started = False

        while True:
            if not triggered and time.time() - last_noise_check > 5.0:
                print("ノイズレベル再測定中...静かにしてください")
                noise_level, buffer = measure_noise_level(buffer, chunk_size, ww)
                SILENCE_THRESHOLD = noise_level + NOISE_MARGIN
                print(f"ノイズレベル: {noise_level}, しきい値: {SILENCE_THRESHOLD}")
                last_noise_check = time.time()

            while q.qsize() > 5:
                try:
                    q.get_nowait()
                except queue.Empty:
                    break

            if not q.empty():
                data = q.get().flatten()
                buffer = np.concatenate([buffer, data])

            while len(buffer) >= chunk_size:
                chunk = buffer[:chunk_size]
                buffer = buffer[chunk_size:]

                resampled = scipy.signal.resample(chunk, ww.engine.frame_length)
                resampled = np.round(resampled).astype(np.int16)
                level = np.max(np.abs(resampled))

                # --- ウェイクワード検出 ---
                if not triggered and ww.engine.process(resampled) >= 0:
                    print("✅ ウェイクワードが検出されました！録音開始")
                    triggered = True
                    rec = recorder.Recorder()
                    silence_start = None
                    record_start = time.time()
                    speech_buffer_accum = 0.0
                    speech_started = False

                # --- 録音中 ---
                if triggered:
                    rec.feed(resampled.tobytes(), triggered=True)
                    print(f"音量: {level}, バッファサイズ: {rec.size_bytes()}")  # デバッグ用

                    # 発話開始検知 (一定時間以上の連続発話が必要)
                    if not speech_started:
                        if level >= SILENCE_THRESHOLD:
                            speech_buffer_accum += chunk_duration
                        else:
                            speech_buffer_accum = 0.0
                        print(f"発話バッファ: {speech_buffer_accum:.2f}s")  # DEBUG
                        if speech_buffer_accum >= MIN_SPEECH_DURATION:
                            speech_started = True
                            print(f"🗣️ 発話開始検知: {speech_buffer_accum:.2f}s")
                            silence_start = None
                        # 無音終了判定は発話開始後に適用
                        continue

                    # 無音判定
                    if level < SILENCE_THRESHOLD:
                        if silence_start is None:
                            silence_start = time.time()
                        elif time.time() - silence_start > SILENCE_DURATION:
                            print("録音終了（無音）、処理開始")
                            triggered = False
                            wav = rec.stop_and_dump()
                            print("STT...")
                            prompt = asyncio.run(stt_openai.speech_to_text(wav))
                            print("[STT]", prompt)
                            print("Chat...")
                            answer = asyncio.run(chat_openai.chat(prompt))
                            print("[Chat]", answer)
                            print("TTS...")
                            pcm24k = asyncio.run(tts_openai.text_to_speech(answer))
                            print("再生します...")
                            play_pcm(pcm24k)
                            print("会話終了。ウェイクワード待機中。")
                            silence_start = None
                            continue
                    else:
                        silence_start = None  # 音があればリセット

                    # 最大録音時間
                    if time.time() - record_start > MAX_RECORD_DURATION:
                        print("録音終了（タイムアウト）、処理開始")
                        triggered = False
                        wav = rec.stop_and_dump()
                        print("STT...")
                        prompt = asyncio.run(stt_openai.speech_to_text(wav))
                        print("[STT]", prompt)
                        print("Chat...")
                        answer = asyncio.run(chat_openai.chat(prompt))
                        print("[Chat]", answer)
                        print("TTS...")
                        pcm24k = asyncio.run(tts_openai.text_to_speech(answer))
                        print("再生します...")
                        play_pcm(pcm24k)
                        print("会話終了。ウェイクワード待機中。")
                        silence_start = None
                        continue

            time.sleep(0.001)

if __name__ == "__main__":
    main()