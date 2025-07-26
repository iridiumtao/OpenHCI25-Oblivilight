// #include <Servo.h>
// #include <Unistep2.h>
#include <Stepper.h>
#include <ArduinoJson.h>

StaticJsonDocument<128> doc;

// Unistep2 stepper(4, 5, 6, 7, 4096, 1000);// IN1, IN2, IN3, IN4, 總step數, 每步的延遲(in micros)

const int TRIG_PIN = 9;
const int ECHO_PIN = 10;
const int MOTO_PIN = 11;
const int LIGHT_PIN = A0;
const int TOUCH_PIN = 2;

const float SOUND_SPEED = 0.0343;  // cm/μs
const int STEPS_PER_REV = 2048;
Stepper motor(STEPS_PER_REV, 4, 6, 5, 7);

// 門檻設定
const float DISTANCE_THRESHOLD = 30;
const unsigned long MAX_INTERVAL = 1000;
const unsigned long SAMPLE_INTERVAL = 20;

int waveState = 0;             // 0=等待「遠」、1=等待「近」、2=等待再「遠」
unsigned long stateTime = 0;   // 記錄每段開始時間
unsigned long lastSample = 0;  // 上次取樣時間

const unsigned long WAVE_COOLDOWN = 3000;   // 3 秒只算一次揮手
unsigned long lastWaveMillis = 0;           // 上次觸發時間

// DEBOUNCE SETTING //

const unsigned long TOUCH_DEBOUNCE = 150;  // 依實際情況調，大約 100~300 ms
const unsigned long QR_DEBOUNCE = 200;

bool touchStableState = false;  // 目前「確認」狀態
bool touchLastReading = false;  // 上一次 raw 讀值
unsigned long touchLastChange = 0;

bool qrStableState = false;
bool qrLastReading = false;
unsigned long qrLastChange = 0;

bool isAwake = false;     // false = Sleep, true = Wake up

//// Light Setting ////
const int LIGHT_THRESHOLD = 550;          // 根據實際環境調整
const unsigned long debounceDelay = 200;  // 去彈跳延遲（毫秒）
bool lastState = false;
bool currentState = false;
unsigned long lastDebounceTime = 0;

static bool qrArmed = true;  // 是否允許觸發
static unsigned long lastQrTime = 0;

const unsigned long QR_STARTUP_BLOCK = 5000;   // 開機後 5 s 內不觸發



// ========= function ========= //


void newMotoSpin() {

  // motor.step(STEPS_PER_REV * 2.05);
  // delay(3000);
  // motor.step(-STEPS_PER_REV * 2);


  motor.step(STEPS_PER_REV * 1.9);
  delay(3000);
  motor.step(-STEPS_PER_REV * 1.85);
  // motor.step(STEPS_PER_REV * 0.8);


  // motor.step(-STEPS_PER_REV);
  // motor.step(STEPS_PER_REV);
  // delay(100);
}

