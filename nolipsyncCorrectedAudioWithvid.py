import os, shutil, tempfile, subprocess, sys
from dotenv import load_dotenv
import whisper
from google import genai
from elevenlabs.client import ElevenLabs

# ---------------- Settings ----------------
MP4_PATH = "/Users/marium3/Downloads/newnew.mp4"     # hard-coded input
VOICE_ID = "FRyuKfPlEWkjhOilQCqk"         # your cloned voice id
OUT_MP4  = "revoiced.mp4"                 # output video
WHISPER_MODEL = "base"                    # tiny/base/small/medium/large
MODE = "fluency"                          # text cleanup mode
# ------------------------------------------

def run(cmd):
    print("▶", " ".join(cmd))
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        print(p.stdout)
        raise RuntimeError("Command failed")
    return p.stdout

def extract_audio(mp4, wav):
    run(["ffmpeg","-y","-i",mp4,"-vn","-ac","1","-ar","16000",wav])

def remux(mp4, new_audio, out_mp4):
    run(["ffmpeg","-y","-i",mp4,"-i",new_audio,"-map","0:v:0","-map","1:a:0","-c:v","copy","-shortest",out_mp4])

def transcribe(wav):
    print("📝 Transcribing…")
    model = whisper.load_model(WHISPER_MODEL)
    res = model.transcribe(wav, fp16=False)
    return res["text"].strip()

def clean_text(text):
    print("🧼 Cleaning text…")
    load_dotenv()
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("No GEMINI_API_KEY")
    client = genai.Client(api_key=key)

    if MODE == "fluency":
        prompt = (
            "Remove stutters (repeated syllables) and filler words (um, uh), "
            "but preserve meaning and tone. Output only the cleaned text.\n\n" + text
        )
    else:
        prompt = "Fix grammar and clarity. Output only corrected text.\n\n" + text

    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return (resp.text or "").strip()

def tts(text, out_mp3):
    print("🔊 Generating voice…")
    load_dotenv()
    key = os.getenv("ELEVEN_LABS")
    if not key:
        raise RuntimeError("No ELEVENLABS_API_KEY")
    client = ElevenLabs(api_key=key)
    audio = client.text_to_speech.convert(
        text=text,
        voice_id=VOICE_ID,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    with open(out_mp3, "wb") as f:
        for c in audio:
            f.write(c)

def main():
    tmp = tempfile.mkdtemp(prefix="revoice_")
    wav = os.path.join(tmp, "audio.wav")
    fixed_txt = os.path.join(tmp, "fixed.txt")
    mp3 = os.path.join(tmp, "corrected.mp3")

    try:
        print("🎬 Starting ReVoice hard-coded run")
        extract_audio(MP4_PATH, wav)
        raw_text = transcribe(wav)
        cleaned = clean_text(raw_text)
        with open(fixed_txt, "w", encoding="utf-8") as f:
            f.write(cleaned)
        tts(cleaned, mp3)
        remux(MP4_PATH, mp3, OUT_MP4)
        print(f"✅ Done → {OUT_MP4}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
