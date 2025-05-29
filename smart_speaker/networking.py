import asyncio, struct

MSG_MIC = 0x01
MSG_TTS = 0x02

class PCMStreamServer:
    def __init__(self, host: str, port: int):
        self._host, self._port = host, port
        self._queue = asyncio.Queue()               # ★ イベントキュー
        self._clients = set()

    async def start(self):
        server = await asyncio.start_server(self._handle, self._host, self._port)
        async with server:
            await server.serve_forever()

    async def _handle(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        self._clients.add(writer)
        try:
            while True:
                header = await reader.readexactly(5)           # 1 + 4
                mtype  = header[0]
                length = struct.unpack("<I", header[1:])[0]
                data   = await reader.readexactly(length)
                await self._queue.put((mtype, data))           # ★ キューに積む
        except (asyncio.IncompleteReadError, ConnectionResetError):
            pass
        finally:
            self._clients.discard(writer)

    # ★ 非同期イテレータを返すメソッド
    async def events(self):
        while True:
            yield await self._queue.get()

    async def broadcast_tts(self, pcm24k: bytes):
        pkt = bytes([MSG_TTS]) + struct.pack("<I", len(pcm24k)) + pcm24k
        for w in self._clients.copy():
            try:
                w.write(pkt); await w.drain()
            except ConnectionResetError:
                self._clients.discard(w)
