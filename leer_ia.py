import numpy as np
import soundfile as sf
from kokoro import KPipeline

texto = open("que_es_la_ia.txt", encoding="utf-8").read()
pipeline = KPipeline(lang_code="e")
audio = [chunk for _, _, chunk in pipeline(texto, voice="ef_dora")]
sf.write("que_es_la_ia.wav", np.concatenate(audio), 24000)
print("audio generado")
