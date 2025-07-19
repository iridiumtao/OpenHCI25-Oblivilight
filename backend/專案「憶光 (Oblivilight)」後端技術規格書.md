

## **專案「憶光 (Oblivilight)」後端技術規格書 for AI Agent**

文件版本: 2.2 (Hardware Gateway Integration)
目標: 本文件旨在作為 Gemini 2.5 Pro 等 AI Coding Agent 的輸入，用於生成專案「憶光」的完整後端應用程式。

### **1.0 專案概述**

本專案為「憶光 (Oblivilight)」，一個 AI 助眠日記燈。系統由兩部分組成：
1.  **核心後端 (Core Backend)**: 負責處理即時語音、情緒分析、對話管理、日記存檔，並透過 API 與使用者網頁互動。
2.  **硬體閘道器 (Hardware Gateway)**: 一個獨立的服務，作為核心後端與 Arduino 硬體之間的橋樑，負責序列埠通訊。

其核心設計理念是「遺忘」與「使用者主導的回憶」，AI 本身不具備主動查詢過往記憶的能力。

### **2.0 核心技術堆疊**

*   **語言**: Python 3.10+
*   **Web 框架**: FastAPI
*   **AI 應用框架**: LangChain
*   **非同步網路**: uvicorn, websockets
*   **序列埠通訊**: pyserial
*   **語音轉文字 (STT)**: openai-whisper (本地端), openai (雲端 API)
*   **文字轉語音 (TTS)**: Yating (透過 REST API), playsound
*   **音訊處理**: sounddevice, scipy
*   **圖片/卡片處理**: Pillow
*   **QR Code**: qrcode
*   **環境變數管理**: python-dotenv

### **3.0 專案目錄結構**

請依照以下結構生成專案檔案：

```
.
├── backend/  
│   ├── main.py             # FastAPI 應用主體，API 路由與 WebSocket 管理  
│   ├── core/  
│   │   ├── agent.py        # 核心業務邏輯與狀態管理器  
│   │   ├── chains.py       # 集中管理所有 LangChain Chains  
│   │   ├── state.py        # 定義並導出全局單例狀態 (system_state)
│   │   └── tools.py        # 集中管理所有 LangChain Tools  
│   ├── services/  
│   │   ├── audio_service.py # 封裝音訊擷取服務
│   │   ├── stt_service.py  # 封裝本地與雲端的 Whisper 呼叫
│   │   └── tts_service.py  # 封裝 TTS 服務呼叫
│   ├── datastore/          # (由程式自動建立) 存放日記 JSON 檔案  
│   ├── config/  
│   │   └── prompts.json  
│   └── requirements.txt
└── hardware/
    └── hardware_gateway.py # 獨立的硬體通訊服務
```

### **4.0 設定檔 (Configuration Files)**

請生成以下設定檔內容。

#### **4.1 config/prompts.json**

```JSON
{  
  "emotion_analysis": {  
    "system_prompt": "你是一個情緒分類器。分析以下使用者文字的情緒，並只回傳 JSON 物件，格式為 {{\"text_emotion\": \"<happy|sad|warm|optimistic|anxious|peaceful|depressed|lonely|angry|neutral>\"}}。\n\n---\n使用者文字: {text}"
  },  
  "daily_summary_full": {  
    "system_prompt": "你是一位溫柔且善於傾聽的日記助手。請將以下使用者整晚的對話，以第一人稱『我』的視角，整理成一段約 150-200 字的、流暢且帶有情感溫度的日記摘要。風格應該是內省的、平和的。"  
  },  
  "daily_summary_short": {  
    "system_prompt": "你是一位精煉短語的詩人。請將以下日記摘要的核心精髓，濃縮成一句 30 字以內的、詩意且耐人尋味的結語。"  
  },  
  "forget_confirmation": {  
    "system_prompt": "使用者剛剛選擇忘記了一段對話。請簡短地總結目前還記得的對話內容，並用溫和的語氣說出『我還記得的是...』作為開頭，讓使用者知道對話是從哪裡繼續的。"  
  },  
  "rag_conversation": {  
    "system_prompt": "你正在與使用者繼續一段過去的對話。以下是那天的日記摘要，請將其作為核心背景知識。在回應使用者的新問題時，請自然地結合這段舊有記憶。\\n--- \\n過往記憶: {injected_context}\\n---"  
  }  
}
```

