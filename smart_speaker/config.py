"""
smart_speaker/config.py
各モジュールで共通して参照する定数・パス・秘密鍵を置くファイル
"""

from pathlib import Path
from dotenv import load_dotenv
import os
load_dotenv()

# ──────────────────────────────────────────────────────────────
# 1. プロジェクト共通パス
# ──────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).resolve().parent.parent          # SmartSpeaker1/
MODEL_DIR  = BASE_DIR / "models" / "porcupine"
WAKEWORD_DIR = MODEL_DIR / "wakewords"                       # *.ppn
ACOUSTIC_DIR = MODEL_DIR / "acoustic"                        # *.pv

PPN_PATH  = str(WAKEWORD_DIR / "kiritan_ja_raspberry-pi_v3_0_0.ppn")
PV_MODEL  = str(ACOUSTIC_DIR / "porcupine_params_ja.pv")
# ──────────────────────────────────────────────────────────────
# 2. Picovoice（Porcupine）設定
# ──────────────────────────────────────────────────────────────
PICO_ACCESS_KEY = os.getenv("PICO_ACCESS_KEY")

# ──────────────────────────────────────────────────────────────
# 3. OpenAI 4-o 関連
# ──────────────────────────────────────────────────────────────
OPENAI_API_KEY  = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
TTS_VOICE       = "coral"                                    # gpt-4o-mini-tts の音声 ID

# ──────────────────────────────────────────────────────────────
# 4. サーバーネットワーク設定
# ──────────────────────────────────────────────────────────────
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 50007

# ──────────────────────────────────────────────────────────────
# 5. 音声処理（共通定数）
# ──────────────────────────────────────────────────────────────
PCM_RATE_IN      = 16_000        # クライアント→サーバ 転送サンプルレート
PCM_RATE_TTS     = 24_000        # サーバ→クライアント TTS サンプルレート
PCM_FRAME        = 512           # Porcupine に渡すフレーム長（サンプル）
BYTES_PER_SAMPLE = 2             # int16 = 2 byte
