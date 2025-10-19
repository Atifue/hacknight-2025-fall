#!/usr/bin/env python3
"""
SIMPLIFIED Stutter Detection
Clean, simple rules - no complex algorithms
"""

import sys, re, json, numpy as np, librosa, soundfile as sf, os
from faster_whisper import WhisperModel
from pydub import AudioSegment

# ============== SIMPLE PARAMETERS ==============
WHISPER_MODEL = "small"
IGNORE_FIRST_SECONDS = 0.0  # Don't ignore any stutters based on time (disabled)

# Detection thresholds (super simple!)
BLOCK_GAP_SECONDS = 1.0      # Pause between words >= 1.0s = block (TUNED)
PROLONGATION_SECONDS = 2.8   # Word duration >= 2.8s = prolongation (for normal words) - VERY STRICT! (TUNED)
PROLONGATION_CONSONANT = 1.3 # Word duration >= 1.3s for prolongable consonants (s, f, r, etc.) (TUNED)
MIN_REPETITIONS = 3          # Need 3+ words in a row to be a repetition
MIN_SINGLE_LETTER_REPS = 4   # Single letters need 4+ reps


# ============== AUDIO & TRANSCRIPTION ==============
def convert_to_wav(file_path):
    """Convert MP3 to WAV if needed"""
    if file_path.lower().endswith(".mp3"):
        wav_path = file_path[:-4] + ".wav"
        # Always regenerate WAV to ensure fresh audio
        if os.path.exists(wav_path):
            os.remove(wav_path)
        print(f"Converting {file_path} to WAV...")
        AudioSegment.from_mp3(file_path).export(wav_path, format="wav")
        return wav_path
    return file_path


def transcribe_words(audio_path):
    """Get word-level transcription with timestamps"""
    print(f"Transcribing audio with Whisper ({WHISPER_MODEL} model)...")
    model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
    segments, _ = model.transcribe(audio_path, word_timestamps=True)
    
    words = []
    for segment in segments:
        if segment.words:
            for w in segment.words:
                words.append({
                    'word': w.word,
                    'start': w.start,
                    'end': w.end
                })
    
    print(f"✓ Transcribed {len(words)} words")
    return words


def load_audio(audio_path, sr=22050):
    """Load audio file"""
    y, sr = librosa.load(audio_path, sr=sr)
    return y, sr


# ============== DETECTION (SUPER SIMPLE!) ==============
def detect_blocks(words):
    """
    Block = long pause (1.5+ seconds) between words
    """
    events = []
    
    for i in range(1, len(words)):
        prev_word = words[i-1]
        curr_word = words[i]
        
        gap = curr_word['start'] - prev_word['end']
        
        # Skip blocks involving the first word (it includes leading silence)
        if i == 1 and prev_word['start'] < 0.1:
            continue
        
        # Simple check: gap >= BLOCK_GAP_SECONDS
        if gap >= BLOCK_GAP_SECONDS and curr_word['start'] >= IGNORE_FIRST_SECONDS:
            events.append({
                "type": "block",
                "word": curr_word['word'],
                "start": curr_word['start'],
                "end": curr_word['end'],
                "gap_duration": gap,
                "confidence": 0.85
            })
    
    return events


def detect_repetitions(words):
    """
    Repetition = same word 3+ times in a row (4+ for single letters)
    """
    events = []
    i = 0
    
    while i < len(words):
        # Clean the word (remove punctuation)
        word = re.sub(r'\W+', '', words[i]['word'].lower())
        
        if len(word) < 1:
            i += 1
            continue
        
        # Count consecutive repetitions
        start_idx = i
        while i + 1 < len(words) and re.sub(r'\W+', '', words[i+1]['word'].lower()) == word:
            i += 1
        end_idx = i
        
        count = end_idx - start_idx + 1
        
        # Check if we have enough repetitions
        if count >= MIN_REPETITIONS:
            # NOTE: We DON'T skip first word for repetitions!
            # If someone repeats a word 4 times starting at 0.0s, that's a real stutter,
            # not just leading silence. Leading silence only matters for prolongations.
            
            # Single letters need 4+ reps (unless it's "i")
            if len(word) == 1 and word not in ['i'] and count < MIN_SINGLE_LETTER_REPS:
                i += 1
                continue
            
            events.append({
                "type": "repetition",
                "word": word,
                "count": count,
                "start": words[start_idx]['start'],
                "end": words[end_idx]['end'],
                "confidence": 0.95
            })
        
        i += 1
    
    return events


