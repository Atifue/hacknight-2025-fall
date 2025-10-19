#!/usr/bin/env python3
"""
Practice Generator - Uses Gemini AI to generate personalized stutter practice exercises
"""

import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# You'll need to install: pip3 install google-genai (newer SDK)
try:
    from google import genai
except ImportError:
    print("⚠️  Please install: pip3 install google-genai")
    sys.exit(1)

# Import our existing modules
try:
    from stutter_detector import detect_all
    from speech_therapy_tips import SpeechTherapyAdvisor, format_advice_for_display
except ImportError:
    print("⚠️  Make sure stutter_detector.py and speech_therapy_tips.py are in the same directory")
    sys.exit(1)


class PracticeGenerator:
    """Generates personalized practice exercises using Gemini AI"""
    
    def __init__(self, api_key=None):
        """
        Initialize with Gemini API key.
        If no key provided, looks for GEMINI_API_KEY environment variable.
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            print("\n❌ No Gemini API key found!")
            print("Add to your .env file: GEMINI_API_KEY=your-key-here")
            print("Or set environment variable: export GEMINI_API_KEY='your-key-here'")
            print("Get a key at: https://makersuite.google.com/app/apikey")
            sys.exit(1)
        
        # Initialize Gemini client (newer SDK pattern)
        self.client = genai.Client(api_key=self.api_key)
        self.model_name = 'gemini-2.5-flash'  # Fast and efficient
    
    def generate_practice_exercises(self, stutter_info: dict) -> dict:
        """
        Generate personalized practice exercises for a specific stutter
        
        Args:
            stutter_info: Dict with 'word', 'sound', 'type', 'advice'
        
        Returns:
            Dict with practice exercises
        """
        word = stutter_info.get('word', '')
        sound = stutter_info.get('sound', '')
        stutter_type = stutter_info.get('type', '')
        advice = stutter_info.get('advice', '')
        
        # Create prompt for Gemini
        prompt = self._create_practice_prompt(word, sound, stutter_type, advice)
        
        try:
            # Use newer SDK pattern
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[{"role": "user", "parts": [{"text": prompt}]}]
            )
            exercises = self._parse_gemini_response(response.text)
            return exercises
        except Exception as e:
            print(f"⚠️  Gemini API error: {e}")
            return self._fallback_exercises(word, sound, stutter_type)
    
    def _create_practice_prompt(self, word: str, sound: str, stutter_type: str, advice: str) -> str:
        """Create a conversational script prompt for Gemini"""
        
        # Build stutter-type specific exercises
        if stutter_type.lower() in ['repetition', 'acoustic_repetition']:
            technique_instructions = f"""
TECHNIQUE: CONTINUOUS PHONATION (Replace Repetition with Smooth Stretch)
Goal: Transform "b-b-b-ball" into "buhhhhh...ball"
- Hold the sound continuously (not repeat it)
- Very gentle articulatory contact
- Smooth, flowing transitions

STRUCTURE (15 seconds max):
1. Sound alone: Hold smooth and steady for 2 seconds (phonetic!)
2. Sound+vowels: Stretch each combo, gentle blending
3. Word: First stretched, then normal pace
4. One phrase: Smooth, connected words (with periods between)

Example for "B" repetition (b-b-ball):
"buhhhhh ..... buhhhhh.

baaaaahhh ..... behhhh ..... bohhhhh.

baaaaaall ..... ball.

Big. ball. The. ball. bounces."

Example for "C" repetition (c-c-can):
"kuhhhhh ..... kuhhhhh.

kaaahhh ..... kehhh ..... kohhh.

kaaaaan ..... can.

I. can. You. can."
"""
        elif stutter_type.lower() == 'prolongation':
            technique_instructions = f"""
TECHNIQUE: SOFT CONTACT with QUICK RELEASE (Fix Prolongations)
Goal: Transform "ssssssnake" into gentle "sss-nake"
- Start the sound softly (no tension)
- Keep it brief and immediately move to next sound
- Minimal air pressure

STRUCTURE (15 seconds max):
1. Sound: Start gentle, keep brief (use ^ for soft start)
2. Quick blends: Sound + next letter, rapid transition
3. Word: Soft start, immediate flow through word
4. One phrase: Gentle beginnings, quick movements

Example for "S" prolongation (ssssnake):
"^sss ..... sss.

s-nake ..... s-nake.

snake ..... snake.

Big. snake. Snakes. move. fast."

Example for "F" prolongation (ffffar):
"^fff ..... fff.

