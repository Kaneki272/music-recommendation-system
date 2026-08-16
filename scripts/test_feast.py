import sys
import subprocess
with open("trace.txt", "w") as f:
    f.write("Starting script...\n")
    try:
        f.write("Running feast apply...\n")
        out = subprocess.run("cd feature_store/repo && feast apply", shell=True, capture_output=True)
        f.write("Return code: " + str(out.returncode) + "\n")
        f.write("Stdout: " + out.stdout.decode('utf-8') + "\n")
        f.write("Stderr: " + out.stderr.decode('utf-8') + "\n")
    except Exception as e:
        f.write("Exception: " + str(e) + "\n")
