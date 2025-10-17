import requests
import os
from dotenv import load_dotenv

class VoiceCloner:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.elevenlabs.io/v1"
    
    def clone_voice(self, audio_file_path, voice_name):
        
        print(f"🎤 Cloning voice from: {audio_file_path}")
        print(f"📝 Voice name: {voice_name}")
        
        url = f"{self.base_url}/voices/add"
        
        headers = {
            "xi-api-key": self.api_key
        }
        
        # Check if file exists
        if not os.path.exists(audio_file_path):
            print(f"❌ ERROR: File not found: {audio_file_path}")
            return None
        
        # Open the audio file
        with open(audio_file_path, 'rb') as audio_file:
            files = {
                'files': audio_file
            }
            
            data = {
                'name': voice_name,
                'description': 'ReVoice user voice clone'
            }
            
            print("⏳ Sending to ElevenLabs...")
            response = requests.post(url, headers=headers, files=files, data=data)
        
        # Check if successful
        if response.status_code == 200:
            voice_id = response.json()['voice_id']
            print(f"✅ SUCCESS! Voice cloned!")
            print(f"🎯 Voice ID: {voice_id}")
            print(f"\n💾 SAVE THIS ID - Your team needs it for speech generation!")
            return voice_id
        else:
            print(f"❌ ERROR: {response.status_code}")
            print(f"Response: {response.text}")
            return None
    
    def list_voices(self):
        """List all your cloned voices"""
        url = f"{self.base_url}/voices"
        headers = {"xi-api-key": self.api_key}
        
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            voices = response.json()['voices']
            print(f"\n📋 You have {len(voices)} voice(s):")
            for voice in voices:
                print(f"  - {voice['name']}: {voice['voice_id']}")
            return voices
        else:
            print(f"❌ Error listing voices: {response.status_code}")
            return []
    
    def delete_voice(self, voice_id):
        """Delete a cloned voice"""
        url = f"{self.base_url}/voices/{voice_id}"
        headers = {"xi-api-key": self.api_key}
        
        response = requests.delete(url, headers=headers)
        
        if response.status_code == 200:
            print(f"✅ Voice {voice_id} deleted successfully")
            return True
        else:
            print(f"❌ Error deleting voice: {response.status_code}")
            return False


# Main execution
if __name__ == "__main__":
    # Load environment variables from .env file
    load_dotenv()
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    
    # Check if API key exists
    if not ELEVENLABS_API_KEY:
        print("❌ ERROR: ELEVENLABS_API_KEY not found in .env file!")
        print("Make sure you have a .env file with:")
        print("ELEVENLABS_API_KEY=your_api_key_here")
        exit()
    
    cloner = VoiceCloner(ELEVENLABS_API_KEY)
    
    # Test: List existing voices
    print("=" * 50)
    print("Checking existing voices...")
    print("=" * 50)
    cloner.list_voices()
    
    print("\n" + "=" * 50)
    print("Ready to clone voices!")
    print("=" * 50)
    print("\nWhen you get the audio file from your teammate:")
    print("1. Put it in this same folder")
    print("2. Update the line below with the correct filename")
    print("3. Run this script again")
    print("\nExample usage:")
    print('voice_id = cloner.clone_voice("user_audio.mp3", "ReVoiceUser1")')
    print("=" * 50)
    
    # Clone the voice from trimm.mp3
    voice_id = cloner.clone_voice("trimm.mp3", "TestVoice1")