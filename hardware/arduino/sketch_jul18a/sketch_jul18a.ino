#include <Servo.h> 
// #include <Unistep2.h>
#include <Stepper.h>

// Unistep2 stepper(4, 5, 6, 7, 4096, 1000);// IN1, IN2, IN3, IN4, 總step數, 每步的延遲(in micros)

const int TRIG_PIN = 9;
const int ECHO_PIN = 10;
const int MOTO_PIN = 11;
const int LIGHT_PIN = A0;
const int TOUCH_PIN = 2;

const float SOUND_SPEED = 0.0343;  // cm/μs

const int STEPS_PER_REV = 2048;
// 一定要用 pin1, pin3, pin2, pin4 的順序
Stepper motor(STEPS_PER_REV, 4, 6, 5, 7);

Servo myservo;  // 建立 SERVO 物件

// 門檻設定
const float DISTANCE_THRESHOLD = 40;
const unsigned long MAX_INTERVAL = 1000;
const unsigned long SAMPLE_INTERVAL = 20;

int waveState = 0;             // 0=等待「遠」、1=等待「近」、2=等待再「遠」
unsigned long stateTime = 0;   // 記錄每段開始時間
unsigned long lastSample = 0;  // 上次取樣時間

//// Light Setting ////
const int threshold = 860; // 根據實際環境調整
const unsigned long debounceDelay = 200; // 去彈跳延遲（毫秒）
bool lastState = false;
bool currentState = false;
unsigned long lastDebounceTime = 0;



int flag = 0;

// ========= function ========= //

// void motoSpin() {
//   myservo.write(180);  //旋轉到90度
//   delay(2000);
//   myservo.write(0);  //旋轉到180度
//   delay(1000);
// }

void newMotoSpin() {
  // stepper.run();

  // if ( stepper.stepsToGo() == 0 ){ // 如果stepsToGo=0，表示步進馬達已轉完應走的step了
  //   delay(500);
  //   stepper.move(4096);    //正轉一圈
  //   //stepper.move(-4096);  //負數就是反轉，反轉一圈
  // }
  motor.step(-STEPS_PER_REV*2);
  delay(5000);
  motor.step(STEPS_PER_REV*2);
  // motor.step(-STEPS_PER_REV);
  // motor.step(STEPS_PER_REV);
  // delay(100);
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


  // myservo.attach(MOTO_PIN);


  motor.setSpeed(12);
  // newMotoSpin();
}

void loop() {


  unsigned long now = millis();



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
        newMotoSpin();
      }
  }

  // ============ ✅ Scanning the QR code ============ //

  int lightValue = analogRead(LIGHT_PIN);
  bool reading = lightValue > threshold;

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
