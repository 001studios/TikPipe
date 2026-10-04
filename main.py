import os
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from playwright.sync_api import sync_playwright
import yt_dlp

# ==========================================================
# CONFIGURATION MANAGER (config.json)
# ==========================================================
CONFIG_FILE = "config.json"

def load_configuration():
    default_config = {
        "download_path": os.path.abspath("./TikTok_Downloads"),
        "video_count": 10,
        "concurrent_downloads": 6
    }

    if not os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_config, f, indent=4)
        return default_config

    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        # Backwards compatibility: supports both English and Spanish keys
        path = config.get("download_path") or config.get("ruta_descargas") or default_config["download_path"]
        count = config.get("video_count") or config.get("cantidad_videos") or default_config["video_count"]
        concurrency = config.get("concurrent_downloads") or config.get("descargas_simultaneas") or default_config["concurrent_downloads"]

        return {
            "download_path": os.path.abspath(path),
            "video_count": int(count),
            "concurrent_downloads": int(concurrency)
        }
    except Exception:
        return default_config


CONFIG = load_configuration()
# Keeps your existing login session folder intact:
SESSION_FOLDER = os.path.abspath("./perfil_navegador")
LINKS_FILE = "videos.txt"
DOWNLOAD_FOLDER = CONFIG["download_path"]
TARGET_COUNT = CONFIG["video_count"]
CONCURRENCY = CONFIG["concurrent_downloads"]

os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)


# ==========================================================
# DIRECT DOWNLOAD CONFIGURATION (NO FFMPEG CONVERSION)
# ==========================================================
YDL_OPTS = {
    # 1. Prioritizes H.264 with standard AAC-LC audio (mp4a.40.2 without SBR)
    # 2. If not available on TikTok servers, falls back to the SBR version
    'format': (
        'bestvideo[vcodec^=avc]+bestaudio[acodec=mp4a.40.2]/'
        'best[acodec=mp4a.40.2]/'
        'bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/'
        'best[vcodec^=avc]/'
        'best'
    ),
    'merge_output_format': 'mp4',
    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(uploader)s_%(id)s.%(ext)s'),
    'ignoreerrors': True,
    'nooverwrites': True,
    'quiet': True,
    'buffersize': 1024 * 1024 * 4,  # 4MB buffer for maximum network throughput
}

def download_single_video(url):
    try:
        with yt_dlp.YoutubeDL(YDL_OPTS) as ydl:
            ydl.download([url])
        return True, url
    except Exception:
        return False, url


# ==========================================================
# MAIN ENGINE: SIMULTANEOUS CAPTURE AND DOWNLOAD PIPELINE
# ==========================================================
def run_live_extractor(target_count):
    intercepted_videos = set()
    download_futures = []

    # Thread pool active from the very start
    executor = ThreadPoolExecutor(max_workers=CONCURRENCY)

    # Clear previous links file
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            pass

    print("\n" + "="*65)
    print("STARTING PIPELINE MODE: LIVE CAPTURE & DIRECT DOWNLOAD")
    print(f"Target: {target_count} videos | Parallel Threads: {CONCURRENCY}")
    print(f"Destination: {DOWNLOAD_FOLDER}")
    print("="*65 + "\n")

    with sync_playwright() as p:
        print("Launching optimized browser...")

        context = p.chromium.launch_persistent_context(
            user_data_dir=SESSION_FOLDER,
            channel="chrome",
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--start-maximized"
            ],
            ignore_default_args=["--enable-automation"],
            no_viewport=True
        )

        page = context.pages[0] if context.pages else context.new_page()

        # NETWORK BANDWIDTH OPTIMIZATION:
        # Blocks images, media, and fonts so Chrome doesn't waste network streaming videos on-screen
        def block_heavy_resources(route):
            if route.request.resource_type in ["image", "media", "font"]:
                route.abort()
            else:
                route.continue_()

        page.route("**/*", block_heavy_resources)

        # INTERCEPTOR WITH IMMEDIATE QUEUEING
        def intercept_and_download(response):
            url = response.url
            if ("item_list" in url or "feed" in url) and response.status == 200:
                try:
                    data = response.json()
                    items = data.get("itemList", [])
                    for item in items:
                        if len(intercepted_videos) >= target_count:
                            break
                        video_id = item.get("id")
                        author = item.get("author", {}).get("uniqueId")
                        if video_id and author:
                            link = f"https://www.tiktok.com/@{author}/video/{video_id}"
                            if link not in intercepted_videos:
                                intercepted_videos.add(link)
                                num = len(intercepted_videos)
                                print(f"-> [{num}/{target_count}] Intercepted and queued: @{author}")

                                with open(LINKS_FILE, "a", encoding="utf-8") as f:
                                    f.write(f"{link}\n")

                                # Immediate background download
                                fut = executor.submit(download_single_video, link)
                                download_futures.append(fut)
                except Exception:
                    pass

        page.on("response", intercept_and_download)

        print("Navigating to 'For You' feed...")
        page.goto("https://www.tiktok.com/foryou")

        # Accelerated scrolling loop
        elapsed_seconds = 0
        while len(intercepted_videos) < target_count and elapsed_seconds < 35:
            if len(intercepted_videos) >= target_count:
                break
            page.keyboard.press("ArrowDown")
            page.mouse.wheel(0, 500)
            time.sleep(0.8)
            elapsed_seconds += 0.8

        print(f"\nAll {len(intercepted_videos)} videos intercepted! Closing browser...")
        context.close()

    # WAIT FOR REMAINING BACKGROUND DOWNLOADS TO FINISH
    print("\nWaiting for active downloads to finish...")
    completed = 0
    total = len(download_futures)

    for f in as_completed(download_futures):
        ok, link = f.result()
        completed += 1
        if ok:
            print(f"[{completed}/{total}] Download finished: {link}")
        else:
            print(f"[{completed}/{total}] Failed: {link}")

    executor.shutdown(wait=True)

    # CLEAR LINKS FILE UPON COMPLETION
    if os.path.exists(LINKS_FILE):
        with open(LINKS_FILE, "w", encoding="utf-8") as f:
            pass
        print(f"\n-> '{LINKS_FILE}' cleared successfully.")

    print("\n" + "="*65)
    print("PROCESS COMPLETED AT MAXIMUM SPEED!")
    print(f"Videos saved to: {DOWNLOAD_FOLDER}")
    print("="*65)


if __name__ == "__main__":
    run_live_extractor(TARGET_COUNT)