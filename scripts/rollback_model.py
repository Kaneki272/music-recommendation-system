import os
import sys
import json
import argparse
from datetime import datetime

MODELS_DIR = os.path.join(os.path.dirname(__file__), "..", "models", "als")
ACTIVE_FILE = os.path.join(MODELS_DIR, "active.json")

def list_versions():
    versions = []
    for d in os.listdir(MODELS_DIR):
        path = os.path.join(MODELS_DIR, d)
        if os.path.isdir(path) and os.path.exists(os.path.join(path, "model.pkl")):
            try:
                with open(os.path.join(path, "metadata.json"), "r") as f:
                    meta = json.load(f)
                    versions.append(meta)
            except:
                versions.append({"model_version": d, "trained_at": "unknown"})
    return sorted(versions, key=lambda x: x.get("trained_at", ""), reverse=True)

def main():
    parser = argparse.ArgumentParser(description="Rollback ALS model version")
    parser.add_argument("--version", type=str, help="Version to rollback to. If omitted, lists available versions.")
    args = parser.parse_args()
    
    if not args.version:
        print("Available Model Versions (newest first):")
        versions = list_versions()
        for v in versions:
            print(f"- {v['model_version']} (Trained: {v.get('trained_at')})")
            metrics = v.get("metrics", {})
            if metrics:
                print(f"  NDCG@10: {metrics.get('NDCG@10', 0):.4f} | HR@10: {metrics.get('HitRate@10', 0):.4f}")
        print("\nTo rollback, run: python scripts/rollback_model.py --version <version_id>")
        return
        
    target_dir = os.path.join(MODELS_DIR, args.version)
    if not os.path.exists(target_dir) or not os.path.exists(os.path.join(target_dir, "model.pkl")):
        print(f"Error: Version '{args.version}' not found or invalid.")
        return
        
    print(f"Rolling back active model to: {args.version}")
    with open(ACTIVE_FILE, "w") as f:
        json.dump({
            "active_version": args.version,
            "promoted_at": datetime.now().isoformat(),
            "reason": "rollback"
        }, f, indent=2)
        
    print("Rollback successful. The backend will use this version on next reload.")

if __name__ == "__main__":
    main()