def detect_prolongations(words):
    """
    Prolongation = word duration >= threshold
    Simple! No complex F0 or RMS checks.
    For words starting with repeatable consonants (s, f, r, etc.), use lower threshold.
    """
    events = []
    
    # Consonants commonly prolonged in stuttering (fricatives, liquids, nasals)
    PROLONGABLE_CONSONANTS = ['s', 'f', 'r', 'l', 'm', 'n', 'v', 'z', 'sh']
    
    for idx, w in enumerate(words):
        duration = w['end'] - w['start']
        word_clean = w['word'].strip().lower().strip('.,!?;:\'"')
        
        # Check if there's a gap BEFORE this word (indicates it might be a block, not prolongation)
        # If so, skip it - this should be detected as a block, not a prolongation
        if idx > 0:
            gap_before = w['start'] - words[idx-1]['end']
            if gap_before >= BLOCK_GAP_SECONDS:
                continue
        
        # Check if word starts with a prolongable consonant (use lower threshold)
        starts_with_prolongable = any(word_clean.startswith(c) for c in PROLONGABLE_CONSONANTS)
        
        # Use lower threshold for prolongable consonants, higher for others
        threshold = PROLONGATION_CONSONANT if starts_with_prolongable else PROLONGATION_SECONDS
        
        if duration >= threshold:
            events.append({
                "type": "prolongation",
                "word": w['word'],
                "start": w['start'],
                "end": w['end'],
                "dur_ms": duration * 1000,
                "confidence": 0.85
            })
    
    return events


def detect_acoustic_repetitions(y, sr, words):
    """
    Acoustic repetition = rapid sound bursts (t-t-t-t)
    Uses onset detection to catch what Whisper misses
    """
    events = []
    
    try:
        # Detect onsets (sudden energy bursts)
        onset_frames = librosa.onset.onset_detect(
            y=y, sr=sr,
            hop_length=512,
            backtrack=False,
            delta=0.12  # High threshold - only very clear repetitions
        )
        
        if len(onset_frames) < 4:
            return events
        
        # Convert to time
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
        
        # Look for clusters of rapid onsets
        i = 0
        while i < len(onset_times) - 3:
            # Check for bursts
            cluster_start = i
            burst_count = 1
            
            for j in range(i, min(i + 10, len(onset_times) - 1)):
                gap_ms = (onset_times[j + 1] - onset_times[j]) * 1000
                
                # Gap between 80-250ms = likely repetition (expanded range)
                if 80 <= gap_ms <= 250:
                    burst_count += 1
                else:
                    break
            
            # Need at least 4 bursts (lowered from 5)
            if burst_count >= 4:
                start_time = onset_times[cluster_start]
                end_time = onset_times[cluster_start + burst_count - 1]
                
                # Skip if too early
                if start_time >= IGNORE_FIRST_SECONDS:
                    # Try to figure out what sound is being repeated
                    inferred_sound = None
                    target_word = None
                    
                    # Find next word after this cluster (within 0.8s)
                    for w in words:
                        if w['start'] >= end_time and (w['start'] - end_time) < 0.8:
                            word_text = w['word'].strip('.,!?;:\'"').lower()
                            if word_text:
                                # Check for consonant clusters first (st, sl, tr, etc.)
                                consonant_clusters = ['st', 'sl', 'sp', 'sk', 'sc', 'tr', 'dr', 'br', 'cr', 'fr', 'gr', 'pr', 'bl', 'cl', 'fl', 'gl', 'pl']
                                if len(word_text) >= 2 and word_text[:2] in consonant_clusters:
                                    inferred_sound = word_text[:2]
                                else:
                                    inferred_sound = word_text[0]
                                target_word = w['word']
                            break
                    
                    # If we still couldn't infer, skip this detection (too unreliable)
                    if not inferred_sound or not target_word:
                        i += burst_count
                        continue
                    events.append({
                        "type": "acoustic_repetition",
                        "word": inferred_sound,  # Just the sound for frontend
                        "inferred_sound": inferred_sound,
                        "target_word": target_word,
                        "count": burst_count,
                        "start": start_time,
                        "end": end_time,
                        "confidence": 0.80
                    })
                
                i += burst_count
            else:
                i += 1
    
    except Exception as e:
        print(f"Warning: Acoustic detection error: {e}")
    
    return events


# ============== MAIN DETECTION ==============
def detect_all(audio_file, verbose=True):
    """
    Detect all stutter types - simple and clean!
    """
    # Convert and load
    wav_file = convert_to_wav(audio_file)
    words = transcribe_words(wav_file)
    y, sr = load_audio(wav_file)
    
    if len(words) < 2:
        return {'events': [], 'words': words}
    
    print("Analyzing acoustic features...")
    
    # Detect each type (all independent, simple checks)
    blocks = detect_blocks(words)
    repetitions = detect_repetitions(words)
    prolongations = detect_prolongations(words)
    acoustic_reps = detect_acoustic_repetitions(y, sr, words)
    
    # Combine all events
    all_events = blocks + repetitions + prolongations + acoustic_reps
    
    # Sort by time
    all_events.sort(key=lambda x: x['start'])
    
    if verbose:
        print(f"\n🗣️  TRANSCRIPTION: '{' '.join([w['word'] for w in words])}'")
        print(f"✅ Detection complete! Found {len(all_events)} stutter event(s)")
        
        if all_events:
            print("📋 Detected stutters:")
            for e in all_events:
                print(f"   - {e['type']}: '{e.get('word', 'unknown')}' at {e['start']:.1f}s")
    
    return {
        'events': all_events,
        'words': words
    }


# ============== CLI ==============
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 stutter_detector.py <audio_file>")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    results = detect_all(audio_file)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"SUMMARY: {len(results['events'])} stutter(s) detected")
    print(f"{'='*60}")
