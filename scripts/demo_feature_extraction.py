"""
Audio Feature Extraction — Demo (writes output to file)
"""
import sys, time, math
import numpy as np
import librosa
from scipy import stats

OUT = open("scripts/extraction_output.txt", "w", encoding="utf-8")

def p(*args, **kw):
    print(*args, **kw, file=OUT)
    OUT.flush()

TARGET_SAMPLE_RATE    = 22_050
N_MFCC                = 20
EXTRACTION_VERSION    = "audio_v1"
CANONICAL_VECTOR_DIM  = 215


def make_signal(seed: int, duration: float = 8.0) -> np.ndarray:
    np.random.seed(seed)
    sr = TARGET_SAMPLE_RATE
    t  = np.linspace(0, duration, int(sr * duration), endpoint=False)
    base_freq = [110.0, 220.0, 82.4][seed % 3]
    y = (
        0.5  * np.sin(2 * np.pi * base_freq * t)
      + 0.25 * np.sin(2 * np.pi * base_freq * 2 * t)
      + 0.15 * np.sin(2 * np.pi * base_freq * 3 * t)
      + 0.08 * np.random.randn(len(t))
    )
    y /= np.max(np.abs(y) + 1e-8)
    return y.astype(np.float32)

def stats7(arr):
    f = arr.flatten()
    return [float(np.mean(f)), float(np.std(f)), float(np.min(f)),
            float(np.max(f)), float(np.median(f)),
            float(stats.skew(f)), float(stats.kurtosis(f))]

def extract(song_id, seed):
    y  = make_signal(seed)
    sr = TARGET_SAMPLE_RATE
    t0 = time.perf_counter()

    onset_env        = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats     = librosa.beat.beat_track(onset_envelope=onset_env, sr=sr)
    tempo_bpm        = float(np.atleast_1d(tempo)[0])

    mfcc             = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC)
    spec_centroid    = librosa.feature.spectral_centroid(y=y, sr=sr)
    spec_rolloff     = librosa.feature.spectral_rolloff(y=y, sr=sr)
    spec_bandwidth   = librosa.feature.spectral_bandwidth(y=y, sr=sr)
    zcr              = librosa.feature.zero_crossing_rate(y=y)
    rms              = librosa.feature.rms(y=y)

    chroma           = librosa.feature.chroma_stft(y=y, sr=sr)
    tonnetz          = librosa.feature.tonnetz(y=y, sr=sr)
    flatness         = librosa.feature.spectral_flatness(y=y)
    harmonic_ratio   = float(1.0 - np.mean(flatness))

    elapsed_ms = (time.perf_counter() - t0) * 1000

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

    assert len(vec) == CANONICAL_VECTOR_DIM, f"Expected {CANONICAL_VECTOR_DIM}, got {len(vec)}"

    return {
        "song_id": song_id, "tempo_bpm": tempo_bpm,
        "beat_count": len(beats), "onset_mean": float(np.mean(onset_env)),
        "mfcc_shape": mfcc.shape,
        "mfcc0_mean": float(np.mean(mfcc[0])), "mfcc0_std": float(np.std(mfcc[0])),
        "centroid_mean": float(np.mean(spec_centroid)),
        "rolloff_mean": float(np.mean(spec_rolloff)),
        "bandwidth_mean": float(np.mean(spec_bandwidth)),
        "zcr_mean": float(np.mean(zcr)), "rms_mean": float(np.mean(rms)),
        "chroma_shape": chroma.shape,
        "dominant_pitch": ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"][
                          int(np.argmax(np.mean(chroma, axis=1)))],
        "tonnetz_shape": tonnetz.shape,
        "harmonic_ratio": harmonic_ratio,
        "vector": vec, "elapsed_ms": elapsed_ms,
    }

songs = [
    ("song_001", 0, "Synthetic Ballad     (A2 fundamental, 110 Hz)"),
    ("song_002", 1, "Synthetic Dance      (A3 fundamental, 220 Hz)"),
    ("song_003", 2, "Synthetic Ambient    (E2 fundamental,  82 Hz)"),
]

SEP = "=" * 72

p()
p("+" + "=" * 70 + "+")
p("|    AUDIO FEATURE EXTRACTION PIPELINE  --  OUTPUT REPORT              |")
p("|    Extraction Version: audio_v1   |   Vector Dimension: 222          |")
p("+" + "=" * 70 + "+")

