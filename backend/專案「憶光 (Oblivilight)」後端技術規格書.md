

## **專案「憶光 (Oblivilight)」後端技術規格書 for AI Agent**

文件版本: 2.1 (Backend Final)  
目標: 本文件旨在作為 Gemini 2.5 Pro 等 AI Coding Agent 的輸入，用於生成專案「憶光」的完整後端應用程式。

### **1.0 專案概述**

本專案為「憶光 (Oblivilight)」，一個 AI 助眠日記燈。後端系統需負責處理即時語音、情緒分析、對話管理、日記存檔，並透過 API 與硬體裝置和使用者網頁互動。其核心設計理念是「遺忘」與「使用者主導的回憶」，AI 本身不具備主動查詢過往記憶的能力。

### **2.0 核心技術堆疊**

* **語言**: Python 3.10+  
* **Web 框架**: FastAPI  
* **AI 應用框架**: LangChain  
* **非同步網路**: uvicorn, websockets  
* **語音轉文字 (STT)**: openai-whisper (本地端), openai (雲端 API)  
* **音訊處理**: sounddevice, scipy  
* **圖片/卡片處理**: Pillow  
* **QR Code**: qrcode  
* **環境變數管理**: python-dotenv

### **3.0 專案目錄結構**

請依照以下結構生成專案檔案：

```
backend/  
├── main.py             \# FastAPI 應用主體，API 路由與 WebSocket 管理  
├── core/  
│   ├── agent.py        \# 核心業務邏輯與狀態管理器  
│   ├── chains.py       \# 集中管理所有 LangChain Chains  
│   └── tools.py        \# 集中管理所有 LangChain Tools  
├── services/  
│   ├── audio_service.py \# 封裝音訊擷取服務
│   └── stt\_service.py  \# 封裝本地與雲端的 Whisper 呼叫  
├── datastore/          \# (由程式自動建立) 存放日記 JSON 檔案  
├── static/videos/      \# (手動建立) 存放燈效影片  
├── config/  
│   ├── prompts.json  
│   └── video\_mapping.json  
└── requirements.txt
```

### **4.0 設定檔 (Configuration Files)**

請生成以下設定檔內容。

#### **4.1 config/prompts.json**

```JSON
{  
  "emotion_analysis": {  
    "system_prompt": "你是一個情緒分類器。分析以下使用者文字的情緒，並只回傳 JSON 物件，格式為 {{\"text_emotion\": \"<happy|sad|angry|surprised|neutral>\"}}。\n\n---\n使用者文字: {text}"
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

#### **4.2 config/video\_mapping.json**

```JSON
{  
  "happy": "static/videos/happy_light.mp4",  
  "sad": "static/videos/sad_light.mp4",  
  "angry": "static/videos/angry_light.mp4",  
  "surprised": "static/videos/surprised_light.mp4",  
  "neutral": "static/videos/neutral_light.mp4",  
  "SLEEP": "static/videos/sleep_mode.mp4",  
  "IDLE": "static/videos/idle_breathing.mp4"  
}
```

### **5.0 核心邏輯與狀態管理 (core/agent.py)**

#### **5.1 狀態模擬**

使用一個簡單的類別來管理系統的全局狀態，以避免引入複雜的狀態機函式庫。

```Python

# In core/agent.py  
class SystemState:  
    def __init__(self):  
        self.is_listening = False  
        self.is_processing = False # 用於鎖定型任務 (忘記, 總結)  
        self.injected_context = None # 用於 RAG 模式  
        self.conversation_history = [] # 用於儲存對話歷史
        # ... 可能還有其他狀態變數
