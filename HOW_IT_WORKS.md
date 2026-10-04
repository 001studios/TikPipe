# Internal Architecture and Technical Overview

This document provides a detailed breakdown of the internal architecture, data pipeline, and design decisions implemented in `user.py` to facilitate easy maintenance, debugging, and extension.

---

## 1. Pipeline Flowchart

```text
[ user.py ]
    │
    ├── 1. Configuration Loading (config.json)
    │
    ├── 2. ThreadPoolExecutor Initialization (Concurrent worker pool)
    │
    ├── 3. Playwright Initialization (Persistent Context + Anti-bot Evasion)
    │       │
    │       ├── Route Blocking (Aborts images, video playback, and web fonts)
    │       │
    │       └── Network Interception (Event listener on page.on("response"))
    │               │
    │               └── Upon detecting JSON containing "itemList":
    │                       ├── Extracts video_id and author
    │                       ├── Constructs canonical URL
    │                       └── Immediately dispatches URL to ThreadPoolExecutor
    │
    ├── 4. Active Scrolling (ArrowDown + Mouse Wheel) -> Triggers API pagination
    │
    ├── 5. Browser Shutdown (Triggered upon reaching TARGET_COUNT)
    │
    ├── 6. Download Synchronization (Active polling via as_completed)
    │       └── yt-dlp downloads with TLS impersonation (curl_cffi)
    │
    └── 7. Cleanup (Truncates videos.txt to 0 bytes)
```

---

## 2. Detailed Technical Components

### A. Session Persistence and Anti-Detection (`launch_persistent_context`)
Instead of launching an ephemeral browser instance without user data or cookies, the script uses:

```python
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
```

* **`user_data_dir`**: Persists authentication cookies on disk using Chromium's native SQLite storage, allowing previously established sessions to be reused.
* **`channel="chrome"`**: Executes the system's official Google Chrome binary rather than the bare Chromium testing build.
* **`--disable-blink-features=AutomationControlled` & `ignore_default_args`**: Strips the internal Blink automation flags and the automation infobar to evade client-side bot detection scripts.

---

### B. Network Bandwidth Optimization (`page.route`)
On desktop browsers, TikTok aggressively buffers media files (between 10 MB and 30 MB per visible feed item). To prevent the browser from consuming bandwidth needed by concurrent download threads, the script blocks these heavy assets at the network layer:

```python
def block_heavy_resources(route):
    if route.request.resource_type in ["image", "media", "font"]:
        route.abort()
    else:
        route.continue_()

page.route("**/*", block_heavy_resources)
```

* **`image`**: Cancels avatar images, video thumbnails, and decorative banners.
* **`media`**: Blocks incoming MP4 and audio streams attempting to play in the browser viewport.
* **`font`**: Prevents external web font downloads.
* **Result:** The browser only transfers lightweight HTML and JSON responses, dedicating nearly 100% of available network bandwidth to `yt-dlp`.

---

### C. Traffic Interception (No DOM Scraping)
TikTok's desktop web player implements **DOM virtualization**: elements above the current viewport are dynamically unmounted and destroyed from memory to keep the page responsive. Furthermore, TikTok does not use standard `<a href="...">` anchor tags on feed videos.

Traditional DOM scraping will frequently fail or miss elements. To address this, the script listens directly to incoming HTTP API responses:

```python
def intercept_and_download(response):
    url = response.url
    if ("item_list" in url or "feed" in url) and response.status == 200:
        data = response.json()
        items = data.get("itemList", [])
        for item in items:
            video_id = item.get("id")
            author = item.get("author", {}).get("uniqueId")
            link = f"https://www.tiktok.com/@{author}/video/{video_id}"
```

Whenever scrolling triggers a request to endpoints like `/api/recommend/item_list/` or `/feed/`, the script parses the raw JSON payload and extracts the canonical video ID and creator handle with 100% accuracy.

---

### D. Concurrent Producer-Consumer Pipeline
Traditional scraping tools operate sequentially: gather all links first, then download all links.

`user.py` implements a **Producer-Consumer** pattern:
1. **Producer:** The automated Playwright browser scrolling and intercepting network packets.
2. **Consumer:** A background `ThreadPoolExecutor` managing concurrent download workers.

The instant a unique video is intercepted:

```python
fut = executor.submit(download_single_video, link)
download_futures.append(fut)
```

The task is submitted immediately to an available background worker. By the time the browser reaches its target count and closes, most videos have already finished downloading to disk.

---

### E. TLS Fingerprint Impersonation via `curl_cffi`
TikTok content delivery networks (CDNs) enforce TLS fingerprint verification (JA3/JA4). Standard Python HTTP libraries (such as `requests` or `urllib`) are rejected with `HTTP 403 Forbidden` responses.

Installing **`curl_cffi`** allows `yt-dlp` to replace its underlying transport engine with a C-based implementation that replicates Google Chrome's native TLS handshake (`Client Hello`, cipher suites, and TLS extensions), ensuring reliable media downloads.

---

### F. Format Hierarchy Matrix (`YDL_OPTS`)
To ensure universal format compatibility without relying on CPU-intensive local FFmpeg re-encoding, the format selection is defined as:

```python
'format': (
    'bestvideo[vcodec^=avc]+bestaudio[acodec=mp4a.40.2]/'
    'best[acodec=mp4a.40.2]/'
    'bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]/'
    'best[vcodec^=avc]/'
    'best'
)
```

1. **`bestvideo[vcodec^=avc]+bestaudio[acodec=mp4a.40.2]`**: Prioritizes H.264 (AVC) video paired with standard **AAC-LC** audio (Audio Object Type 2, **without SBR**).
2. **`best[acodec=mp4a.40.2]`**: Prioritizes single pre-muxed streams containing standard non-SBR audio.
3. **`bestvideo[vcodec^=avc]+bestaudio[acodec^=mp4a]`**: If a non-SBR version is unavailable on TikTok's servers, it gracefully falls back via `/` to the available SBR stream (`mp4a.40.5`).
4. **`merge_output_format: 'mp4'`**: Guarantees that the resulting media container is `.mp4`.
5. **`buffersize: 4MB`**: Allocates an in-memory buffer to optimize disk write speed and high-bandwidth network connections.

---

## 3. Developer Modification Guide

### Adjusting the Scroll Frequency
In `user.py`, locate the scrolling loop inside `run_live_extractor`:
```python
page.keyboard.press("ArrowDown")
page.mouse.wheel(0, 500)
time.sleep(0.8)  # Lower to 0.5 for fast connections, or raise to 1.2 on lower-spec hardware
```

### Customizing Output Filenames
Modify the `'outtmpl'` parameter in `YDL_OPTS`:
```python
# Default format: uploader_id.mp4
'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(uploader)s_%(id)s.%(ext)s'),

# Alternative format with date and title:
'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(upload_date)s - %(title)s.%(ext)s'),
```

### Extracting Audio Only (MP3)
If you want to adapt the pipeline to extract only the audio tracks from your feed, configure `YDL_OPTS` as follows:
```python
YDL_OPTS = {
    'format': 'bestaudio/best',
    'outtmpl': os.path.join(DOWNLOAD_FOLDER, '%(uploader)s_%(id)s.%(ext)s'),
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'mp3',
        'preferredquality': '192',
    }],
    'quiet': True,
}
```