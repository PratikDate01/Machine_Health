/*******************************************************************************
 * AI Machine Health Monitor
 * Sensor Diagnostic & Standalone Verification Sketch
 *
 * Hardware:
 *   - ESP32 DevKit V1
 *   - MPU6500 IMU (I2C: SDA -> GPIO 21, SCL -> GPIO 22)
 *   - DS18B20 Temperature Sensor (DATA -> GPIO 4 with 4.7k ohm pull-up resistor)
 *
 * Libraries Required:
 *   - MPU6500-DMP (by xreef)
 *   - OneWire (by Paul Stoffregen)
 *   - DallasTemperature (by Miles Burton)
 *
 * Notice:
 *   - The vibration indicator here is a basic calculated Euclidean norm residual,
 *     NOT a calibrated industrial ISO 10816 vibration severity measurement.
 *   - IMU internal temperature is the sensor die temp; DS18B20 is machine external surface temp.
 *******************************************************************************/

#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <MPU6500-DMP.h>

// Pin Definitions
#define DS18B20_PIN 4
#define I2C_SDA_PIN 21
#define I2C_SCL_PIN 22

// Sensor Instances
OneWire oneWire(DS18B20_PIN);
DallasTemperature ds18b20(&oneWire);
MPU6500_DMP imu;

bool imu_ready = false;
bool ds18b20_ready = false;

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println("==================================================");
  Serial.println("AI Machine Health Monitor - Sensor Diagnostic Mode");
  Serial.println("==================================================");

  // Initialize I2C bus
  Wire.begin(I2C_SDA_PIN, I2C_SCL_PIN);

  // Initialize DS18B20
  ds18b20.begin();
  int deviceCount = ds18b20.getDeviceCount();
  Serial.print("DS18B20 Bus Scan: ");
  Serial.print(deviceCount);
  Serial.println(" sensor(s) detected.");
  if (deviceCount > 0) {
    ds18b20_ready = true;
  } else {
    Serial.println("[WARNING] No DS18B20 probe detected on GPIO 4. Check 4.7k pull-up resistor.");
  }

  // Initialize MPU6500
  Serial.println("Initializing MPU6500 IMU...");
  if (imu.begin() == INV_SUCCESS) {
    imu.setAccelFSR(2); // +/- 2g range
    imu.setLPF(5);      // 5Hz Low-Pass Filter
    imu.setSampleRate(10); // 10Hz sampling
    imu_ready = true;
    Serial.println("[SUCCESS] MPU6500 IMU initialized successfully.");
  } else {
    Serial.println("[ERROR] Unable to initialize MPU6500 on I2C (GPIO 21/22). Check wiring.");
  }

  Serial.println("\nBeginning diagnostic telemetry stream (CSV format):");
  Serial.println("time_ms,ax_g,ay_g,az_g,gyro_x_dps,gyro_y_dps,gyro_z_dps,imu_temp_c,external_temp_c,vibration_indicator_g,status");
}

void loop() {
  unsigned long now = millis();

  float ax = 0.0, ay = 0.0, az = 0.0;
  float gx = 0.0, gy = 0.0, gz = 0.0;
  float imu_temp = 0.0;
  float ext_temp = 0.0;
  float vibration_indicator = 0.0;
  String status_str = "OK";

  // 1. Read MPU6500 IMU
  if (imu_ready) {
    imu.update(UPDATE_ACCEL | UPDATE_GYRO | UPDATE_TEMP);
    ax = imu.calcAccel(imu.ax);
    ay = imu.calcAccel(imu.ay);
    az = imu.calcAccel(imu.az);
    gx = imu.calcGyro(imu.gx);
    gy = imu.calcGyro(imu.gy);
    gz = imu.calcGyro(imu.gz);
    imu_temp = imu.calcTempCelsius();

    // Basic vibration indicator: dynamic deviation magnitude from nominal 1g gravity vector
    // sqrt(ax^2 + ay^2 + (az - 1.0)^2)
    float dynamic_az = az - 1.0;
    vibration_indicator = sqrt((ax * ax) + (ay * ay) + (dynamic_az * dynamic_az));
  } else {
    status_str = "IMU_UNAVAILABLE";
  }

  // 2. Read DS18B20 External Temperature Probe
  if (ds18b20_ready) {
    ds18b20.requestTemperatures();
    float t = ds18b20.getTempCByIndex(0);
    if (t == DEVICE_DISCONNECTED_C || t < -55.0 || t > 125.0) {
      ext_temp = -999.0; // Error indicator
      status_str = (status_str == "OK") ? "DS18B20_DISCONNECTED" : status_str + "+DS18B20_DISCONNECTED";
    } else {
      ext_temp = t;
    }
  } else {
    ext_temp = -999.0;
    status_str = (status_str == "OK") ? "DS18B20_UNAVAILABLE" : status_str + "+DS18B20_UNAVAILABLE";
  }

  // Print CSV formatted row
  Serial.print(now);
  Serial.print(",");
  Serial.print(ax, 4);
  Serial.print(",");
  Serial.print(ay, 4);
  Serial.print(",");
  Serial.print(az, 4);
  Serial.print(",");
  Serial.print(gx, 2);
  Serial.print(",");
  Serial.print(gy, 2);
  Serial.print(",");
  Serial.print(gz, 2);
  Serial.print(",");
  Serial.print(imu_temp, 2);
  Serial.print(",");
  if (ext_temp == -999.0) {
    Serial.print("NaN");
  } else {
    Serial.print(ext_temp, 2);
  }
  Serial.print(",");
  Serial.print(vibration_indicator, 4);
  Serial.print(",");
  Serial.println(status_str);

  delay(1000); // 1-second interval
}
