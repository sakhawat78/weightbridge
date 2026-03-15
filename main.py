"""
main.py — Entry Point for WeighBridge Pro v2.0

Usage:
    python main.py

This is a lightweight wrapper around the main application implementation in
`weightbridge.py`. It ensures dependencies are installed and then launches the
Tkinter UI.
"""

import sys
import subprocess
import os

# ─────────────────────────── DEPENDENCY CHECK ────────────────────────────────
REQUIRED = {
    "serial":     "pyserial",
    "openpyxl":   "openpyxl",
    "fpdf":       "fpdf2",
    "matplotlib": "matplotlib",
    "PIL":        "Pillow",
}


def ensure_deps():
    missing = []
    for mod, pkg in REQUIRED.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"WeighBridge Pro — Installing missing packages: {', '.join(missing)}")
        try:
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install"] + missing,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print("Packages installed successfully.")
        except Exception as e:
            print(f"Warning: could not auto-install: {e}")
            print("You can install manually with:")
            print(f"  pip install {' '.join(missing)}")


# ─────────────────────────── MAIN ────────────────────────────────────────────
if __name__ == "__main__":
    # Change working directory to the script's folder so database and resources resolve.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    ensure_deps()

    # The actual UI/application logic lives in weightbridge.py
    import weightbridge

    weightbridge.init_db()
    app = weightbridge.LoginWindow()
    app.mainloop()
