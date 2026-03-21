from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uuid, os, scipy
from transformers import AutoProcessor, MusicgenForConditionalGeneration

app = FastAPI()

print("Loading MusicGen...")
processor = AutoProcessor.from_pretrained("facebook/musicgen-small")
model = MusicgenForConditionalGeneration.from_pretrained("facebook/musicgen-small")
print("MusicGen ready!")

os.makedirs("/tmp/audio", exist_ok=True)

class GenerateRequest(BaseModel):
    prompt: str
    duration: int = 15

@app.get("/")
def root():
    return {"status": "running", "service": "FocusTune MusicGen"}

@app.post("/generate")
async def generate(req: GenerateRequest):
    max_tokens = min(req.duration * 51, 1503)
    inputs = processor(text=[req.prompt], padding=True, return_tensors="pt")
    audio_values = model.generate(**inputs, do_sample=True, guidance_scale=3, max_new_tokens=max_tokens)
    filename = f"/tmp/audio/{uuid.uuid4()}.wav"
    scipy.io.wavfile.write(filename, rate=model.config.audio_encoder.sampling_rate, data=audio_values[0, 0].numpy())
    return FileResponse(filename, media_type="audio/wav")