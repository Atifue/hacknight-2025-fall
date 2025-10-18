import os
import requests
import mimetypes
from pathlib import Path


ELEVEN_API_BASE = "https://api.elevenlabs.io"


# =======================================================
# 1. FIXED VOICE CLONE FUNCTION
# =======================================================
def clone_voice_from_audio(audio_path: str):
    """
    Clones a voice from a local audio sample and returns the new voice_id.
    """
    if not os.path.exists(audio_path):
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    api_key = os.getenv("ELEVEN_API_KEY")
    if not api_key:
        raise EnvironmentError("Missing ELEVEN_API_KEY environment variable.")

    # Detect MIME type
    mime, _ = mimetypes.guess_type(audio_path)
    if not mime or not mime.startswith("audio/"):
        mime = "audio/wav"

    url = f"{ELEVEN_API_BASE}/v1/voices/add"
    headers = {"xi-api-key": api_key}
    data = {
        "name": "ReVoice Clone",
        "description": "Instant clone for ReVoice prototype"
    }

    print("Uploading voice sample to ElevenLabs...")

    with open(audio_path, "rb") as f:
        files = [("files", (os.path.basename(audio_path), f, mime))]
        r = requests.post(url, headers=headers, data=data, files=files, timeout=120)

    # Debug info if something goes wrong
    if r.status_code >= 400:
        print(f"❌ ElevenLabs API returned {r.status_code}")
        try:
            print("Response:", r.json())
        except Exception:
            print("Raw response:", r.text)
        raise RuntimeError(f"Voice clone failed (HTTP {r.status_code})")

    resp = r.json()
    voice_id = (
        resp.get("voice_id")
        or (resp.get("voice") or {}).get("voice_id")
        or (resp.get("data") or {}).get("voice_id")
    )

    if not voice_id:
        raise RuntimeError(f"Could not find voice_id in response: {resp}")

    print("✅ Voice cloned successfully! Voice ID:", voice_id)
    return voice_id


# =======================================================
# 2. GENERATE SPEECH FUNCTION
# =======================================================
def generate_speech(text: str, voice_id: str, output_path: str):
    """
    Generate speech using the cloned voice.
    """
    api_key = os.getenv("ELEVEN_LABS")
    if not api_key:
        raise EnvironmentError("Missing ELEVEN_API_KEY environment variable.")

    url = f"{ELEVEN_API_BASE}/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": api_key,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.4,
            "similarity_boost": 0.8
        }
    }

    print("Generating speech...")

    r = requests.post(url, headers=headers, json=payload, timeout=60)
    if r.status_code >= 400:
        try:
            print("TTS error:", r.json())
        except Exception:
            print("Raw error:", r.text)
        raise RuntimeError(f"Text-to-speech failed ({r.status_code})")

    with open(output_path, "wb") as f:
        f.write(r.content)
    print(f"✅ Speech saved to {output_path}")


# =======================================================
# 3. MAIN WORKFLOW
# =======================================================
def main():
    """
    Full workflow:
    - Clone voice from sample
    - Generate example speech
    """
    sample_path = str(Path(__file__).parent / "sample_voice.wav")
    output_mp3 = str(Path(__file__).parent / "generated_output.mp3")

    if not os.path.exists(sample_path):
        print(f"❌ Missing audio sample: {sample_path}")
        print("Please place a clear 30-60s WAV/MP3 sample in this folder.")
        return

    # Ensure file isn’t empty
    if os.path.getsize(sample_path) < 50_000:
        print("❌ Audio file too small. Needs to be at least ~60 seconds.")
        return

    try:
        voice_id = clone_voice_from_audio(sample_path)
    except Exception as e:
        print("⚠️ Voice cloning failed:", e)
        return

    try:
        generate_speech("Hello! This is my cloned voice speaking naturally.", voice_id, output_mp3)
    except Exception as e:
        print("⚠️ Speech generation failed:", e)
        return

    print("\n🎉 All done! Check your folder for generated_output.mp3")


# =======================================================
# 4. ENTRY POINT
# =======================================================
if __name__ == "__main__":
    main()
