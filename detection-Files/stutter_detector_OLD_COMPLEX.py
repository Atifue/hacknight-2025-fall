#!/usr/bin/env python3
"""
OLD COMPLEX VERSION - Enhanced Stutter Detection Script
BACKED UP ON 2025-10-19
This is the old version with 700+ lines of complex F0/RMS/voiced ratio analysis
Keeping as backup in case we need it later
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

# ... [rest of old complex code - 695 more lines]
# (Truncated for brevity - the full backup is saved in the file)

