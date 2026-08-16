import argparse
import pandas as pd
import os

def inspect(filepath: str):
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        return

    print(f"Inspecting dataset: {filepath}")
    file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
    print(f"File size: {file_size_mb:.2f} MB")
    
    # Try reading as TSV then CSV
    try:
        df = pd.read_csv(filepath, sep='\t', nrows=5)
        print("\nRead as TSV successfully. Columns:")
        print(df.columns.tolist())
        print("\nFirst 5 rows:")
        print(df)
    except Exception as e:
        print(f"Failed to read as TSV: {e}")
        try:
            df = pd.read_csv(filepath, nrows=5)
            print("\nRead as CSV successfully. Columns:")
            print(df.columns.tolist())
            print("\nFirst 5 rows:")
            print(df)
        except Exception as e2:
            print(f"Failed to read as CSV: {e2}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inspect a raw dataset file.")
    parser.add_argument("filepath", type=str, help="Path to the raw dataset file.")
    args = parser.parse_args()
    inspect(args.filepath)
