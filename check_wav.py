import wave
import sys
import os

for f in os.listdir('uploads'):
    if f.endswith('.wav'):
        path = os.path.join('uploads', f)
        try:
            with wave.open(path, 'rb') as w:
                print(f"{f}: channels={w.getnchannels()}, rate={w.getframerate()}, width={w.getsampwidth()}, frames={w.getnframes()}")
        except Exception as e:
            print(f"{f}: error {e}")
