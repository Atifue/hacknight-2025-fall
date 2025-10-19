# server.py
import os, sys, tempfile, shutil, subprocess, uuid, mimetypes, traceback
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

# === your imports from the script ===
import whisper
from google import genai
from elevenlabs.client import ElevenLabs
from voice_cloner import VoiceCloner

# === stutter detection imports ===
from pydub import AudioSegment
from pathlib import Path
sys.path.append(str(Path(__file__).parent / 'detection-Files'))
from stutter_detector import detect_all
from practice_generator import PracticeGenerator
from generate_audio import generate_practice_audio
from speech_therapy_tips import SpeechTherapyAdvisor

# ================== CONFIG ==================
load_dotenv()
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
PORT = int(os.getenv("PORT", "5001"))

WHISPER_MODEL = "base"     # tiny/base/small/medium/large
CLEAN_MODE = "fluency"     # "fluency" or "grammar"
USE_LIPSYNC_DEFAULT = True

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
W2L_REPO_DIR = os.path.join(PROJECT_DIR, "vendor", "wav2lip-onnx")
W2L_INFER    = os.path.join(W2L_REPO_DIR, "inference_onnxModel.py")
W2L_MODEL    = os.path.join(W2L_REPO_DIR, "checkpoints", "wav2lip.onnx")

OUTPUT_DIR = os.path.join(PROJECT_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# === stutter detection folders ===
UPLOAD_FOLDER = os.path.join(PROJECT_DIR, "temp_uploads")
STUTTER_OUTPUT_FOLDER = os.path.join(PROJECT_DIR, "detection-Files", "outputFiles")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(STUTTER_OUTPUT_FOLDER, exist_ok=True)

# ================== HELPERS ==================
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
        raise RuntimeError("❌ ffmpeg/ffprobe not found. Install ffmpeg.")

def extract_for_asr(src_path, wav16k_mono):
    run(["ffmpeg","-y","-i", src_path, "-vn", "-ac","1", "-ar","16000", wav16k_mono])

def convert_to(src_path, dst_path, ar=None, ac=None):
    # Force audio-only conversion to avoid container quirks
    cmd = ["ffmpeg","-y","-i", src_path, "-vn"]
    if ac: cmd += ["-ac", ac]
    if ar: cmd += ["-ar", ar]
    cmd += [dst_path]
    run(cmd)

def transcribe_whisper(wav16k, model_name=WHISPER_MODEL):
    print("📝 Transcribing…")
    model = whisper.load_model(model_name)
    res = model.transcribe(wav16k, fp16=False)
    return res["text"].strip()

def clean_text_with_gemini(raw_text, mode=CLEAN_MODE):
    print("🧼 Cleaning text…")
    if not GEMINI_API_KEY:
        return raw_text.strip()
    client = genai.Client(api_key=GEMINI_API_KEY)
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
    return cleaned if cleaned else raw_text.strip()

def elevenlabs_tts_to_mp3(text, out_mp3, voice_id):
    print("🔊 Generating TTS…")
    if not ELEVENLABS_API_KEY:
        raise RuntimeError("No ELEVENLABS_API_KEY in .env")
    client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
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
    if not os.path.exists(W2L_INFER):
        raise RuntimeError(f"❌ Wav2Lip-ONNX script not found at: {W2L_INFER}")
    if not os.path.exists(W2L_MODEL):
        raise RuntimeError(f"❌ Wav2Lip model not found at: {W2L_MODEL}")

def wav2lip_onnx(face_video, corrected_audio, out_video, model_path=W2L_MODEL):
    face_abs = os.path.abspath(face_video)
    aud_abs  = os.path.abspath(corrected_audio)
    out_abs  = os.path.abspath(out_video)
    model_abs = os.path.abspath(model_path)
    for p, label in [(face_abs, "--face"), (aud_abs, "--audio"), (model_abs, "--checkpoint_path")]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"{label} path does not exist: {p}")

    py = sys.executable
    cmd = [
        py, W2L_INFER,
        "--checkpoint_path", model_abs,
        "--face", face_abs,
        "--audio", aud_abs,
        "--outfile", out_abs,
    ]
    print("▶", " ".join(cmd))
    p = subprocess.run(
        cmd,
        cwd=W2L_REPO_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    print(p.stdout)
    if p.returncode != 0:
        raise RuntimeError(f"Wav2Lip-ONNX failed.\n{p.stdout}")

def has_video_stream(path):
    """Return True if file has at least one video stream."""
    try:
        out = run([
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=index",
            "-of", "csv=p=0", path
        ]).strip()
        return bool(out)
    except Exception:
        return False

def safe_mux_video_with_audio(src_video, new_audio, out_path):
    """
    If src has no video, just return the audio path.
    If src is webm (vp8/vp9), write webm with video copy + opus audio.
    Otherwise write mp4 and re-encode to h264/aac to avoid container/codec mismatch.
    Returns the actual output path used.
    """
    if not has_video_stream(src_video):
        # Nothing to mux; caller can use audio file
        return new_audio

    src_ext = os.path.splitext(src_video)[1].lower()
    if src_ext == ".webm":
        # Output webm
        out_webm = out_path if out_path.lower().endswith(".webm") else os.path.splitext(out_path)[0] + ".webm"
        run([
            "ffmpeg","-y",
            "-i", src_video, "-i", new_audio,
            "-map","0:v:0", "-map","1:a:0",
            "-c:v","copy",            # keep VP8/VP9
            "-c:a","libopus",         # webm-friendly audio
            "-shortest",
            out_webm
        ])
        return out_webm
    else:
        # Output mp4 with safe re-encode
        out_mp4 = out_path if out_path.lower().endswith(".mp4") else os.path.splitext(out_path)[0] + ".mp4"
        run([
            "ffmpeg","-y",
            "-i", src_video, "-i", new_audio,
            "-map","0:v:0", "-map","1:a:0",
            "-c:v","libx264",         # ensure h264 for mp4
            "-pix_fmt","yuv420p",
            "-preset","veryfast",
            "-crf","23",
            "-c:a","aac",
            "-movflags","+faststart",
            "-shortest",
            out_mp4
        ])
        return out_mp4

# ================== FLASK APP ==================
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

@app.route("/files/<path:filename>")
def files(filename):
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=False)

