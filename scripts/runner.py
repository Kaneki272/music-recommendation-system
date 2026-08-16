import subprocess
import os
try:
    env = os.environ.copy()
    env["PYTHONPATH"] = "."
    result = subprocess.run(["python", "scripts/run_e2e_feature_pipeline.py"], capture_output=True, text=True, env=env)
    with open("e2e_stdout.txt", "w", encoding="utf-8") as f:
        f.write(result.stdout)
    with open("e2e_stderr.txt", "w", encoding="utf-8") as f:
        f.write(result.stderr)
    print("Return code:", result.returncode)
except Exception as e:
    print(e)
