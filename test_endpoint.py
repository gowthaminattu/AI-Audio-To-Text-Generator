import requests
import os

url = "http://127.0.0.1:5000/transcribe"
filepath = "uploads/recorded_audio.wav"

if not os.path.exists(filepath):
    # Try a smaller one first if recorded_audio doesn't exist
    filepath = "uploads/voice.wav"

print(f"Testing transcription for {filepath}...")
with open(filepath, 'rb') as f:
    files = {'audio_file': f}
    data = {'language': 'en-US'}
    try:
        r = requests.post(url, files=files, data=data)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
    except Exception as e:
        print(f"Error: {e}")
