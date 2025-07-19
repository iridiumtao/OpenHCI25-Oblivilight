import serial
import time

# 請根據實際情況改成你的埠名
PORT = '/dev/cu.usbserial-110'
BAUD = 9600

def main():
    # 開啟 Serial 連線
    ser = serial.Serial(PORT, BAUD, timeout=1)
    time.sleep(2)  # 等 Arduino reset

    try:
        print("開始監聽 Arduino 訊息...")
        while True:
            # 讀一行，到 '\n' 為止
            raw = ser.readline()
            if not raw:
                continue

            # 解碼，忽略 decode 錯誤
            line = raw.decode('utf-8', errors='ignore').strip()
            if not line:
                continue

            # 印出原始接收到的訊息
            print(f"[Arduino] {line}")

            # 檢查是不是 WAVEDETECTED
            if "WAVEDETECTED" in line:
                # 你可以把這裡換成任何你想做的事
                on_wave_detected()

    except KeyboardInterrupt:
        print("手動中斷程式。")

    finally:
        ser.close()
        print("Serial port 已關閉。")

def on_wave_detected():
    # 收到揮手偵測後執行的動作
    print(">>> 收到揮手偵測，開始執行後續動作！")

if __name__ == '__main__':
    main()
