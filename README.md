# CatBat - Battle Cats 自動化腳本

自動化執行《貓咪大戰爭》(Battle Cats TW) 的重複刷關流程，透過 ADB 控制 Android 模擬器 + 螢幕圖像辨識實現全自動循環。

## 功能

- **全自動循環刷關** — 支援最多 1100 輪連續執行
- **圖像辨識點擊** — 使用 pyautogui 偵測 UI 元素（按鈕、彈窗、獎勵畫面）
- **系統時間操控** — 透過 ADB 回調裝置時間以重置遊戲冷卻
- **防火牆控制** — 自動啟動 NoRoot Firewall 阻斷/恢復網路連線
- **智慧容錯** — 偵測逾時自動重試，關鍵步驟失敗自動重啟循環
- **雙路徑處理** — 根據是否出現 GOLD 獎勵自動切換不同結算流程

## 環境需求

- Python 3.10+
- Android 模擬器（預設 `emulator-5554`）
- ADB (Android Debug Bridge)
- 模擬器需有 root 權限（`su 0`）

### Python 套件

```
pyautogui
```

### Android 端

- [NoRoot Firewall](https://github.com/AnyLeaf/NoRootFirewall)（`app.greyshirts.firewall`）— 已附帶 APK
- 貓咪大戰爭 TW 版（`jp.co.ponos.battlecatstw`）

## 使用方式

1. 啟動 Android 模擬器並確認 ADB 連線：
   ```bash
   adb devices
   ```

2. 安裝 NoRoot Firewall（如尚未安裝）：
   ```bash
   adb install "NoRoot Firewall.apk"
   ```

3. 執行自動化腳本：
   ```bash
   python auto_click_start_stop.py
   ```

## 檔案結構

```
catbat/
├── auto_click_start_stop.py   # 主自動化腳本
├── click_dodo_once.py         # 單次測試用輔助腳本
├── readme.txt                 # 流程步驟文件
├── *.png                      # UI 元素截圖（圖像辨識用）
├── NoRoot Firewall.apk        # 防火牆 APK
└── platform-tools-latest-windows.zip  # ADB 工具包
```

## 設定參數

主要參數在 `auto_click_start_stop.py` 頂部：

| 參數 | 預設值 | 說明 |
|------|--------|------|
| `ADB_SERIAL` | `emulator-5554` | 目標裝置 |
| `CONFIDENCE` | `0.90` | 圖像辨識信心度門檻 |
| `POLL_INTERVAL` | `0.3` | 偵測輪詢間隔（秒） |
| `ADB_RETRIES` | `5` | ADB 指令重試次數 |
| `ADB_RETRY_DELAY` | `1.5` | 重試間隔（秒） |

## 單次循環流程

1. 強制停止遊戲 → 回調系統時間 2 天
2. 啟動遊戲 → 偵測 SKIP 畫面
3. 啟動防火牆阻斷網路 → 點擊開始
4. 依序偵測並點擊：選關 → 世界地圖 → 進入關卡 → DODO 戰鬥
5. 恢復網路 → 恢復自動時間 → 切換防火牆
6. 偵測獎勵畫面（GOLD / 一般）→ 點擊結算序列
7. 完成地圖 / 旅行 / 確認 → 進入下一循環
