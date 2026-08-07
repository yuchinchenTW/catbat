import ctypes
import time


INTERVAL_SECONDS = 0.5
VK_Y = 0x59
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004

user32 = ctypes.windll.user32


def is_stop_key_pressed() -> bool:
    return bool(user32.GetAsyncKeyState(VK_Y) & 0x8000)


def left_click() -> None:
    user32.mouse_event(MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    user32.mouse_event(MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def main() -> None:
    print("Auto clicker started. Press Y to stop.")

    while True:
        if is_stop_key_pressed():
            break

        left_click()

        end_time = time.monotonic() + INTERVAL_SECONDS
        while time.monotonic() < end_time:
            if is_stop_key_pressed():
                print("Y detected. Stopping.")
                return
            time.sleep(0.03)

    print("Y detected. Stopping.")


if __name__ == "__main__":
    main()
