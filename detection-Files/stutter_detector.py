#!/usr/bin/env python3
"""
Enhanced Stutter Detection Script
Detects repetitions, prolongations, and blocks in audio files
"""

import sys, re, json, numpy as np, librosa, soundfile as sf, os
from faster_whisper import WhisperModel
from pydub import AudioSegment
from typing import List, Dict
from pathlib import Path

# ---------- TUNABLE PARAMETERS ----------
MODEL_SIZE = "small"              # Whisper model size (tiny, base, small, medium, large)
REPEAT_WINDOW_S = 0.7             # max gap between repeated words for merging
PROLONG_MS = 650                  # min voiced duration (ms) to count as prolongation (increased to reduce false positives)
MIN_WORD_MS_FOR_PROLONG = 500     # ignore words shorter than this for prolongation  
PROLONG_RATIO = 0.70              # voiced duration must be >70% of word duration
LEADING_SILENCE_IGNORE = 0.35     # ignore blocks in first N seconds
BLOCK_RMS_THRESH = 0.004          # RMS threshold for block detection (increased from 0.003)
IGNORE_SHORT_WORDS = ["i","to","the","a","an","and","is","of","in","it","at","or","for","but","not","can","will","that","these","those","very","difficult"]  # ignore these for prolongation
IGNORE_CONTRACTIONS = ["isn't","aren't","wasn't","weren't","don't","doesn't","didn't","can't","won't","wouldn't","shouldn't","couldn't","haven't","hasn't","hadn't"]  # ignore contractions
MIN_WORD_DURATION_MS = 150        # minimum word duration to consider for analysis

# Acoustic pattern detection (for catching stutters Whisper misses)  
# NOTE: This is experimental and may have false positives. Tune these carefully.
# Acoustic detection is HARD - it may miss some stutters or catch false positives
# THESE ARE VERY STRICT to avoid false positives from normal syllables
ACOUSTIC_ONSET_THRESH = 0.10      # VERY high threshold - only strong, sharp bursts
MIN_BURST_GAP_MS = 80             # Longer minimum - normal syllables are faster than this
MAX_BURST_GAP_MS = 200            # Shorter maximum - true stutters are rapid and close together
MIN_BURSTS_FOR_STUTTER = 5        # Need at least 5 bursts (very strict to avoid false positives)
# --------------------------------------

# Color codes for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

# ----------------- AUDIO CONVERSION -----------------
def convert_to_wav(file_path):
    """Convert MP3 to WAV if needed"""
    if file_path.lower().endswith(".mp3"):
        wav_path = file_path[:-4] + ".wav"
        # Always regenerate WAV to ensure fresh audio (remove old file first)
        if os.path.exists(wav_path):
            os.remove(wav_path)
        print(f"Converting {file_path} to WAV...")
        AudioSegment.from_mp3(file_path).export(wav_path, format="wav")
        return wav_path
    return file_path

# ----------------- TRANSCRIPTION -----------------
def transcribe_words(audio_path):
    """Transcribe audio and get word-level timestamps"""
    print(f"Transcribing audio with Whisper ({MODEL_SIZE} model)...")
    model = WhisperModel(MODEL_SIZE, device="cpu")
    segments, info = model.transcribe(audio_path, word_timestamps=True)
    
    words = []
    for seg in segments:
        for w in seg.words:
            words.append({
                "word": w.word.strip(),
                "start": float(w.start),
                "end": float(w.end)
            })
    
    words = sorted(words, key=lambda x: x['start'])
    print(f"✓ Transcribed {len(words)} words")
    return words

# ----------------- AUDIO LOADING -----------------
def load_audio(audio_path, sr=16000):
    """Load audio file with librosa"""
    y, sr = librosa.load(audio_path, sr=sr)
    return y, sr

