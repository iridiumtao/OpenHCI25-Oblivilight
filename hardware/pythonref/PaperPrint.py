import serial
import time

PORT = '/dev/cu.usbserial-110'
BAUD = 9600

# 建立 Serial 連線
ser = serial.Serial(PORT, BAUD, timeout=1)
time.sleep(2)  # 等待 Arduino reset 完成

def send_cmd(cmd: str):
    """送出一行指令（自動加上換行）"""
    ser.write((cmd + '\n').encode('utf-8'))
    # ser.flush()  # 視需要可強制送出緩衝區

send_cmd("PRINT_ON")

# 程式結束前關閉序列埠
ser.close()
