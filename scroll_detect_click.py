"""
Scroll the mouse wheel downward until a target image appears on screen, then click it.

How to use:
1) Save the target snippet from the user-provided screenshot as ``target_banner.png`` in the same folder as this script.
2) Open the window you want to scroll and make sure it has focus.
3) Run the script: ``python scroll_detect_click.py``.
4) The script gives you a 3‑second countdown, then slowly scrolls down, checks the screen, and clicks the target once found.

Tips:
- Press Ctrl+C to stop at any time.
- Adjust SCROLL_STEPS or CONFIDENCE below if detection is too strict/lenient.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import pyautogui

# Configuration
# Default to the provided silver banner image.
TARGET_IMAGE = Path(__file__).with_name("silver.png")
CONFIDENCE = 0.88          # 0..1, higher = stricter match
SCROLL_AMOUNT = -700       # Negative scrolls down; units are "wheel clicks"
SCROLL_PAUSE = 0.35        # Pause after each scroll (seconds)
MAX_SCROLLS = 400          # Safety cap to avoid infinite scrolling
POST_FIND_DELAY = 0.20     # Delay before clicking once detected
EXTRA_SCROLLS_AFTER_DETECT = 1
EXTRA_SCROLL_PAUSE = 0.18
POST_SCROLL_AMOUNT = -200  # Smaller nudge after detection to avoid overshoot
REDETECT_RETRIES = 5
REDETECT_PAUSE = 0.08


def locate_center(image_path: Path):
    """Return the screen center point of the first match or None if not found."""
    try:
        return pyautogui.locateCenterOnScreen(
            str(image_path),
            confidence=CONFIDENCE,
            grayscale=False,
        )
    except pyautogui.ImageNotFoundException:
        return None


def main() -> int:
    if not TARGET_IMAGE.exists():
        print(f"[ERROR] Target image not found: {TARGET_IMAGE}")
        print("Save the provided snippet as 'target_banner.png' next to this script and retry.")
        return 1

    print("[INFO] Starting in 3 seconds. Focus the window you want to scroll...")
    time.sleep(3)

    for i in range(1, MAX_SCROLLS + 1):
        point = locate_center(TARGET_IMAGE)
        if point:
            print(f"[INFO] Found target at {point}. Clicking...")
            for _ in range(EXTRA_SCROLLS_AFTER_DETECT):
                pyautogui.scroll(POST_SCROLL_AMOUNT)
                time.sleep(EXTRA_SCROLL_PAUSE)

            # Re-detect after the additional scroll(s)
            refreshed_point = None
            for _ in range(REDETECT_RETRIES):
                refreshed_point = locate_center(TARGET_IMAGE)
                if refreshed_point:
                    break
                time.sleep(REDETECT_PAUSE)

            click_point = refreshed_point or point

            time.sleep(POST_FIND_DELAY)
            pyautogui.click(click_point.x, click_point.y, clicks=3, interval=0.05)
            print("[INFO] Done.")
            return 0

        pyautogui.scroll(SCROLL_AMOUNT)
        print(f"[SCAN] Scroll #{i} (looking for target)...")
        time.sleep(SCROLL_PAUSE)

    print(f"[WARN] Reached max scrolls ({MAX_SCROLLS}) without finding the target.")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[INFO] Stopped by user.")
        sys.exit(1)
