import sys
import os
import glob
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    import static_ffmpeg
    static_ffmpeg.add_paths()
    print("ffmpeg binaries initialized via static-ffmpeg.")
except Exception as e:
    print(f"static-ffmpeg initialization note: {e}")

TARGET_DIR = os.path.join("datasets", "raw", "audio_samples")

def convert_all():
    webm_files = glob.glob(os.path.join(TARGET_DIR, "*.webm"))
    m4a_files = glob.glob(os.path.join(TARGET_DIR, "*.m4a"))
    files = webm_files + m4a_files
    print(f"Found {len(files)} audio files needing conversion to MP3 in {TARGET_DIR}...\n")

    converted = 0
    for f in files:
        base, _ = os.path.splitext(f)
        mp3_out = base + ".mp3"
        if not os.path.exists(mp3_out):
            print(f"Converting: {os.path.basename(f)} -> {os.path.basename(mp3_out)}")
            try:
                cmd = ["ffmpeg", "-y", "-i", f, "-vn", "-ab", "192k", mp3_out]
                subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
                converted += 1
                try:
                    os.remove(f)
                except Exception:
                    pass
            except Exception as e:
                print(f"  Conversion failed for {os.path.basename(f)}: {e}")
        else:
            try:
                os.remove(f)
            except Exception:
                pass

    print(f"\nFinished converting {converted} files to MP3!")

if __name__ == "__main__":
    convert_all()