# ----------------- REPETITION DETECTION -----------------
def detect_repetitions(words):
    """Detect word repetitions (e.g., "I I I went")"""
    events = []
    i = 0
    
    print(f"\n🔍 DEBUG: Checking {len(words)} words for repetitions")
    
    while i < len(words):
        # Normalize word (remove punctuation, lowercase)
        run_word = re.sub(r'\W+', '', words[i]['word'].lower())
        
        # Skip empty words
        if len(run_word) < 1:
            i += 1
            continue
        
        start = i
        # Count consecutive repetitions
        while i + 1 < len(words) and re.sub(r'\W+', '', words[i+1]['word'].lower()) == run_word:
            i += 1
        end = i
        
        # Require at least 3 occurrences to reduce false positives (was 2)
        if end - start >= 2:  # at least 3 occurrences
            count = end - start + 1
            print(f"   Found potential repetition: '{run_word}' x{count} at {words[start]['start']:.1f}s")
            
            # SKIP repetitions at the very beginning (first 1.5 seconds) - usually just initial noise/startup
            if words[start]['start'] < 1.5:
                print(f"   ❌ Skipped: Too early ({words[start]['start']:.1f}s < 1.5s)")
                i += 1
                continue
            
            # For single-letter words: Only flag if it's "i" OR if there are 4+ repetitions (very obvious)
            # This filters random "a a" or "o o" but catches clear stutters like "t-t-t-t-t"
            if len(run_word) == 1:
                if run_word not in ['i'] and count < 4:
                    print(f"   ❌ Skipped: Single letter '{run_word}' needs 4+ reps, got {count}")
                    i += 1
                    continue
            
            print(f"   ✅ DETECTED: '{run_word}' repetition!")
            events.append({
                "type": "repetition",
                "word": run_word,
                "count": count,
                "start": words[start]['start'],
                "end": words[end]['end'],
                "confidence": 0.95
            })
        
        i += 1
    
    return events

# ----------------- ACOUSTIC REPETITION DETECTION -----------------
def detect_acoustic_repetitions(y, sr, words=None):
    """
    Detect sound repetitions using onset detection (catches "t-t-t-t" that Whisper misses)
    Now infers which sound is being repeated by looking at the next word.
    """
    events = []
    
    try:
        # Detect onsets (sudden increases in energy)
        onset_frames = librosa.onset.onset_detect(
            y=y, sr=sr,
            hop_length=512,
            backtrack=False,
            delta=ACOUSTIC_ONSET_THRESH
        )
        
        # Convert frames to time
        onset_times = librosa.frames_to_time(onset_frames, sr=sr, hop_length=512)
        
        if len(onset_times) < MIN_BURSTS_FOR_STUTTER:
            return events
        
        # Find clusters of onsets (rapid bursts)
        i = 0
        while i < len(onset_times):
            cluster_start = i
            burst_count = 1
            
            # Look for closely spaced onsets
            while i + 1 < len(onset_times):
                gap_ms = (onset_times[i + 1] - onset_times[i]) * 1000
                
                # If gap is within repetition range, it's part of the cluster
                if MIN_BURST_GAP_MS <= gap_ms <= MAX_BURST_GAP_MS:
                    burst_count += 1
                    i += 1
                else:
                    break
            
            cluster_end = i
            
            # If we found enough bursts, it's a repetition
            if burst_count >= MIN_BURSTS_FOR_STUTTER:
                start_time = float(onset_times[cluster_start])
                end_time = float(onset_times[cluster_end])
                
                event = {
                    "type": "acoustic_repetition",
                    "pattern": "rapid_bursts",
                    "count": burst_count,
                    "start": start_time,
                    "end": end_time,
                    "confidence": 0.80
                }
                
                # Infer the repeated sound by finding the next word
                if words:
                    # Find the word that starts closest to (and after) the cluster
                    next_word = None
                    min_gap = float('inf')
                    
                    for w in words:
                        # Look for words that start within 0.5s after the cluster ends
                        if w['start'] >= end_time and (w['start'] - end_time) < 0.5:
                            gap = w['start'] - end_time
                            if gap < min_gap:
                                min_gap = gap
                                next_word = w
                    
                    if next_word:
                        # Extract the first 1-2 letters as the likely repeated sound
                        word_text = next_word['word'].strip('.,!?;:\'"').lower()
                        
                        # For consonant clusters (like 'st', 'sl', 'tr'), take first 2
                        # Otherwise take first letter
                        consonant_clusters = ['st', 'sl', 'sp', 'sk', 'sc', 'tr', 'dr', 'br', 'cr', 'fr', 'gr', 'pr', 'th', 'sh', 'ch', 'wh']
                        
                        if len(word_text) >= 2 and word_text[:2] in consonant_clusters:
                            inferred_sound = word_text[:2]
                        else:
                            inferred_sound = word_text[0] if word_text else '?'
                        
                        event['inferred_sound'] = inferred_sound
                        event['target_word'] = next_word['word']
                        event['word'] = f"{inferred_sound}-{inferred_sound}-... ({next_word['word']})"
                    else:
                        event['word'] = "unknown sound"
                else:
                    event['word'] = "sound bursts"
                
                # SKIP acoustic repetitions at the very beginning (first 1.5 seconds) - usually just initial noise/mic activation
                if start_time >= 1.5:
                    events.append(event)
            
            i += 1
        
    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Acoustic repetition detection error: {e}{Colors.ENDC}")
    
    return events

