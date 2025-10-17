from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
import os

# Load API key
load_dotenv()
client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))

# Read text from file
with open("fixed.txt", "r", encoding="utf-8") as f:
    text = f.read()

# Your saved voice ID
voice_id = "FRyuKfPlEWkjhOilQCqk"

# Generate audio
audio = client.text_to_speech.convert(
    text=text,
    voice_id=voice_id,
    model_id="eleven_multilingual_v2",
    output_format="mp3_44100_128",
)

# Save MP3
with open("output.mp3", "wb") as f:
    for chunk in audio:
        f.write(chunk)

print("✅ Audio saved as output.mp3")