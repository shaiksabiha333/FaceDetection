from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FACE_DIR = DATA_DIR / "faces"
MODEL_DIR = DATA_DIR / "face_models"
LOG_DIR = BASE_DIR / "logs"
ASSET_DIR = BASE_DIR / "assets"
DB_PATH = DATA_DIR / "faceguard.db"

FACE_SIZE = (200, 200)
FACE_SAMPLES_REQUIRED = 35
FACE_CONFIDENCE_THRESHOLD = 65.0  # Lower LBPH confidence is better.

DEFAULT_APPLICATIONS = [
    ("PythonIDLE", ""),
    ("Google Chrome", ""),
    ("Visual Studio Code", ""),
    ("Calculator", ""),
    ("File Explorer", ""),
]
for directory in (DATA_DIR, FACE_DIR, MODEL_DIR, LOG_DIR, ASSET_DIR):
    directory.mkdir(parents=True, exist_ok=True)
