
#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <MPU6500-DMP.h>
#include <math.h>

// =============== WIFI AND API CONFIGURATION ===============
const char* WIFI_SSID     = "IOT";
const char* WIFI_PASSWORD = "00000000";

const char* SERVER_URL =
  "http://192.168.43.98:8000/api/readings";

const char* DEVICE_ID = "esp32-machine-01";
const char* DEVICE_TOKEN = "demo-secret-token-change-in-production";

const unsigned long TELEMETRY_INTERVAL_MS = 1000;

// ======================= PIN CONFIGURATION ==================
#define DS18B20_PIN 4
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22

// L298N: Motor A
// ENA jumper must remain installed for full enabled drive.
#define MOTOR_IN1 26
#define MOTOR_IN2 27

// ======================== OBJECTS ===========================
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);
MPU6500_DMP imu;

bool imu_ready = false;
bool ds18b20_ready = false;

unsigned long lastTransmit = 0;
unsigned long lastImuRetry = 0;
unsigned long lastWiFiRetry = 0;

// Motor demonstration sequence:
// Forward 2 sec -> Stop 2 sec -> Reverse 2 sec -> Stop 2 sec.
enum MotorState {
  MOTOR_FORWARD,
  MOTOR_STOP_1,
  MOTOR_REVERSE,
  MOTOR_STOP_2
};

MotorState motorState = MOTOR_STOP_1;
unsigned long motorStateStart = 0;
const unsigned long MOTOR_STEP_MS = 2000;

// ======================== MOTOR CONTROL =====================
void stopMotor() {
  digitalWrite(MOTOR_IN1, LOW);
  digitalWrite(MOTOR_IN2, LOW);
}

void updateMotor() {
  unsigned long now = millis();

  if (now - motorStateStart < MOTOR_STEP_MS) return;

  motorStateStart = now;

  switch (motorState) {
    case MOTOR_STOP_1:
      Serial.println("[Motor] Forward");
      digitalWrite(MOTOR_IN1, HIGH);
      digitalWrite(MOTOR_IN2, LOW);
      motorState = MOTOR_FORWARD;
      break;

    case MOTOR_FORWARD:
      Serial.println("[Motor] Stop");
      stopMotor();
      motorState = MOTOR_STOP_2;
      break;

    case MOTOR_STOP_2:
      Serial.println("[Motor] Reverse");
      digitalWrite(MOTOR_IN1, LOW);
      digitalWrite(MOTOR_IN2, HIGH);
      motorState = MOTOR_REVERSE;
      break;

    case MOTOR_REVERSE:
      Serial.println("[Motor] Stop");
      stopMotor();
      motorState = MOTOR_STOP_1;
      break;
  }
}

// ======================== WIFI ==============================
void connectWiFi() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("[Wi-Fi] Connecting to ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  unsigned long start = millis();

  while (WiFi.status() != WL_CONNECTED &&
         millis() - start < 10000) {
    delay(250);
    Serial.print(".");
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[Wi-Fi] Connected");
    Serial.print("[Wi-Fi] ESP32 IP: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("\n[Wi-Fi] Not connected; will retry");
  }
}

// ======================== IMU INITIALIZATION ================
bool initializeIMU() {
  Serial.println("[IMU] Checking I2C address 0x68...");

  Wire.beginTransmission(0x68);
  byte error = Wire.endTransmission();

  if (error != 0) {
    Serial.println("[IMU] No response at 0x68");
    return false;
  }

  Serial.println("[IMU] Address detected; initializing library");

  if (imu.begin() == INV_SUCCESS) {
    imu.setAccelFSR(2);
    imu.setLPF(5);
    imu.setSampleRate(10);

    Serial.println("[IMU] Initialized successfully");
    return true;
  }

  Serial.println("[IMU] Library initialization failed");
  return false;
}

// ======================== SETUP =============================
void setup() {
  Serial.begin(115200);
  delay(1200);

  Serial.println("\nESP32 Machine Health Monitor");

  // Put motor outputs into a safe state immediately.
  pinMode(MOTOR_IN1, OUTPUT);
  pinMode(MOTOR_IN2, OUTPUT);
  stopMotor();

  // Initialize I2C once, using the existing sensor pins.
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);
  Wire.setClock(100000);
  delay(300);

  // Initialize DS18B20.
  ds18b20.begin();
  ds18b20.setResolution(10);

  ds18b20_ready = ds18b20.getDeviceCount() > 0;

  Serial.println(ds18b20_ready
    ? "[DS18B20] Detected"
    : "[DS18B20] Not detected; check wiring and pull-up");

  // Initialize IMU, with a few startup attempts.
  for (int attempt = 1; attempt <= 3 && !imu_ready; attempt++) {
    Serial.printf("[IMU] Initialization attempt %d/3\n", attempt);
    imu_ready = initializeIMU();

    if (!imu_ready) delay(500);
  }

  lastImuRetry = millis();

  // Motor starts stopped; sequence begins after startup.
  motorState = MOTOR_STOP_1;
  motorStateStart = millis();

  connectWiFi();
}