@app.route("/api/health")
def health():
    return jsonify({"ok": True})

# JSON errors (so frontend never sees HTML)
from werkzeug.exceptions import HTTPException
@app.errorhandler(Exception)
def handle_ex(e):
    code = 500
    if isinstance(e, HTTPException):
        code = e.code
    print("ERROR:", e, "\n", traceback.format_exc())
    return jsonify({"error": str(e)}), code

@app.route("/api/revoice", methods=["POST"])
def revoice():
    """
    Accepts 'media' (audio/video). Optional 'use_lipsync' (true/false). Optional 'voice_id'.
    If no voice_id, it clones a voice from the uploaded media automatically.
    Saves results under ./outputs and returns URLs.
    """
    need_ffmpeg()
    if "media" not in request.files:
        return jsonify({"error":"No 'media' file part"}), 400

    file = request.files["media"]
    if not file.filename:
        return jsonify({"error":"Empty filename"}), 400

    uid = uuid.uuid4().hex
    ext = os.path.splitext(file.filename)[1].lower() or ".webm"
    src_path = os.path.join(OUTPUT_DIR, f"src_{uid}{ext}")
    file.save(src_path)

    # Determine if the uploaded file truly has video
    is_video = has_video_stream(src_path)

    use_lipsync = (request.form.get("use_lipsync", str(USE_LIPSYNC_DEFAULT)).lower() == "true")
    voice_id = request.form.get("voice_id")  # may be None

    tmp = tempfile.mkdtemp(prefix="revoice_")
    try:
        # 1) ASR audio
        wav16 = os.path.join(tmp, "audio_16k_mono.wav")
        extract_for_asr(src_path, wav16)

        # 2) Whisper
        raw_text = transcribe_whisper(wav16)

        # 3) Clean
        cleaned = clean_text_with_gemini(raw_text, CLEAN_MODE)

        # 4) Ensure voice_id (clone from uploaded media if missing) — use the WAV we already have
        if not voice_id:
            clone_audio = wav16  # safest: 16k mono wav used for Whisper
            cloner = VoiceCloner(ELEVENLABS_API_KEY)
            voice_id = cloner.clone_voice(clone_audio, f"ReVoice-{uid}")
            if not voice_id:
                return jsonify({"error":"Voice cloning failed"}), 500

        # 5) TTS -> corrected mp3
        out_mp3 = os.path.join(OUTPUT_DIR, f"tts_{uid}.mp3")
        elevenlabs_tts_to_mp3(cleaned, out_mp3, voice_id)

        audio_url = f"/files/{os.path.basename(out_mp3)}"
        video_url = None

        # 6) If video, produce lipsync (default) or container-safe remux
        if is_video:
            if use_lipsync:
                ensure_wav2lip_paths()
                corrected_wav = os.path.join(tmp, "tts.wav")
                convert_to(out_mp3, corrected_wav, ar="44100", ac="2")
                out_mp4 = os.path.join(OUTPUT_DIR, f"lips_{uid}.mp4")
                wav2lip_onnx(src_path, corrected_wav, out_mp4, W2L_MODEL)
                video_url = f"/files/{os.path.basename(out_mp4)}"
            else:
                out_guess = os.path.join(OUTPUT_DIR, f"remux_{uid}.mp4")  # may flip to .webm
                out_video = safe_mux_video_with_audio(src_path, out_mp3, out_guess)
                # If file had no video, safe_mux returns the audio path, so only set video_url if it differs
                if out_video != out_mp3:
                    video_url = f"/files/{os.path.basename(out_video)}"

        return jsonify({
            "cleaned_text": cleaned,
            "audio_url": audio_url,
            "video_url": video_url,
            "voice_id": voice_id
        })
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

