import os
import tarfile
import urllib.request
from tqdm import tqdm

DATASET_URL = "http://mtg.upf.edu/static/datasets/last.fm/lastfm-dataset-1K.tar.gz"
DOWNLOAD_PATH = "datasets/raw/lastfm/lastfm-dataset-1K.tar.gz"
TARGET_DIR = "datasets/raw/lastfm"
TSV_NAME = "lastfm-dataset-1K/userid-timestamp-artid-artname-traid-traname.tsv"

def download_dataset():
    os.makedirs(TARGET_DIR, exist_ok=True)
    if not os.path.exists(DOWNLOAD_PATH):
        print(f"Downloading {DATASET_URL}...")
        # Since standard URL might redirect or Zenodo is preferred, let's try the primary URL.
        try:
            class DownloadProgressBar(tqdm):
                def update_to(self, b=1, bsize=1, tsize=None):
                    if tsize is not None:
                        self.total = tsize
                    self.update(b * bsize - self.n)
            
            req = urllib.request.Request(DATASET_URL, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response, open(DOWNLOAD_PATH, 'wb') as out_file:
                total_size = int(response.headers.get('content-length', 0))
                with DownloadProgressBar(unit='B', unit_scale=True, miniters=1, desc="Downloading") as t:
                    t.total = total_size
                    block_size = 1024 * 8
                    while True:
                        buffer = response.read(block_size)
                        if not buffer:
                            break
                        out_file.write(buffer)
                        t.update(len(buffer))
                        
        except Exception as e:
            print(f"Failed to download from primary URL: {e}")
            print("Trying Zenodo fallback...")
            # We can skip Zenodo for now if this fails and just stop.

def extract_subset(num_lines=100000):
    print(f"Extracting first {num_lines} lines for smoke test...")
    subset_path = os.path.join(TARGET_DIR, f"lastfm_subset_{num_lines}.tsv")
    
    if os.path.exists(subset_path):
        print(f"Subset already exists at {subset_path}")
        return subset_path

    with tarfile.open(DOWNLOAD_PATH, "r:gz") as tar:
        member = tar.getmember(TSV_NAME)
        f_in = tar.extractfile(member)
        with open(subset_path, "wb") as f_out:
            for i, line in enumerate(f_in):
                if i >= num_lines:
                    break
                f_out.write(line)
                
    print(f"Subset created at {subset_path}")
    return subset_path

def extract_full():
    print("Extracting full dataset...")
    full_path = os.path.join(TARGET_DIR, "lastfm_full.tsv")
    if os.path.exists(full_path):
        print(f"Full dataset already exists at {full_path}")
        return full_path
        
    with tarfile.open(DOWNLOAD_PATH, "r:gz") as tar:
        member = tar.getmember(TSV_NAME)
        f_in = tar.extractfile(member)
        with open(full_path, "wb") as f_out:
            # Chunk read to save memory
            while True:
                chunk = f_in.read(1024 * 1024 * 64)
                if not chunk:
                    break
                f_out.write(chunk)
                
    print(f"Full dataset created at {full_path}")
    return full_path

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true")
    args = parser.parse_args()
    
    download_dataset()
    if args.full:
        extract_full()
    else:
        extract_subset(100000)
