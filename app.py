from flask import Flask, render_template, request, redirect, url_for, jsonify, send_file
import os
import speech_recognition as sr
from fpdf import FPDF
import tempfile

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

@app.route('/')
def login():
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def do_login():
    username = request.form.get('username')
    password = request.form.get('password')
    if username and password:
        return redirect(url_for('home'))
    return redirect(url_for('login'))

@app.route('/home')
def home():
    return render_template('index.html')

import wave
import audioop

def convert_to_mono(filepath):
    print(f"Checking mono status for: {filepath}")
    try:
        with wave.open(filepath, 'rb') as wav_in:
            channels = wav_in.getnchannels()
            if channels == 1:
                print("Already mono.")
                return filepath # Already mono
            
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
        print(f"Successfully converted to mono: {temp_path}")
        return temp_path
    except Exception as e:
        print(f"Mono conversion error: {e}")
        # If any wave module error occurs, return original and let SpeechRecognition handle it
        return filepath

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio_file' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    file = request.files['audio_file']
    language = request.form.get('language', 'en-US')
    
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    
    filepath = convert_to_mono(filepath)
    
    recognizer = sr.Recognizer()
    try:
        logging_file = "transcription_debug.log"
        def log_msg(msg):
            with open(logging_file, "a") as f:
                f.write(f"{msg}\n")
            print(msg)

        log_msg(f"Processing audio file: {filepath} with language: {language}")
        with sr.AudioFile(filepath) as source:
            # Better way to get duration if source.DURATION is missing
            audio_duration = getattr(source, 'DURATION', 0)
            if audio_duration == 0:
                # Approximate duration: frame_count / frame_rate
                audio_duration = source.FRAME_COUNT / source.SAMPLE_RATE
            
            log_msg(f"Audio duration: {audio_duration:.2f} seconds")
            
            # Google Speech API synchronous requests limit is approx 1 minute.
            # We chunk the audio into 45-second segments to avoid "Bad Request".
            chunk_duration = 45
            
            if audio_duration > chunk_duration:
                log_msg(f"File is large, processing in chunks of {chunk_duration}s...")
                text_list = []
                offset = 0
                chunk_index = 1
                while offset < audio_duration:
                    log_msg(f"Transcribing chunk {chunk_index} (offset: {offset})...")
                    audio_data = recognizer.record(source, duration=chunk_duration)
                    if not audio_data.frame_data:
                        log_msg(f"Chunk {chunk_index} is empty, breaking.")
                        break
                    try:
                        chunk_text = recognizer.recognize_google(audio_data, language=language)
                        text_list.append(chunk_text)
                        log_msg(f"Chunk {chunk_index} success: {chunk_text[:30]}...")
                    except sr.UnknownValueError:
                        log_msg(f"Chunk {chunk_index} was unintelligible.")
                        pass # Ignore unintelligible chunks
                    except Exception as e:
                        log_msg(f"Chunk {chunk_index} error: {str(e)}")
                        
                    offset += chunk_duration
                    chunk_index += 1
                
                if not text_list:
                    log_msg("No chunks were successfully transcribed.")
                    return jsonify({'error': 'Audio not clearly understood. Please try again or check the audio quality.'}), 400
                    
                text = " ".join(text_list)
                log_msg(f"All chunks processed successfully. Total length: {len(text)} chars.")
                return jsonify({'text': text})
            else:
                log_msg("Small file, transcribing in one go...")
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=language)
                log_msg("Transcription success.")
                return jsonify({'text': text})
                
    except sr.UnknownValueError:
        log_msg("Audio not clearly understood.")
        return jsonify({'error': 'Audio not clearly understood. Please try again or speak more clearly.'}), 400
    except sr.RequestError as e:
        log_msg(f"Google Speech API Request error: {e}")
        return jsonify({'error': f'Could not request results from Google Speech API; {e}'}), 500
    except Exception as e:
        log_msg(f"General transcription error: {str(e)}")
        return jsonify({'error': f'Error processing audio file: {str(e)}\n\n(Make sure you uploaded a valid WAV format)'}), 500

@app.route('/download/txt', methods=['POST'])
def download_txt():
    text = request.form.get('text', '')
    fd, path = tempfile.mkstemp(suffix='.txt')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(text)
    return send_file(path, as_attachment=True, download_name='transcription.txt')

class UnicodePDF(FPDF):
    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')

@app.route('/download/pdf', methods=['POST'])
def download_pdf():
    text = request.form.get('text', '')
    
    pdf = UnicodePDF()
    pdf.add_page()
    
    # Safely encode text using latin-1 to avoid fpdf crashes for languages like Tamil/Hindi
    safe_text = text.encode('latin-1', 'replace').decode('latin-1')
    
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, txt=safe_text)
    
    fd, path = tempfile.mkstemp(suffix='.pdf')
    os.close(fd)
    pdf.output(path)
    
    return send_file(path, as_attachment=True, download_name='transcription.pdf')
if __name__ == "__main__":
    # Local testing only
    app.run()
