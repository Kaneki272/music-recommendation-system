import sys, time
import numpy as np
import librosa
from scipy import stats

TARGET_SAMPLE_RATE = 22050
N_MFCC = 20
CANONICAL_DIM = 222

def make_signal(seed, duration=2.0):
    np.random.seed(seed)
    sr = TARGET_SAMPLE_RATE
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    base = [110.0, 220.0, 82.4][seed % 3]
    y = (0.5 * np.sin(2*np.pi*base*t)
       + 0.25 * np.sin(2*np.pi*base*2*t)
       + 0.15 * np.sin(2*np.pi*base*3*t)
       + 0.08 * np.random.randn(len(t)))
    return (y / (np.max(np.abs(y)) + 1e-8)).astype(np.float32)

def s7(a):
    f = a.flatten()
    return [float(np.mean(f)), float(np.std(f)), float(np.min(f)),
            float(np.max(f)), float(np.median(f)),
            float(stats.skew(f)), float(stats.kurtosis(f))]

NOTES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']

def extract(song_id, seed, label):
    y  = make_signal(seed)
    sr = TARGET_SAMPLE_RATE
    t0 = time.perf_counter()

    # compute mel spec once to speed up everything else
    S = np.abs(librosa.stft(y))
    oe          = librosa.onset.onset_strength(S=librosa.amplitude_to_db(S, ref=np.max), sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=oe, sr=sr)
    bpm         = float(np.atleast_1d(tempo)[0])
    
    mfcc        = librosa.feature.mfcc(S=librosa.power_to_db(S**2), sr=sr, n_mfcc=N_MFCC)
    centroid    = librosa.feature.spectral_centroid(S=S, sr=sr)
    rolloff     = librosa.feature.spectral_rolloff(S=S, sr=sr)
    bandwidth   = librosa.feature.spectral_bandwidth(S=S, sr=sr)
    zcr         = librosa.feature.zero_crossing_rate(y=y)
    rms         = librosa.feature.rms(S=S)
    chroma      = librosa.feature.chroma_stft(S=S, sr=sr)
    
    # Approx Tonnetz
    r = 2*np.pi*np.arange(12)/12
    mapping = np.array([np.sin(r), np.cos(r), np.sin(2*r), np.cos(2*r), np.sin(3*r), np.cos(3*r)])
    tonnetz     = mapping @ chroma
    
    flatness    = librosa.feature.spectral_flatness(y=y)
    hr          = float(1.0 - np.mean(flatness))
    elapsed     = (time.perf_counter() - t0) * 1000

    # Build 222-dim vector
    vec = []
    vec += [bpm, float(len(beats)), float(np.mean(oe))]        # 3
    for i in range(N_MFCC):                                      # 140
        vec += s7(mfcc[i, :])
    vec += s7(centroid)                                           # 7
    vec += s7(rolloff)                                            # 7
    vec += s7(bandwidth)                                          # 7
    vec += s7(zcr)                                                # 7
    vec += s7(rms)                                                # 7
    for p in range(12):                                           # 24
        row = chroma[p, :]
        vec += [float(np.mean(row)), float(np.std(row))]
    for d in range(6):                                            # 12
        row = tonnetz[d, :]
        vec += [float(np.mean(row)), float(np.std(row))]
    vec += [hr]                                                   # 1

    assert len(vec) == CANONICAL_DIM, f"Got {len(vec)}, expected {CANONICAL_DIM}"

    dominant = NOTES[int(np.argmax(np.mean(chroma, axis=1)))]

    return {
        "song_id": song_id, "label": label,
        "bpm": bpm, "beat_count": len(beats), "onset_mu": float(np.mean(oe)),
        "mfcc_shape": mfcc.shape,
        "mfcc0_mu": float(np.mean(mfcc[0])), "mfcc0_sd": float(np.std(mfcc[0])),
        "centroid_mu": float(np.mean(centroid)),
        "rolloff_mu":  float(np.mean(rolloff)),
        "bandwidth_mu":float(np.mean(bandwidth)),
        "zcr_mu": float(np.mean(zcr)),
        "rms_mu": float(np.mean(rms)),
        "chroma_shape": chroma.shape, "dominant": dominant,
        "tonnetz_shape": tonnetz.shape,
        "hr": hr, "vec": vec, "elapsed": elapsed,
    }

SEP = "=" * 68

songs = [
    ("song_001", 0, "Synthetic Ballad   (A2, 110 Hz)"),
    ("song_002", 1, "Synthetic Dance    (A3, 220 Hz)"),
    ("song_003", 2, "Synthetic Ambient  (E2,  82 Hz)"),
]

print()
print("+" + "=" * 66 + "+")
print("|   AUDIO FEATURE EXTRACTION PIPELINE  --  OUTPUT REPORT          |")
print("|   Extraction Version: audio_v1   |   Vector Dimension: 222      |")
print("+" + "=" * 66 + "+")