float measureDistance() {
  digitalWrite(TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(TRIG_PIN, LOW);
  unsigned long dur = pulseIn(ECHO_PIN, HIGH, 30000UL);
  if (dur == 0) {
    return DISTANCE_THRESHOLD + 10;
  }

  return dur * SOUND_SPEED / 2.0;
}

void detectWave(float d, unsigned long t) {
  // Serial.println("Distance = ");
  // Serial.println(d);
  switch (waveState) {
    case 0:
      // 等待「遠」
      if (d > DISTANCE_THRESHOLD) {
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
      // if (t - stateTime > MAX_INTERVAL) {
      //   resetWave();
      // } else if (d > DISTANCE_THRESHOLD) {
      //   Serial.println("FORGET_SIGNAL");
      //   resetWave();
      // }
      // break;
      if (t - stateTime > MAX_INTERVAL) {
          resetWave();
        } else if (d > DISTANCE_THRESHOLD) {
          if (t - lastWaveMillis >= WAVE_COOLDOWN) {   // 超過冷卻才觸發
            Serial.println("FORGET_SIGNAL");
            lastWaveMillis = t;                        // 更新時間
          }
          resetWave();
        }
        break;




  }
}

void resetWave() {
  waveState = 0;
  stateTime = 0;
}

bool debounceDigital(bool raw, bool &lastReading,
                     bool &stableState, unsigned long &lastChange,
                     unsigned long interval) {
  unsigned long now = millis();
  if (raw != lastReading) {
    lastChange = now;  // 發生跳動，重新計時
    lastReading = raw;
  }
  if (now - lastChange > interval && raw != stableState) {
    stableState = raw;  // 穩定超過 interval，才算真正改變
    return true;        // 回傳「狀態剛改變」
  }
  return false;  // 沒有改變
}

int flag = 0;

// ========================= Main ==================== //

void setup() {

  delay(2000);

  pinMode(TRIG_PIN, OUTPUT);
  pinMode(ECHO_PIN, INPUT);
  pinMode(TOUCH_PIN, INPUT);
  digitalWrite(TRIG_PIN, LOW);

  Serial.begin(9600);
  // delay(50);


  // myservo.attach(MOTO_PIN);


  motor.setSpeed(12);
  // newMotoSpin();
}

void loop() {


  unsigned long now = millis();

  // if(flag == 0){
  //   newMotoSpin();
  //   flag = 1;
  // }



  // ============ Turn on the Light ============ //




  // bool touchRaw = digitalRead(TOUCH_PIN);
  // if (debounceDigital(touchRaw,
  //                     touchLastReading, touchStableState,
  //                     touchLastChange, TOUCH_DEBOUNCE)) {
  //   if (touchStableState) {  // 只有由 LOW→HIGH 才送訊號
  //     Serial.println("WAKEUP_SIGNAL");
  //   }
  // }


  bool touchRaw = digitalRead(TOUCH_PIN);
  if (debounceDigital(touchRaw,
                      touchLastReading, touchStableState,
                      touchLastChange, TOUCH_DEBOUNCE))
  {
    if (touchStableState) {            // 只有 LOW→HIGH 觸發
      if (isAwake) {
        // Serial.println("SLEEP_SIGNAL");
        Serial.println("WAKEUP_SIGNAL");
        isAwake = false;               // 進入 Sleep
      } else {
        Serial.println("WAKEUP_SIGNAL");
        isAwake = true;                // 進入 Wake up
      }
    }
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

  // ============ ✅ Paper Printing (Spinning) Function ============ //
  // if (Serial.available() > 0) {
  //   // Serial.println("Serial Good!");

  //   String cmd = Serial.readStringUntil('\n');
  //   cmd.trim();  // 去掉潛在的 \r 或空白

  //   // 比對指令
  //   if (cmd.equals("PRINT_CARD")) {
  //     newMotoSpin();
  //   }
  // }

  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    if (!deserializeJson(doc, line)) {
      const char *cmd = doc["command"];
      if (strcmp(cmd, "PRINT_CARD") == 0) {
        newMotoSpin();
      }
    }
  }

  // ============ ✅ Scanning the QR code ============ //

  // int lightValue = analogRead(LIGHT_PIN);
  // bool qrRaw = lightValue > LIGHT_THRESHOLD;
  // if (debounceDigital(qrRaw,
  //                     qrLastReading, qrStableState,
  //                     qrLastChange, QR_DEBOUNCE)) {
  //   if (qrStableState) {
  //     Serial.println("REWIND_SIGNAL");
  //   }
  // }

  static bool qrReady  = false;                  // 是否允許觸發
  static bool qrArmed  = false;                  // 上膛：暗→亮才算一次
  // unsigned long now = millis();

  // 超過 5 s 才開放觸發
  if (now > QR_STARTUP_BLOCK) qrReady = true;

  int lightValue = analogRead(LIGHT_PIN);
  // Serial.println('light = ');
  // Serial.println(lightValue);
  bool qrRaw = lightValue > LIGHT_THRESHOLD;

  if (debounceDigital(qrRaw,
                      qrLastReading, qrStableState,
                      qrLastChange, QR_DEBOUNCE))
  {
    if (qrStableState && qrReady && !qrArmed) {  // 暗→亮
      Serial.println("REWIND_SIGNAL");
      qrArmed = true;            // 已觸發，等待變暗
      qrReady = false;           // 鎖住，直到再次變暗
    }
    if (!qrStableState) {        // 亮→暗
      qrArmed = false;           // 解除上膛
      if (now > QR_STARTUP_BLOCK) qrReady = true; // 重新允許
    }
  }

  // int lightValue = analogRead(LIGHT_PIN);
  // bool reading = lightValue > threshold;

  // if (reading != lastState) {
  //   // 狀態改變，重設計時器
  //   lastDebounceTime = millis();
  // }

  // if ((millis() - lastDebounceTime) > debounceDelay) {
  //   // 狀態穩定超過 debounceDelay，才認定為真正改變
  //   if (reading != currentState) {
  //     currentState = reading;
  //     if (currentState) {
  //       Serial.println("REWIND_SIGNAL");
  //     }
  //     // else {
  //     //   Serial.println("暗");
  //     // }
  //   }
  // }

  // lastState = reading;


  delay(10);  // 100ms 迴圈
}