# ----------------- PROLONGATION DETECTION -----------------
def detect_prolongations(y, sr, words):
    """Detect prolonged/elongated sounds using pitch tracking"""
    events = []

    try:
        # Use pyin for F0 (pitch) tracking to detect voiced segments
        f0, voiced_flag, voiced_probs = librosa.pyin(
            y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C7'),
            sr=sr, frame_length=1024, hop_length=256
        )

        frame_times = librosa.frames_to_time(
            np.arange(len(voiced_flag)), sr=sr, hop_length=256, n_fft=1024
        )
        
        # Calculate gaps between words to identify blocks
        # (to avoid flagging words after blocks as prolongations)
        gaps = []
        for i in range(1, len(words)):
            gap = words[i]['start'] - words[i-1]['end']
            if gap > 0.01:  # Only consider real gaps
                gaps.append(gap)
        
        # Calculate MEDIAN gap (more robust than mean, not affected by outliers)
        median_gap = np.median(gaps) if len(gaps) > 0 else 0.2

        for idx, w in enumerate(words):
            # Skip short words or ignored words
            word_dur_ms = (w['end'] - w['start']) * 1000
            if word_dur_ms < MIN_WORD_MS_FOR_PROLONG:
                continue
            
            # Normalize word (remove punctuation and whitespace, lowercase)
            word_clean = w['word'].strip().lower().strip('.,!?;:\'"')
            
            # Skip ignored words and contractions
            if word_clean in IGNORE_SHORT_WORDS or word_clean in IGNORE_CONTRACTIONS:
                continue
            
            # Skip if previous word was flagged as prolongation and this word is close to it
            # (Avoids catching words spoken slowly after a prolongation)
            if idx > 0:
                prev_word = words[idx-1]
                # Check if previous word was already flagged in events so far
                prev_prolonged = any(
                    e.get('type') == 'prolongation' and 
                    abs(e.get('start') - prev_word['start']) < 0.1 
                    for e in events
                )
                if prev_prolonged and (w['start'] - prev_word['end']) < 0.3:
                    continue
            
            # Skip if there's an abnormal gap before this word (likely a block, not prolongation)
            if idx > 0:
                gap_before = w['start'] - words[idx-1]['end']
                if gap_before > (median_gap * 2.0):  # If gap is 2x median, skip this word
                    continue
            
            # Skip if abnormally long AND has high voiced ratio (likely genuine prolongation, not a block-in-word)
            # But first check if it might be a real prolongation by looking at voiced content
            all_word_durations = [(words[i]['end'] - words[i]['start']) * 1000 for i in range(len(words))]
            median_word_dur = np.median(all_word_durations)
            
            # Only skip if it's VERY long (4x+) compared to median (those are likely blocks)
            # Prolongations are typically 2-3x, so don't skip those
            if word_dur_ms > (median_word_dur * 4.0):  # Word is 4x+ longer than median - likely a block
                continue

            # Find frames corresponding to this word
            s_frame = int(max(0, np.searchsorted(frame_times, w['start'])))
            e_frame = int(min(len(frame_times)-1, np.searchsorted(frame_times, w['end'])))
            
            if e_frame - s_frame < 1:
                continue

            # Also check RMS energy for this word segment
            start_sample = int(w['start'] * sr)
            end_sample = int(w['end'] * sr)
            word_segment = y[start_sample:min(end_sample, len(y))]
            
            # Calculate mean RMS energy for the word
            if len(word_segment) > 0:
                word_rms = librosa.feature.rms(y=word_segment, frame_length=1024, hop_length=256)[0]
                mean_rms = float(np.mean(word_rms))
            else:
                mean_rms = 0.0
            
            # Skip if energy is VERY low (means truly silent, not real voicing)
            # This catches cases where Whisper's timestamp includes silence before the word
            # Threshold is very low to accommodate quiet recordings
            if mean_rms < 0.001:  # Extremely low energy = truly silent
                continue

            sub_v = voiced_flag[s_frame:e_frame]

            # Find longest contiguous voiced segment
            max_run = run = 0
            for v in sub_v:
                if not np.isnan(v):
                    run += 1
                else:
                    max_run = max(max_run, run)
                    run = 0
            max_run = max(max_run, run)

            # Convert frames to milliseconds
            dur_ms = (max_run * 256.0 / sr) * 1000.0
            
            # Calculate ratio of voiced to total word duration
            voiced_ratio = dur_ms / word_dur_ms if word_dur_ms > 0 else 0

            # Skip if word is long but voiced content is NOT long
            # (This means Whisper included silence/pause in the word timestamp)
            # Example: Word is 1800ms but only 600ms is actually voiced = not a prolongation
            # UNLESS it has consistent RMS energy (consonant prolongation like "rrrr")
            if word_dur_ms > 1000 and dur_ms < 800:  # Long word but short actual voicing
                # Check if there's consistent RMS energy (for consonant prolongations)
                # Calculate percentage of frames with significant energy
                rms_frames = word_rms > (mean_rms * 0.3)  # Frames with at least 30% of mean energy
                energy_ratio = np.sum(rms_frames) / len(word_rms) if len(word_rms) > 0 else 0
                
                # If less than 50% of frames have energy, skip it
                if energy_ratio < 0.50:
                    continue
            
            # Also skip if word has no gap before it, is abnormally long, BUT doesn't have sustained voicing
            # (Whisper sometimes includes previous stutter/pause in the timestamp)
            # But if it HAS sustained voicing (high ratio), it's a real prolongation, so don't skip!
            if idx > 0:
                gap_before = w['start'] - words[idx-1]['end']
                if gap_before < 0.1 and word_dur_ms > (median_word_dur * 2.0):
                    # Only skip if voiced ratio is LOW (not a real prolongation)
                    if voiced_ratio < 0.70:
                        continue  # No gap + long word + low voicing = probably includes previous stutter

            # FIRST CHECK: Does this word contain a REPETITION pattern (like "r r r r really")?
            # Check ANY word that's longer than expected (>500ms) for repetition patterns
            is_actually_repetition = False
            repetition_count = 0
            if word_dur_ms > 500:  # Check any word that's abnormally long
                try:
                    # Detect onsets within this word segment
                    word_onsets = librosa.onset.onset_detect(
                        y=word_segment, sr=sr,
                        hop_length=256,
                        backtrack=False,
                        delta=0.08  # Moderate threshold
                    )
                    
                    # If there are 3+ distinct onsets with gaps, it's likely a repetition
                    if len(word_onsets) >= 3:
                        # Convert to times
                        onset_times = librosa.frames_to_time(word_onsets, sr=sr, hop_length=256)
                        
                        # Check if onsets are separated by gaps (not just continuous)
                        gaps_between_onsets = []
                        for i in range(1, len(onset_times)):
                            gap_ms = (onset_times[i] - onset_times[i-1]) * 1000
                            gaps_between_onsets.append(gap_ms)
                        
                        # If there are clear repetition gaps (90-240ms), it's a repetition
                        # This range avoids very fast syllables (<90ms) and very slow pauses (>240ms)
                        if len(gaps_between_onsets) >= 2:
                            # Count gaps in the typical repetition range
                            repetition_gaps = [g for g in gaps_between_onsets if 90 <= g <= 240]
                            # Need at LEAST 2 gaps in this range
                            if len(repetition_gaps) >= 2:
                                is_actually_repetition = True
                                repetition_count = len(onset_times)
                except:
                    pass
            
            # If it's a repetition pattern, flag it and skip prolongation checks
            if is_actually_repetition and repetition_count > 0:
                # SKIP repetitions at the very beginning (first 1.5 seconds) - usually just initial noise
                if w['start'] >= 1.5:
                    # Extract the first letter as the repeated sound
                    word_clean = w['word'].strip().lower().strip('.,!?;:\'"')
                    repeated_sound = word_clean[0] if word_clean else w['word'][0]
                    
                    events.append({
                        "type": "repetition",
                        "word": repeated_sound,
                        "pattern": f"{repeated_sound} (in '{w['word']}')",
                        "start": float(w['start']),
                        "end": float(w['end']),
                        "count": repetition_count,
                        "confidence": 0.90
                    })
                continue  # Skip prolongation checks for this word
            
            # SECOND CHECK: If NOT a repetition, check if it's a prolongation
            # 1. Voiced duration exceeds threshold AND voiced ratio is high (vowel prolongations like "soooo")
            # OR
            # 2. Word is long AND has consistent RMS energy (consonant prolongations like "rrrr")
            is_vowel_prolong = (dur_ms > PROLONG_MS and voiced_ratio > PROLONG_RATIO)
            
            # Check for consonant prolongation (consistent energy even if F0 doesn't detect voicing)
            is_consonant_prolong = False
            if word_dur_ms > 1000:  # Word is abnormally long
                # Calculate energy consistency
                rms_frames_with_energy = word_rms > (mean_rms * 0.3)
                energy_ratio = np.sum(rms_frames_with_energy) / len(word_rms) if len(word_rms) > 0 else 0
                # If >60% of frames have consistent energy, it's a consonant prolongation
                if energy_ratio > 0.60 and mean_rms > 0.002:
                    is_consonant_prolong = True
            
            # Flag as prolongation
            if is_vowel_prolong or is_consonant_prolong:
                # SKIP prolongations at the very beginning (first 1.5 seconds) - usually just initial noise/startup
                if w['start'] < 1.5:
                    continue
                
                events.append({
                    "type": "prolongation",
                    "word": w['word'],
                    "start": float(w['start']),
                    "end": float(w['end']),
                    "dur_ms": float(dur_ms),
                    "word_dur_ms": float(word_dur_ms),
                    "voiced_ratio": float(voiced_ratio),
                    "confidence": 0.85
                })

    except Exception as e:
        print(f"{Colors.YELLOW}Warning: Prolongation detection error: {e}{Colors.ENDC}")

    return events