all_results = []
for sid, seed, label in songs:
    r = extract(sid, seed)
    all_results.append((label, r))
    v = r["vector"]

    p(f"\n{SEP}")
    p(f"  {sid}  |  {label}")
    p(SEP)

    p(f"\n  [PREPROCESSOR]")
    p(f"    Sample Rate     : {TARGET_SAMPLE_RATE:,} Hz  (mono PCM float32, 8 s)")

    p(f"\n  [DSP EXTRACTOR]")
    p(f"    RHYTHM")
    p(f"      Tempo (BPM)       : {r['tempo_bpm']:>8.2f}")
    p(f"      Beat Count        : {r['beat_count']:>8}")
    p(f"      Onset Strength mu : {r['onset_mean']:>8.4f}")
    p(f"    TIMBRAL")
    p(f"      MFCC Shape        : {r['mfcc_shape']}  ({N_MFCC} coefficients x T frames)")
    p(f"      MFCC[0]  mu +/- s : {r['mfcc0_mean']:>+8.3f}  +/-  {r['mfcc0_std']:.3f}")
    p(f"      Spectral Centroid : {r['centroid_mean']:>8.1f} Hz (mean)")
    p(f"      Spectral Rolloff  : {r['rolloff_mean']:>8.1f} Hz (mean)")
    p(f"      Bandwidth         : {r['bandwidth_mean']:>8.1f} Hz (mean)")
    p(f"      ZCR mean          : {r['zcr_mean']:>8.5f}")
    p(f"      RMS Energy mean   : {r['rms_mean']:>8.6f}")
    p(f"    HARMONIC")
    p(f"      Chroma Shape      : {r['chroma_shape']}  (12 pitch classes x T frames)")
    p(f"      Dominant Pitch    : {r['dominant_pitch']}")
    p(f"      Tonnetz Shape     : {r['tonnetz_shape']}  (6 tonal dims x T frames)")
    p(f"      Harmonic Ratio    : {r['harmonic_ratio']:>8.4f}  (0=percussive -> 1=harmonic)")

    p(f"\n  [AGGREGATOR OUTPUT  ->  222-dim AudioFeatureVector]")
    p(f"    Total Dimensions  : {len(v)}")
    p(f"    Breakdown:")
    p(f"      [  3] Rhythm     : {v[0]:.2f} BPM | {v[1]:.0f} beats | onset_mu={v[2]:.4f}")
    ms = v[3:143]
    p(f"      [140] MFCC       : mu={np.mean(ms):+.4f}  sigma={np.std(ms):.4f}  range=[{min(ms):.3f}, {max(ms):.3f}]")
    cs = v[143:150]
    p(f"      [  7] Centroid   : mu={np.mean(cs):.2f}  sigma={np.std(cs):.2f}")
    rs = v[150:157]
    p(f"      [  7] Rolloff    : mu={np.mean(rs):.2f}  sigma={np.std(rs):.2f}")
    bs = v[157:164]
    p(f"      [  7] Bandwidth  : mu={np.mean(bs):.2f}  sigma={np.std(bs):.2f}")
    zs = v[164:171]
    p(f"      [  7] ZCR        : mu={np.mean(zs):.6f}  sigma={np.std(zs):.6f}")
    es = v[171:178]
    p(f"      [  7] RMS        : mu={np.mean(es):.7f}  sigma={np.std(es):.7f}")
    hs = v[178:202]
    p(f"      [ 24] Chroma     : mu={np.mean(hs):.4f}  sigma={np.std(hs):.4f}  range=[{min(hs):.4f}, {max(hs):.4f}]")
    ts = v[202:214]
    p(f"      [ 12] Tonnetz    : mu={np.mean(ts):.5f}  sigma={np.std(ts):.5f}")
    p(f"      [  1] Harm Ratio : {v[-1]:.4f}")
    p(f"    Vector Preview (dims 0-11):")
    prev = "  ".join(f"{x:+.4f}" for x in v[:12])
    p(f"      [ {prev} ... ]")
    p(f"    Qdrant Payload:")
    p(f"      song_id            : {r['song_id']}")
    p(f"      vector_dimension   : {len(v)}")
    p(f"      extraction_version : {EXTRACTION_VERSION}")
    p(f"      tempo_bpm          : {r['tempo_bpm']:.2f}")
    p(f"      harmonic_ratio     : {r['harmonic_ratio']:.4f}")
    p(f"\n  Extraction time : {r['elapsed_ms']:.1f} ms")

p(f"\n\n{SEP}")
p("  CROSS-SONG COMPARISON SUMMARY")
p(SEP)
p(f"  {'Label':<45} {'BPM':>6} {'HR':>6} {'ZCR':>9} {'RMS':>11} {'Centroid':>10} {'ms':>7}")
p(f"  {'-'*45} {'-'*6} {'-'*6} {'-'*9} {'-'*11} {'-'*10} {'-'*7}")
for label, r in all_results:
    p(f"  {label:<45} {r['tempo_bpm']:>6.1f} {r['harmonic_ratio']:>6.4f}"
      f" {r['zcr_mean']:>9.5f} {r['rms_mean']:>11.7f}"
      f" {r['centroid_mean']:>10.1f} {r['elapsed_ms']:>7.1f}")

p(f"\n  OK  {len(all_results)} songs processed  |  {CANONICAL_VECTOR_DIM}-dim vectors ready for Qdrant\n")
OUT.close()
print("Done. Output written to scripts/extraction_output.txt")
