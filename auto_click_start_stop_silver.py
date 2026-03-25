import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
import sys
import pyautogui


BASE_DIR = Path(__file__).resolve().parent
ADB_SERIAL = "emulator-5554"
CONFIDENCE = 0.82
POLL_INTERVAL = 0.3
ADB_RETRIES = 5
ADB_RETRY_DELAY = 1.5
ADB_WAIT_TIMEOUT = 15
GAME_PACKAGE = "jp.co.ponos.battlecatstw"
FIREWALL_PACKAGE = "app.greyshirts.firewall"
pyautogui.PAUSE = 0

TARGET_IMAGE = str(Path(__file__).with_name("silver.png"))
ONCE_SCRIPT = str(Path(__file__).with_name("auto_click_start_stop_once.py"))
SCROLL_AMOUNT = -280       # Negative scrolls down; units are "wheel clicks"
SCROLL_PAUSE = 0.35        # Pause after each scroll (seconds)
MAX_SCROLLS = 200          # Safety cap to avoid infinite scrolling
POST_FIND_DELAY = 1     # Delay before clicking once detected
EXTRA_SCROLLS_AFTER_DETECT = 0
EXTRA_SCROLL_PAUSE = 0.18
POST_SCROLL_AMOUNT = -40   # Used only when mouse-wheel scrolling is enabled
REDETECT_RETRIES = 8
REDETECT_PAUSE = 0.08
POST_DETECT_WAIT = 1.0
PRE_SCROLL_DETECT_TIMEOUT = 0.3
TARGET_STABLE_TOLERANCE = 12
TARGET_STABLE_HITS = 2
USE_MOUSE_SCROLL = False
USE_ADB_SCROLL_FALLBACK = True
# This screen responds to touch-drag more reliably than mouse wheel.
# Keep the swipe in the same lane that previously worked, but slow it down to avoid tap-like input.
ADB_SWIPE_ARGS = ["shell", "input", "swipe", "780", "450", "780", "120", "640"]
ADB_BACKTRACK_SWIPE_ARGS = ["shell", "input", "swipe", "780", "140", "780", "560", "520"]
ADB_REVERSE_SCAN_SWIPE_ARGS = ["shell", "input", "swipe", "780", "200", "780", "380", "620"]


def perform_scroll_step() -> None:
    """Scroll down once using the configured method."""
    if USE_MOUSE_SCROLL:
        pyautogui.scroll(SCROLL_AMOUNT)
        time.sleep(SCROLL_PAUSE)
    if USE_ADB_SCROLL_FALLBACK:
        try:
            run_adb(ADB_SWIPE_ARGS)
            time.sleep(SCROLL_PAUSE)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] adb swipe failed (continuing): {exc}")


def perform_backtrack_step() -> None:
    """Scroll back up a little when post-detect nudge overshoots the target."""
    if USE_MOUSE_SCROLL:
        pyautogui.scroll(-POST_SCROLL_AMOUNT)
        time.sleep(EXTRA_SCROLL_PAUSE)
    if USE_ADB_SCROLL_FALLBACK:
        try:
            run_adb(ADB_BACKTRACK_SWIPE_ARGS)
            time.sleep(EXTRA_SCROLL_PAUSE)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] adb backtrack swipe failed (continuing): {exc}")


def perform_reverse_scan_step() -> None:
    """Scroll back up slowly when searching upward from the event bottom."""
    if USE_MOUSE_SCROLL:
        pyautogui.scroll(POST_SCROLL_AMOUNT // 2)
        time.sleep(SCROLL_PAUSE)
    if USE_ADB_SCROLL_FALLBACK:
        try:
            run_adb(ADB_REVERSE_SCAN_SWIPE_ARGS)
            time.sleep(SCROLL_PAUSE)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] adb reverse scan swipe failed (continuing): {exc}")


def perform_post_detect_nudge() -> None:
    if USE_MOUSE_SCROLL:
        pyautogui.scroll(POST_SCROLL_AMOUNT)
        time.sleep(EXTRA_SCROLL_PAUSE)
    elif USE_ADB_SCROLL_FALLBACK:
        try:
            run_adb(ADB_SWIPE_ARGS)
            time.sleep(EXTRA_SCROLL_PAUSE)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] adb post-detect swipe failed (continuing): {exc}")