# ----------------- BLOCK DETECTION -----------------
def detect_blocks(y, sr, words, repetitions=None, prolongations=None):
    """
    Detect blocks using relative gap analysis
    A block is when a gap between words is significantly larger than average
    """
    if repetitions is None:
        repetitions = []
    if prolongations is None:
        prolongations = []
    
    events = []
    
    if len(words) < 3:
        return events
    
    # Calculate all gaps between consecutive words
    gaps = []
    for i in range(1, len(words)):
        prev_end = words[i-1]['end']
        curr_start = words[i]['start']
        gap = curr_start - prev_end
        
        # Skip leading silence and unreasonably large gaps
        if curr_start > LEADING_SILENCE_IGNORE and gap > 0.01 and gap < 3.0:
            gaps.append({
                'duration': gap,
                'word_idx': i,
                'start_time': prev_end,
                'end_time': curr_start
            })
    
    # Only check gap-based blocks if we have enough gaps
    if len(gaps) >= 2:
        # ABSOLUTE THRESHOLD: Only flag gaps that are 1.5+ seconds (very obvious blocks)
        # This is MUCH stricter than before (was relative to median, now absolute)
        ABSOLUTE_BLOCK_THRESHOLD = 1.5  # seconds
        
        for gap_info in gaps:
            # Only flag if gap is 1.5+ seconds AND not at the beginning
            if gap_info['duration'] >= ABSOLUTE_BLOCK_THRESHOLD:
                word = words[gap_info['word_idx']]
                
                # SKIP blocks at the very beginning (first 1.5 seconds) - usually just initial silence
                if word['start'] < 1.5:
                    continue
                
                events.append({
                    "type": "block",
                    "word": word['word'],
                    "start": float(word['start']),
                    "end": float(word['end']),
                    "gap_duration": float(gap_info['duration']),
                    "confidence": 0.85
                })
    
    # Also check for abnormally long words (Whisper sometimes includes pauses within word timestamps)
    if len(words) >= 3:
        word_durations = [(w['end'] - w['start']) for w in words]
        median_word_dur = np.median(word_durations)
        
        for idx, w in enumerate(words):
            word_dur = w['end'] - w['start']
            
            # Skip if already flagged as a block
            already_flagged = any(e['word'] == w['word'] and abs(e['start'] - w['start']) < 0.1 for e in events)
            if already_flagged:
                continue
            
            # Skip if this word is part of a detected repetition
            in_repetition = any(rep['start'] <= w['start'] <= rep['end'] for rep in repetitions)
            if in_repetition:
                continue
            
            # Skip if this word is already detected as a prolongation
            in_prolongation = any(abs(prol['start'] - w['start']) < 0.1 for prol in prolongations)
            if in_prolongation:
                continue
            
            # DISABLED: This check causes too many false positives
            # Only enable if word is EXTREMELY long (5x+ median AND > 2 seconds absolute)
            if word_dur > (median_word_dur * 5.0) and word_dur > 2.0:
                # SKIP blocks at the very beginning (first 1.5 seconds) - usually just initial silence
                if w['start'] < 1.5:
                    continue
                
                events.append({
                    "type": "block",
                    "word": w['word'],
                    "start": float(w['start']),
                    "end": float(w['end']),
                    "gap_duration": float(word_dur),
                    "confidence": 0.70,
                    "note": "abnormally_long_word"
                })
    
    return events

