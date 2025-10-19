# 🎤 ReVoice Practice - Setup Guide

## What's Connected Now:

✅ **Record Button** → Saves audio as MP3  
✅ **Stutter Detection** → Analyzes your speech  
✅ **Practice Generation** → Creates custom exercises with Gemini AI  
✅ **Audio Playback** → Plays ElevenLabs practice audio  
✅ **Results Display** → Shows everything in the nice boxes your friend made!

---

## 🚀 How to Run:

### 1. **Start the Backend API** (Terminal 1)

```bash
cd /Users/tariquef/Documents/hacknight-2025-fall

# Make sure you're in your virtual environment
source revoice-env/bin/activate

# Install Flask if you haven't
pip3 install flask flask-cors

# Start the backend
python3 backend_api.py
```

You should see:
```
🚀 Starting ReVoice Practice Backend API...
📍 API will be available at: http://localhost:5000
```

### 2. **Start the Frontend** (Terminal 2)

```bash
cd /Users/tariquef/Documents/hacknight-2025-fall/revoice-frontend

# Install dependencies (only first time)
npm install

# Start React app
npm start
```

Browser should open automatically to `http://localhost:3000`

---

## 🎯 How to Use:

1. Click **"📚 Assistance / Practice"** button
2. Click **"🎤 Start Recording"**
3. Say something (try stuttering on purpose for testing!)
4. Click **"⏹ Stop Recording"**
5. Click **"🤖 Analyze My Speech"**
6. Wait a few seconds...
7. **See your results in the boxes!**
   - Analysis Summary
   - Stutter Types Detected
   - Specific Moments
   - **Personalized Practice** (with audio player!)

---

## 📦 What Happens Behind the Scenes:

1. **Recording** → Browser captures audio as WebM
2. **Backend API** → Converts WebM to MP3
3. **Stutter Detector** → Analyzes the MP3 (`detection-Files/stutter_detector.py`)
4. **Practice Generator** → Creates exercises with Gemini (`detection-Files/practice_generator.py`)
5. **Audio Generator** → Uses ElevenLabs to speak the exercises (`detection-Files/generate_audio.py`)
6. **Frontend** → Displays everything in the nice boxes and plays the audio!

---

## 📁 Output Files:

All generated files go to: `/detection-Files/outputFiles/`

- `practice_script_<word>.txt` - The practice script
- `practice_script_<word>_audio.mp3` - The ElevenLabs audio
- `recording.mp3` - Your recorded audio (in temp_uploads/)

---

## 🔧 Troubleshooting:

### "Analysis error: Failed to fetch"
- **Fix**: Make sure backend is running on port 5000
- Check Terminal 1 for errors

### "No Gemini API key found"
- **Fix**: Make sure `.env` file exists in `detection-Files/` with `GEMINI_API_KEY=your-key`

### "No ElevenLabs API key found"
- **Fix**: Add `ELEVENLABS_API_KEY=your-key` to the `.env` file

### Audio player doesn't show up
- **Fix**: Backend might have failed to generate audio. Check Terminal 1 for ElevenLabs errors.

---

## 🎨 Your Friend's Code:

**NOT CHANGED:**
- `Practice.css` - All her beautiful styling is untouched!
- `App.js` - Her main page is still the same
- `App.css` - All her animations and design
- Header, logo, waveform animations - All preserved!

**CHANGED:**
- `Practice.js` - Only the `analyzeAudio()` function and the results display
  - Removed mock data
  - Connected to real backend
  - Display real stutter detection results
  - Added audio player for practice exercises

---

## 🎉 You're All Set!

Now when you record, it will:
1. Detect REAL stutters using your Python scripts
2. Generate REAL practice exercises with Gemini
3. Play REAL audio from ElevenLabs
4. Look BEAUTIFUL with your friend's design!

Enjoy! 🚀

