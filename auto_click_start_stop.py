import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path

import pyautogui


BASE_DIR = Path(__file__).resolve().parent
ADB_SERIAL = "emulator-5554"
CONFIDENCE = 0.90
POLL_INTERVAL = 0.3
ADB_RETRIES = 5
ADB_RETRY_DELAY = 1.5
ADB_WAIT_TIMEOUT = 15
GAME_PACKAGE = "jp.co.ponos.battlecatstw"
FIREWALL_PACKAGE = "app.greyshirts.firewall"
pyautogui.PAUSE = 0


def build_image_map() -> dict[str, str]:
    image_paths = {
        "SKIP": BASE_DIR / "skip.png",
        "START_GREEN": BASE_DIR / "start_green.png",
        "STARTM": BASE_DIR / "startm.png",
        "WORLDM": BASE_DIR / "worldm.png",
        "WORLDM2": BASE_DIR / "worldm2.png",
        "CROSS": BASE_DIR / "cross.png",
        "DODO": BASE_DIR / "dodo.png",
        "GOLD": BASE_DIR / "gold.png",
        "RESULT0": BASE_DIR / "result0.png",
        "RESULT0-1": BASE_DIR / "result0-1.png",
        "RESULT": BASE_DIR / "result.png",
        "RESULT1": BASE_DIR / "result1.png",
        "RESULT2": BASE_DIR / "result2.png",
        "RESULT3": BASE_DIR / "result3.png",
        "RESULT4": BASE_DIR / "result4.png",
        "MAP": BASE_DIR / "map.png",
        "TRAVEL": BASE_DIR / "travel.png",
        "YES": BASE_DIR / "yes.png",
    }

    missing = [name for name, path in image_paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"missing image files: {', '.join(missing)}")

    start_red = BASE_DIR / "start_red.png"
    if start_red.exists():
        image_paths["START_RED"] = start_red
    else:
        stop_red = BASE_DIR / "stop_red.png"
        if stop_red.exists():
            print("[WARN] start_red.png not found, fallback to stop_red.png.")
            image_paths["START_RED"] = stop_red
        else:
            raise FileNotFoundError("missing image file: START_RED (start_red.png/stop_red.png)")

    return {name: str(path) for name, path in image_paths.items()}


def _print_process_output(result: subprocess.CompletedProcess) -> None:
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="")