# ----------------- MAIN DETECTION FUNCTION -----------------
def detect_all(audio_file, verbose=True):
    """Main function to detect all stutter types"""
    # Convert to WAV if needed
    audio_file = convert_to_wav(audio_file)
    
    # Transcribe
    words = transcribe_words(audio_file)
    
    # Load audio for acoustic analysis
    if verbose:
        print("Analyzing acoustic features...")
    y, sr = load_audio(audio_file)
    
    # Detect each type (order matters - prolongations before blocks!)
    reps = detect_repetitions(words)  # Word-level repetitions (from Whisper)
    prolongs = detect_prolongations(y, sr, words)  # Detect prolongations first
    acoustic_reps = detect_acoustic_repetitions(y, sr, words)  # Acoustic repetitions (sound bursts) - now infers the sound!
    
    # Filter out acoustic repetitions that overlap with prolongations
    # (Prolongations can create false acoustic repetition patterns)
    filtered_acoustic_reps = []
    for arep in acoustic_reps:
        overlaps_prolong = any(
            arep['start'] >= prol['start'] - 0.2 and arep['start'] <= prol['end'] + 0.2
            for prol in prolongs
        )
        if not overlaps_prolong:
            filtered_acoustic_reps.append(arep)
    
    blocks = detect_blocks(y, sr, words, reps, prolongs)  # Pass repetitions and prolongs to avoid double-flagging
    
    # Combine and sort by time
    events = sorted(reps + filtered_acoustic_reps + prolongs + blocks, key=lambda x: x.get("start", 0))
    
    return {"words": words, "events": events}

