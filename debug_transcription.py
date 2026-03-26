import speech_recognition as sr
import os
import wave
import audioop
import tempfile
import sys

print("--- DEBUG TRANSCRIPTION START ---")

def convert_to_mono(filepath):
    print(f"Checking mono status for: {filepath}")
    try:
        with wave.open(filepath, 'rb') as wav_in:
            channels = wav_in.getnchannels()
            if channels == 1:
                print("Already mono.")
                return filepath
            
            print(f"Converting {channels} channels to mono...")
            sample_width = wav_in.getsampwidth()
            framerate = wav_in.getframerate()
            frames = wav_in.readframes(wav_in.getnframes())
            frames = audioop.tomono(frames, sample_width, 1, 1)

        temp_fd, temp_path = tempfile.mkstemp(suffix='.wav')
        with os.fdopen(temp_fd, 'wb') as f:
            with wave.open(f, 'wb') as wav_out:
                wav_out.setnchannels(1)
                wav_out.setsampwidth(sample_width)
                wav_out.setframerate(framerate)
                wav_out.writeframes(frames)
        print(f"Mono conversion done: {temp_path}")
        return temp_path
    except Exception as e:
        print(f"Mono conversion error: {e}")
        return filepath

def test_transcription(filename, language='en-US'):
    filepath = os.path.join('uploads', filename)
    print(f"Looking for file: {filepath}")
    if not os.path.exists(filepath):
        print(f"File not found: {filepath}")
        return

    filepath = convert_to_mono(filepath)
    recognizer = sr.Recognizer()
    try:
        print("Opening AudioFile...")
        with sr.AudioFile(filepath) as source:
            duration = getattr(source, 'DURATION', 0)
            print(f"Duration: {duration:.2f}s")
            
            chunk_duration = 45
            if duration > chunk_duration:
                print(f"Processing in chunks of {chunk_duration}s...")
                text_list = []
                offset = 0
                idx = 1
                while offset < duration:
                    print(f"Recording chunk {idx} (offset {offset})...")
                    audio_data = recognizer.record(source, duration=chunk_duration)
                    if not audio_data.frame_data:
                        break
                    try:
                        print(f"Recognizing chunk {idx}...")
                        chunk_text = recognizer.recognize_google(audio_data, language=language)
                        text_list.append(chunk_text)
                        print(f"Chunk {idx} done: {chunk_text[:30]}...")
                    except sr.UnknownValueError:
                        print(f"Chunk {idx} unrecognizible.")
                    except sr.RequestError as e:
                        print(f"API Request error for chunk {idx}: {e}")
                    offset += chunk_duration
                    idx += 1
                print("\n--- FINAL RESULT ---")
                print(" ".join(text_list))
            else:
                print("Processing in one go...")
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=language)
                print("\n--- FINAL RESULT ---")
                print(text)
    except Exception as e:
        print(f"Critical Transcription Error: {e}")

if __name__ == "__main__":
    fname = sys.argv[1] if len(sys.argv) > 1 else 'audio.wav'
    test_transcription(fname)