def recover_adb_connection() -> None:
    print("[ADB] recovering connection...")
    subprocess.run(["adb", "kill-server"], capture_output=True, text=True, check=False)
    subprocess.run(["adb", "start-server"], capture_output=True, text=True, check=False)
    subprocess.run(["adb", "reconnect", "offline"], capture_output=True, text=True, check=False)
    try:
        subprocess.run(
            ["adb", "-s", ADB_SERIAL, "wait-for-device"],
            capture_output=True,
            text=True,
            check=False,
            timeout=ADB_WAIT_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        print("[ADB] wait-for-device timeout, will retry command.")


def run_cmd(cmd: list[str], retries: int = ADB_RETRIES) -> None:
    for attempt in range(1, retries + 1):
        print(f"[CMD] {' '.join(cmd)} (attempt {attempt}/{retries})")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        _print_process_output(result)
        if result.returncode == 0:
            return

        is_adb_cmd = bool(cmd) and cmd[0].lower() == "adb"
        if is_adb_cmd and attempt < retries:
            recover_adb_connection()
            time.sleep(ADB_RETRY_DELAY)
            continue

        raise subprocess.CalledProcessError(
            result.returncode, cmd, output=result.stdout, stderr=result.stderr
        )


def run_adb(args: list[str]) -> None:
    run_cmd(["adb", "-s", ADB_SERIAL, *args])


def launch_package(package_name: str) -> None:
    run_adb(
        [
            "shell",
            "monkey",
            "-p",
            package_name,
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]
    )


def locate_center(image_path: str):
    try:
        return pyautogui.locateCenterOnScreen(
            image_path,
            confidence=CONFIDENCE,
            grayscale=False,
        )
    except pyautogui.ImageNotFoundException:
        return None


def click_point(point, clicks: int = 1, interval: float = 0.0, hold: float = 0.02) -> None:
    x, y = int(point.x), int(point.y)
    for i in range(clicks):
        pyautogui.moveTo(x, y, duration=0.0)
        pyautogui.mouseDown(x, y)
        time.sleep(hold)
        pyautogui.mouseUp(x, y)
        if i < clicks - 1:
            time.sleep(interval)


def wait_until_detect_then_delay_click_with_timeout(
    image_path: str,
    label: str,
    delay_before_click_sec: float,
    timeout_sec: float,
    click_kwargs: dict | None = None,
) -> bool:
    click_kwargs = click_kwargs or {}
    print(
        f"[{label}] waiting for detect (timeout={timeout_sec}s), then click after {delay_before_click_sec}s..."
    )
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        point = locate_center(image_path)
        if point is not None:
            print(f"[{label}] detected at: {point}")
            time.sleep(delay_before_click_sec)
            refreshed_point = locate_center(image_path) or point
            click_point(refreshed_point, **click_kwargs)
            print(f"[{label}] clicked at: {refreshed_point}")
            return True
        time.sleep(POLL_INTERVAL)
    print(f"[{label}] not detected within {timeout_sec}s.")
    return False


def wait_until_detect_and_click(image_path: str, label: str) -> None:
    print(f"[{label}] waiting for detect and click...")
    while True:
        point = locate_center(image_path)
        if point is not None:
            time.sleep(0.3)
            click_point(point)
            print(f"[{label}] clicked at: {point}")
            return
        time.sleep(POLL_INTERVAL)


def wait_until_detect(image_path: str, label: str) -> None:
    print(f"[{label}] waiting for detect...")
    while True:
        point = locate_center(image_path)
        if point is not None:
            print(f"[{label}] detected at: {point}")
            return
        time.sleep(POLL_INTERVAL)


def run_cycle(images: dict[str, str], cycle_idx: int) -> bool:
    print(f"=== cycle {cycle_idx} start ===")
    strong_single = {"clicks": 1, "hold": 0.05}
    gold_click = {"clicks": 3, "hold": 0.08, "interval": 0.08}
    triple_dodo = {"clicks": 3, "interval": 0.5, "hold": 0.02}

    tail_steps = [
        ("GOLD", 7.0, gold_click),
        ("RESULT0", 1, strong_single),
        ("RESULT0-1", 1, strong_single),
        ("RESULT", 7.0, strong_single),
        ("RESULT1", 0.3, strong_single),
        ("RESULT2", 0.3, strong_single),
        ("RESULT3", 0.3, strong_single),
        ("RESULT4", 0.3, strong_single),
        ("MAP", 3, strong_single),
        ("TRAVEL", 3, strong_single),
        ("YES", 1.2, strong_single),
    ]

    try:
        # 1
        run_adb(["shell", "am", "force-stop", GAME_PACKAGE])
        run_adb(["shell", "su", "0", "settings", "put", "global", "auto_time", "0"])

        # 2
        time.sleep(0.1)
        adb_date = (datetime.now() - timedelta(days=2)).strftime("%m%d%H%M%Y.%S")
        run_adb(["shell", "su", "0", "date", adb_date])

        # 3
        time.sleep(0.1)
        launch_package(GAME_PACKAGE)

        # 4
        wait_until_detect(images["SKIP"], "SKIP-DETECT-1")
        launch_package(FIREWALL_PACKAGE)

        # 5
        wait_until_detect_and_click(images["START_GREEN"], "START-GREEN")

        # 6
        launch_package(GAME_PACKAGE)

        # 7
        time.sleep(0.1)
        wait_until_detect_and_click(images["SKIP"], "SKIP-CLICK-2")
        wait_until_detect_then_delay_click_with_timeout(
            images["SKIP"], "SKIP-CLICK-2", delay_before_click_sec=0.1, timeout_sec=0.1
        )

        # 8
        wait_until_detect_then_delay_click_with_timeout(
            images["STARTM"], "STARTM", delay_before_click_sec=0.1, timeout_sec=4.0
        )

        # 9
        time.sleep(0.1)
        wait_until_detect_then_delay_click_with_timeout(
            images["WORLDM"], "WORLDM", delay_before_click_sec=0.0, timeout_sec=1.0
        )

        # 10
        time.sleep(0.1)
        if not wait_until_detect_then_delay_click_with_timeout(
            images["WORLDM2"], "WORLDM2", delay_before_click_sec=0.0, timeout_sec=1.0
        ):
            print("stop: WORLDM2 not detected in 2 seconds.")
            return False

        # 11
        time.sleep(0.5)
        wait_until_detect_then_delay_click_with_timeout(
            images["CROSS"], "CROSS", delay_before_click_sec=0.3, timeout_sec=1.5
        )
        time.sleep(0.5)
        wait_until_detect_then_delay_click_with_timeout(
            images["CROSS"], "CROSS", delay_before_click_sec=0.3, timeout_sec=1.5
        )

        # 12
        time.sleep(0.1)
        if not wait_until_detect_then_delay_click_with_timeout(
            images["DODO"], "DODO-TRIPLE", delay_before_click_sec=0.6, timeout_sec=2.0, click_kwargs=triple_dodo
        ):
            print("stop: DODO (first) not detected in time.")
            return False

        # 13
        time.sleep(0.1)
        wait_until_detect_then_delay_click_with_timeout(
            images["DODO"], "DODO-ONCE", delay_before_click_sec=0.5, timeout_sec=1.0
        )

        # 14
        time.sleep(0.1)
        launch_package(FIREWALL_PACKAGE)

        # 15
        time.sleep(0.1)
        run_adb(["shell", "su", "0", "settings", "put", "global", "auto_time", "1"])

        # 16
        time.sleep(0.1)
        launch_package(GAME_PACKAGE)

        # 17
        time.sleep(0.5)
        launch_package(FIREWALL_PACKAGE)

        # 18
        wait_until_detect_and_click(images["START_RED"], "START-RED")

        # 19
        time.sleep(0.1)
        launch_package(GAME_PACKAGE)
        time.sleep(0.5)

        # 20-28
        gold_found = wait_until_detect_then_delay_click_with_timeout(
            images["GOLD"], "GOLD", delay_before_click_sec=0.3, timeout_sec=7.0, click_kwargs=gold_click
        )

        if not gold_found:
            print("GOLD not detected, skip to MAP/TRAVEL/YES sequence")
            tail = [
                ("MAP", 3, strong_single),
                ("TRAVEL", 1.5, strong_single),
                ("YES", 2, strong_single),
                ("YES", 1, strong_single),
            ]
        else:
            tail = [
                ("RESULT0", 1, strong_single),
                ("RESULT0-1", 1, strong_single),
                ("RESULT", 7.0, strong_single),
                ("RESULT1", 0.2, strong_single),
                ("RESULT2", 0.2, strong_single),
                ("RESULT3", 0.2, strong_single),
                ("RESULT3", 0.25, strong_single),
                ("RESULT3", 0.25, strong_single),
                ("RESULT4", 0.2, strong_single),
                ("MAP", 3, strong_single),
                ("TRAVEL", 1.5, strong_single),
                ("YES", 2, strong_single),
                ("YES", 1, strong_single),
            ]

        for label, timeout, kwargs in tail:
            time.sleep(0.5)
            wait_until_detect_then_delay_click_with_timeout(
                images[label], label, delay_before_click_sec=0.3, timeout_sec=timeout, click_kwargs=kwargs
            )

        print(f"=== cycle {cycle_idx} completed ===")
        return True
    except Exception as exc:
        print(f"cycle {cycle_idx} error: {exc}")
        return False


def main() -> None:
    images = build_image_map()
    pyautogui.FAILSAFE = True
    print("tip: move mouse to top-left corner quickly to abort.")

    for i in range(1, 1100):
        ok = run_cycle(images, i)
        if not ok:
            print(f"stop: aborted at cycle {i}.")
            break
        time.sleep(1.0)
    else:
        print("all 10 cycles completed.")


if __name__ == "__main__":
    main()
