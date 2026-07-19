#include <Wire.h>
#include <Adafruit_Sensor.h>
#include <Adafruit_BNO055.h>
#include <Adafruit_AS5600.h>
#include <Servo.h>
#include "HX711.h"
#include <IRremote.h>

const int IR_RECEIVER_PIN = 4;
#define IR_BUTTON_0 0xE916FF00
#define IR_BUTTON_1 0xF30CFF00
#define IR_BUTTON_2 0xE718FF00
#define IR_BUTTON_UP 0xF609FF00
#define IR_BUTTON_DOWN 0xF807FF00

int systemMode = 0;

const int EMG_PIN = A0;
const int EMG_SMOOTH_SAMPLES = 10;
const int EMG_THRESHOLD_MIN = 50;
const int EMG_THRESHOLD_MAX = 500;
const int EMG_THRESHOLD_STEP = 10;
int EMG_THRESHOLD = 150;

float emgReadings[EMG_SMOOTH_SAMPLES];
int emgIndex = 0;
long emgTotal = 0;
int emgAverage = 0;

Servo myServo;
const int SERVO_PIN = 11;
int servoCommand = 1500;
bool servoAttached = false;

Adafruit_BNO055 bno = Adafruit_BNO055(55);
sensors_event_t imuEvent;

Adafruit_AS5600 as5600;
const int ENCODER_OFFSET = 1750;

#define HX711_DOUT 3
#define HX711_CLK 2
HX711 scale;

const int LOAD_SMOOTH_SAMPLES = 10;
const float GRAMS_PER_COUNT = 0.01134;
float loadReadings[LOAD_SMOOTH_SAMPLES];
int loadIndex = 0;
float loadTotal = 0;
float loadAverage = 0;

float getSmoothedEMG() {
  int rawEMG = analogRead(EMG_PIN);
  emgTotal -= emgReadings[emgIndex];
  emgReadings[emgIndex] = rawEMG;
  emgTotal += emgReadings[emgIndex];
  emgIndex = (emgIndex + 1) % EMG_SMOOTH_SAMPLES;
  emgAverage = emgTotal / EMG_SMOOTH_SAMPLES;
  return emgAverage;
}

uint16_t getScaledAngle() {
  uint16_t rawAngle = as5600.getRawAngle();
  return (rawAngle + 4096 - ENCODER_OFFSET) % 4096;
}

bool isMagnetOK() {
  return as5600.isMagnetDetected();
}

void updateServo(float emgValue, bool magnetOK, uint16_t encoderAngle) {
  int newCommand = 1500;
  if (magnetOK && encoderAngle > 2000)
    newCommand = 1500;
  else if (emgValue > EMG_THRESHOLD && encoderAngle > 1000)
    newCommand = 1750;

  if (!servoAttached) {
    myServo.attach(SERVO_PIN);
    servoAttached = true;
  }
  myServo.writeMicroseconds(newCommand);
  servoCommand = newCommand;
}

void detachServoIfAttached() {
  if (servoAttached) {
    myServo.detach();
    servoAttached = false;
  }
}

float getSmoothedLoadCellGrams() {
  if (!scale.is_ready()) return loadAverage;
  float grams = scale.read() * GRAMS_PER_COUNT;
  loadTotal -= loadReadings[loadIndex];
  loadReadings[loadIndex] = grams;
  loadTotal += loadReadings[loadIndex];
  loadIndex = (loadIndex + 1) % LOAD_SMOOTH_SAMPLES;
  loadAverage = loadTotal / LOAD_SMOOTH_SAMPLES;
  return loadAverage;
}

