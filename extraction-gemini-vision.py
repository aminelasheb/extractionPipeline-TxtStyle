import os
import time
import json
from collections import deque
from typing import Optional

import PIL.Image
from google import genai
from config import STYLE_MODE  # <--- add this


# =========================
# CONFIG — EDIT AS NEEDED
# =========================
MODEL_NAME = "gemini-2.5-flash"

# Set these to what your Google AI Studio dashboard shows
MAX_RPM = 10          # requests per minute
MAX_RPD = 250         # requests per day
# Optional: tiny spacing to smooth bursts after retries (seconds)
POST_SUCCESS_PAUSE = 0.25

# ---- Booléen de mode style / normal ----
# True  => utilise promptStyle.txt + extractionOutStyle
# False => utilise prompt.txt      + extractionOut

# Project layout
api_key_path = r"C:\Users\lasheb\PycharmProjects\MALIN-extraction-with-images\apikey.txt"
base_dir = r"C:\Users\lasheb\PycharmProjects\extractionPipeline-TS"
image_dir = os.path.join(base_dir, "files-out")
text_dir = os.path.join(base_dir, "files_style")

if STYLE_MODE:
    prompt_file = os.path.join(base_dir, "promptStyle.txt")
    output_dir = os.path.join(base_dir, "extractionOutStyle")
else:
    prompt_file = os.path.join(base_dir, "prompt.txt")
    output_dir = os.path.join(base_dir, "extractionOut")

os.makedirs(output_dir, exist_ok=True)


# =========================
# RATE LIMITER (leaky bucket)
# =========================
_one_min = 60.0
_one_day = 86400.0
_minute_window = deque()
_day_window = deque()

def _purge_windows(now: float) -> None:
    while _minute_window and (now - _minute_window[0]) >= _one_min:
        _minute_window.popleft()
    while _day_window and (now - _day_window[0]) >= _one_day:
        _day_window.popleft()

def allow_request() -> None:
    """
    Blocks until it's safe to fire one more request under RPM/RPD caps.
    Raises RuntimeError if daily cap is reached.
    """
    while True:
        now = time.time()
        _purge_windows(now)

        if len(_day_window) >= MAX_RPD:
            raise RuntimeError(f"Daily request limit reached ({MAX_RPD}).")

        if len(_minute_window) < MAX_RPM:
            _minute_window.append(now)
            _day_window.append(now)
            return

        # Need to wait for the earliest minute slot to expire
        sleep_for = _one_min - (now - _minute_window[0]) + 0.05
        time.sleep(max(0.05, sleep_for))


# =========================
# UTILITIES
# =========================
def read_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

def clean_fenced_json(text: str) -> str:
    t = text.strip()
    if t.startswith("```json"):
        t = t[len("```json"):].strip()
    if t.startswith("```"):
        t = t[len("```"):].strip()
    if t.endswith("```"):
        t = t[:-3].strip()
    return t

def save_json_safely(raw_text: str, out_path: str) -> None:
    """
    Try to parse the model output as JSON and pretty-print it.
    If parsing fails, save the raw text to help debug.
    """
    cleaned = clean_fenced_json(raw_text)
    try:
        parsed = json.loads(cleaned)
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
    except Exception:
        # Fallback: save the cleaned text (still useful)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

def load_api_key(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


# =========================
# GEMINI CALLER (with backoff)
# =========================
def generate_with_backoff(client: genai.Client, contents) -> Optional[str]:
    """
    Calls generate_content with an exponential backoff on rate/quota errors.
    Returns response text or None on repeated failures.
    """
    max_attempts = 6  # 6 attempts: ~2,4,8,16,32,64s (capped below)
    for attempt in range(max_attempts):
        try:
            allow_request()
            resp = client.models.generate_content(model=MODEL_NAME, contents=contents)
            # smooth bursts after success
            if POST_SUCCESS_PAUSE:
                time.sleep(POST_SUCCESS_PAUSE)
            return getattr(resp, "text", None)
        except Exception as e:
            msg = str(e).lower()
            # treat common transient errors as retryable
            retryable = any(k in msg for k in (
                "rate", "limit", "quota", "exceeded", "resource exhausted",
                "temporarily", "please try again"
            ))
            if not retryable:
                # Non-rate error: bubble up for visibility
                print(f" Non-retryable error: {e}")
                return None

            # Exponential backoff with cap (max 5 minutes)
            backoff = min(300, max(2, 2 ** attempt))
            print(f"Rate/quota error: {e}. Backing off {backoff}s (attempt {attempt+1}/{max_attempts})…")
            time.sleep(backoff)

    print(" Failed after retries; giving up on this item.")
    return None


# =========================
# MAIN PIPELINE
# =========================
def process_image_file(client: genai.Client, image_path: str) -> None:
    name = os.path.basename(image_path)
    stem, _ = os.path.splitext(name)

    # Paths
    csv_path = os.path.join(text_dir, f"{stem}.csv")
    txt_path = os.path.join(text_dir, f"{stem}.txt")
    out_json = os.path.join(output_dir, f"{stem}.json")

    # Skip if already processed
    if os.path.exists(out_json):
        print(f" Skipping (already exists): {out_json}")
        return

    # =========================
    # 1) READ CSV, CONVERT → TXT
    # =========================
    if not os.path.exists(csv_path):
        print(f" CSV NOT FOUND for {stem}")
        return

    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            csv_content = f.read()

        # Create TXT from CSV
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(csv_content)

        print(f" Converted CSV > TXT : {csv_path} -> {txt_path}")

    except Exception as e:
        print(f" ERROR converting CSV {csv_path}: {e}")
        return

    # =========================
    # 2) LOAD IMAGE
    # =========================
    try:
        image = PIL.Image.open(image_path)
    except Exception as e:
        print(f" Could not open image {image_path}: {e}")
        return

    # =========================
    # 3) LOAD PROMPT + TXT (just converted)
    # =========================
    base_prompt = read_file(prompt_file)

    try:
        side_text = read_file(txt_path)
    except Exception as e:
        print(f" Cannot read TXT after conversion: {txt_path}")
        return

    full_prompt = (
            base_prompt
            + '\n\n--- { CSV input :  "\n'
            + side_text
            + '\n"}'
    )

    # =========================
    # 4) SEND TO GEMINI
    # =========================
    contents = [full_prompt, image]

    resp_text = generate_with_backoff(client, contents)
    if not resp_text:
        print(f" No response for {name}")
        return

    # =========================
    # 5) SAVE RESULT
    # =========================
    save_json_safely(resp_text, out_json)
    print(f" Saved {out_json}")


def main():
    api_key = load_api_key(api_key_path)
    client = genai.Client(api_key=api_key)

    # Walk the image directory
    for fname in sorted(os.listdir(image_dir)):
        if fname.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            fpath = os.path.join(image_dir, fname)
            process_image_file(client, fpath)
    print(" Done.")

if __name__ == "__main__":
    main()