# ----------------- OUTPUT FORMATTING -----------------
def print_summary(results):
    """Print a nice summary of detection results"""
    events = results['events']
    words = results['words']
    
    # Count by type
    repetitions = [e for e in events if e['type'] == 'repetition']
    acoustic_repetitions = [e for e in events if e['type'] == 'acoustic_repetition']
    prolongations = [e for e in events if e['type'] == 'prolongation']
    blocks = [e for e in events if e['type'] == 'block']
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}STUTTER DETECTION SUMMARY{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")
    
    # Statistics
    print(f"{Colors.CYAN}Total words transcribed:{Colors.ENDC} {len(words)}")
    print(f"{Colors.CYAN}Total stutter events:{Colors.ENDC} {len(events)}")
    print(f"  {Colors.RED}• Word Repetitions:{Colors.ENDC} {len(repetitions)}")
    print(f"  {Colors.RED}• Sound Repetitions (acoustic):{Colors.ENDC} {len(acoustic_repetitions)}")
    print(f"  {Colors.YELLOW}• Prolongations:{Colors.ENDC} {len(prolongations)}")
    print(f"  {Colors.BLUE}• Blocks:{Colors.ENDC} {len(blocks)}")
    
    # Detailed events
    if events:
        print(f"\n{Colors.BOLD}Detected Events:{Colors.ENDC}")
        print(f"{'-'*60}")
        
        for e in events:
            if e['type'] == 'repetition':
                color = Colors.RED
                detail = f"(repeated {e['count']} times)"
                word_display = f"'{e['word']}'"
            elif e['type'] == 'acoustic_repetition':
                color = Colors.RED
                # Show the inferred sound if available
                if 'inferred_sound' in e and 'target_word' in e:
                    detail = f"({e['count']} bursts of '{e['inferred_sound']}' sound)"
                    word_display = f"'{e['inferred_sound']}-{e['inferred_sound']}-...' → '{e['target_word']}'"
                else:
                    detail = f"({e['count']} sound bursts - likely phoneme repetition)"
                    word_display = f"[{e.get('pattern', 'unknown')}]"
            elif e['type'] == 'prolongation':
                color = Colors.YELLOW
                ratio_str = f", {e['voiced_ratio']*100:.0f}% voiced" if 'voiced_ratio' in e else ""
                detail = f"({e['dur_ms']:.0f}ms{ratio_str})"
                word_display = f"'{e['word']}'"
            else:  # block
                color = Colors.BLUE
                ratio_str = f", {e.get('ratio', 0):.1f}x avg" if 'ratio' in e else ""
                detail = f"(gap: {e.get('gap_duration', 0):.2f}s{ratio_str})"
                word_display = f"'{e['word']}'"
            
            print(f"{color}[{e['type'].upper().replace('_', ' ')}]{Colors.ENDC} "
                  f"{e['start']:.2f}s - {e['end']:.2f}s | "
                  f"{word_display} {detail} "
                  f"(confidence: {e['confidence']:.0%})")
    else:
        print(f"\n{Colors.GREEN}✓ No stutters detected!{Colors.ENDC}")
    
    print(f"\n{Colors.BOLD}{Colors.HEADER}{'='*60}{Colors.ENDC}\n")

# ----------------- SCRIPT ENTRY -----------------
def main():
    if len(sys.argv) < 2:
        print(f"{Colors.BOLD}Usage:{Colors.ENDC} python3 stutter_detector.py <audio_file.wav|mp3> [--json]")
        print(f"\nOptions:")
        print(f"  --json    Output raw JSON instead of formatted summary")
        sys.exit(1)

    audio_file = sys.argv[1]
    json_output = "--json" in sys.argv
    
    if not os.path.exists(audio_file):
        print(f"{Colors.RED}Error: File not found: {audio_file}{Colors.ENDC}")
        sys.exit(1)
    
    print(f"\n{Colors.BOLD}Analyzing: {audio_file}{Colors.ENDC}\n")
    
    try:
        results = detect_all(audio_file)
        
        if json_output:
            print(json.dumps(results, indent=2))
        else:
            print_summary(results)
            
    except Exception as e:
        print(f"{Colors.RED}Error during analysis: {e}{Colors.ENDC}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()