void setup() {
  Serial.begin(115200);
  delay(500);

  IrReceiver.begin(IR_RECEIVER_PIN, ENABLE_LED_FEEDBACK);

  myServo.attach(SERVO_PIN);
  servoAttached = true;
  myServo.writeMicroseconds(1500);

  for (int i = 0; i < EMG_SMOOTH_SAMPLES; i++) emgReadings[i] = 0;
  for (int i = 0; i < LOAD_SMOOTH_SAMPLES; i++) loadReadings[i] = 0;

  if (!bno.begin()) {
    Serial.println("BNO055 not detected.");
    while (1)
      ;
  }
  delay(1000);
  bno.setExtCrystalUse(true);

  if (!as5600.begin()) {
    Serial.println("AS5600 not detected.");
    while (1)
      ;
  }
  as5600.enableWatchdog(false);
  as5600.setPowerMode(AS5600_POWER_MODE_NOM);
  as5600.setHysteresis(AS5600_HYSTERESIS_OFF);
  as5600.setOutputStage(AS5600_OUTPUT_STAGE_ANALOG_FULL);
  as5600.setSlowFilter(AS5600_SLOW_FILTER_16X);
  as5600.setFastFilterThresh(AS5600_FAST_FILTER_THRESH_SLOW_ONLY);
  as5600.setZPosition(0);
  as5600.setMPosition(4095);
  as5600.setMaxAngle(4095);

  scale.begin(HX711_DOUT, HX711_CLK);
  if (!scale.is_ready()) {
    Serial.println("HX711 not responding.");
  } else {
    scale.set_scale();
    scale.tare();
  }

  Serial.println("System initialized.");
  Serial.print("Mode: ");
  Serial.println(systemMode);
  Serial.print("EMG Threshold: ");
  Serial.println(EMG_THRESHOLD);
}

void loop() {
  if (IrReceiver.decode()) {
    uint32_t code = IrReceiver.decodedIRData.decodedRawData & 0xFFFFFFFF;

    if (code == IR_BUTTON_0) {
      systemMode = 0;
      Serial.println("Mode: 0 (OFF)");
    } else if (code == IR_BUTTON_1) {
      systemMode = 1;
      Serial.println("Mode: 1 (Sensors Only)");
    } else if (code == IR_BUTTON_2) {
      systemMode = 2;
      Serial.println("Mode: 2 (Sensors + Servo)");
    } else if (code == IR_BUTTON_UP) {
      EMG_THRESHOLD = min(EMG_THRESHOLD + EMG_THRESHOLD_STEP, EMG_THRESHOLD_MAX);
      Serial.print("EMG Threshold: ");
      Serial.println(EMG_THRESHOLD);
    } else if (code == IR_BUTTON_DOWN) {
      EMG_THRESHOLD = max(EMG_THRESHOLD - EMG_THRESHOLD_STEP, EMG_THRESHOLD_MIN);
      Serial.print("EMG Threshold: ");
      Serial.println(EMG_THRESHOLD);
    }

    IrReceiver.resume();
  }

  if (systemMode == 0) {
    detachServoIfAttached();
    delay(10);
    return;
  }

  float emgValue = getSmoothedEMG();
  bool magnetOK = isMagnetOK();
  uint16_t encoderAngle = magnetOK ? getScaledAngle() : 0;
  float grams = getSmoothedLoadCellGrams();

  bno.getEvent(&imuEvent);

  String out = "";
  out += "Raw EMG: " + String(analogRead(EMG_PIN));
  out += " | Smoothed: " + String(emgValue, 2);
  out += " | Threshold: " + String(EMG_THRESHOLD);
  out += " | Encoder: " + String(magnetOK ? encoderAngle : -1);
  out += " | IMU: " + String(imuEvent.orientation.x, 2) + "," + String(imuEvent.orientation.y, 2) + "," + String(imuEvent.orientation.z, 2);
  out += " | Load: " + String(grams, 2) + "g " + String(grams / 1000.0, 3) + "kg " + String((grams / 1000.0) * 9.80665, 2) + "N";

  if (systemMode == 1) {
    detachServoIfAttached();
  } else if (systemMode == 2) {
    updateServo(emgValue, magnetOK, encoderAngle);
    out += " | Servo: " + String(servoCommand);
  }

  Serial.println(out);
  delay(10);
}