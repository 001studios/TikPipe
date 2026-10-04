# TikTok Feed Harvester & Fast Downloader

A high-performance automated script for Windows designed to intercept and download videos from your TikTok **"For You" Page (FYP)** in original quality, watermark-free, utilizing your active session, and in the universally compatible **H.264 (AVC) + AAC** format.

---

## Prerequisites

Before getting started, make sure your computer meets the following requirements:

1. **Windows 10 or 11 (64-bit)**.
2. **Python 3.10 or higher** (compatible with Python 3.11, 3.12, and 3.13).
   * When installing Python, make sure to check the box that says **"Add python.exe to PATH"** on the first setup screen.
3. **Google Chrome** installed officially on your system.

---

## Project Structure

Your project directory (e.g., `D:\tiktok extractor\`) should be organized as follows:

```text
tiktok extractor/
│
├── user.py                     # Main capture and download script
├── requirements.txt            # Python dependencies list
├── update_dependencies.bat     # 1-click dependency installer/updater
├── setup_login.py              # One-time login helper script
├── config.json                 # Configuration file (auto-generated on first run)
├── videos.txt                  # Temporary file storing extracted URLs
└── perfil_navegador/           # Persistent folder storing your Chrome session
```

---

## Step 1: Install Dependencies

1. Open the project folder.
2. **Double-click** the file **`update_dependencies.bat`**.
3. A command prompt window will open and automatically execute:
   * Upgrading the `pip` package manager.
   * Installing `yt-dlp`, `playwright`, and `curl_cffi`.
   * Downloading the Chromium browser binaries for Playwright.
4. When it completes and displays `ALL DEPENDENCIES INSTALLED AND UPDATED SUCCESSFULLY!`, press any key to close the window.

---

## Step 2: One-Time Session Setup (Login)

To allow the program to access your personalized "For You" feed, it must use your active account. To prevent Google from blocking your login with the *"This browser or app may not be secure"* error, a native launch setup is used:

1. Create a file named **`setup_login.py`** in the project folder with the following content:

```python
import os
import subprocess
import sys

CARPETA_SESION = os.path.abspath("./perfil_navegador")
os.makedirs(CARPETA_SESION, exist_ok=True)

chrome_paths = [
    os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
    os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
]

chrome_exe = next((p for p in chrome_paths if os.path.exists(p)), None)

if not chrome_exe:
    print("Error: Google Chrome was not found on your system.")
    sys.exit(1)

print("Launching Google Chrome for session setup...")
print("1. Log in to Google and TikTok in the browser tabs that will open.")
print("2. Once your TikTok account is visible and active, simply CLOSE the Chrome window.")

process = subprocess.Popen([
    chrome_exe,
    f"--user-data-dir={CARPETA_SESION}",
    "--no-first-run",
    "https://accounts.google.com",
    "https://www.tiktok.com/login"
])
process.wait()
print("Session successfully saved to ./perfil_navegador!")
```

2. Close all existing Google Chrome windows running on your PC.
3. Open a terminal in the project directory and run:
   ```cmd
   python setup_login.py
   ```
4. A fresh Chrome window will launch:
   * In the first tab, sign in to your Google account.
   * In the second tab, click **"Continue with Google"** on TikTok (it will sign in automatically).
5. **Close the Chrome window using the red "X" button.**
6. Your session is now securely saved in `perfil_navegador`, and you will not need to sign in again.

---

## Step 3: Configuration (`config.json`)

The first time you run `user.py`, it will automatically create `config.json`. You can open it in **Notepad** to customize your settings:

```json
{
    "download_path": "D:\\tiktok extractor\\TikTok_Downloads",
    "video_count": 10,
    "concurrent_downloads": 6
}
```

* **`download_path`**: The folder where downloaded videos will be stored (you can set any valid directory path).
* **`video_count`**: The number of videos you want to harvest from your feed per execution.
* **`concurrent_downloads`**: How many videos are downloaded simultaneously in parallel (recommended range: 4 to 8).

---

## Step 4: Running the Program

Whenever you want to download videos:

1. Open your terminal in the project folder.
2. Run:
   ```cmd
   python user.py
   ```
3. The program will:
   * Launch Chrome in the background with your saved session.
   * Block on-screen images and video playback to save network bandwidth.
   * Intercept your "For You" network feed packets.
   * **Download videos concurrently in real time** while it continues to scroll.
   * Automatically truncate `videos.txt` upon completion and notify you in the console.

---

## FAQ & Troubleshooting

#### 1. Why do I see a "Database is locked" error or Chrome fails to open?
Make sure you do not have another Google Chrome window open using the same profile folder (`perfil_navegador`) before launching the script.

#### 2. Do the downloaded videos have watermarks?
No. `yt-dlp` extracts the clean, original-quality media streams directly from ByteDance/TikTok content delivery networks.

#### 3. How do I download from a specific creator profile instead of my "For You" feed?
In `user.py`, find the following line:
```python
page.goto("https://www.tiktok.com/foryou")
```
And replace it with the desired profile URL:
```python
page.goto("https://www.tiktok.com/@username")
```