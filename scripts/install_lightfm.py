import urllib.request
import tarfile
import os
import subprocess
import builtins

def install_lightfm():
    print("Downloading lightfm source...")
    url = "https://files.pythonhosted.org/packages/source/l/lightfm/lightfm-1.17.tar.gz"
    urllib.request.urlretrieve(url, "lightfm-1.17.tar.gz")
    
    print("Extracting...")
    with tarfile.open("lightfm-1.17.tar.gz", "r:gz") as tar:
        tar.extractall()
    
    print("Patching setup.py for Python 3.12 compatibility...")
    setup_path = "lightfm-1.17/setup.py"
    with open(setup_path, "r") as f:
        content = f.read()
    
    # Python 3.12 removed the ability for setup.py to rely on builtins injection the way lightfm does
    # We will just patch setup.py to not rely on __LIGHTFM_SETUP__
    content = content.replace("builtins.__LIGHTFM_SETUP__ = True", "import os; os.environ['LIGHTFM_SETUP'] = 'True'")
    content = content.replace("if not hasattr(builtins, '__LIGHTFM_SETUP__'):", "if not os.environ.get('LIGHTFM_SETUP'):")
    
    with open(setup_path, "w") as f:
        f.write(content)
        
    init_path = "lightfm-1.17/lightfm/__init__.py"
    with open(init_path, "r") as f:
        content = f.read()
    content = content.replace("import builtins", "import builtins, os")
    content = content.replace("if hasattr(builtins, '__LIGHTFM_SETUP__') and builtins.__LIGHTFM_SETUP__:", "if os.environ.get('LIGHTFM_SETUP'):")
    with open(init_path, "w") as f:
        f.write(content)

    print("Installing patched lightfm...")
    os.chdir("lightfm-1.17")
    subprocess.run(["pip", "install", "Cython", "numpy", "scipy"], check=True)
    subprocess.run(["pip", "install", "--no-build-isolation", "."], check=True)
    
if __name__ == "__main__":
    install_lightfm()