```
應用程式中應存在一個此類別的單例。

#### **5.2 主要工作流程**

1. **即時情緒分析循環**:  
   * 當 `system_state.is_listening` 為 True 時，`audio_service` 會在背景執行緒中持續錄製音訊，並將音訊塊放入一個共享的佇列 (`Queue`)。
   * 應用程式的主迴圈或一個獨立的背景任務會從佇列中取得音訊。
   * 將音訊傳給 `stt_service` 的本地 Whisper (`transcribe_realtime`) 進行辨識。
   * 取得文字後，累加到 `system_state.conversation_history`。
   * 將辨識出的文字傳給 `emotion_analysis` chain。  
   * 取得情緒 JSON 後，透過 WebSocket 將情緒標籤發送給前端。  
2. **忘記記憶流程**:  
   * 接收到 FORGET\_\* signal。  
   * 設定 `system_state.is_processing = True`。  
   * 根據訊號（FORGET\_8S/FORGET\_30S），計算需移除的字數（暫定 25/90 字）。  
   * 操作 `system_state.conversation_history` 字串列表，從後往前移除訊息，直到滿足字數。  
   * 使用 `forget_confirmation` prompt 產生確認摘要。  
   * (可選) 呼叫 TTS 服務播放摘要。  
   * 設定 system\_state.is\_processing \= False。  
3. **每日總結流程**:  
   * 接收到 SLEEP\_TRIGGER signal。  
   * 設定 `system_state.is_listening = False` 及 `system_state.is_processing = True`。  
   * 將 `system_state.conversation_history` 中儲存的完整對話文字組合起來。
   * （可選，若有儲存完整音檔）將 session 期間錄製的完整音訊傳給 `stt_service` 的雲端 Whisper API (`transcribe_full`)。
   * 使用 `daily_summary_full` prompt 產生完整摘要。  
   * 使用 `daily_summary_short` prompt 產生 30 字結語。  
   * 呼叫 database\_tool 的 create\_memory 存檔並取得 uuid。  
   * 呼叫 printer\_tool 的 generate\_card\_image 生成卡片圖片。  
   * 重設所有 session 狀態，回到 IDLE。  
4. **注入上下文 (RAG) 流程**:  
   * 接收到 POST /api/session/inject-context 的請求。  
   * 將請求 body 中的 context 字串賦值給 system\_state.injected\_context。  
   * 在後續的對話中，LangChain 的主對話 Chain 應使用 rag\_conversation prompt，它會將 injected\_context 插入到 LLM 的上下文中。

### **6.0 API 端點定義 (FastAPI) (main.py)**

#### **6.1 WebSocket for Real-time Control**

* **路由**: WS /ws/projector  
* **功能**: 建立與前端投影頁面的長連線，用於後端主動推送燈效指令。  
* **訊息格式 (後端 \-\> 前端)**: {"type": "SET\_EMOTION", "payload": {"emotion": "\<emotion\_label\>"}} 或 {"type": "SET\_MODE", "payload": {"mode": "\<mode\_name\>"}}。

#### **6.2 Device-to-Backend Communication**

* **路由**: POST /api/device/signal  
* **功能**: 接收來自 Arduino 的訊號，觸發後端核心行為。  
* **請求 Body**: {"signal": "\<signal\_type\>"}，signal\_type 可為 "FORGET\_8S", "FORGET\_30S", "SLEEP\_TRIGGER", "WAKE\_UP"。  
* **成功回應**: 200 OK {"status": "ok", "message": "Signal received."}。  
* **錯誤回應**: 400 Bad Request {"detail": "Invalid signal type."}。

#### **6.3 Web App-to-Backend Communication**

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
*   當 `system_state.is_listening` 為 `True` 時，將錄製到的音訊塊 (Numpy Array) 放入一個全域共享的 `queue.Queue` 中，供其他模組（如 `core/agent.py`）消費。

#### **7.2 services/stt\_service.py**

*   應包含兩個函式：  
    *   `transcribe_realtime(audio_chunk)`: 載入本地 Whisper (`small`) 模型，對傳入的音訊塊 (`Numpy Array`) 進行辨識。它不直接處理音訊錄製。
    *   `transcribe_full(audio_file_path)`: 使用 `openai` client，呼叫雲端 Whisper API 對完整音訊檔案進行辨識。

#### **7.3 core/tools.py \- Database Tool**

* create\_memory(summary\_data): 生成 `uuid.uuid4()`，將 `summary_data` (一個 dict) 寫入 `datastore/{uuid}.json`。  
* read\_memory(uuid): 讀取並回傳 `datastore/{uuid}.json` 的內容。  
* update\_memory(uuid, update\_data): 讀取、更新、並寫回 `datastore/{uuid}.json`。

#### **7.4 core/tools.py \- Printer Tool**

* generate\_card\_image(date\_str, short\_summary, qr\_data, output\_path):  
  * 使用 Pillow 建立一張 1080x720 的米黃色 (\#FDF6E3) 背景圖片。  
  * 載入字體 (若 arial.ttf 不可用，則使用預設字體)。  
  * 在 (60, 60\) 位置繪製日期文字 (字號 48)。  
  * 在 (60, 200\) 位置繪製 30 字結語 (字號 72)。  
  * 使用 qrcode 生成一個 250x250 的 QR Code 圖片。  
  * 將 QR Code 貼到 (780, 470\) 的位置。  
  * 將最終圖片儲存到 `output_path`。

#### **7.5 core/tools.py \- Light Control Tool**

* set\_light\_effect(effect\_name): 此函式應與 `main.py` 中的 WebSocket 管理器互動，將對應的指令（如 `{"type": "SET_EMOTION", "payload": {"emotion": "happy"}}`）發送給所有已連接的客戶端。

#### **7.6 core/agent.py**

*   此檔案應包含 `SystemState` 類別。  
*   應包含一個主控類別 `Agent`，用於初始化 LCEL (LangChain Expression Language)、Tools。
*   `Agent` 應負責從 `audio_service` 的佇列中獲取音訊，傳遞給 `stt_service` 進行即時辨識。
*   `Agent` 應根據 API 傳來的指令，調用正確的工作流程（如 `process_daily_summary`, `process_forget_memory` 等）。

#### **7.7 core/chains.py**

* 此檔案應初始化所有需要的 LCEL，並預先綁定從 `prompts.json` 讀取到的 Prompt 模板。

