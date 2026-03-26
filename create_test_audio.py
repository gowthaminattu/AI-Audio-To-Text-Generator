
import urllib.request
import os

print("Downloading test_speech.wav...")
url = "https://www2.cs.uic.edu/~i101/SoundFiles/preamble10.wav"
filename = "test_speech.wav"
urllib.request.urlretrieve(url, filename)

if os.path.exists(filename):
    print(f"Success! {filename} has been saved to your folder.")
else:
    print("Download failed.")
input("Press Enter to close this window...")
