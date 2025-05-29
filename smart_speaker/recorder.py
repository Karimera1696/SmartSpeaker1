import io
import wave

class Recorder:
    def __init__(self):
        self._buf = io.BytesIO()
        self._recording = False

    def feed(self, pcm_frame: bytes, triggered=False):
        if triggered:
            self._recording = True
        if self._recording:
            self._buf.write(pcm_frame)

    def stop_and_dump(self) -> bytes:
        """録音終了。バッファを WAV (16bit/mono/16kHz) 形式に変換して返す。"""
        self._recording = False
        pcm_data = self._buf.getvalue()
        self._buf = io.BytesIO()

        # PCM → WAV 変換
        wav_io = io.BytesIO()
        with wave.open(wav_io, 'wb') as wf:
            wf.setnchannels(1)        # mono
            wf.setsampwidth(2)        # 16bit
            wf.setframerate(16000)    # 16kHz
            wf.writeframes(pcm_data)
        return wav_io.getvalue()

    def size_bytes(self) -> int:
        """現在の録音バッファのサイズ（PCMバイト数）"""
        return self._buf.tell()
