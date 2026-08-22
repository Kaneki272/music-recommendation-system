import sys
import os
import subprocess

TARGET_DIR = os.path.join("datasets", "raw", "audio_samples")

def install_ytdlp():
    try:
        import yt_dlp
    except ImportError:
        print("Installing yt-dlp package...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "yt-dlp"])

def download_youtube(url_or_query: str):
    install_ytdlp()
    import yt_dlp

    os.makedirs(TARGET_DIR, exist_ok=True)
    out_template = os.path.join(TARGET_DIR, "%(title)s.%(ext)s")

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': out_template,
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        # Fallback if ffmpeg is missing
        'prefer_ffmpeg': False,
        'ignoreerrors': True,
    }

    print(f"\nDownloading audio from: {url_or_query}")
    print(f"Target Directory: {TARGET_DIR}\n")

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url_or_query])

    print(f"\nDone! Downloaded files placed in {TARGET_DIR}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/download_youtube_audio.py <YOUTUBE_URL_OR_PLAYLIST>")
        print("Example: python scripts/download_youtube_audio.py https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        sys.exit(1)

    url = sys.argv[1]
    download_youtube(url)