### **5.0 核心邏輯與狀態管理 (core/agent.py)**

專案的核心邏輯由 `core/agent.py` 中的 `Agent` 類別統一管理。`main.py` 僅負責初始化 FastAPI 應用、定義 API 端點以及在啟動時觸發 Agent 的主迴圈。

#### **5.1 狀態管理 (`core/state.py`)**

為了避免循環引用 (circular imports)，所有全局共享的狀態都被定義在 `core/state.py` 中。

```Python
# In core/state.py
class SystemState:  
    def __init__(self):  
        self.is_listening = False  
        self.is_processing = False 
        self.injected_context = None 
        self.conversation_history = []
        self.full_audio_path = None

# ... 此檔案還會導出一個全局單例 ...
# system_state = SystemState()
```
任何需要讀取或修改系統狀態的模組（如 `agent.py` 或 `audio_service.py`）都應該從此檔案導入 `system_state` 單例。

#### **5.2 主要工作流程 (`core/agent.py`)**

1.  **即時情緒分析循環 (Agent 主迴圈)**:
    *   應用程式啟動時，`main.py` 會呼叫並以背景任務形式執行 `agent.run_real_time_emotion_analysis()`。
    *   此方法是 Agent 的主迴圈，持續檢查 `system_state.is_listening` 狀態。
    *   當 `is_listening` 為 `True` 時，它會從 `audio_service` 提供的共享佇列 (`Queue`) 中取得音訊塊。
    *   將音訊傳給 `stt_service` 的本地 Whisper (`transcribe_realtime`) 進行辨識。
    *   取得文字後，累加到 `system_state.conversation_history`。
    *   將辨識出的文字傳給 `emotion_analysis` chain。
    *   取得情緒 JSON 後，透過 `LightControlTool` 將情緒標籤發送給前端。
2.  **硬體訊號處理**:
    *   所有來自硬體的訊號（透過 `/api/device/signal`）都會被路由到 `agent.handle_signal` 方法。
    *   **`WAKE_UP`**: 設定 `system_state.is_listening = True`，並重設對話歷史，準備開始新的對話。
    *   **`SLEEP_TRIGGER`**: 呼叫 `agent.process_daily_summary` 流程。
    *   **`FORGET_8S` / `FORGET_30S`**: 呼叫 `agent.process_forget_memory` 流程。
3.  **忘記記憶流程**:
    *   設定 `system_state.is_processing = True`。
    *   根據訊號，計算需移除的字數（`FORGET_8S` 約 30 字，`FORGET_30S` 約 60 字）。
    *   操作 `system_state.conversation_history` 列表，從後往前移除訊息，直到滿足字數。
    *   使用 `forget_confirmation` prompt 產生確認摘要。
    *   呼叫 `tts_service` 播放摘要語音，給予使用者聽覺回饋。
    *   設定 `system_state.is_processing = False`。
4.  **每日總結流程**:
    *   設定 `system_state.is_listening = False` 及 `system_state.is_processing = True`。
    *   將 `system_state.conversation_history` 中儲存的完整對話文字組合起來。
    *   使用 `daily_summary_full` prompt 產生完整摘要。
    *   使用 `daily_summary_short` prompt 產生 30 字結語。
    *   呼叫 `database_tool` 的 `create_memory` 存檔並取得 uuid。
    *   為 QR Code 產生指向前端應用的 URL (例如 `http://localhost:3000/memory/{uuid}`)。
    *   **呼叫 `CardAndPrinterTool` 的 `generate_and_print_card` 方法，此方法會完成以下兩件事：**
        *   **生成包含日期、結語和 QR Code 的卡片圖片。**
        *   **向硬體閘道器 (Hardware Gateway) 發送 HTTP 請求，觸發實體卡片列印。**
    *   呼叫 `system_state.reset_session()` 重設所有狀態，回到 IDLE。
5.  **注入上下文 (RAG) 流程**:
    *   `main.py` 中的 `POST /api/session/inject-context` 端點接收請求。
    *   將請求 body 中的 context 字串賦值給 `system_state.injected_context`。

