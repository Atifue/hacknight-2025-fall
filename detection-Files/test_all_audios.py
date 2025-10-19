#!/usr/bin/env python3
"""
Automated testing script for stutter detection
Tests all audio files and reports results
"""

import sys
import os
from stutter_detector import detect_all

# Test cases: (filename, expected_stutters)
TEST_CASES = [
    ("farsianaTestStutter/elongation.mp3", ["prolongation: snake"]),
    ("farsianaTestStutter/elongSo.mp3", ["prolongation: so"]),
    ("farsianaTestStutter/repeatCan.mp3", ["repetition: can x4"]),
    ("farsianaTestStutter/repeatingReally.mp3", ["acoustic_repetition: r-r-r-r"]),
    ("farsianaTestStutter/blocks.mp3", ["block: between very and pretty"]),
]

print("="*70)
print("STUTTER DETECTION TEST SUITE")
print("="*70)

for audio_file, expected in TEST_CASES:
    print(f"\n\n{'='*70}")
    print(f"Testing: {audio_file}")
    print(f"Expected: {', '.join(expected)}")
    print(f"{'='*70}")
    
    try:
        results = detect_all(audio_file, verbose=True)
        events = results.get('events', [])
        
        print(f"\n✅ FOUND {len(events)} stutter(s):")
        for e in events:
            print(f"   • {e['type']}: '{e.get('word', 'unknown')}' at {e['start']:.1f}s")
        
    except FileNotFoundError:
        print(f"❌ File not found: {audio_file}")
    except Exception as e:
        print(f"❌ Error: {e}")

print(f"\n\n{'='*70}")
print("TEST SUITE COMPLETE")
print(f"{'='*70}")

