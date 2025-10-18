import os, sys, shutil, tempfile, subprocess
from dotenv import load_dotenv
import whisper
from google import genai
from elevenlabs.client import ElevenLabs



# ================== HARD-CODE YOUR SETTINGS ==================
MP4_PATH = "/Users/marium3/Downloads/newnew.mp4"          # your input video
VOICE_ID = "FRyuKfPlEWkjhOilQCqk"              # your ElevenLabs cloned voice
WHISPER_MODEL = "base"                         # tiny/base/small/medium/large
CLEAN_MODE = "fluency"                         # "fluency" (recommended) or "grammar"

USE_LIPSYNC = True                             # set False to just remux

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
# point these at your local Wav2Lip-ONNX clone
W2L_REPO_DIR = os.path.join(PROJECT_DIR, "vendor", "wav2lip-onnx")
W2L_INFER    = os.path.join(W2L_REPO_DIR, "inference_onnxModel.py")
W2L_MODEL    = os.path.join(W2L_REPO_DIR, "checkpoints", "wav2lip.onnx")
# Make the output paths absolute (they will always save here)
OUT_MP4  = os.path.join(PROJECT_DIR, "revoiced.mp4")
OUT_LIPS = os.path.join(PROJECT_DIR, "revoiced_lipsync.mp4")

# ============================================================

def run(cmd):
    print("▶", " ".join(str(x) for x in cmd))
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        print(p.stdout)
        raise RuntimeError("Command failed")
    return p.stdout

def need_ffmpeg():
    try:
        run(["ffmpeg","-version"])
        run(["ffprobe","-version"])
    except Exception:
        sys.exit("❌ ffmpeg/ffprobe not found. Install ffmpeg and retry.")

def extract_audio_for_asr(mp4, wav16k_mono):
    # best input for Whisper
    run(["ffmpeg","-y","-i", mp4, "-vn", "-ac","1", "-ar","16000", wav16k_mono])

def remux_video_with_new_audio(mp4, new_audio, out_mp4):
    # swap audio track, keep original video
    run([
        "ffmpeg","-y",
        "-i", mp4, "-i", new_audio,
        "-map","0:v:0", "-map","1:a:0",
        "-c:v","copy", "-shortest",
        out_mp4
    ])

def transcribe_whisper(wav16k, model_name=WHISPER_MODEL):
    print("📝 Transcribing…")
    # Optional: pin whisper cache dir if you like:
    # CACHE = os.path.expanduser("~/.cache/whisper")
    # os.makedirs(CACHE, exist_ok=True)
    model = whisper.load_model(model_name)  # , download_root=CACHE
    res = model.transcribe(wav16k, fp16=False)
    return res["text"].strip()

def clean_text_with_gemini(raw_text, mode=CLEAN_MODE):
    print("🧼 Cleaning text…")
    load_dotenv()
    gkey = os.getenv("GEMINI_API_KEY")
    if not gkey:
        raise RuntimeError("No GEMINI_API_KEY in .env")
    client = genai.Client(api_key=gkey)

    if mode == "fluency":
        prompt = (
            "You are cleaning a transcript for fluent re-synthesis.\n"
            "Rules:\n"
            "1) Remove repeated syllables/words from stuttering.\n"
            "2) Remove filler disfluencies (um, uh, you know) only if meaning is unchanged.\n"
            "3) Preserve wording and tone; do NOT rewrite for style/grammar.\n"
            "4) Keep punctuation minimal and natural.\n"
            "5) Output ONLY the cleaned text.\n\n" + raw_text
        )
    else:
        prompt = "Fix grammar and clarity. Output only corrected text.\n\n" + raw_text

    resp = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    cleaned = (resp.text or "").strip()
    if not cleaned:
        cleaned = raw_text.strip()
    return cleaned