# ================== STUTTER DETECTION ROUTES ==================
@app.route('/api/analyze', methods=['POST'])
def analyze_speech():
    """
    Analyze speech recording for stutters and generate practice exercises
    """
    try:
        # Clean up ALL old output files before generating new ones
        try:
            import glob
            for pattern in ['practice_script_*.txt', 'practice_script_*_audio.mp3']:
                files = glob.glob(os.path.join(STUTTER_OUTPUT_FOLDER, pattern))
                for old_file in files:
                    try:
                        os.remove(old_file)
                        print(f"🧹 Cleaned up old file: {os.path.basename(old_file)}")
                    except:
                        pass
        except:
            pass
        
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        
        # Save uploaded file
        webm_path = os.path.join(UPLOAD_FOLDER, 'recording.webm')
        audio_file.save(webm_path)
        
        # Convert webm to mp3
        print("Converting audio to MP3...")
        mp3_path = os.path.join(UPLOAD_FOLDER, 'recording.mp3')
        audio = AudioSegment.from_file(webm_path, format="webm")
        audio.export(mp3_path, format="mp3")
        
        # Debug: Show file info
        import hashlib
        import time
        file_size = os.path.getsize(mp3_path)
        with open(mp3_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        print(f"📊 Processing: {mp3_path} ({file_size} bytes) Hash: {file_hash} at {time.strftime('%H:%M:%S')}")
        
        # Detect stutters
        print("Detecting stutters...")
        detection_results = detect_all(mp3_path, verbose=True)
        
        events = detection_results.get('events', [])
        words = detection_results.get('words', [])
        
        # Show what was transcribed
        transcribed_text = ' '.join([w.get('word', '') for w in words])
        print(f"\n🗣️  TRANSCRIPTION: '{transcribed_text}'")
        print(f"✅ Detection complete! Found {len(events)} stutter event(s)")
        
        # Show what stutters were detected
        if events:
            print("📋 Detected stutters:")
            for e in events:
                print(f"   - {e['type']}: '{e.get('word', 'unknown')}' at {e['start']:.1f}s")
        
        # Prepare response data
        response_data = {
            'has_stutters': len(events) > 0,
            'stutter_count': len(events),
            'events': events,
            'detection_summary': _create_summary(detection_results)
        }
        
        # If stutters detected, generate practice exercises
        if len(events) > 0:
            print("Generating practice exercises...")
            
            # Get the first stutter for practice generation (skip blocks - too many false positives)
            first_event = None
            for event in events:
                if event['type'] != 'block':  # Skip blocks
                    first_event = event
                    break
            
            # If only blocks were detected, skip practice generation
            if not first_event:
                print("⚠️  Only blocks detected (likely false positives) - skipping practice generation")
                return jsonify(response_data)
            
            stutter_type = first_event['type']
            
            # Determine the word and sound
            if stutter_type == 'acoustic_repetition' and 'target_word' in first_event:
                word = first_event['target_word']
                sound = first_event.get('inferred_sound', word[0] if word else '?')
            else:
                word = first_event.get('word', '').strip('.,!?;:\'"')
                sound = word[0].upper() if word else '?'
            
            # Generate practice script
            generator = PracticeGenerator()
            practice_info = {
                'word': word,
                'sound': sound,
                'stutter_type': stutter_type,
                'event': first_event
            }
            
            exercises = generator.generate_practice_exercises(practice_info)
            script = exercises.get('raw_response', '')
            
            # Save script
            script_filename = f"practice_script_{word}.txt"
            script_path = os.path.join(STUTTER_OUTPUT_FOLDER, script_filename)
            with open(script_path, 'w') as f:
                f.write(script)
            
            # Generate audio
            print("Generating practice audio...")
            audio_filename = f"practice_script_{word}_audio.mp3"
            audio_path = os.path.join(STUTTER_OUTPUT_FOLDER, audio_filename)
            
            # Always regenerate to ensure fresh results
            try:
                generate_practice_audio(script_path, audio_path)
            except Exception as e:
                print(f"Warning: Could not generate audio: {e}")
                audio_filename = None
            
            # Generate detailed therapy tips
            advisor = SpeechTherapyAdvisor()
            detailed_advice = advisor.generate_advice(detection_results)
            
            # Build comprehensive, detailed tips
            detailed_tips = ""
            sound_lower = sound.lower() if sound else ""
            
            # 1. WHY THIS HAPPENS - Be specific!
            stutter_lookup = stutter_type if stutter_type != 'acoustic_repetition' else 'repetition'
            if stutter_lookup in advisor.tips:
                tip_data = advisor.tips[stutter_lookup]
                detailed_tips += f"🔍 WHY THIS HAPPENS:\n{tip_data['why_it_happens']}\n\n"
            
            # 2. SOUND-SPECIFIC ARTICULATION - Very detailed!
            if sound_lower in advisor.sound_guidance:
                sound_info = advisor.sound_guidance[sound_lower]
                detailed_tips += f"🗣️ CORRECT MOUTH POSITION FOR '{sound.upper()}':\n"
                detailed_tips += f"• WHERE: {sound_info['position']}\n"
                detailed_tips += f"• COMMON MISTAKE: {sound_info['common_issue']}\n"
                detailed_tips += f"• HOW TO FIX: {sound_info['fix']}\n\n"
            
            # 3. STEP-BY-STEP WORD GUIDANCE
            if 'word_specific_guidance' in detailed_advice and detailed_advice['word_specific_guidance']:
                guidance = detailed_advice['word_specific_guidance'][0]  # Get first (most relevant)
                detailed_tips += f"📝 HOW TO SAY '{word.upper()}':\n{guidance['how_to_say_it']}\n\n"
            
            # 4. KEY TECHNIQUES - Full, not truncated!
            if stutter_lookup in advisor.tips:
                tip_data = advisor.tips[stutter_lookup]
                techniques = tip_data.get('techniques', [])
                if techniques:
                    detailed_tips += "💡 TECHNIQUES TO PRACTICE:\n"
                    for i, technique in enumerate(techniques, 1):
                        # Remove markdown formatting for cleaner display
                        clean_tech = technique.replace('**', '')
                        detailed_tips += f"{i}. {clean_tech}\n\n"
            
            # 5. PRACTICE EXERCISES - Specific, actionable
            if stutter_lookup in advisor.tips:
                tip_data = advisor.tips[stutter_lookup]
                exercises = tip_data.get('exercises', [])
                if exercises:
                    detailed_tips += "🏋️ PRACTICE EXERCISES:\n"
                    for i, exercise in enumerate(exercises, 1):
                        clean_ex = exercise.replace('**', '')
                        detailed_tips += f"{i}. {clean_ex}\n\n"
            
            # 6. SPECIFIC PRACTICE FOR THIS SOUND
            if sound_lower in advisor.sound_guidance:
                sound_info = advisor.sound_guidance[sound_lower]
                detailed_tips += f"🎯 SPECIFIC PRACTICE FOR '{sound.upper()}':\n{sound_info['practice']}\n\n"
            
            # 7. MOUTH POSITIONS - Physical guidance
            if stutter_lookup in advisor.tips:
                tip_data = advisor.tips[stutter_lookup]
                mouth_positions = tip_data.get('mouth_positions', [])
                if mouth_positions:
                    detailed_tips += "👄 CORRECT MOUTH POSITIONS:\n"
                    for pos in mouth_positions:
                        detailed_tips += f"• {pos}\n"
                    detailed_tips += "\n"
            
            response_data['practice'] = {
                'word': word,
                'sound': sound,
                'stutter_type': stutter_type,
                'script': script,
                'audio_file': audio_filename if os.path.exists(audio_path) else None,
                'detailed_tips': detailed_tips.strip()
            }
        
        # Clean up temp files
        try:
            os.remove(webm_path)
            os.remove(mp3_path)
            # Also clean up the WAV file created by stutter_detector
            wav_path = mp3_path.replace('.mp3', '.wav')
            if os.path.exists(wav_path):
                os.remove(wav_path)
        except:
            pass
        
        return jsonify(response_data)
    
    except Exception as e:
        print(f"Error in analyze_speech: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500


@app.route('/api/audio/<filename>', methods=['GET'])
def get_practice_audio(filename):
    """
    Serve practice audio files
    """
    try:
        audio_path = os.path.join(STUTTER_OUTPUT_FOLDER, filename)
        if not os.path.exists(audio_path):
            return jsonify({'error': 'Audio file not found'}), 404
        return send_from_directory(STUTTER_OUTPUT_FOLDER, filename)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _create_summary(detection_results):
    """Create a summary of detection results for the frontend"""
    events = detection_results.get('events', [])
    
    if not events:
        return {
            'message': 'No stutters detected',
            'stutter_types': {},
            'events_detail': []
        }
    
    # Count each stutter type
    stutter_types = {}
    for event in events:
        stype = event.get('type', 'unknown')
        stutter_types[stype] = stutter_types.get(stype, 0) + 1
    
    # Format detailed events
    events_detail = []
    for event in events:
        events_detail.append({
            'type': event.get('type', 'unknown'),
            'word': event.get('word', 'unknown'),
            'time': f"{event.get('start', 0):.1f}s",
            'confidence': f"{int(event.get('confidence', 0.5) * 100)}%"
        })
    
    return {
        'message': f"Found {len(events)} stutter event(s)",
        'stutter_types': stutter_types,
        'events_detail': events_detail
    }


if __name__ == "__main__":
    print(f"→ ReVoice API (with Stutter Detection) on http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=True)