### **6.0 API 端點定義 (FastAPI) (main.py)**

#### **6.1 WebSocket for Real-time Control**

* **路由**: WS /ws/projector  
* **功能**: 建立與前端投影頁面的長連線，用於後端主動推送燈效指令。  
* **訊息格式 (後端 \-\> 前端)**: {"type": "SET\_EMOTION", "payload": {"emotion": "\<emotion\_label\>"}} 或 {"type": "SET\_MODE", "payload": {"mode": "\<mode\_name\>"}}。

#### **6.2 Device-to-Backend Communication**

* **路由**: POST /api/device/signal  
* **功能**: **接收來自獨立運行的「硬體閘道器」的訊號**，觸發後端核心行為。  
* **請求 Body**: {"signal": "<signal_type>"}，signal_type 可為 "FORGET_8S", "FORGET_30S", "SLEEP_TRIGGER", "WAKE_UP"。  
* **成功回應**: 200 OK {"status": "ok", "message": "Signal 'WAKE_UP' received and is being processed."}。
* **錯誤回應**: 400 Bad Request {"detail": "Invalid signal type."}。

#### **6.3 Web App-to-Backend Communication**

* **讀取後端狀態**:
  * **路由**: GET /api/status
  * **功能**: 獲取後端系統當前的運行狀態，用於監控與除錯。
  * **成功回應**: 200 OK，回傳 `BackendStatus` 模型定義的 JSON 物件，包含 `is_listening`, `is_processing` 等狀態。
* **讀取回憶**:  
  * **路由**: GET /api/memory/{uuid}  
  * **功能**: 獲取單日日記的 JSON 資料。  
  * **成功回應**: 200 OK，回傳日記的 JSON 物件。  
  * **錯誤回應**: 404 Not Found {"detail": "Memory not found."}。  
* **更新回憶**:  
  * **路由**: PUT /api/memory/{uuid}  
  * **功能**: 更新日記摘要。  
  * **請求 Body**: {"full\_summary": "new updated text..."}。  
  * **成功回應**: 200 OK，回傳更新後的 JSON 物件。  
* **注入上下文 (RAG)**:  
  * **路由**: POST /api/session/inject-context  
  * **功能**: 接收前端傳遞的文字，注入到當前對話 session。  
  * **請求 Body**: {"context": "text\_of\_the\_past\_memory..."}。  
  * **成功回應**: 200 OK {"status": "success", "message": "Context injected."}。

### **7.0 詳細模組功能實現**

#### **7.1 services/audio\_service.py**
*   **功能**: 負責從麥克風即時擷取音訊。
*   應包含一個 `start_mic_thread` 函式，用於啟動一個背景監聽執行緒。
*   該執行緒使用 `sounddevice` 函式庫，持續錄製音訊。
*   當 `system_state.is_listening` 為 `True` 時，將錄製到的音訊塊 (Numpy Array) 放入一個全域共享的 `queue.Queue` 中，供 `core/agent.py` 中的 `run_real_time_emotion_analysis` 方法消費。

#### **7.2 services/stt\_service.py**

*   應包含兩個函式：  
    *   `transcribe_realtime(audio_chunk)`: 載入本地 Whisper (`small`) 模型，對傳入的音訊塊 (`Numpy Array`) 進行辨識。它不直接處理音訊錄製。
    *   `transcribe_full(audio_file_path)`: 使用 `openai` client，呼叫雲端 Whisper API 對完整音訊檔案進行辨識。

#### **7.3 services/tts\_service.py**
*   **功能**: 封裝對外部文字轉語音服務 (如 Yating) 的呼叫。
*   應包含一個函式，例如 `text_to_speech_and_play(text)`。
*   此函式接收文字輸入，使用 `requests` 函式庫向 TTS 服務的 API 端點發送請求。
*   接收到音訊檔案 (如 MP3) 後，使用 `playsound` 函式庫進行播放。
*   此模組主要被 `core/agent.py` 中的「忘記記憶」流程調用，以提供語音回饋。

#### **7.4 core/tools.py \- Database Tool**

