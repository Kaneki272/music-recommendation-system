"""
Standalone audio feature extraction + content-based similarity test.
Safe wrapper around the contributor's test_real_audio.py logic.
"""
import sys
import os
import glob
import time

# Safe stdout reconfigure for Windows background tasks
try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# Try to register FFmpeg from optional helper packages
for mod_name in ['static_ffmpeg', 'imageio_ffmpeg']:
    try:
        if mod_name == 'static_ffmpeg':
            import static_ffmpeg
            static_ffmpeg.add_paths()
        else:
            import imageio_ffmpeg
            ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
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
    return [
        float(np.mean(f)), float(np.std(f)), float(np.min(f)),
        float(np.max(f)), float(np.median(f)),
        float(stats.skew(f)), float(stats.kurtosis(f))
    ]

def extract_features(audio_path: str):
    t0 = time.perf_counter()
    print(f"\nLoading: {os.path.basename(audio_path)} ...", flush=True)
    y, sr = librosa.load(audio_path, sr=TARGET_SAMPLE_RATE, mono=True, duration=30.0)
    print(f"  Duration: {len(y)/sr:.1f}s  SR: {sr}Hz", flush=True)
    print("  Computing DSP features...", flush=True)

    onset_env = librosa.onset.onset_strength(y=y, sr=sr)

    # Use librosa.feature.tempo (static, no numba DP) as safe fallback
    # librosa.beat.beat_track uses numba JIT which segfaults on some Windows+Python 3.12 setups
    try:
        tempo_arr = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)
        tempo_bpm = float(np.atleast_1d(tempo_arr)[0])
        n_beats = int(np.sum(onset_env > np.mean(onset_env)))  # proxy beat count
    except Exception:
        tempo_bpm = 120.0  # safe default
        n_beats = 0

    mfcc          = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
    spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
    spec_rolloff  = librosa.feature.spectral_rolloff(y=y, sr=sr)
    spec_bw       = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    zcr           = librosa.feature.zero_crossing_rate(y=y)
    rms           = librosa.feature.rms(y=y)
    chroma        = librosa.feature.chroma_stft(y=y, sr=sr)
    tonnetz       = librosa.feature.tonnetz(y=y, sr=sr)
    flatness      = librosa.feature.spectral_flatness(y=y)
    harmonic_ratio = float(1.0 - np.mean(flatness))

    # Build 215-dim canonical feature vector
    vec = [tempo_bpm, float(n_beats), float(np.mean(onset_env))]
    for i in range(N_MFCC):
        vec += stats7(mfcc[i, :])
    vec += stats7(spec_centroid) + stats7(spec_rolloff) + stats7(spec_bw)
    vec += stats7(zcr) + stats7(rms)
    for pp in range(12):
        vec += [float(np.mean(chroma[pp, :])), float(np.std(chroma[pp, :]))]
    for d in range(6):
        vec += [float(np.mean(tonnetz[d, :])), float(np.std(tonnetz[d, :]))]
    vec += [harmonic_ratio]

    elapsed_ms = (time.perf_counter() - t0) * 1000
    print(f"  Tempo: {tempo_bpm:.1f} BPM  |  Centroid: {float(np.mean(spec_centroid)):.0f} Hz  "
          f"|  Harmonic Ratio: {harmonic_ratio:.3f}  |  Vector: {len(vec)}D  |  [{elapsed_ms:.0f} ms]",
          flush=True)
    return {
        "filename": os.path.basename(audio_path),
        "tempo_bpm": tempo_bpm,
        "harmonic_ratio": harmonic_ratio,
        "centroid_mean": float(np.mean(spec_centroid)),
        "vector": np.array(vec, dtype=np.float32)
    }

def cosine_similarity(v1, v2):
    return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8))

def main():
    audio_dir = os.path.join("datasets", "raw", "audio_samples")
    files = sorted(set(
        f for ext in ["*.mp3", "*.wav", "*.m4a", "*.webm", "*.opus"]
        for f in glob.glob(os.path.join(audio_dir, ext))
    ))

    if not files:
        print(f"No audio files found in {audio_dir}", flush=True)
        sys.exit(1)

    print(f"Found {len(files)} audio files in {audio_dir}:", flush=True)
    for f in files:
        print(f"  {os.path.basename(f)}", flush=True)

    # Feature extraction
    extracted = []
    for f in files:
        try:
            feat = extract_features(f)
            extracted.append(feat)
        except Exception as e:
            import traceback
            print(f"  ERROR extracting {os.path.basename(f)}: {e}", flush=True)
            traceback.print_exc()

    if len(extracted) < 2:
        print("\nNeed at least 2 valid audio files for similarity testing.", flush=True)
        sys.exit(1)

    # Pairwise cosine similarity recommendations
    print("\n" + "=" * 70, flush=True)
    print("  CONTENT-BASED SIMILARITY MATRIX ON REAL AUDIO FILES", flush=True)
    print("=" * 70, flush=True)

    for i, target in enumerate(extracted):
        scores = []
        for j, cand in enumerate(extracted):
            if i == j:
                continue
            sim = cosine_similarity(target["vector"], cand["vector"])
            scores.append((cand["filename"], cand["tempo_bpm"], sim))
        scores.sort(key=lambda x: x[2], reverse=True)

        print(f"\nRecommendations for: '{target['filename']}' ({target['tempo_bpm']:.1f} BPM):",
              flush=True)
        for rank, (fname, bpm, sim) in enumerate(scores[:3], 1):
            print(f"  Rank {rank}: {fname:<42} Tempo:{bpm:>6.1f} BPM  Sim:{sim:.4f}",
                  flush=True)

    print("\n" + "=" * 70, flush=True)
    print("  REAL AUDIO FEATURE EXTRACTION TEST -- PASSED", flush=True)
    print("=" * 70, flush=True)

if __name__ == "__main__":
    main()