f-ar ..... f-ar.

far ..... far.

Very. far. The. farm."
"""
        elif stutter_type.lower() == 'block':
            technique_instructions = f"""
TECHNIQUE: PRE-PHONATORY AIRFLOW (Break Through Blocks)
Goal: Get air moving BEFORE trying to say the sound
- Start with "h" breath or "mmm" hum
- Let air flow first, then add the sound
- Gentle, breathy beginning

STRUCTURE (15 seconds max):
1. Airflow + sound: "hhh-{sound}" or "mmm-{sound}"
2. Airflow + word: "hhh-{word}" (breath leads into word)
3. Word: Gentle, breathy start
4. One phrase: Each word starts with gentle airflow

Example for "B" block (....ball):
"hhh-buh ..... mmm-buh.

h-ball ..... mmm-ball.

ball ..... ball.

Big. ball. Throw. the. ball."

Example for "C" block (....can):
"hhh-kuh ..... mmm-kuh.

h-can ..... mmm-can.

can ..... can.

I. can. We. can."
"""
        else:
            # Fallback for unknown types
            technique_instructions = f"""
STRUCTURE (under 15 seconds):
1. Isolated sound 2 times: PHONETIC spelling
2. Sound + vowels: 3 combinations
3. Target word 2 times
4. Two short phrases
"""
        
        prompt = f"""You are a speech therapist. Create a BRIEF practice recording for the "{sound}" sound in "{word}".

Stutter type: {stutter_type}

PHONETIC RULES (critical for TTS):
- Consonants: Use natural syllables with "uh" vowel
  • P → "puh", B → "buh", T → "tuh", D → "duh"
  • K/C → "kuh", G → "guh", M → "muh", N → "nuh"
  • F → "fuh", V → "vuh", S → "sss" (prolonged hiss), Z → "zzz"
  • TH → "thuh", SH → "shuh", CH → "chuh"
  • L → "luh", R → "ruh", W → "wuh", Y → "yuh"
- Vowels: Use actual vowel sounds
  • A → "ahh", E → "ehh", I → "ihh", O → "ohh", U → "uhh"
- NEVER use single letters or underscores
- Stretch sounds naturally with repetition (sss not s_s_s)

PACING RULES:
- Add periods after EVERY word in phrases: "Big. red. ball."
- Use "..." for 1-second pause between items
- Blank line for 2-second pause between sections
- Keep total under 15 seconds

{technique_instructions}

IMPORTANT: Output ONLY the practice script. Do NOT include:
- "Here's your script" or similar introductions
- Explanations, headings, or meta-text
- "Now you try" or encouragement
- Any text that isn't part of the spoken exercise

Start directly with the practice sounds and words:"""
        
        return prompt
    
    def _parse_gemini_response(self, response_text: str) -> dict:
        """Parse Gemini's response into structured exercises"""
        
        exercises = {
            'level_1': '',
            'level_2': [],
            'level_3': [],
            'level_4': []
        }
        
        # Simple parsing - split by levels
        lines = response_text.strip().split('\n')
        current_level = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Detect level headers
            if 'Level 1' in line or '**Level 1' in line:
                current_level = 'level_1'
            elif 'Level 2' in line or '**Level 2' in line:
                current_level = 'level_2'
            elif 'Level 3' in line or '**Level 3' in line:
                current_level = 'level_3'
            elif 'Level 4' in line or '**Level 4' in line:
                current_level = 'level_4'
            elif current_level:
                # Skip "Slowly try this:" lines
                if 'Slowly try this' in line:
                    continue
                # Add content to current level
                if current_level == 'level_1':
                    if exercises['level_1']:
                        exercises['level_1'] += '\n' + line
                    else:
                        exercises['level_1'] = line
                else:
                    # Remove bullet points and clean up
                    clean_line = line.lstrip('*-• ').strip()
                    if clean_line:
                        exercises[current_level].append(clean_line)
        
        return {
            'exercises': exercises,
            'raw_response': response_text
        }
    
    def _fallback_exercises(self, word: str, sound: str, stutter_type: str) -> dict:
        """Fallback exercises if Gemini API fails"""
        return {
            'exercises': {
                'level_1': f'Practice the "{sound}" sound by itself 10 times slowly and gently.',
                'level_2': [
                    f'{sound}a',
                    f'{sound}e',
                    f'{sound}i',
                    f'{sound}o'
                ],
                'level_3': [
                    word,
                    f'{word} today',
                    f'I say {word}',
                    f'I can say {word} clearly'
                ],
                'level_4': [
                    f'Try saying words starting with "{sound}"',
                    f'Practice {word} in different sentences',
                    'Keep breathing and stay relaxed'
                ]
            },
            'raw_response': 'Fallback exercises (Gemini unavailable)'
        }