def build_image_map() -> dict[str, str]:
    image_paths = {
        "SKIP": BASE_DIR / "skip.png",
        "START_GREEN": BASE_DIR / "start_green.png",
        "STARTM": BASE_DIR / "startm.png",
        "WORLDM": BASE_DIR / "worldevent.png",
        "WORLDM2": BASE_DIR / "worldevent.png",
        "OK": BASE_DIR / "worldeventok.png",
        "STARTBATTLE": BASE_DIR / "worldeventstartbattle.png",
        "CROSS": BASE_DIR / "cross.png",
        "CROSS2": BASE_DIR / "cross2.png",
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
        "SILVERSTART": BASE_DIR / "silver_battlestart.png",
        "SILVERGET": BASE_DIR / "silverget.png",
        "SILVEROK": BASE_DIR / "silverok.png",
        "EVENTBOTTOM": BASE_DIR / "eventbottom.png",
        "EVENTBACK": BASE_DIR / "event_back.png",
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


def maybe_add_optional_image(images: dict[str, str], key: str, filename: str) -> None:
    path = BASE_DIR / filename
    if path.exists():
        images[key] = str(path)
    else:
        print(f"[WARN] optional image not found: {filename}")


def run_python_script(script_path: str) -> bool:
    if not Path(script_path).exists():
        print(f"[WARN] script not found: {script_path}")
        return False
    print(f"[SCRIPT] running: {script_path}")
    result = subprocess.run([sys.executable, script_path], check=False)
    print(f"[SCRIPT] finished: {script_path} (exit={result.returncode})")
    return result.returncode == 0


def try_click_target_if_visible(image_path: str) -> bool:
    point = locate_center(image_path)
    if point is None:
        return False

    print(f"[INFO] Found target at {point}. Clicking...", flush=True)
    for _ in range(EXTRA_SCROLLS_AFTER_DETECT):
        perform_post_detect_nudge()

    time.sleep(POST_DETECT_WAIT)

    refreshed_point = redetect_stable_target(image_path)
    if refreshed_point is None:
        print("[WARN] Target moved or vanished after scroll; backtracking before continuing.", flush=True)
        for _ in range(EXTRA_SCROLLS_AFTER_DETECT):
            perform_backtrack_step()
        time.sleep(POST_DETECT_WAIT)
        refreshed_point = redetect_stable_target(image_path)
    if refreshed_point is None:
        print("[WARN] Target still not stable after backtrack; keep scanning.", flush=True)
        return False

    time.sleep(POST_FIND_DELAY)
    click_point(refreshed_point, clicks=3, interval=0.05, hold=0.03)
    print("[INFO] Done.")
    return True


def try_click_target_before_scroll(image_path: str, timeout_sec: float = PRE_SCROLL_DETECT_TIMEOUT) -> bool:
    point = wait_until_detect_with_timeout(image_path, "TARGET-PRESCROLL", timeout_sec)
    if point is None:
        return False
    return try_click_target_if_visible(image_path)


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
            grayscale=True,
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


def points_close(a, b, tolerance: int = TARGET_STABLE_TOLERANCE) -> bool:
    return abs(int(a.x) - int(b.x)) <= tolerance and abs(int(a.y) - int(b.y)) <= tolerance


def redetect_stable_target(image_path: str):
    stable_hits = 0
    last_point = None
    for _ in range(REDETECT_RETRIES):
        point = locate_center(image_path)
        if point is None:
            stable_hits = 0
            last_point = None
            time.sleep(REDETECT_PAUSE)
            continue

        if last_point is not None and points_close(last_point, point):
            stable_hits += 1
        else:
            stable_hits = 1

        last_point = point
        if stable_hits >= TARGET_STABLE_HITS:
            return point

        time.sleep(REDETECT_PAUSE)

    return None


def wait_until_detect_then_delay_click_with_timeout(
    image_path: str,
    label: str,
    delay_before_click_sec: float,
    timeout_sec: float,
    click_kwargs: dict | None = None,
    reuse_detect_point: bool = False,
) -> bool:
    click_kwargs = click_kwargs or {}
    print(
        f"[{label}] waiting for detect (timeout={timeout_sec}s), then click after {delay_before_click_sec}s..."
    )
    deadline = time.monotonic() + timeout_sec
    detect_point = None
    while time.monotonic() < deadline:
        point = locate_center(image_path)
        if point is not None:
            detect_point = point
            print(f"[{label}] detected at: {point}")
            time.sleep(delay_before_click_sec)
            click_target = detect_point if reuse_detect_point else (locate_center(image_path) or detect_point)
            click_point(click_target, **click_kwargs)
            print(f"[{label}] clicked at: {click_target}")
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


def wait_until_detect_with_timeout(image_path: str, label: str, timeout_sec: float):
    print(f"[{label}] waiting for detect (timeout={timeout_sec}s)...")
    deadline = time.monotonic() + timeout_sec
    while time.monotonic() < deadline:
        point = locate_center(image_path)
        if point is not None:
            print(f"[{label}] detected at: {point}")
            return point
        time.sleep(POLL_INTERVAL)
    print(f"[{label}] not detected within {timeout_sec}s.")
    return None


def run_cycle(images: dict[str, str], cycle_idx: int) -> bool:
    print(f"=== cycle {cycle_idx} start ===")
    strong_single = {"clicks": 1, "hold": 0.05}
    gold_click = {"clicks": 3, "hold": 0.08, "interval": 0.08}
    triple_dodo = {"clicks": 3, "interval": 0.5, "hold": 0.02}
    heavy_startm = {"clicks": 2, "hold": 0.1, "interval": 0.05}

    tail_steps = [
        ("GOLD", 7.0, gold_click),
        ("RESULT0", 1.5, strong_single),
        ("RESULT0-1", 1.5, strong_single),
        ("RESULT", 7.0, strong_single),
        ("RESULT1", 0.2, strong_single),
        ("RESULT2", 0.2, strong_single),
        ("RESULT3", 0.2, strong_single),
        ("RESULT4", 0.2, strong_single),
        ("MAP", 3, strong_single),
        ("TRAVEL", 3, strong_single),
        ("YES", 1.2, strong_single),
        ("YES", 1.2, strong_single),
    ]

    try:
        # 1
        #run_adb(["shell", "am", "force-stop", GAME_PACKAGE])
        #run_adb(["shell", "su", "0", "settings", "put", "global", "auto_time", "0"])
        run_adb(["shell", "su", "0", "settings", "put", "global", "auto_time", "1"])
        time.sleep(0.1)
        launch_package(FIREWALL_PACKAGE)        
        time.sleep(0.1)
        wait_until_detect_and_click(images["START_RED"], "START_RED")
        time.sleep(0.1)
        run_adb(["shell", "am", "force-stop", GAME_PACKAGE])
        # 2
        time.sleep(0.4)
        adb_date = (datetime.now() - timedelta(days=2)).strftime("%m%d%H%M%Y.%S")
        #run_adb(["shell", "su", "0", "date", adb_date])
        run_adb(["shell", "settings", "put", "global", "auto_time_zone", "1"])
        # 3
        time.sleep(0.1)
        launch_package(GAME_PACKAGE)

        # 4
        #wait_until_detect(images["SKIP"], "SKIP-DETECT-1")
        #launch_package(FIREWALL_PACKAGE)

        # 5
        #wait_until_detect_and_click(images["START_GREEN"], "START-GREEN")

        #adb shell su 0 am force-stop app.greyshirts.firewall 
        #adb shell su 0 service call connectivity 48 i32 0 s16 app.greyshirts.firewall i32 0
        
        #run_adb(["shell", "su", "0", "service", "call", "connectivity", "48", "i32", "0", "s16", "app.greyshirts.firewall", "i32", "0"])

        # 6
        #launch_package(GAME_PACKAGE)

        # 7
        time.sleep(0.1)
        wait_until_detect_and_click(images["SKIP"], "SKIP-CLICK-2")
        wait_until_detect_then_delay_click_with_timeout(
            images["SKIP"], "SKIP-CLICK-2", delay_before_click_sec=0.3, timeout_sec=1
        )
        time.sleep(0.5)
        # 8
        wait_until_detect_then_delay_click_with_timeout(
            images["STARTM"], "STARTM", delay_before_click_sec=0.5, timeout_sec=1.0, click_kwargs=heavy_startm, reuse_detect_point=True
        )
        wait_until_detect_then_delay_click_with_timeout(
            images["STARTM"], "STARTM", delay_before_click_sec=0.2, timeout_sec=0.3, click_kwargs=heavy_startm, reuse_detect_point=True
        )
        wait_until_detect_then_delay_click_with_timeout(
            images["STARTM"], "STARTM", delay_before_click_sec=0.2, timeout_sec=0.3, click_kwargs=heavy_startm, reuse_detect_point=True
        )

        # 9
        #time.sleep(0.3)
       # wait_until_detect_then_delay_click_with_timeout(
       #     images["WORLDM"], "WORLDM", delay_before_click_sec=0.1, timeout_sec=0.2
       # )

        # 10
        time.sleep(0.3)
        if not wait_until_detect_then_delay_click_with_timeout(
            images["WORLDM2"], "WORLDM2", delay_before_click_sec=0.2, timeout_sec=2.0
        ):
            print("WORLDM2 miss -> restart next cycle")
            return True  # do not stop; move to next loop

        time.sleep(0.3)
        if not wait_until_detect_then_delay_click_with_timeout(
            images["OK"], "OK", delay_before_click_sec=0.2, timeout_sec=2.0
        ):
            print("WORLDM2 miss -> restart next cycle")
            return True  # do not stop; move to next loop            
            #STARTBATTLE

        #adb shell setprop persist.sys.timezone Asia/Dubai   ///gmt+4
        #adb shell setprop persist.sys.timezone Europe/Moscow //gmt+3
        #adb shell setprop persist.sys.timezone Africa/Cairo //gmt+2
        #adb shell setprop persist.sys.timezone Africa/Lagos  gmt+1
        #adb shell setprop persist.sys.timezone Australia/Sydney gmt+10
        #adb shell settings put global auto_time_zone 0


        time.sleep(0.2)
        wait_until_detect_then_delay_click_with_timeout(
            images["CROSS"], "CROSS", delay_before_click_sec=0.6, timeout_sec=1
        )
        time.sleep(0.1)
        wait_until_detect_then_delay_click_with_timeout(
            images["CROSS"], "CROSS", delay_before_click_sec=0.4, timeout_sec=1
        )
        wait_until_detect_then_delay_click_with_timeout(
            images["CROSS"], "CROSS", delay_before_click_sec=0.4, timeout_sec=1
        )


        #adb shell setprop persist.sys.timezone Asia/Dubai   ///gmt+4
        #adb shell setprop persist.sys.timezone Europe/Moscow //gmt+3
        #adb shell setprop persist.sys.timezone Africa/Cairo //gmt+2
        #adb shell setprop persist.sys.timezone Africa/Lagos  gmt+1
        #adb shell setprop persist.sys.timezone Australia/Sydney gmt+10
        #adb shell setprop persist.sys.timezone Asia/Ho_Chi_Minh +7
        #adb shell setprop persist.sys.timezone Asia/Dhaka +6
        #adb shell setprop persist.sys.timezone Asia/Karachi +5
        #EVENTBACK

        run_adb(["shell", "settings", "put", "global", "auto_time_zone", "0"])
        run_adb(["shell", "setprop", "persist.sys.timezone", "Africa/Lagos"])
        

        time.sleep(0.3)
        if not wait_until_detect_then_delay_click_with_timeout(
            images["STARTBATTLE"], "STARTBATTLE", delay_before_click_sec=0.2, timeout_sec=2.0
        ):
            print("WORLDM2 miss -> restart next cycle")
            return True  # do not stop; move to next loop

        if not Path(TARGET_IMAGE).exists():
            raise FileNotFoundError(f"target image not found: {TARGET_IMAGE}")

        while True:
        
            time.sleep(0.3)
            wait_until_detect_then_delay_click_with_timeout(
                images["STARTBATTLE"], "STARTBATTLE", delay_before_click_sec=0.2, timeout_sec=2.0
            )        

            wait_until_detect_then_delay_click_with_timeout(
                images["STARTBATTLE"], "STARTBATTLE", delay_before_click_sec=0.2, timeout_sec=0.2
            )          
            wait_until_detect_then_delay_click_with_timeout(
                images["STARTBATTLE"], "STARTBATTLE", delay_before_click_sec=0.2, timeout_sec=0.2
            )  
            wait_until_detect_then_delay_click_with_timeout(
                images["STARTBATTLE"], "STARTBATTLE", delay_before_click_sec=0.2, timeout_sec=0.2
            )              
            print("[SCAN] Starting scroll-search for target image...", flush=True)

            target_clicked = False
            if try_click_target_if_visible(TARGET_IMAGE):
                target_clicked = True

            scanning_down = True
            for i in range(1, MAX_SCROLLS + 1):
                if target_clicked:
                    break
                print(f"[SCAN] iter {i}: locating...", flush=True)
                if try_click_target_if_visible(TARGET_IMAGE):
                    target_clicked = True
                    break

                if scanning_down and locate_center(images["EVENTBOTTOM"]) is not None:
                    scanning_down = False
                    print(f"[SCAN] iter {i}: reached event bottom, reversing search direction.", flush=True)

                if try_click_target_before_scroll(TARGET_IMAGE):
                    target_clicked = True
                    break


                m_found = wait_until_detect_then_delay_click_with_timeout(
                    images["WORLDM"], "WORLDM", delay_before_click_sec=0.2, timeout_sec=0.2
                )

                if m_found:
                    wait_until_detect_then_delay_click_with_timeout(
                        images["EVENTBACK"], "EVENTBACK", delay_before_click_sec=0.2, timeout_sec=0.2
                    )
                    
                    
                    time.sleep(0.2)
                    wait_until_detect_then_delay_click_with_timeout(
                        images["CROSS"], "CROSS", delay_before_click_sec=0.6, timeout_sec=1
                    )                    

                direction_label = "down" if scanning_down else "up"
                print(f"[SCAN] iter {i}: scrolling {direction_label}...", flush=True)
                try:
                    if scanning_down:
                        perform_scroll_step()
                    else:
                        perform_reverse_scan_step()
                except Exception as exc:  # noqa: BLE001
                    print(f"[WARN] scroll step failed, continuing: {exc}", flush=True)

            if not target_clicked:
                print("[WARN] Max scrolls reached without finding target.")

            time.sleep(0.2)
            silverstart_found = wait_until_detect_then_delay_click_with_timeout(
                images["SILVERSTART"], "SILVERSTART", delay_before_click_sec=0.6, timeout_sec=1
            )

            if not silverstart_found:
                print("[SILVERSTART] not detected, scroll down once and resume silver search.")
                perform_scroll_step()
                continue

            wait_until_detect_then_delay_click_with_timeout(
                images["SILVERSTART"], "SILVERSTART", delay_before_click_sec=0.6, timeout_sec=0.2
            )


            if silverstart_found and "NOMANA" in images:
                nomana_point = wait_until_detect_with_timeout(images["NOMANA"], "NOMANA", timeout_sec=1.5)
                if nomana_point is not None:
                    print(f"[NOMANA] detected at: {nomana_point}, running once script before continuing.")
                    run_python_script(ONCE_SCRIPT)
                    break


            wait_until_detect_and_click(images["SILVERGET"], "SILVERGET")

            wait_until_detect_then_delay_click_with_timeout(
                images["SILVERGET"], "SILVERGET", delay_before_click_sec=0.2, timeout_sec=0.2
            )

            time.sleep(0.2)
            wait_until_detect_then_delay_click_with_timeout(
                images["SILVEROK"], "SILVEROK", delay_before_click_sec=0.2, timeout_sec=0.2
            )
            wait_until_detect_then_delay_click_with_timeout(
                images["SILVEROK"], "SILVEROK", delay_before_click_sec=0.2, timeout_sec=0.2
            )
     
            time.sleep(0.2)
            wait_until_detect_then_delay_click_with_timeout(
                images["CROSS"], "CROSS", delay_before_click_sec=0.2, timeout_sec=1.5
            )
            time.sleep(0.1)
            wait_until_detect_then_delay_click_with_timeout(
                images["CROSS"], "CROSS", delay_before_click_sec=0.4, timeout_sec=0.2
            )
            wait_until_detect_then_delay_click_with_timeout(
                images["CROSS"], "CROSS", delay_before_click_sec=0.4, timeout_sec=0.2
            )
 
        
        return True


        # 11
        time.sleep(0.2)
        wait_until_detect_then_delay_click_with_timeout(
            images["CROSS"], "CROSS", delay_before_click_sec=0.6, timeout_sec=1
        )
        time.sleep(0.1)
        wait_until_detect_then_delay_click_with_timeout(
            images["CROSS"], "CROSS", delay_before_click_sec=0.2, timeout_sec=1
        )

        # 12
        time.sleep(0.1)
        if not wait_until_detect_then_delay_click_with_timeout(
            images["DODO"], "DODO-TRIPLE", delay_before_click_sec=0.3, timeout_sec=1.0, click_kwargs=triple_dodo
        ):
            print("DODO first miss -> restart next cycle")
            return True  # do not stop; move to next loop

        # 13
        time.sleep(0.1)
        wait_until_detect_then_delay_click_with_timeout(
            images["DODO"], "DODO-ONCE", delay_before_click_sec=0.2, timeout_sec=0.4
        )
        time.sleep(0.1)
        wait_until_detect_then_delay_click_with_timeout(
            images["DODO"], "DODO-ONCE", delay_before_click_sec=0.1, timeout_sec=0.2
        )
        time.sleep(0.1)
        wait_until_detect_then_delay_click_with_timeout(
            images["DODO"], "DODO-ONCE", delay_before_click_sec=0.1, timeout_sec=0.1
        )        
        
        # 14
        #time.sleep(0.1)
        #launch_package(FIREWALL_PACKAGE)

        # 15
        time.sleep(0.1)
        run_adb(["shell", "su", "0", "settings", "put", "global", "auto_time", "1"])

        # 16
        #time.sleep(0.3)
        launch_package(GAME_PACKAGE)

        # 17
        time.sleep(0.6)
        launch_package(FIREWALL_PACKAGE)
        #        #adb shell su 0 service call connectivity 48 i32 0 s16 app.greyshirts.firewall i32 0
        #adb shell su 0 am force-stop app.greyshirts.firewall 

        # 18
        wait_until_detect_and_click(images["START_RED"], "START-RED")
       # run_adb(["shell", "su", "0", "am", "force-stop", "app.greyshirts.firewall"])

        # 19
        time.sleep(0.1)
        launch_package(GAME_PACKAGE)
        #time.sleep(1)

        time.sleep(0.1)
        wait_until_detect_then_delay_click_with_timeout(
            images["RESULT3"], "RESULT3", delay_before_click_sec=0.1, timeout_sec=0.1, click_kwargs=strong_single
        )   


        # 20-28
        gold_found = wait_until_detect_then_delay_click_with_timeout(
            images["GOLD"], "GOLD", delay_before_click_sec=0.1, timeout_sec=3.0, click_kwargs=gold_click
        )
        
     

        if not gold_found:
            print("GOLD not detected, skip to MAP/TRAVEL/YES sequence")

            time.sleep(0.1)
            wait_until_detect_then_delay_click_with_timeout(
                images["CROSS2"], "CROSS2", delay_before_click_sec=0.2, timeout_sec=0.2, click_kwargs=strong_single
            )

            def try_map_with_result3_retries(map_timeout: float) -> None:
                time.sleep(0.2)
                map_ok = wait_until_detect_then_delay_click_with_timeout(
                    images["MAP"], "MAP", delay_before_click_sec=0.33, timeout_sec=map_timeout, click_kwargs=strong_single
                )
                if not map_ok:
                    for _ in range(3):
                        time.sleep(0.2)
                        wait_until_detect_then_delay_click_with_timeout(
                            images["RESULT3"], "RESULT3-RETRY", delay_before_click_sec=0.15, timeout_sec=0.33, click_kwargs=strong_single, reuse_detect_point=True
                        )
                    time.sleep(0.2)
                    wait_until_detect_then_delay_click_with_timeout(
                        images["MAP"], "MAP-RETRY", delay_before_click_sec=0.35, timeout_sec=map_timeout, click_kwargs=strong_single
                    )

            try_map_with_result3_retries(map_timeout=2)

            time.sleep(0.1)
            wait_until_detect_then_delay_click_with_timeout(
                images["TRAVEL"], "TRAVEL", delay_before_click_sec=0.1, timeout_sec=1, click_kwargs=strong_single
            )


            time.sleep(0.1)
            wait_until_detect_then_delay_click_with_timeout(
                images["TRAVEL"], "TRAVEL", delay_before_click_sec=0.2, timeout_sec=0.2, click_kwargs=strong_single
            )
            time.sleep(0.3)
            wait_until_detect_then_delay_click_with_timeout(
                images["YES"], "YES", delay_before_click_sec=0.3, timeout_sec=2, click_kwargs=strong_single
            )

            time.sleep(0.1)
            wait_until_detect_then_delay_click_with_timeout(
                images["TRAVEL"], "TRAVEL", delay_before_click_sec=0.2, timeout_sec=0.2, click_kwargs=strong_single
            )            
            
            time.sleep(0.3)
            wait_until_detect_then_delay_click_with_timeout(
                images["YES"], "YES-SECOND", delay_before_click_sec=0.3, timeout_sec=2, click_kwargs=strong_single
            )

        else:
            # gold found path with MAP fallback
            tail = [
                ("RESULT0", 1, strong_single),
                ("RESULT0-1", 1.5, strong_single),
                ("RESULT", 4.0, strong_single),
                ("RESULT1", 0.3, strong_single),
                ("RESULT2", 0.3, strong_single),
                ("RESULT3", 0.2, strong_single),
                ("RESULT3", 0.2, strong_single),
                ("RESULT3", 0.2, strong_single),
                ("RESULT4", 0.3, strong_single),
                ("CROSS2", 0.1, strong_single),
                ("CROSS2", 0.1, strong_single),
                ("MAP", 2, strong_single),
                ("TRAVEL", 0.5, strong_single),
                ("TRAVEL", 0.1, strong_single),
                ("YES", 2, strong_single),
                ("TRAVEL", 0.1, strong_single),
                ("YES", 2, strong_single),
            ]

            for label, timeout, kwargs in tail:
                time.sleep(0.1)
                if label == "MAP":
                    map_ok = wait_until_detect_then_delay_click_with_timeout(
                        images[label], label, delay_before_click_sec=0.3, timeout_sec=timeout, click_kwargs=kwargs
                    )
                    if not map_ok:
                        for _ in range(3):
                            time.sleep(0.1)
                            wait_until_detect_then_delay_click_with_timeout(
                                images["RESULT3"], "RESULT3-RETRY", delay_before_click_sec=0.2, timeout_sec=0.4, click_kwargs=strong_single, reuse_detect_point=True
                            )
                        time.sleep(0.1)
                        wait_until_detect_then_delay_click_with_timeout(
                            images[label], f"{label}-RETRY", delay_before_click_sec=0.3, timeout_sec=timeout, click_kwargs=kwargs
                        )
                else:
                    if label == "RESULT":
                       time.sleep(0.1)
                       wait_until_detect_then_delay_click_with_timeout(
                           images[label], label, delay_before_click_sec=0.2, timeout_sec=1, click_kwargs=kwargs
                       )
                       wait_until_detect_then_delay_click_with_timeout(
                           images[label], label, delay_before_click_sec=0.2, timeout_sec=0.2, click_kwargs=kwargs
                       )

                       wait_until_detect_then_delay_click_with_timeout(
                           images[label], label, delay_before_click_sec=0.2, timeout_sec=0.2, click_kwargs=kwargs
                       )                    

                       wait_until_detect_then_delay_click_with_timeout(
                           images[label], label, delay_before_click_sec=0.2, timeout_sec=0.2, click_kwargs=kwargs
                       )                    
                    else:
                       wait_until_detect_then_delay_click_with_timeout(
                           images[label], label, delay_before_click_sec=0.5, timeout_sec=timeout, click_kwargs=kwargs
                       )

        print(f"=== cycle {cycle_idx} completed ===")
        return True
    except Exception as exc:
        print(f"cycle {cycle_idx} error: {exc}")
        return False


def main() -> None:
    images = build_image_map()
    maybe_add_optional_image(images, "NOMANA", "nomana.png")
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
