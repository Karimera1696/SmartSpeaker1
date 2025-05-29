import pvporcupine, array

class WakeWord:
    def __init__(self, access_key, ppn_path, model_path):
        self.engine = pvporcupine.create(access_key=access_key,
                                         keyword_paths=[ppn_path],
                                         model_path=model_path)

    def process(self, pcm_bytes: bytes) -> bool:
        pcm = array.array('h', pcm_bytes)
        return self.engine.process(pcm) >= 0
