import os
import subprocess
from pathlib import Path


def launch_application(executable_path: str):
    if not executable_path:
        raise FileNotFoundError("No executable path is configured for this application.")

    path = Path(executable_path.strip().strip('"'))
    if not path.exists():
        raise FileNotFoundError(f"Application path not found:\n{path}")

    # Popen is non-blocking, so FaceGuard remains responsive after launching.
    if path.suffix.lower() == ".exe":
        subprocess.Popen([str(path)], cwd=str(path.parent))
    else:
        subprocess.Popen([str(path)], cwd=str(path.parent))


def launch_special_windows_target(app_name: str):
    """Optional helper for Windows shell targets configured as commands."""
    if app_name == "File Explorer":
        subprocess.Popen(["explorer.exe"])
        return True
    if app_name == "Calculator":
        subprocess.Popen(["calc.exe"])
        return True
    return False
