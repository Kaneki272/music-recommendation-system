import sys
import os
import glob
import time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Register FFmpeg binary location for Librosa / Audioread
try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
except Exception:
    pass

try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

import numpy as np
import librosa
from scipy import stats

TARGET_SAMPLE_RATE = 22050
N_MFCC = 20

def stats7(arr):
    f = arr.flatten()
    return [float(np.mean(f)), float(np.std(f)), float(np.min(f)),
            float(np.max(f)), float(np.median(f)),
            float(stats.skew(f)), float(stats.kurtosis(f))]

def extract_features(audio_path: str):
    t0 = time.perf_counter()
    print(f"\nLoading audio: {os.path.basename(audio_path)} ...")
    # Load first 30 seconds for fast feature extraction
    y, sr = librosa.load(audio_path, sr=TARGET_SAMPLE_RATE, mono=True, duration=30.0)
    
    print(f"  Signal loaded: {len(y)/sr:.1f} sec @ {sr} Hz")
    
    # Compute DSP features
    onset_env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    tempo_bpm = float(np.atleast_1d(tempo)[0])
    
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
    spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    spec_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
    spec_bandwidth = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    zcr = librosa.feature.zero_crossing_rate(y=y)
    rms = librosa.feature.rms(y=y)
    chroma = librosa.feature.chroma_stft(y=y, sr=sr)
    tonnetz = librosa.feature.tonnetz(y=y, sr=sr)
    flatness = librosa.feature.spectral_flatness(y=y)
    harmonic_ratio = float(1.0 - np.mean(flatness))

    # Build 215-dim canonical feature vector
    vec = []
    vec += [tempo_bpm, float(len(beats)), float(np.mean(onset_env))]
    for i in range(N_MFCC):
        vec += stats7(mfcc[i, :])
    vec += stats7(spec_centroid)
    vec += stats7(spec_rolloff)
    vec += stats7(spec_bandwidth)
    vec += stats7(zcr)
    vec += stats7(rms)
    for pp in range(12):
        row = chroma[pp, :]
        vec += [float(np.mean(row)), float(np.std(row))]
    for d in range(6):
        row = tonnetz[d, :]
        vec += [float(np.mean(row)), float(np.std(row))]
    vec += [harmonic_ratio]

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  Extraction complete in {elapsed:.1f} ms | Vector dimension: {len(vec)}")
    
    return {
        "filename": os.path.basename(audio_path),
        "tempo_bpm": tempo_bpm,
        "harmonic_ratio": harmonic_ratio,
        "centroid_mean": float(np.mean(spec_centroid)),
        "vector": np.array(vec, dtype=np.float32)
    }

def cosine_similarity(v1, v2):
    dot = np.dot(v1, v2)
    norm = np.linalg.norm(v1) * np.linalg.norm(v2)
    return dot / (norm + 1e-8)

def main():
    audio_dir = os.path.join("datasets", "raw", "audio_samples")
    extensions = ["*.mp3", "*.m4a", "*.webm", "*.opus", "*.wav"]
    files = []
    for ext in extensions:
        files.extend(glob.glob(os.path.join(audio_dir, ext)))
    files = sorted(list(set(files)))
    
    if not files:
        print(f"No audio files found in {audio_dir}")
        return

    print(f"Found {len(files)} audio files in {audio_dir}:")

    # Extract features for all files
    extracted = []
    for f in files:
        try:
            feats = extract_features(f)
            extracted.append(feats)
        except Exception as e:
            print(f"Error extracting {os.path.basename(f)}: {e}")

    if len(extracted) < 2:
        print("\nNeed at least 2 valid audio files to test similarity recommendations.")
        return

    print("\n" + "="*70)
    print("  CONTENT-BASED SIMILARITY MATRIX ON REAL AUDIO FILES")
    print("="*70)

    # Compute pairwise cosine similarity matrix
    for i, target in enumerate(extracted[:10]): # Show top recommendations for first 10 tracks
        print(f"\nRecommendations for Target Song: '{target['filename']}' ({target['tempo_bpm']:.1f} BPM):")
        scores = []
        for j, cand in enumerate(extracted):
            if i == j:
                continue
            sim = cosine_similarity(target["vector"], cand["vector"])
            scores.append((cand['filename'], cand['tempo_bpm'], sim))
        
        scores.sort(key=lambda x: x[2], reverse=True)
        for rank, (fname, bpm, sim) in enumerate(scores[:5], 1):
            print(f"  Rank {rank}: {fname:<45} | Tempo: {bpm:>5.1f} BPM | Similarity: {sim:.4f}")

if __name__ == "__main__":
    main()
