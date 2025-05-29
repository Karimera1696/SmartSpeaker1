import socket, struct, pvporcupine, array, pkg_resources, os

ACCESS_KEY = "J8dboWcogE2JThalqTfm06ENYZ2wAdYQQlBDdaZMaHsL7NDKaqflWw=="
KEYWORD_PATH = "models/porcupine/wakewords/kiritan_ja_raspberry-pi_v3_0_0.ppn"

MODEL_PATH = 'models/porcupine/acoustic/porcupine_params_ja.pv'

porcupine = pvporcupine.create(
    access_key   = ACCESS_KEY,
    keyword_paths=[KEYWORD_PATH],
    model_path   = MODEL_PATH,
    sensitivities=[0.5],
)

server = socket.socket()
server.bind(("", 50007))
server.listen(1)
conn, _ = server.accept()

payload_size = struct.calcsize("I")  # 4byte
buf = b""

try:
    while True:
        # --- 長さ付きフレームを受信 ---
        while len(buf) < payload_size:
            buf += conn.recv(4096)
        (frame_len,) = struct.unpack("I", buf[:payload_size])
        buf = buf[payload_size:]

        while len(buf) < frame_len:
            buf += conn.recv(4096)
        frame = buf[:frame_len]
        buf = buf[frame_len:]

        # --- Porcupine へ ---
        pcm = array.array('h', frame)  # int16 little-endian
        if porcupine.process(pcm) >= 0:
            print("✅ きりたん検出!")
finally:
    conn.close()
    porcupine.delete()
