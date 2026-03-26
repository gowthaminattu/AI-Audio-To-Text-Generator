import speech_recognition as sr
import sys

filename = sys.argv[1]
try:
    print(f"Reading {filename}...")
    r = sr.Recognizer()
    with sr.AudioFile(filename) as source:
        audio = r.record(source)
    print(f"Length: {len(audio.frame_data)} bytes, rate={audio.sample_rate}, width={audio.sample_width}")
    print("Calling recognize_google...")
    text = r.recognize_google(audio)
    print(f"Success: {text}")
except Exception as e:
    print(f"Error: {e}")
