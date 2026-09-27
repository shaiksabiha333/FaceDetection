# FaceGuard – Multi-Factor Face-Based Application Authentication System

A local Windows desktop application using Python, CustomTkinter, SQLite and OpenCV LBPH.

## Security flow

1. Select a registered FaceGuard user.
2. Select an application assigned to that user.
3. Enter that user's private PIN.
4. Only after a correct PIN, FaceGuard opens the webcam.
5. The webcam checks the face against that same user's registered LBPH model.
6. FaceGuard checks application permission.
7. Only if PIN + same-user face + permission all succeed is the Windows application launched.
8. Every attempt is recorded in SQLite.

PINs are stored as salted PBKDF2-SHA256 hashes. PIN values are never written to logs.

## Windows installation

Open PowerShell in the FaceGuard folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\.venv\Scripts\Activate.ps1
```

## First run

1. Click **Admin Setup / Registration**.
2. Open **Application Paths** and configure the actual executable paths on your PC.
3. Open **Register User**.
4. Enter full name, unique username, PIN and confirmation.
5. Select allowed applications.
6. Click **Register User & Capture Face**.
7. Follow the camera window. Keep only one person in view and make small natural changes in angle/expression.
8. When 35 samples are collected, the LBPH model is saved locally.
9. Close Admin and select the registered user from the welcome screen.
10. Open an assigned application and complete PIN + face authentication.

## Typical Windows executable paths

These vary by installation. Use the Settings screen rather than assuming these paths.

- Chrome: usually `C:\Program Files\Google\Chrome\Application\chrome.exe`
- VS Code: commonly under `%LocalAppData%\Programs\Microsoft VS Code\Code.exe`
- WhatsApp: the Microsoft Store version may not expose a simple traditional EXE path. If so, choose a launchable executable/shortcut target available on your installation.
- Calculator: `C:\Windows\System32\calc.exe`
- File Explorer: the app launcher uses `explorer.exe` directly.

## OpenCV requirement

FaceGuard requires `opencv-contrib-python` because the LBPH recognizer is part of the OpenCV contrib face module.

Do not install `opencv-python` alongside it in the same environment. If both are installed, remove both and reinstall only contrib:

```powershell
pip uninstall opencv-python opencv-contrib-python -y
pip install opencv-contrib-python
```

## Webcam troubleshooting

- Windows Settings -> Privacy & security -> Camera -> allow desktop apps to access the camera.
- Close other programs using the webcam.
- Try restarting FaceGuard.
- Press ESC in the OpenCV camera window to cancel registration or verification.

## Data and privacy

All data remains local:

- SQLite database: `data/faceguard.db`
- LBPH models: `data/face_models/`
- Temporary face samples are held in memory during registration and are not saved as image files.
- No cloud API or external server is used.

The face model is biometric data, so protect the Windows account and FaceGuard folder with normal OS security.

## Important limitation

LBPH is a traditional local face recognizer, not a high-security biometric system. Lighting, camera quality, pose, and similar faces can affect results. For a classroom/B.Tech project it provides a fully local demonstration of the requested architecture, but it should not be treated as a replacement for Windows Hello or enterprise-grade authentication.

## Project structure

```text
FaceGuard/
├── main.py
├── config.py
├── database.py
├── authentication.py
├── face_detection.py
├── face_recognition.py
├── registration.py
├── app_launcher.py
├── security_log.py
├── dashboard.py
├── settings.py
├── requirements.txt
├── README.md
├── data/
│   ├── faces/
│   └── face_models/
├── logs/
└── assets/
```
