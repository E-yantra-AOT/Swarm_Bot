/**
 * @file sketch_pi_motor_bridge.ino
 * @brief Phase 1 — Raspberry Pi → Arduino Motor Command Bridge + OLED Display
 *
 * Purpose:
 *   Receives ASCII motor commands from the Raspberry Pi over USB serial
 *   and drives the AlphaBot2-Ar motors (TB6612FNG via proper dual-direction pins).
 *   Also drives the onboard 0.96" SSD1306 OLED (128x64, I2C) to show swarm status.
 *
 * Command Protocol (Pi → Arduino, 115200 baud, newline terminated):
 *   M,<leftSpeed>,<leftDir>,<rightSpeed>,<rightDir>   — Motor command
 *   D,<line1>,<line2>                                  — OLED display (2 lines)
 *
 *   leftSpeed / rightSpeed : 0–255
 *   leftDir  / rightDir   : F (forward) | B (backward)
 *
 * Hardware (Verified via AlphaBot2-Ar jumper matrix):
 *   Motor A (Left)  — PWM: D6, AIN1: A1, AIN2: A0
 *   Motor B (Right) — PWM: D5, BIN1: A2, BIN2: A3
 *   OLED Display    — I2C: SDA (A4), SCL (A5), Address 0x3C
 */

#include <Arduino.h>
#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ============================================================================
// Pin Definitions (Verified from hardware photos)
// ============================================================================
#define PWMA 6
#define AIN1 A1
#define AIN2 A0

#define PWMB 5
#define BIN1 A2
#define BIN2 A3

// ============================================================================
// OLED Display Config (AlphaBot2-Ar onboard SSD1306)
// ============================================================================
#define OLED_WIDTH    128
#define OLED_HEIGHT   64
#define OLED_ADDRESS  0x3C

Adafruit_SSD1306 oled(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
bool oledReady = false;

// ============================================================================
// Safety Config
// ============================================================================
#define MAX_SPEED       200   // Hard cap — never go above this (0–255)
#define WATCHDOG_MS    2000   // Stop motors if no command received in 2 seconds
#define SERIAL_BAUD   115200

// ============================================================================
// State
// ============================================================================
unsigned long lastCmdTime = 0;
bool motorsRunning = false;
String inputBuffer = "";

// ============================================================================
// OLED Helpers
// ============================================================================

void oledShow(const String& line1, const String& line2) {
  if (!oledReady) return;
  oled.clearDisplay();
  oled.setTextSize(2);
  oled.setTextColor(SSD1306_WHITE);
  oled.setCursor(0, 8);
  oled.println(line1);
  oled.setCursor(0, 36);
  oled.println(line2);
  oled.display();
}

// ============================================================================
// Motor Helpers
// ============================================================================

void setMotor(int pwmPin, int in1Pin, int in2Pin, int speed, char dir) {
  speed = constrain(abs(speed), 0, MAX_SPEED);
  
  if (dir == 'F') {
    digitalWrite(in1Pin, HIGH);
    digitalWrite(in2Pin, LOW);
  } else {
    digitalWrite(in1Pin, LOW);
    digitalWrite(in2Pin, HIGH);
  }
  
  analogWrite(pwmPin, speed);
}

void stopMotors() {
  digitalWrite(AIN1, LOW);
  digitalWrite(AIN2, LOW);
  analogWrite(PWMA, 0);

  digitalWrite(BIN1, LOW);
  digitalWrite(BIN2, LOW);
  analogWrite(PWMB, 0);
  
  motorsRunning = false;
}

// ============================================================================
// Command Parser
// ============================================================================

void parseCommand(const String& cmd) {
  if (cmd.length() < 2) {
    Serial.println("ERR:too_short");
    return;
  }

  char type = cmd.charAt(0);

  // ── Display command: D,<line1>,<line2> ──
  if (type == 'D') {
    int c1 = cmd.indexOf(',', 0);
    int c2 = cmd.indexOf(',', c1 + 1);
    if (c1 < 0 || c2 < 0) {
      Serial.println("ERR:display_missing_fields");
      return;
    }
    String line1 = cmd.substring(c1 + 1, c2);
    String line2 = cmd.substring(c2 + 1);
    oledShow(line1, line2);
    lastCmdTime = millis();
    Serial.println("OK");
    return;
  }

  // ── Motor command: M,<leftSpd>,<leftDir>,<rightSpd>,<rightDir> ──
  if (type != 'M') {
    Serial.println("ERR:unknown_command");
    return;
  }

  if (cmd.length() < 5) {
    Serial.println("ERR:motor_too_short");
    return;
  }

  // Split by comma
  int idx[5];
  idx[0] = cmd.indexOf(',', 0);
  idx[1] = cmd.indexOf(',', idx[0] + 1);
  idx[2] = cmd.indexOf(',', idx[1] + 1);
  idx[3] = cmd.indexOf(',', idx[2] + 1);

  if (idx[0] < 0 || idx[1] < 0 || idx[2] < 0 || idx[3] < 0) {
    Serial.println("ERR:malformed_missing_fields");
    return;
  }

  int leftSpeed   = cmd.substring(idx[0] + 1, idx[1]).toInt();
  char leftDir    = cmd.charAt(idx[1] + 1);
  int rightSpeed  = cmd.substring(idx[2] + 1, idx[3]).toInt();
  char rightDir   = cmd.charAt(idx[3] + 1);

  // Validate direction chars
  if ((leftDir != 'F' && leftDir != 'B') || (rightDir != 'F' && rightDir != 'B')) {
    Serial.println("ERR:invalid_direction_char");
    return;
  }

  // Apply (Assuming A is left and B is right)
  setMotor(PWMA, AIN1, AIN2, leftSpeed,  leftDir);
  setMotor(PWMB, BIN1, BIN2, rightSpeed, rightDir);

  motorsRunning = (leftSpeed > 0 || rightSpeed > 0);
  lastCmdTime   = millis();

  Serial.println("OK");
}

// ============================================================================
// Setup
// ============================================================================

void setup() {
  Serial.begin(SERIAL_BAUD);

  pinMode(PWMA, OUTPUT);
  pinMode(AIN1, OUTPUT);
  pinMode(AIN2, OUTPUT);
  
  pinMode(PWMB, OUTPUT);
  pinMode(BIN1, OUTPUT);
  pinMode(BIN2, OUTPUT);

  stopMotors();
  lastCmdTime = millis();

  // Initialise OLED (non-fatal if not present)
  Wire.begin();
  if (oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
    oledReady = true;
    oledShow("SWARM BOT", "Ready...");
  } else {
    Serial.println("WARN:oled_init_failed");
  }

  Serial.println("READY:swarm_motor_bridge_v3");
}

// ============================================================================
// Loop
// ============================================================================

void loop() {
  // -- Read serial input (non-blocking, newline terminated) --
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      inputBuffer.trim();
      if (inputBuffer.length() > 0) {
        parseCommand(inputBuffer);
      }
      inputBuffer = "";
    } else if (c != '\r') {
      inputBuffer += c;
    }
  }

  // -- Watchdog: stop if no command received within WATCHDOG_MS --
  if (motorsRunning && (millis() - lastCmdTime > WATCHDOG_MS)) {
    stopMotors();
    Serial.println("WATCHDOG:motors_stopped");
  }
}