*   create_memory(summary_data): 生成 `uuid.uuid4()`，將 `summary_data` (一個 dict) 寫入 `datastore/{uuid}.json`。
*   read_memory(uuid): 讀取並回傳 `datastore/{uuid}.json` 的內容。
*   update_memory(uuid, update_data): 讀取、更新、並寫回 `datastore/{uuid}.json`。

#### **7.5 core/tools.py \- Card and Printer Tool**

*   **職責**: 此工具類別 (`CardAndPrinterTool`) 整合了卡片圖片生成與觸發硬體列印的功能。
*   `generate_and_print_card(date_str, short_summary, qr_data)`:
    *   **生成圖片**: 使用 Pillow 建立一張包含日期、結語和 QR Code 的卡片圖片，並儲存於本地。
    *   **觸發列印**: 使用 `requests` 向 `hardware_gateway.py` 服務的 `/hardware/command` 端點發送一個 `{"command": "PRINT_CARD"}` 的 POST 請求。
    *   Agent 在每日總結流程的最後，會呼叫此方法來完成實體卡片的產出。

#### **7.6 core/tools.py \- Light Control Tool**

* set\_light\_effect(effect\_name): 此函式應與 `main.py` 中的 WebSocket 管理器互動，將對應的指令（如 `{"type": "SET_EMOTION", "payload": {"emotion": "happy"}}`）發送給所有已連接的客戶端。

#### **7.7 core/agent.py**

*   **職責**: 包含主控類別 `Agent`，作為狀態與邏輯的集中管理者。它從 `core.state` 導入 `system_state` 來存取全局狀態。
*   **主要方法**:
    *   `run_real_time_emotion_analysis`: Agent 的主處理迴圈。
    *   `handle_signal`: 處理來自硬體的觸發事件。
    *   `process_daily_summary` / `process_forget_memory`: 執行具體的業務邏輯。
*   `Agent` 是整個應用程式核心業務邏輯的中心。

#### **7.8 core/chains.py**

* 此檔案應初始化所有需要的 LCEL，並預先綁定從 `prompts.json` 讀取到的 Prompt 模板。

#### **7.9 main.py**
*   **功能**: FastAPI 應用主體，主要作為 Web 層，負責處理 HTTP 請求與 WebSocket 連線。
*   **啟動程序**: 使用 `lifespan` 管理器處理應用程式的生命週期。在啟動時，它會初始化 `agent`、啟動 `audio_service` 的監聽執行緒，並啟動 `agent.run_real_time_emotion_analysis()` 作為背景任務。在關閉時，它會優雅地取消背景任務。
*   **API 路由**: 定義所有 `/api/...` 與 `/ws/...` 端點，並將需要複雜處理的請求（如 `/api/device/signal`）委派給 `agent` 的相應方法。
*   它自身 **不** 包含核心業務邏輯的實作。

### **8.0 硬體整合 (Hardware Integration)**

專案的硬體互動由一個獨立的 Python 腳本 `hardware/hardware_gateway.py` 負責，它扮演著「硬體閘道器」的角色。

#### **8.1 職責**

*   **監聽 Arduino**: 持續透過 `pyserial` 監聽來自 Arduino 的序列埠訊息 (如 `WAVEDETECTED_START`)。
*   **轉發訊號**: 將接收到的硬體訊息，轉換成定義好的訊號 (如 `WAKE_UP`)，並透過 HTTP POST 請求發送至主後端 `main.py` 的 `/api/device/signal` 端點。
*   **接收指令**: 運行一個迷你的 FastAPI 伺服器，開放 `/hardware/command` 端點。
*   **執行指令**: 當收到來自 `core/tools.py` 的指令時 (如 `PRINT_CARD`)，透過序列埠將對應的指令 (如 `PRINT_ON`) 發送給 Arduino。

#### **8.2 運行方式**

此閘道器必須作為一個獨立的行程與主後端 `main.py` 同時運行。

```bash
# 啟動主後端 (在專案根目錄)
uvicorn backend.main:app --reload --port 8000

# 啟動硬體閘道器 (在另一個終端機)
python hardware/hardware_gateway.py
```

這種分離式架構確保了硬體通訊的穩定性不會影響核心後端服務。

