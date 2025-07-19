# 憶光 (Oblivilight) - 後端服務 README

本文件為「憶光 (Oblivilight)」專案的後端服務說明，旨在引導開發者完成環境設定、服務配置與啟動流程。

## 1. 專案簡介

憶光 (Oblivilight) 是一個 AI 助眠日記燈，其後端服務是整個系統的核心，負責處理以下主要功能：
-   即時語音辨識與情緒分析
-   與 AI 的對話管理與互動
-   日記的生成、儲存與檢索
-   透過 WebSocket 與前端投影頁面溝通，傳送燈效指令
-   接收並處理來自硬體閘道器的訊號

## 2. 技術棧

-   **語言**: Python 3.10+
-   **Web 框架**: FastAPI
-   **AI 應用框架**: LangChain
-   **非同步伺服器**: Uvicorn
-   **WebSocket**: websockets
-   **語音轉文字 (STT)**: OpenAI Whisper
-   **文字轉語音 (TTS)**: Yating
-   **硬體通訊**: PySerial

## 3. 環境設置

請依照以下步驟設置您的本地開發環境。

### 步驟 1: 建立並啟用虛擬環境

在專案根目錄下執行以下指令，建立並啟用 Python 虛擬環境：

```bash
# 建立虛擬環境
python3 -m venv venv

# 啟用虛擬環境 (macOS / Linux)
source venv/bin/activate

# 啟用虛擬環境 (Windows)
# venv\Scripts\activate
```

### 步驟 2: 安裝相依套件

確認虛擬環境已啟用後，安裝 `requirements.txt` 中定義的所有套件：

```bash
pip install -r backend/requirements.txt
```

## 4. 設定

在啟動服務前，請完成以下設定。

### 環境變數

後端服務需要一些 API 金鑰才能正常運作。請在 `backend/` 資料夾下建立一個名為 `.env` 的檔案，並填入以下內容：

```env
# .env

# OpenAI API 金鑰，用於語音轉文字服務
OPENAI_API_KEY="YOUR_OPENAI_API_KEY"

# Yating TTS API 金鑰，用於文字轉語音服務
YATING_API_KEY="YOUR_YATING_API_KEY"
```
> **注意**: `.env` 檔案應被視為機密資訊，不應提交至版本控制系統。

### 設定檔

專案的 AI 提示詞與燈效影片對應關係，定義於 `backend/config/` 資料夾中：
-   `prompts.json`: 管理所有與 LangChain 互動的 Prompt 模板。
-   `video_mapping.json`: 定義情緒或系統狀態與對應燈效影片的路徑。

### 靜態影片檔案

請確保所有在 `video_mapping.json` 中定義的燈效影片，都已正確放置於 `backend/static/videos/` 資料夾中。

## 5. 執行專案

本專案的後端系統由兩個獨立運行的服務組成：**核心後端**與**硬體閘道器**。您需要開啟兩個終端機視窗來分別啟動它們。

### 啟動核心後端 (FastAPI)

在 **第一個終端機** 中，從 **專案根目錄** 執行以下指令來啟動主服務：

```bash
uvicorn backend.main:app --reload --port 8000
```
此服務將會運行在 `http://localhost:8000`。

### 啟動硬體閘道器

在 **第二個終端機** 中，從 **專案根目錄** 執行以下指令來啟動硬體通訊服務：

```bash
python hardware/hardware_gateway.py
```
此閘道器負責監聽來自 Arduino 的序列埠訊號，並將其轉發給核心後端。同時，它也會接收來自後端的指令，以控制硬體（如印表機）。

## 6. API 端點詳解

本後端服務提供多個 API 端點，用於系統內部通訊以及與前端應用程式的互動。

### 6.1 WebSocket: `/ws/projector`

-   **用途**: 建立一個與前端燈效投影頁面的長連線。後端可透過此連線主動推送指令，即時改變燈光效果。
-   **方向**: 後端 -> 前端
-   **訊息格式**:

    #### 1. 設定情緒燈效 (`SET_EMOTION`)
    後端會根據即時對話分析出的情緒，發送此訊息來改變燈光。
    ```json
    {"type": "SET_EMOTION", "payload": {"emotion": "<emotion_type>"}}
    ```
    -   **`emotion_type`** (string): 可用的情緒類型包含：
        -   `happy`, `sad`, `warm`, `optimistic`, `anxious`, `peaceful`, `depressed`, `lonely`, `angry`, `neutral`

    #### 2. 設定特定模式 (`SET_MODE`)
    後端會根據系統狀態（如閒置、遺忘、睡眠）發送此訊息。
    ```json
    {"type": "SET_MODE", "payload": {"mode": "<mode_name>"}}
    ```
    -   **`mode_name`** (string): 可用的模式包含：
        -   `IDLE`: 閒置狀態，通常是呼吸燈效果。
        -   `SLEEP`: 進入睡眠總結流程時的狀態。
        -   `FORGET`: 執行遺忘記憶功能時的狀態。

### 6.2 硬體訊號: `POST /api/device/signal`

-   **用途**: 接收來自「硬體閘道器」的訊號，以觸發核心業務邏輯。這是硬體與軟體之間的主要溝通橋樑。
-   **請求 Body**:
    ```json
    {"signal": "SIGNAL_TYPE"}
    ```
    其中 `SIGNAL_TYPE` 可以是 `"WAKE_UP"`, `"SLEEP_TRIGGER"`, `"FORGET_8S"`, `"FORGET_30S"`。
-   **成功回應 (200 OK)**:
    ```json
    {"status": "ok", "message": "Signal 'WAKE_UP' received and is being processed."}
    ```
-   **錯誤回應 (400 Bad Request)**:
    ```json
    {"detail": "Invalid signal type."}
    ```

### 6.3 系統狀態: `GET /api/status`

-   **用途**: 讓外部應用（如前端監控頁面）可以查詢後端當前的運行狀態。
-   **成功回應 (200 OK)**:
    ```json
    {
      "is_listening": false,
      "is_processing": true,
      "conversation_history_length": 15
    }
    ```

### 6.4 讀取回憶: `GET /api/memory/{uuid}`

-   **用途**: 根據日記的唯一識別碼 (UUID) 獲取其完整的 JSON 存檔資料。
-   **路徑參數**: `uuid` - 日記的唯一識別碼。
-   **成功回應 (200 OK)**:
    ```json
    // 返回該篇日記的完整 JSON 結構
    {
      "uuid": "...",
      "date": "...",
      "full_summary": "...",
      "short_summary": "...",
      "raw_conversation": [...]
    }
    ```
-   **錯誤回應 (404 Not Found)**:
    ```json
    {"detail": "Memory not found."}
    ```

### 6.5 更新回憶: `PUT /api/memory/{uuid}`

-   **用途**: 允許使用者（透過前端介面）修改已存檔日記的摘要內容。
-   **路徑參數**: `uuid` - 日記的唯一識別碼。
-   **請求 Body**:
    ```json
    {"full_summary": "這是更新後的日記摘要內容..."}
    ```
-   **成功回應 (200 OK)**: 返回更新後的完整日記 JSON 物件。

### 6.6 注入上下文 (RAG): `POST /api/session/inject-context`

-   **用途**: 將一篇過去的日記摘要注入到當前的對話中，讓 AI 能夠基於這段記憶與使用者進行更有連續性的對話 (Retrieval-Augmented Generation)。
-   **請求 Body**:
    ```json
    {"context": "這是從過去某篇日記中提取的摘要文字..."}
    ```
-   **成功回應 (200 OK)**:
    ```json
    {"status": "success", "message": "Context injected."}
    ``` 