#!/usr/bin/env python3
"""
Generate audio from practice scripts using ElevenLabs
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    print("⚠️  Please install: pip3 install elevenlabs")
    sys.exit(1)

def generate_practice_audio(script_file, output_file=None):
    """Generate audio from a practice script"""
    
    # Set API key (check both naming conventions)
    api_key = os.getenv('ELEVEN_LABS_API_KEY') or os.getenv('ELEVENLABS_API_KEY')
    if not api_key:
        print("❌ No ElevenLabs API key found!")
        print("Add to .env: ELEVEN_LABS_API_KEY=your-key-here")
        print("Get a key at: https://elevenlabs.io/")
        return
    
    # Initialize ElevenLabs client
    client = ElevenLabs(api_key=api_key)
    
    # Read script
    with open(script_file, 'r') as f:
        script = f.read()
    
    print(f"📖 Reading script: {script_file}")
    print(f"📝 Script length: {len(script)} characters")
    
    # Output file
    if not output_file:
        base_name = Path(script_file).stem
        # Create outputFiles directory if it doesn't exist
        os.makedirs("outputFiles", exist_ok=True)
        output_file = f"outputFiles/{base_name}_audio.mp3"
    
    print(f"\n🎙️  Generating audio with ElevenLabs...")
    print("Voice: Rachel (calm, instructive)")
    
    try:
        # Generate audio using the newer SDK
        #try kurt itjA83RExdsQkFbXkihc
        audio = client.text_to_speech.convert(
            voice_id="itjA83RExdsQkFbXkihc",  # kurt 
            text=script,
            model_id="eleven_multilingual_v2",
            voice_settings={
                "stability": 0.7,        # Higher = more stable/consistent
                "similarity_boost": 0.7, # Voice clarity
                "style": 0.0,            # Lower = more neutral/calm
                "use_speaker_boost": True,
                "speed": 0.7     # Much slower - half speed for child practice
            }
        )
        
        # Save audio to file
        with open(output_file, 'wb') as f:
            for chunk in audio:
                f.write(chunk)
        
        print(f"\n✅ Audio generated successfully!")
        print(f"💾 Saved to: {output_file}")
        print(f"\n🎧 Play it: open {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error generating audio: {e}")
        print("\nTroubleshooting:")
        print("- Check your API key is valid")
        print("- Check you have credits remaining")
        print("- Try a shorter script (ElevenLabs has character limits)")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 generate_audio.py <script_file>")
        print("\nExample: python3 generate_audio.py practice_script_can.txt")
        sys.exit(1)
    
    script_file = sys.argv[1]
    
    if not Path(script_file).exists():
        print(f"❌ File not found: {script_file}")
        sys.exit(1)
    
    # Optional output file
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    generate_practice_audio(script_file, output_file)

if __name__ == '__main__':
    main()

