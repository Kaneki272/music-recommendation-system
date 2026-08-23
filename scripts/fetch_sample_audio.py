import os
import urllib.request
import numpy as np
import soundfile as sf

TARGET_DIR = os.path.join("datasets", "raw", "audio_samples")
os.makedirs(TARGET_DIR, exist_ok=True)

# 1. Download Public Domain / Royalty-Free MP3 Sample Tracks
MP3_SAMPLES = [
    ("soundhelix_song1.mp3", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"),
    ("soundhelix_song2.mp3", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-2.mp3"),
    ("soundhelix_song3.mp3", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-3.mp3"),
]

def download_mp3s():
    headers = {'User-Agent': 'Mozilla/5.0'}
    for filename, url in MP3_SAMPLES:
        dest_path = os.path.join(TARGET_DIR, filename)
        if not os.path.exists(dest_path):
            print(f"Downloading real MP3 sample: {filename}...")
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
                    out_file.write(resp.read())
                print(f"  Saved {filename} ({os.path.getsize(dest_path) // 1024} KB)")
            except Exception as e:
                print(f"  Failed to download {filename}: {e}")
        else:
            print(f"  {filename} already exists.")

# 2. Generate Real WAV Audio Files with Acoustic Frequencies
def generate_wavs():
    sr = 22050
    duration = 5.0 # 5 seconds
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)

    tracks = [
        ("synth_ballad.wav", [110.0, 138.59, 164.81], 0.5),   # A Major triad (slow ballad)
        ("synth_upbeat.wav", [220.0, 277.18, 329.63], 2.0),   # Fast dance rhythm
        ("synth_ambient.wav", [82.41, 123.47, 164.81], 0.2),  # E Minor low drone
    ]

    for filename, freqs, tempo_mod in tracks:
        dest_path = os.path.join(TARGET_DIR, filename)
        if not os.path.exists(dest_path):
            print(f"Generating synthesized WAV audio: {filename}...")
            # Combine fundamental frequencies + harmonics + rhythmic amplitude modulation
            signal = np.zeros_like(t)
            for i, f in enumerate(freqs):
                signal += (1.0 / (i + 1)) * np.sin(2 * np.pi * f * t)
            
            # Add beat pulse modulation
            pulse = 0.5 + 0.5 * np.sin(2 * np.pi * tempo_mod * t)
            signal = signal * pulse
            
            # Normalize float32 audio
            signal = signal / (np.max(np.abs(signal)) + 1e-8)
            sf.write(dest_path, signal.astype(np.float32), sr)
            print(f"  Saved {filename} ({os.path.getsize(dest_path) // 1024} KB)")

if __name__ == "__main__":
    print("Populating datasets/raw/audio_samples/ with real MP3 and WAV files...")
    download_mp3s()
    generate_wavs()
    print("\nDone! All sample audio files placed in datasets/raw/audio_samples/")
