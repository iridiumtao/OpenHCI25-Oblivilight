#include <Servo.h> 

const int TRIG_PIN = 9;
const int ECHO_PIN = 10;
const int MOTO_PIN = 11;
const int LIGHT_PIN = A0;
const int TOUCH_PIN = 2;

const float SOUND_SPEED = 0.0343;  // cm/μs

Servo myservo;  // 建立 SERVO 物件

// 門檻設定
// const float NEAR_THRESHOLD = 30.0;
// const float FAR_THRESHOLD = 40.0;
const float DISTANCE_THRESHOLD = 40;
const unsigned long MAX_INTERVAL = 1000;
const unsigned long SAMPLE_INTERVAL = 20;  // 每 50 ms 取樣一次

int waveState = 0;             // 0=等待「遠」、1=等待「近」、2=等待再「遠」
unsigned long stateTime = 0;   // 記錄每段開始時間
unsigned long lastSample = 0;  // 上次取樣時間

//// Light Setting ////
const int threshold = 860; // 根據實際環境調整
const unsigned long debounceDelay = 200; // 去彈跳延遲（毫秒）
bool lastState = false;
bool currentState = false;
unsigned long lastDebounceTime = 0;




// ========= function ========= //

void motoSpin() {
  myservo.write(180);  //旋轉到90度
  delay(2000);
  myservo.write(0);  //旋轉到180度
  // delay(1000);
}

float measureDistance() {
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long dur = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (dur == 0){
    return DISTANCE_THRESHOLD+10;
  }

  return dur * SOUND_SPEED / 2.0;
}

void detectWave(float d, unsigned long t) {
  switch (waveState) {
    case 0:
      // 等待「遠」
      if (d > DISTANCE_THRESHOLD ) {
        waveState = 1;
        stateTime = t;
        // Serial.println("Wait for far!");
      }
      break;
    case 1:
      // 「遠」→「近」
      if (t - stateTime > MAX_INTERVAL) {
        resetWave();
      } else if (d < DISTANCE_THRESHOLD) {
        waveState = 2;
        stateTime = t;
        // Serial.println("Far to close");
      }
      break;
    case 2:
      // 「近」→再「遠」
      if (t - stateTime > MAX_INTERVAL) {
        resetWave();
      } else if (d > DISTANCE_THRESHOLD) {
        Serial.println("👋 WAVEDETECTED!");
        resetWave();
      }
      break;
  }
}

void resetWave() {
  waveState = 0;
  stateTime = 0;
}


// ========================= Main ==================== //

void setup() {
  
  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(TOUCH_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  Serial.begin(9600);
  // delay(50);


  myservo.attach(MOTO_PIN);
}

void loop() {

  unsigned long now = millis();


  // motoSpin();


  // ============ Turn on the Light ============ //

  int touchState = digitalRead(TOUCH_PIN);
  if( touchState == HIGH){
    Serial.println("Touched!");
  }

  // ============ ✅ Waving to Light ============ //
  if (now - lastSample >= SAMPLE_INTERVAL) {
    lastSample = now;
    float d = measureDistance();
    // Serial.println('Distance = ');
    // Serial.println(d);
    if (d < 0) {
      resetWave();
    } else {
      detectWave(d, now);
    }
  }

  // ============ ❓ Paper Printing (Spinning) Function ============ //
    if (Serial.available() > 0) {
      // Serial.println("Serial Good!");
      
      String cmd = Serial.readStringUntil('\n');
      cmd.trim();  // 去掉潛在的 \r 或空白

      // 比對指令
      if (cmd.equals("PRINT_ON")) {
        motoSpin();
      }
  }

  // ============ ✅ Scanning the QR code ============ //

  int lightValue = analogRead(LIGHT_PIN);
  bool reading = lightValue > threshold; // true: 亮, false: 暗

  if (reading != lastState) {
    // 狀態改變，重設計時器
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    // 狀態穩定超過 debounceDelay，才認定為真正改變
    if (reading != currentState) {
      currentState = reading;
      if (currentState) {
        Serial.println("SCANNED");
      } 
      // else {
      //   Serial.println("暗");
      // }
    }
  }

  lastState = reading;
  delay(10); // 100ms 迴圈
  
}
