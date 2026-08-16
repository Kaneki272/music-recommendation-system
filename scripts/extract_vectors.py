import numpy as np
import librosa
from scipy import stats
import json
import soundfile as sf
import os

TARGET_SAMPLE_RATE = 22050
N_MFCC = 20

def make_signal(seed=42, duration=2.0):
    np.random.seed(seed)
    sr = TARGET_SAMPLE_RATE
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    base = 220.0
    y = (0.5 * np.sin(2*np.pi*base*t) + 0.08 * np.random.randn(len(t)))
    return (y / (np.max(np.abs(y)) + 1e-8)).astype(np.float32)

def s7(a):
    f = a.flatten()
    return [float(np.mean(f)), float(np.std(f)), float(np.min(f)),
            float(np.max(f)), float(np.median(f)),
            float(stats.skew(f)), float(stats.kurtosis(f))]

def extract(y):
    sr = TARGET_SAMPLE_RATE
    S = np.abs(librosa.stft(y))
    oe = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S, ref=np.max), sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=oe, sr=sr)
    bpm = float(np.atleast_1d(tempo)[0])
    
    mfcc = librosa.feature.mfcc(S=librosa.power_to_db(S**2), sr=sr, n_mfcc=N_MFCC)
    centroid = librosa.feature.spectral_centroid(S=S, sr=sr)
    rolloff = librosa.feature.spectral_rolloff(S=S, sr=sr)
    bandwidth = librosa.feature.spectral_bandwidth(S=S, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y=y)
    rms = librosa.feature.rms(S=S)
    chroma = librosa.feature.chroma_stft(S=S, sr=sr)
    
    r = 2*np.pi*np.arange(12)/12
    mapping = np.array([np.sin(r), np.cos(r), np.sin(2*r), np.cos(2*r), np.sin(3*r), np.cos(3*r)])
    tonnetz = mapping @ chroma
    
    flatness = librosa.feature.spectral_flatness(y=y)
    hr = float(1.0 - np.mean(flatness))

    vec = []
    vec += [bpm, float(len(beats)), float(np.mean(oe))]
    for i in range(N_MFCC): vec += s7(mfcc[i, :])
    vec += s7(centroid) + s7(rolloff) + s7(bandwidth) + s7(zcr) + s7(rms)
    for p in range(12): vec += [float(np.mean(chroma[p, :])), float(np.std(chroma[p, :]))]
    for d in range(6): vec += [float(np.mean(tonnetz[d, :])), float(np.std(tonnetz[d, :]))]
    vec += [hr]
    
    return vec, bpm

if __name__ == "__main__":
    y1 = make_signal(42)
    vec1, bpm1 = extract(y1)
    
    y2 = make_signal(1)
    vec2, bpm2 = extract(y2)
    
    sf.write("test_fixture.wav", y1, TARGET_SAMPLE_RATE)
    file_size = os.path.getsize("test_fixture.wav") / (1024 * 1024)
    
    data = {
        "vec1": vec1,
        "bpm1": bpm1,
        "vec2": vec2,
        "bpm2": bpm2,
        "file_size": file_size
    }
    with open("vecs.json", "w") as f:
        json.dump(data, f)