// ======================== MAIN LOOP =========================
void loop() {
  unsigned long now = millis();

  // Retry Wi-Fi without repeatedly blocking the loop.
  if (WiFi.status() != WL_CONNECTED &&
      now - lastWiFiRetry >= 5000) {
    lastWiFiRetry = now;
    connectWiFi();
  }

  // Retry IMU initialization periodically if unavailable.
  if (!imu_ready && now - lastImuRetry >= 5000) {
    lastImuRetry = now;
    imu_ready = initializeIMU();
  }

  // Run the demonstration motor cycle.
  updateMotor();

  if (now - lastTransmit < TELEMETRY_INTERVAL_MS) {
    delay(2);
    return;
  }

  lastTransmit = now;

  float ax = 0, ay = 0, az = 0;
  float gx = 0, gy = 0, gz = 0;
  float imuTemp = 0;
  float externalTemp = -999.0;
  float vibration = 0;

  bool imuReadingValid = false;
  String status = "OK";

  // Read IMU only if initialization succeeded.
  if (imu_ready) {
    imu.update(UPDATE_ACCEL | UPDATE_GYRO | UPDATE_TEMP);

    ax = imu.calcAccel(imu.ax);
    ay = imu.calcAccel(imu.ay);
    az = imu.calcAccel(imu.az);

    gx = imu.calcGyro(imu.gx);
    gy = imu.calcGyro(imu.gy);
    gz = imu.calcGyro(imu.gz);

    imuTemp = imu.calcTempCelsius();

    imuReadingValid =
      isfinite(ax) && isfinite(ay) && isfinite(az) &&
      isfinite(gx) && isfinite(gy) && isfinite(gz) &&
      isfinite(imuTemp);

    if (imuReadingValid) {
      float dynamicAz = az - 1.0f;
      vibration = sqrtf(
        ax * ax + ay * ay + dynamicAz * dynamicAz
      );
    } else {
      imu_ready = false;
      status = "IMU_UNAVAILABLE";
    }
  } else {
    status = "IMU_UNAVAILABLE";
  }

  // Read external temperature.
  if (ds18b20_ready) {
    ds18b20.requestTemperatures();
    float t = ds18b20.getTempCByIndex(0);

    if (t != DEVICE_DISCONNECTED_C &&
        isfinite(t) && t >= -55.0f && t <= 125.0f) {
      externalTemp = t;
    } else {
      status = status == "OK"
        ? "DS18B20_FAULT"
        : status + "+DS18B20_FAULT";
    }
  } else {
    status = status == "OK"
      ? "DS18B20_UNAVAILABLE"
      : status + "+DS18B20_UNAVAILABLE";
  }

  // Use null for missing sensor readings instead of fake zeros.
  char axStr[20], ayStr[20], azStr[20];
  char gxStr[20], gyStr[20], gzStr[20];
  char imuTempStr[20], extTempStr[20], vibrationStr[20];

  if (imuReadingValid) {
    snprintf(axStr, sizeof(axStr), "%.4f", ax);
    snprintf(ayStr, sizeof(ayStr), "%.4f", ay);
    snprintf(azStr, sizeof(azStr), "%.4f", az);
    snprintf(gxStr, sizeof(gxStr), "%.2f", gx);
    snprintf(gyStr, sizeof(gyStr), "%.2f", gy);
    snprintf(gzStr, sizeof(gzStr), "%.2f", gz);
    snprintf(imuTempStr, sizeof(imuTempStr), "%.2f", imuTemp);
    snprintf(vibrationStr, sizeof(vibrationStr), "%.4f", vibration);
  } else {
    strcpy(axStr, "null");
    strcpy(ayStr, "null");
    strcpy(azStr, "null");
    strcpy(gxStr, "null");
    strcpy(gyStr, "null");
    strcpy(gzStr, "null");
    strcpy(imuTempStr, "null");
    strcpy(vibrationStr, "null");
  }

  if (externalTemp == -999.0f) {
    strcpy(extTempStr, "null");
  } else {
    snprintf(extTempStr, sizeof(extTempStr), "%.2f", externalTemp);
  }

  char payload[640];

  snprintf(payload, sizeof(payload),
    "{"
    "\"device_id\":\"%s\","
    "\"timestamp_ms\":%lu,"
    "\"ax_g\":%s,"
    "\"ay_g\":%s,"
    "\"az_g\":%s,"
    "\"gyro_x_dps\":%s,"
    "\"gyro_y_dps\":%s,"
    "\"gyro_z_dps\":%s,"
    "\"imu_temp_c\":%s,"
    "\"external_temp_c\":%s,"
    "\"vibration_indicator_g\":%s,"
    "\"status\":\"%s\""
    "}",
    DEVICE_ID,
    millis(),
    axStr, ayStr, azStr,
    gxStr, gyStr, gzStr,
    imuTempStr, extTempStr, vibrationStr,
    status.c_str()
  );

  Serial.print("[Telemetry] ");
  Serial.println(payload);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(SERVER_URL);
    http.addHeader("Content-Type", "application/json");
    http.addHeader("X-Device-Token", DEVICE_TOKEN);
    http.setTimeout(2500);

    int response = http.POST(payload);

    if (response > 0) {
      Serial.printf("[HTTP] Response: %d\n", response);
    } else {
      Serial.printf("[HTTP] Error: %s\n",
        http.errorToString(response).c_str());
    }

    http.end();
  }
}