results = []
for sid, seed, label in songs:
    r = extract(sid, seed, label)
    results.append(r)
    v = r["vec"]

    print(f"\n{SEP}")
    print(f"  {r['song_id']}  |  {r['label']}")
    print(f"{SEP}")

    print(f"\n  [PREPROCESSOR]")
    print(f"    Signal       : 2.0 s, {TARGET_SAMPLE_RATE:,} Hz, mono PCM float32")

    print(f"\n  [DSP EXTRACTOR]")
    print(f"    RHYTHM")
    print(f"      Tempo (BPM)        : {r['bpm']:.2f}")
    print(f"      Beat Count         : {r['beat_count']}")
    print(f"      Onset Strength mu  : {r['onset_mu']:.4f}")
    print(f"    TIMBRAL")
    print(f"      MFCC shape         : {r['mfcc_shape']}  ({N_MFCC} coefficients x T frames)")
    print(f"      MFCC[0]  mu+/-sd   : {r['mfcc0_mu']:+.3f}  +/-  {r['mfcc0_sd']:.3f}")
    print(f"      Spectral Centroid  : {r['centroid_mu']:.1f} Hz (mean)")
    print(f"      Spectral Rolloff   : {r['rolloff_mu']:.1f} Hz (mean)")
    print(f"      Spectral Bandwidth : {r['bandwidth_mu']:.1f} Hz (mean)")
    print(f"      ZCR mean           : {r['zcr_mu']:.5f}")
    print(f"      RMS Energy mean    : {r['rms_mu']:.6f}")
    print(f"    HARMONIC")
    print(f"      Chroma shape       : {r['chroma_shape']}  (12 pitch classes x T)")
    print(f"      Dominant Pitch     : {r['dominant']}")
    print(f"      Tonnetz shape      : {r['tonnetz_shape']}  (6 tonal dims x T)")
    print(f"      Harmonic Ratio     : {r['hr']:.4f}  (0=percussive -> 1=harmonic)")

    ms = v[3:143]
    cs = v[143:150]; rs2 = v[150:157]; bs = v[157:164]
    zs = v[164:171]; es = v[171:178]; hs = v[178:202]; ts = v[202:214]

    print(f"\n  [AGGREGATOR  ->  {CANONICAL_DIM}-dim AudioFeatureVector]")
    print(f"    Total dims   : {len(v)}")
    print(f"    [ 3] Rhythm  : {v[0]:.2f} BPM  {v[1]:.0f} beats  onset_mu={v[2]:.4f}")
    print(f"    [140] MFCC   : mu={np.mean(ms):+.4f}  sd={np.std(ms):.4f}  range=[{min(ms):.3f}, {max(ms):.3f}]")
    print(f"    [  7] Centrd : mu={np.mean(cs):.2f}  sd={np.std(cs):.2f}")
    print(f"    [  7] Rolloff: mu={np.mean(rs2):.2f}  sd={np.std(rs2):.2f}")
    print(f"    [  7] BW     : mu={np.mean(bs):.2f}  sd={np.std(bs):.2f}")
    print(f"    [  7] ZCR    : mu={np.mean(zs):.5f}  sd={np.std(zs):.5f}")
    print(f"    [  7] RMS    : mu={np.mean(es):.6f}  sd={np.std(es):.6f}")
    print(f"    [ 24] Chroma : mu={np.mean(hs):.4f}  sd={np.std(hs):.4f}  range=[{min(hs):.4f},{max(hs):.4f}]")
    print(f"    [ 12] Tonnetz: mu={np.mean(ts):.5f}  sd={np.std(ts):.5f}")
    print(f"    [  1] HRatio : {v[221]:.4f}")
    prev = "  ".join(f"{x:+.4f}" for x in v[:8])
    print(f"    Preview [0:8]: {prev}  ...")
    print(f"\n    Qdrant Payload:")
    print(f"      song_id            : {r['song_id']}")
    print(f"      vector_dimension   : {len(v)}")
    print(f"      extraction_version : audio_v1")
    print(f"      tempo_bpm          : {r['bpm']:.2f}")
    print(f"      harmonic_ratio     : {r['hr']:.4f}")
    print(f"\n  Extraction time: {r['elapsed']:.1f} ms")

print(f"\n\n{SEP}")
print("  CROSS-SONG COMPARISON")
print(SEP)
hdr = "Song           BPM   HR       ZCR       RMS         Centroid  ms"
print("  " + hdr)
print("  " + "-" * len(hdr))
for r in results:
    print(f"  {r['song_id']:<14} {r['bpm']:>5.1f} {r['hr']:>6.4f} {r['zcr_mu']:>9.5f} {r['rms_mu']:>11.7f} {r['centroid_mu']:>10.1f} {r['elapsed']:>6.1f}")

print(f"\n  OK: {len(results)} songs  |  {CANONICAL_DIM}-dim vectors ready for Qdrant\n")
