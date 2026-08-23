"""Step-by-step diagnosis: find which librosa feature call crashes on the MP3."""
import sys, os, traceback
sys.path.insert(0, '.')

import numpy as np
import librosa
from scipy import stats

SR = 22050
audio_path = os.path.join("datasets", "raw", "audio_samples", "soundhelix_song1.mp3")

print(f"Loading {audio_path} ...", flush=True)
y, sr = librosa.load(audio_path, sr=SR, mono=True, duration=30.0)
print(f"  OK: {len(y)/sr:.1f}s @ {sr}Hz", flush=True)

steps = [
    ("onset_strength",  lambda: librosa.onset.onset_strength(y=y, sr=sr)),
    ("beat_track",      lambda: librosa.beat.beat_track(
                            onset_envelope=librosa.onset.onset_strength(y=y, sr=sr), sr=sr)),
    ("mfcc",            lambda: librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)),
    ("spectral_centroid", lambda: librosa.feature.spectral_centroid(y=y, sr=sr)),
    ("spectral_rolloff",  lambda: librosa.feature.spectral_rolloff(y=y, sr=sr)),
    ("spectral_bandwidth",lambda: librosa.feature.spectral_bandwidth(y=y, sr=sr)),
    ("zero_crossing_rate",lambda: librosa.feature.zero_crossing_rate(y=y)),
    ("rms",             lambda: librosa.feature.rms(y=y)),
    ("chroma_stft",     lambda: librosa.feature.chroma_stft(y=y, sr=sr)),
    ("tonnetz",         lambda: librosa.feature.tonnetz(y=y, sr=sr)),
    ("spectral_flatness", lambda: librosa.feature.spectral_flatness(y=y)),
    ("scipy.stats.skew",  lambda: stats.skew(y[:1000])),
    ("scipy.stats.kurtosis", lambda: stats.kurtosis(y[:1000])),
]

for name, fn in steps:
    try:
        result = fn()
        shape = getattr(result, 'shape', 'scalar') if not isinstance(result, tuple) else str(tuple(r.shape if hasattr(r,'shape') else r for r in result))
        print(f"  [OK]   {name:30s}  shape={shape}", flush=True)
    except Exception as e:
        print(f"  [FAIL] {name:30s}  ERROR: {e}", flush=True)
        traceback.print_exc()

print("\nDiagnosis complete.", flush=True)
