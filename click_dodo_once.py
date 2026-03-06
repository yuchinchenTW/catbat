import time
from pathlib import Path

import pyautogui

# Simple watcher: wait until dodo.png appears on screen, then click its center once.
# Move mouse to top-left corner to abort (pyautogui FAILSAFE).

BASE_DIR = Path(__file__).resolve().parent
DODO_PATH = BASE_DIR / "dodo.png"
CONFIDENCE = 0.90
POLL_INTERVAL = 0.3

def main() -> None:
    if not DODO_PATH.exists():
        raise FileNotFoundError(f"missing image file: {DODO_PATH}")

    pyautogui.FAILSAFE = True
    print("Waiting for dodo.png ... (Ctrl+C or move mouse to top-left to abort)")

    while True:
        try:
            point = pyautogui.locateCenterOnScreen(
                str(DODO_PATH), confidence=CONFIDENCE, grayscale=False
            )
        except pyautogui.ImageNotFoundException:
            point = None

        if point is not None:
            pyautogui.click(point)
            print(f"dodo clicked at: {point}")
            return

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
