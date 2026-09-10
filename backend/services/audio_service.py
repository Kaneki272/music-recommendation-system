import os
import uuid
import hashlib
import time
import numpy as np
import librosa
from scipy import stats
from typing import Dict, Any, List

TARGET_SAMPLE_RATE = 22050
N_MFCC = 20
AUDIO_EXTS = [".mp3", ".wav", ".flac", ".m4a"]

def generate_file_hash(filepath: str) -> str:
    hasher = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()

def generate_deterministic_uuid(hash_str: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_OID, hash_str)

def stats7(arr: np.ndarray) -> List[float]:
    f = arr.flatten()
    return [
        float(np.mean(f)), float(np.std(f)), float(np.min(f)),
        float(np.max(f)), float(np.median(f)),
        float(stats.skew(f)), float(stats.kurtosis(f))
    ]

def extract_features_for_file(filepath: str) -> Dict[str, Any]:
    t0 = time.perf_counter()
    file_hash = generate_file_hash(filepath)
    song_id = generate_deterministic_uuid(file_hash)
    
    try:
        y, sr = librosa.load(filepath, sr=TARGET_SAMPLE_RATE, mono=True)
        duration = len(y) / sr
        
        onset_env = librosa.onset.onset_strength(y=y, sr=sr)
        try:
            tempo_arr = librosa.feature.tempo(onset_envelope=onset_env, sr=sr)
            tempo_bpm = float(np.atleast_1d(tempo_arr)[0])
            n_beats = int(np.sum(onset_env > np.mean(onset_env)))
        except Exception:
            tempo_bpm = 120.0
            n_beats = 0

        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
        spec_centroid = librosa.feature.spectral_centroid(y=y, sr=sr)
        spec_rolloff = librosa.feature.spectral_rolloff(y=y, sr=sr)
        spec_bw = librosa.feature.spectral_bandwidth(y=y, sr=sr)
        zcr = librosa.feature.zero_crossing_rate(y=y)
        rms = librosa.feature.rms(y=y)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        tonnetz = librosa.feature.tonnetz(y=y, sr=sr)
        flatness = librosa.feature.spectral_flatness(y=y)
        harmonic_ratio = float(1.0 - np.mean(flatness))

        vec = [tempo_bpm, float(n_beats), float(np.mean(onset_env))]
        for i in range(N_MFCC): vec += stats7(mfcc[i, :])
        vec += stats7(spec_centroid) + stats7(spec_rolloff) + stats7(spec_bw)
        vec += stats7(zcr) + stats7(rms)
        for pp in range(12): vec += [float(np.mean(chroma[pp, :])), float(np.std(chroma[pp, :]))]
        for d in range(6): vec += [float(np.mean(tonnetz[d, :])), float(np.std(tonnetz[d, :]))]
        vec += [harmonic_ratio]

        vec_arr = np.array(vec, dtype=np.float32)
        
        # Validations
        if len(vec) != 215:
            raise ValueError(f"Extracted dimension {len(vec)} != 215")
        if np.isnan(vec_arr).any():
            raise ValueError("NaN values encountered")
        if np.isinf(vec_arr).any():
            raise ValueError("Infinity values encountered")

        return {
            "status": "success",
            "song_id": song_id,
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "file_hash": file_hash,
            "format": os.path.splitext(filepath)[1].lower(),
            "duration": duration,
            "sample_rate": sr,
            "tempo_bpm": tempo_bpm,
            "harmonic_ratio": harmonic_ratio,
            "feature_dimension": len(vec),
            "extraction_version": "audio_v2",
            "vector": vec,
            "processing_time": time.perf_counter() - t0
        }
    except Exception as e:
        return {
            "status": "error",
            "filename": os.path.basename(filepath),
            "filepath": filepath,
            "file_hash": file_hash,
            "error_type": type(e).__name__,
            "error_msg": str(e),
            "processing_time": time.perf_counter() - t0
        }