def format_practice_exercises(exercises_data: dict, word: str, sound: str, stutter_type: str) -> str:
    """Format practice exercises for display"""
    exercises = exercises_data.get('exercises', {})
    
    output = []
    output.append("\n" + "="*70)
    output.append("🎯 AI-GENERATED PRACTICE EXERCISES")
    output.append("="*70)
    output.append(f"\nFor: '{word}' | Sound: [{sound}] | Type: {stutter_type.replace('_', ' ').title()}")
    output.append("")
    
    # Level 1
    if exercises.get('level_1'):
        output.append("📍 **Level 1: Sound Isolation**")
        output.append("Slowly try this:")
        output.append(f"  {exercises['level_1']}")
        output.append("")
    
    # Level 2
    if exercises.get('level_2'):
        output.append("📍 **Level 2: Syllable Building**")
        output.append("Slowly try this:")
        for item in exercises['level_2']:
            output.append(f"  • {item}")
        output.append("")
    
    # Level 3
    if exercises.get('level_3'):
        output.append("📍 **Level 3: Progressive Phrases**")
        output.append("Slowly try this:")
        for item in exercises['level_3']:
            output.append(f"  • {item}")
        output.append("")
    
    # Level 4
    if exercises.get('level_4'):
        output.append("📍 **Level 4: Tongue Twisters**")
        output.append("Slowly try this:")
        for item in exercises['level_4']:
            output.append(f"  • {item}")
        output.append("")
    
    output.append("💡 Tip: Practice 5-10 minutes daily. Start with Level 1 until comfortable.")
    output.append("="*70)
    
    return '\n'.join(output)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 practice_generator.py <audio_file>")
        print("\nExample: python3 practice_generator.py myaudio.mp3")
        print("\nMake sure GEMINI_API_KEY is in your .env file!")
        sys.exit(1)
    
    audio_file = sys.argv[1]
    
    if not Path(audio_file).exists():
        print(f"❌ Error: File not found: {audio_file}")
        sys.exit(1)
    
    print(f"\n🎙️  Analyzing {audio_file}...")
    
    # Step 1: Detect stutters
    print("Step 1: Detecting stutters...")
    results = detect_all(audio_file, verbose=False)
    
    if not results['events']:
        print("\n✅ No stutters detected - no practice exercises needed!")
        return
    
    # Step 2: Generate therapy advice
    print("Step 2: Generating therapy advice...")
    advisor = SpeechTherapyAdvisor()
    advice = advisor.generate_advice(results)
    
    # Print basic advice
    print("\n" + format_advice_for_display(advice))
    
    # Step 3: Generate AI-powered practice exercises
    print("\n" + "="*70)
    print("Step 3: Generating AI-powered practice exercises with Gemini...")
    print("="*70)
    
    generator = PracticeGenerator()
    
    # Generate exercises for each stuttered moment
    word_guidance = advice.get('word_specific_guidance', [])
    
    for guidance in word_guidance[:3]:  # Top 3 stuttered words
        word = guidance.get('word', '')
        sound = guidance.get('problem_sound', '')
        stutter_type = guidance.get('stutter_type', '')
        
        print(f"\n🤖 Asking Gemini AI to create exercises for '{word}'...")
        
        stutter_info = {
            'word': word,
            'sound': sound,
            'type': stutter_type,
            'advice': guidance.get('sound_details', {})
        }
        
        exercises = generator.generate_practice_exercises(stutter_info)
        
        # Display the conversational script
        script = exercises.get('raw_response', '')
        print("\n" + "="*70)
        print("🎙️  CONVERSATIONAL PRACTICE SCRIPT")
        print("="*70)
        print(script)
        print("="*70)
        
        # Save as text file for ElevenLabs
        # Create outputFiles directory if it doesn't exist
        os.makedirs("outputFiles", exist_ok=True)
        script_file = f"outputFiles/practice_script_{word}.txt"
        with open(script_file, 'w') as f:
            f.write(script)
        
        print(f"\n💾 Saved script to: {script_file}")
        print(f"\n🎤 Ready for ElevenLabs! Use: {script_file}")


if __name__ == '__main__':
    main()

