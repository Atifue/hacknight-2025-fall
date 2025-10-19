#!/usr/bin/env python3
"""
⚠️⚠️⚠️ NOTE: THIS FILE IS NOT ACTIVELY USED - IT'S SITTING IDLE ⚠️⚠️⚠️

All stutter detection functionality has been MERGED into server.py
This file is kept as a BACKUP/REFERENCE ONLY.

❌ DO NOT RUN THIS FILE - Use server.py instead!
❌ This is NOT part of the active server

---

Backend API for ReVoice Practice
Connects the React frontend with stutter detection and practice generation
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from pydub import AudioSegment
import os
import sys
import json
from pathlib import Path

# Add detection-Files to path
sys.path.append(str(Path(__file__).parent / 'detection-Files'))

from stutter_detector import detect_all
from practice_generator import PracticeGenerator
from generate_audio import generate_practice_audio
from speech_therapy_tips import SpeechTherapyAdvisor

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend

# Create temp directories
UPLOAD_FOLDER = 'temp_uploads'
OUTPUT_FOLDER = 'detection-Files/outputFiles'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

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
                files = glob.glob(os.path.join(OUTPUT_FOLDER, pattern))
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
        import time
        import hashlib
        file_size = os.path.getsize(mp3_path)
        # Create unique hash of file content to verify it's actually different
        with open(mp3_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        print(f"📊 Processing: {mp3_path} ({file_size} bytes) Hash: {file_hash} at {time.strftime('%H:%M:%S')}")
        
        # Run stutter detection
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
            script_path = os.path.join(OUTPUT_FOLDER, script_filename)
            with open(script_path, 'w') as f:
                f.write(script)
            
            # Generate audio
            print("Generating practice audio...")
            audio_filename = f"practice_script_{word}_audio.mp3"
            audio_path = os.path.join(OUTPUT_FOLDER, audio_filename)
            
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
        audio_path = os.path.join(OUTPUT_FOLDER, filename)
        if os.path.exists(audio_path):
            return send_file(audio_path, mimetype='audio/mpeg')
        else:
            return jsonify({'error': 'Audio file not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def _create_summary(detection_results):
    """Create a human-readable summary of detection results"""
    events = detection_results.get('events', [])
    
    if not events:
        return {
            'total_stutters': 0,
            'message': 'No stutters detected! Great fluent speech!',
            'stutter_types': {}
        }
    
    # Count by type
    stutter_types = {}
    for event in events:
        stype = event['type']
        stutter_types[stype] = stutter_types.get(stype, 0) + 1
    
    # Format types
    type_descriptions = {
        'repetition': 'Sound/word repetitions',
        'prolongation': 'Sound prolongations',
        'block': 'Speech blocks',
        'acoustic_repetition': 'Rapid sound repetitions'
    }
    
    formatted_types = {
        type_descriptions.get(k, k): v 
        for k, v in stutter_types.items()
    }
    
    return {
        'total_stutters': len(events),
        'message': f"Detected {len(events)} stutter event(s)",
        'stutter_types': formatted_types,
        'events_detail': [
            {
                'type': e['type'],
                'word': e.get('word', ''),
                'time': f"{e['start']:.1f}s",
                'confidence': f"{e.get('confidence', 0) * 100:.0f}%"
            }
            for e in events[:5]  # Show first 5
        ]
    }


if __name__ == '__main__':
    print("❌ ERROR: backend_api.py is NOT the active server!")
    print("❌ This file is IDLE and should not be run.")
    print("✅ Please run server.py instead:")
    print("   python3 server.py")
    print("\n⚠️  Exiting to prevent conflicts...")
    exit(1)
    
    # OLD CODE (commented out - DO NOT USE):
    # print("🚀 Starting ReVoice Practice Backend API...")
    # print("📍 API will be available at: http://localhost:5001")
    # print("📁 Output files will be saved to: detection-Files/outputFiles/")
    # app.run(host='0.0.0.0', debug=True, port=5001)