def elevenlabs_tts_to_mp3(text, out_mp3, voice_id=VOICE_ID):
    print("🔊 Generating TTS…")
    load_dotenv()
    ekey = os.getenv("ELEVEN_LABS")
    if not ekey:
        raise RuntimeError("No ELEVENLABS_API_KEY in .env")
    client = ElevenLabs(api_key=ekey)
    stream = client.text_to_speech.convert(
        text=text,
        voice_id=voice_id,
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )
    with open(out_mp3, "wb") as f:
        for chunk in stream:
            f.write(chunk)

def ensure_wav2lip_paths():
    if not USE_LIPSYNC:
        return
    if not os.path.exists(W2L_INFER):
        raise RuntimeError(f"❌ Wav2Lip-ONNX script not found at: {W2L_INFER}\n"
                           f"Set W2L_REPO_DIR/W2L_INFER to your repo paths.")
    # onnxruntime etc. should be installed per that repo's README

def wav2lip_onnx(face_video, corrected_audio, out_video, model_path=W2L_MODEL):
    """
    Call your ONNX repo's inference script.
    This fork requires the flag --checkpoint_path instead of --model.
    """
    py = sys.executable
    cmd = [
        py,
        W2L_INFER,
        "--checkpoint_path", model_path,   # <--- this line changed
        "--face", face_video,
        "--audio", corrected_audio,
        "--outfile", out_video,            # <--- correct flag from error message
    ]

    print("▶", " ".join(cmd))
    p = subprocess.run(
        cmd,
        cwd=W2L_REPO_DIR,  # run inside the repo folder
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(p.stdout)

    if p.returncode != 0:
        raise RuntimeError(f"Wav2Lip-ONNX failed.\n{p.stdout}")




def maybe_convert_to_wav(src_audio, dst_wav):
    """
    Some ONNX repos prefer WAV input; if your repo can handle MP3 directly, you can skip this.
    We'll convert MP3 -> WAV to be safe; cheap + fast.
    """
    if os.path.splitext(src_audio)[1].lower() == ".wav":
        return src_audio
    run(["ffmpeg","-y","-i", src_audio, "-ar","44100", "-ac","2", dst_wav])
    return dst_wav

def main():
    if not os.path.exists(MP4_PATH):
        sys.exit(f"❌ Input video not found: {MP4_PATH}")
    need_ffmpeg()
    ensure_wav2lip_paths()

    tmp = tempfile.mkdtemp(prefix="revoice_")
    wav16 = os.path.join(tmp, "audio_16k_mono.wav")
    corrected_mp3 = os.path.join(tmp, "corrected.mp3")
    corrected_wav = os.path.join(tmp, "corrected.wav")
    fixed_txt = os.path.join(tmp, "fixed.txt")

    try:
        print("🎬 ReVoice (hard-coded, with optional ONNX lip-sync)")
        # 1) Extract audio for ASR
        extract_audio_for_asr(MP4_PATH, wav16)

        # 2) STT
        raw_text = transcribe_whisper(wav16)

        # 3) Clean text
        cleaned = clean_text_with_gemini(raw_text, CLEAN_MODE)
        with open(fixed_txt, "w", encoding="utf-8") as f:
            f.write(cleaned)

        # 4) TTS -> corrected MP3
        elevenlabs_tts_to_mp3(cleaned, corrected_mp3, VOICE_ID)

        # 5) Output
        if USE_LIPSYNC:
            print("👄 Lip-syncing with Wav2Lip-ONNX (free, CPU)…")
            # convert to WAV if your ONNX script prefers wav input
            audio_for_w2l = maybe_convert_to_wav(corrected_mp3, corrected_wav)
            wav2lip_onnx(MP4_PATH, audio_for_w2l, OUT_LIPS, W2L_MODEL)
            print(f"✅ Lip-synced video → {OUT_LIPS}")
        else:
            print("🎛️ Remuxing corrected audio (no face edit)…")
            remux_video_with_new_audio(MP4_PATH, corrected_mp3, OUT_MP4)
            print(f"✅ Done → {OUT_MP4}")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    main()
