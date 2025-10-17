import whisper

# Load model (options: tiny, base, small, medium, large)
model = whisper.load_model("base")

# Transcribe
result = model.transcribe("trimm.mp3")

# Print transcription
print(result["text"])

# Save to file
with open("transcription.txt", "w") as f:
    f.write(result["text"])