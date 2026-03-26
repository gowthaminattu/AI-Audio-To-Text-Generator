let currentAudioBlob = null;
let currentFileName = "";

// Web Audio API for WAV Recording
let audioContext;
let scriptProcessor;
let mediaStreamSource;
let isRecording = false;
let audioChunks = [];
let localStream;

document.addEventListener('DOMContentLoaded', () => {
    // Ensure basic UI state
});

async function toggleRecording() {
    const btn = document.getElementById('recordBtn');
    const textSpan = document.getElementById('recordText');

    if (!isRecording) {
        // Start Recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            localStream = stream;
            
            audioContext = new (window.AudioContext || window.webkitAudioContext)({sampleRate: 44100});
            mediaStreamSource = audioContext.createMediaStreamSource(stream);
            scriptProcessor = audioContext.createScriptProcessor(4096, 1, 1);
            
            scriptProcessor.onaudioprocess = function(e) {
                if (!isRecording) return;
                const inputData = e.inputBuffer.getChannelData(0);
                audioChunks.push(new Float32Array(inputData));
            };

            const gainNode = audioContext.createGain();
            gainNode.gain.value = 0; // Prevent feedback loop

            mediaStreamSource.connect(scriptProcessor);
            scriptProcessor.connect(gainNode);
            gainNode.connect(audioContext.destination);

            isRecording = true;
            btn.classList.add('glow-effect');
            btn.style.backgroundColor = 'var(--danger)';
            textSpan.textContent = "Stop Recording";
            
            // clear previous file
            clearFileSelection();
            
            document.getElementById('fileInfo').classList.remove('hidden');
            document.getElementById('fileInfo').textContent = "🔴 Recording in progress...";
            
        } catch (err) {
            console.error(err);
            alert("Could not access microphone! Make sure you granted permissions.");
        }
    } else {
        // Stop Recording
        isRecording = false;
        
        mediaStreamSource.disconnect();
        scriptProcessor.disconnect();
        localStream.getTracks().forEach(t => t.stop());
        
        btn.classList.remove('glow-effect');
        btn.style.backgroundColor = 'var(--primary)';
        textSpan.textContent = "Record Audio";

        // Process audio chunks into WAV
        const numFrames = audioChunks.reduce((acc, chunk) => acc + chunk.length, 0);
        const flattened = new Float32Array(numFrames);
        let offset = 0;
        for(let i=0; i<audioChunks.length; i++) {
            flattened.set(audioChunks[i], offset);
            offset += audioChunks[i].length;
        }
        
        currentAudioBlob = exportWAV(flattened, audioContext.sampleRate);
        currentFileName = "recorded_audio.wav";
        audioChunks = []; // reset
        
        document.getElementById('fileInfo').textContent = "✅ Recording saved ready for conversion.";
        document.getElementById('convertBtn').disabled = false;
    }
}

function exportWAV(audioData, sampleRate) {
    const buffer = new ArrayBuffer(44 + audioData.length * 2);
    const view = new DataView(buffer);

    // RIFF identifier
    writeString(view, 0, 'RIFF');
    view.setUint32(4, 36 + audioData.length * 2, true);
    writeString(view, 8, 'WAVE');
    writeString(view, 12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true); // mono
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeString(view, 36, 'data');
    view.setUint32(40, audioData.length * 2, true);

    let offset = 44;
    for (let i = 0; i < audioData.length; i++) {
        let s = Math.max(-1, Math.min(1, audioData[i]));
        view.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        offset += 2;
    }

    return new Blob([view], { type: 'audio/wav' });
}

function writeString(view, offset, string) {
    for (let i = 0; i < string.length; i++) {
        view.setUint8(offset + i, string.charCodeAt(i));
    }
}

function handleFileUpload(event) {
    const file = event.target.files[0];
    if (file) {
        currentAudioBlob = file;
        currentFileName = file.name;
        
        document.getElementById('fileInfo').classList.remove('hidden');
        document.getElementById('fileInfo').textContent = `📁 File selected: ${file.name}`;
        document.getElementById('convertBtn').disabled = false;
    }
}

function clearFileSelection() {
    currentAudioBlob = null;
    currentFileName = "";
    document.getElementById('fileUpload').value = "";
    document.getElementById('fileInfo').classList.add('hidden');
    document.getElementById('convertBtn').disabled = true;
}

function clearAll() {
    clearFileSelection();
    document.getElementById('transcribedText').value = "";
    document.getElementById('downTxtBtn').disabled = true;
    document.getElementById('downPdfBtn').disabled = true;
    document.getElementById('errorMsg').classList.add('hidden');
}

async function convertToText() {
    if (!currentAudioBlob) return;

    const language = document.getElementById('languageSelect').value;
    console.log("Starting transcription for:", currentFileName);
    
    // UI states
    const loadingMessage = document.getElementById('loadingSpinner').querySelector('p');
    loadingMessage.textContent = "AI is transcribing your audio... This may take a minute for large files.";
    document.getElementById('loadingSpinner').classList.remove('hidden');
    document.getElementById('errorMsg').classList.add('hidden');
    document.getElementById('transcribedText').value = "";
    document.getElementById('convertBtn').disabled = true;

    const formData = new FormData();
    formData.append('audio_file', currentAudioBlob, currentFileName);
    formData.append('language', language);

    try {
        console.log("Sending request to /transcribe...");
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });

        console.log("Response received. Status:", response.status);
        const result = await response.json();
        
        if (response.ok) {
            console.log("Transcription successful!");
            document.getElementById('transcribedText').value = result.text;
            document.getElementById('downTxtBtn').disabled = false;
            document.getElementById('downPdfBtn').disabled = false;
        } else {
            console.error("Transcription failed:", result.error);
            showError(result.error || "An unknown error occurred during transcription.");
        }
    } catch (error) {
        console.error("Fetch error:", error);
        showError("Network error: Could not reach the server. If the file is very large, the server might have timed out.");
    } finally {
        document.getElementById('loadingSpinner').classList.add('hidden');
        document.getElementById('convertBtn').disabled = false;
    }
}

function showError(message) {
    const errDiv = document.getElementById('errorMsg');
    errDiv.textContent = message;
    errDiv.classList.remove('hidden');
}

function downloadFile(type) {
    const text = document.getElementById('transcribedText').value;
    if (!text) return;

    if (type === 'txt') {
        document.getElementById('txtInput').value = text;
        document.getElementById('txtForm').submit();
    } else if (type === 'pdf') {
        document.getElementById('pdfInput').value = text;
        document.getElementById('pdfForm').submit();
    }
}
