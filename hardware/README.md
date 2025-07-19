# 憶光 (Oblivilight) - 硬體閘道器 (Hardware Gateway)

本文件為「憶光」專案的硬體閘道器 (`arduino_gateway.py`) 提供說明，旨在引導開發者理解其功能、完成設定並正確執行。

## 1. 功能簡介

硬體閘道器是一個獨立的 Python 服務，扮演著「核心後端」與「實體硬體 (Arduino)」之間的重要橋樑。它的主要職責有二：

1.  **上行通訊 (Arduino -> 後端)**:
    -   持續監聽來自 Arduino 透過序列埠 (Serial Port) 發送的訊號。
    -   將原始的硬體訊號（如 `WAKEUP_SIGNAL`）轉換為標準化的 API 訊號（如 `WAKE_UP`）。
    -   透過 HTTP POST 請求，將這些標準化訊號轉發給核心後端的 `/api/device/signal` 端點。

2.  **(未實踐) 下行通訊 (後端 -> Arduino)**:
    -   運行一個迷你的 FastAPI 伺服器，開放 `/hardware/command` 端點。
    -   (未實踐)接收來自核心後端（例如，在日記生成後）的指令，如 `PRINT_CARD`。
    -   (未實踐)將這些應用層指令轉換為具體的硬體指令（如 `PRINT_ON`），並透過序列埠發送給 Arduino，以控制印表機等週邊設備。

這種分離式架構確保了硬體通訊的穩定性不會直接影響核心後端服務的運作。

## 2. 設定

在啟動閘道器之前，請開啟 `hardware/arduino_gateway.py` 檔案並根據您的實際環境修改以下常數：

```python
# --- 設定 ---
# 請根據實際情況修改
SERIAL_PORT = '/dev/cu.usbserial-110'  # Arduino 的序列埠
BAUD_RATE = 9600
MAIN_BACKEND_URL = "http://localhost:8000/api/device/signal"
GATEWAY_HOST = "0.0.0.0"
GATEWAY_PORT = 8001
```

-   `SERIAL_PORT`: Arduino 連接到您電腦的序列埠名稱。
    -   在 macOS 上通常是 `/dev/cu.usbserial-XXXX` 或 `/dev/cu.usbmodemXXXX`。
    -   在 Linux 上可能是 `/dev/ttyUSB0` 或 `/dev/ttyACM0`。
    -   在 Windows 上則是 `COM3`, `COM4` 等。
-   `BAUD_RATE`: 序列埠通訊的鮑率，必須與 Arduino 草稿碼中的設定一致（通常為 9600）。
-   `MAIN_BACKEND_URL`: 核心後端服務接收硬體訊號的 API 端點位址。
-   `GATEWAY_HOST`: 硬體閘道器自身服務器運行的主機位址。`0.0.0.0` 表示允許來自任何網路介面的連線。
-   `GATEWAY_PORT`: 硬體閘道器自身服務器運行的埠號。

## 3. 執行

硬體閘道器需要與核心後端服務同時運行。請開啟一個獨立的終端機視窗來啟動它。

**執行步驟**:
1.  確保您的 Python 環境已安裝 `requirements.txt` 中的所有相依套件（特別是 `fastapi`, `uvicorn`, `pyserial`, `requests`）。
2.  從 **專案根目錄** 執行以下指令：

    ```bash
    python hardware/arduino_gateway.py
    ```
3.  成功啟動後，您將會看到類似以下的輸出訊息，表示閘道器已開始監聽序列埠並提供 API 服務：

    ```
    硬體閘道器 (Hardware Gateway) 啟動中...
    它將會監聽來自序列埠 '/dev/cu.usbserial-110' 的訊號。
    並將訊號轉發到: http://localhost:8000/api/device/signal
    同時，它也會在 http://0.0.0.0:8001 接收來自後端的指令。
    ---
    INFO:     Started server process [XXXXX]
    INFO:     Waiting for application startup.
    應用程式啟動，準備執行啟動程序...
    成功連接到序列埠: /dev/cu.usbserial-110
    啟動 Arduino 監聽線程...
    INFO:     Application startup complete.
    INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
    ```

## 4. 通訊協定

### 4.1 Arduino -> 後端

閘道器會監聽序列埠傳來的包含特定關鍵字的行：

| Arduino 輸出關鍵字 | 轉換後發送給後端的訊號 | 代表意義     |
| ------------------ | ---------------------- | -------------- |
| `WAKEUP_SIGNAL`    | `WAKE_UP`              | 觸碰開機     |
| `REWIND_SIGNAL`    | `REWIND`               | 蓋住回顧     |
| `SLEEP_SIGNAL`     | `SLEEP`                | 觸碰關機睡眠 |
| `FORGET_SIGNAL`    | `FORGET`               | 揮手遺忘     |

### 4.2 後端 -> Arduino

閘道器透過 `POST /hardware/command` 端點接收指令。

-   **請求範例**:
    ```json
    {
      "command": "PRINT_CARD"
    }
    ```

-   **指令對應關係**:

| 接收到的後端指令 | 轉換後發送給 Arduino 的指令 | 代表意義         |
| ------------------ | --------------------------- | ------------------ |
| `PRINT_CARD`       | `PRINT_ON`                  | 啟動印表機列印 |

您可以在 `execute_hardware_command` 函式中擴充更多指令對應。 