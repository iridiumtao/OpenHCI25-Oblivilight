
import serial
import time
import requests
import threading
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# --- 設定 ---
# 請根據實際情況修改
SERIAL_PORT = '/dev/cu.usbserial-110'  # Arduino 的序列埠
BAUD_RATE = 9600
MAIN_BACKEND_URL = "http://localhost:8000/api/device/signal"
GATEWAY_HOST = "0.0.0.0"
GATEWAY_PORT = 8001

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage the application's lifespan. This handles startup and shutdown events.
    """
    # --- Startup Logic ---
    print("應用程式啟動，準備執行啟動程序...")
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # 等待 Arduino 重置
        print(f"成功連接到序列埠: {SERIAL_PORT}")
        
        print("啟動 Arduino 監聽線程...")
        listener_thread = threading.Thread(target=listen_to_arduino, daemon=True)
        listener_thread.start()
    except serial.SerialException as e:
        print(f"錯誤：無法開啟序列埠 {SERIAL_PORT}。請檢查連接。")
        print(f"詳細錯誤: {e}")
        ser = None # 確保 ser 在失敗時為 None

    yield

    # --- Shutdown Logic ---
    print("應用程式關閉，執行清理程序...")
    if ser and ser.is_open:
        ser.close()
        print("序列埠連線已關閉。")


# --- FastAPI 應用 ---
app = FastAPI(lifespan=lifespan)

class Command(BaseModel):
    command: str

# --- 序列埠通訊 ---
# 將 serial 物件的初始化移至 lifespan 中，以更好地管理資源
ser = None

def send_command_to_arduino(cmd: str):
    """發送指令到 Arduino"""
    if ser and ser.is_open:
        try:
            print(f"正在發送指令到 Arduino: {cmd}")
            ser.write((cmd + '\n').encode('utf-8'))
            return True
        except Exception as e:
            print(f"發送指令到 Arduino 時出錯: {e}")
            return False
    else:
        print("錯誤: 序列埠未連接，無法發送指令。")
        return False

def listen_to_arduino():
    """在背景線程中持續監聽來自 Arduino 的訊息"""
    while True:
        if ser and ser.is_open:
            try:
                raw_line = ser.readline()
                if not raw_line:
                    continue

                line = raw_line.decode('utf-8', errors='ignore').strip()
                if not line:
                    continue
                
                print(f"[Arduino Said] {line}")

                # TODO: 揮手遺忘、蓋住回顧、觸碰開機

                # --- 在這裡定義來自 Arduino 的訊號與對應的後端 API 訊號 ---
                if "WAKEUP_SIGNAL" in line:
                    signal = "WAKE_UP"
                    print(f"偵測到觸碰開機，準備發送 '{signal}' 訊號到主後端...")
                    requests.post(MAIN_BACKEND_URL, json={"signal": signal})
                elif "REWIND_SIGNAL" in line:
                    signal = "REWIND"
                    print(f"偵測到蓋住回顧，準備發送 '{signal}' 訊號到主後端...")
                    requests.post(MAIN_BACKEND_URL, json={"signal": signal})
                elif "SLEEP_SIGNAL" in line:
                    signal = "SLEEP"
                    print(f"偵測到觸碰關機睡眠，準備發送 '{signal}' 訊號到主後端...")
                    requests.post(MAIN_BACKEND_URL, json={"signal": signal})
                elif "FORGET_SIGNAL" in line:
                    signal = "FORGET"
                    print(f"偵測到揮手遺忘，準備發送 '{signal}' 訊號到主後端...")
                    requests.post(MAIN_BACKEND_URL, json={"signal": signal})

            except requests.exceptions.RequestException as e:
                print(f"錯誤：無法連接到主後端 ({MAIN_BACKEND_URL})。請確保後端服務正在運行。")
                print(f"詳細錯誤: {e}")
            except Exception as e:
                print(f"從 Arduino 讀取時發生未知錯誤: {e}")
                # 短暫停止以避免在連續錯誤時消耗過多 CPU
                time.sleep(5)
        else:
            # 如果序列埠未連接，每 5 秒重試一次
            print("序列埠未連接，5 秒後重試...")
            time.sleep(5)


# --- API 端點 ---
@app.post("/hardware/command")
async def execute_hardware_command(command_data: Command):
    """
    接收來自主要後端的指令並將其發送給硬體
    範例請求: {"command": "PRINT_ON"}
    """
    cmd = command_data.command
    print(f"從主後端收到指令: {cmd}")
    
    # --- 在這裡定義後端指令與 Arduino 指令的對應關係 ---
    if cmd == "PRINT_CARD":
        success = send_command_to_arduino("PRINT_ON")
        if success:
            return {"status": "success", "message": f"指令 '{cmd}' 已成功發送至 Arduino。"}
        else:
            raise HTTPException(status_code=500, detail="無法發送指令到 Arduino，請檢查序列埠連線。")
    # ... 你可以在這裡添加更多 else if 來處理不同的後端指令
    # elif cmd == "LIGHT_OFF":
    #     send_command_to_arduino("LIGHT_OFF")
    
    else:
        raise HTTPException(status_code=400, detail=f"未知的指令: '{cmd}'")

if __name__ == "__main__":
    print("硬體閘道器 (Hardware Gateway) 啟動中...")
    print(f"它將會監聽來自序列埠 '{SERIAL_PORT}' 的訊號。")
    print(f"並將訊號轉發到: {MAIN_BACKEND_URL}")
    print(f"同時，它也會在 http://{GATEWAY_HOST}:{GATEWAY_PORT} 接收來自後端的指令。")
    print("---")
    uvicorn.run(app, host=GATEWAY_HOST, port=GATEWAY_PORT) 