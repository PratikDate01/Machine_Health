# ESP32 Hardware Wiring & Firmware Guide
## AI Machine Health Monitor

This document details the hardware connections, pinout, safety precautions, and firmware flashing steps for the machine health monitoring prototype.

---

### 1. Hardware Bill of Materials (BOM)

| Component | Function | Operating Voltage |
| :--- | :--- | :--- |
| **ESP32 DevKit V1** | Microcontroller with Wi-Fi & I2C | 3.3V / 5V USB |
| **MPU6500 IMU Module** | 6-DOF Accelerometer, Gyroscope & Die Temp | 3.3V |
| **DS18B20 Probe** | Waterproof digital machine temperature sensor | 3.0V – 5.5V (3.3V used) |
| **4.7 kΩ Resistor** | Pull-up resistor for DS18B20 1-Wire bus | Passive |
| **3–6V DC Demonstration Motor** | Simulates operational rotating machine load | External DC Power |
| **Motor Driver (e.g., L298N / L9110S)** | Intermediary motor driver circuit | Motor supply voltage |
| **Breadboard & Jumper Wires** | Prototyping interconnections | N/A |

---

### 2. Sensor Wiring Pinout

#### A. MPU6500 IMU (I²C Bus)
| MPU6500 Pin | ESP32 GPIO | Description |
| :--- | :--- | :--- |
| **VCC** | **3V3** | 3.3V Power from ESP32 |
| **GND** | **GND** | Common Ground |
| **SDA** | **GPIO 21** | I²C Data Line |
| **SCL** | **GPIO 22** | I²C Clock Line |

#### B. DS18B20 Temperature Probe (1-Wire Bus)
| DS18B20 Wire Color | Function | ESP32 Connection | Notes |
| :--- | :--- | :--- | :--- |
| **Red** | VCC | **3V3** | Power supply |
| **Black / Blue** | GND | **GND** | Ground |
| **Yellow / White** | DATA | **GPIO 4** | **Requires 4.7 kΩ pull-up to 3.3V** |

> **Critical Note on DS18B20 Pull-up Resistor:**  
> The 4.7 kΩ resistor must bridge **GPIO 4 (DATA)** and **3.3V (VCC)**. Without this pull-up resistor, the 1-Wire bus floats, causing the sensor count to show 0 or read -127°C / 85°C error codes.

---

### 3. Motor Driver & Safety Rules

> **SAFETY MANDATE:**  
> **NEVER CONNECT A DC MOTOR DIRECTLY TO AN ESP32 GPIO PIN.**  
> An ESP32 GPIO can supply a maximum of 12–40 mA, whereas even a small 3–6V DC motor draws 300 mA to >1500 mA stall current. Connecting a motor directly to GPIO will permanently destroy the microcontroller due to overcurrent and inductive flyback voltage spikes.

#### Motor Driver Integration (e.g. L9110S or L298N):
1. **Power:** The motor MUST be powered from an external battery pack or DC power supply (3–6V), with its ground line tied to ESP32 **GND** (Common Ground).
2. **Control Inputs:** Connect the motor driver logic input pins (e.g. INA / INB) to low-current ESP32 PWM pins (e.g. GPIO 18, 19).
3. **Automated Shutdown Notice:** In accordance with safety engineering guidelines, this monitoring system performs non-invasive telemetry analysis. It does NOT automatically trigger mechanical emergency shutoffs without operator approval and safety interlocks.

---

### 4. Technical Distinctions in Telemetry

1. **IMU Internal Temperature vs. External DS18B20 Temperature:**
   - `imu_temp_c`: The internal silicon die temperature of the MPU6500 sensor. It measures chip self-heating.
   - `external_temp_c`: The physical machine casing surface temperature measured by the stainless-steel DS18B20 probe.
   - These are separate metrics and are tracked independently.

2. **Vibration Indicator:**
   - `vibration_indicator_g`: Calculated as the Euclidean norm deviation from the 1g Earth gravity baseline ($\sqrt{a_x^2 + a_y^2 + (a_z - 1.0)^2}$).
   - This represents a relative dynamic motion indicator. It is **NOT** a calibrated ISO 10816 root-mean-square (RMS) velocity measurement.

---

### 5. Flashing the Firmware

#### Step 1: Install Arduino Libraries
In Arduino IDE, open **Tools -> Manage Libraries** and install:
1. `MPU6500-DMP` (by xreef)
2. `OneWire` (by Paul Stoffregen)
3. `DallasTemperature` (by Miles Burton)

#### Step 2: Verification with Sensor Diagnostic Sketch
1. Open [`firmware/sensor_test/sensor_test.ino`](sensor_test/sensor_test.ino).
2. Select Board: **ESP32 Dev Module** and the correct COM Port.
3. Upload and open the Serial Monitor at **115200 baud**.
4. Verify that both sensors initialize and output comma-separated telemetry rows.

#### Step 3: Wi-Fi Telemetry Transmitter Sketch
1. Open [`firmware/esp32_wifi_monitor/esp32_wifi_monitor.ino`](esp32_wifi_monitor/esp32_wifi_monitor.ino).
2. Configure your Wi-Fi credentials:
   ```cpp
   const char* WIFI_SSID     = "MyHomeWiFi";
   const char* WIFI_PASSWORD = "MyPassword123";
   ```
3. Find your PC's local LAN IP address on Windows:
   - Open PowerShell and run: `ipconfig`
   - Look for the `IPv4 Address` under your active Wi-Fi or Ethernet adapter (e.g., `192.168.1.45`).
4. Set the server URL in the sketch:
   ```cpp
   const char* SERVER_URL    = "http://192.168.1.45:8000/api/readings";
   ```
   *(Notice: Never use `http://localhost:8000` because from the ESP32's perspective, localhost is the ESP32 itself!)*
5. Upload the sketch to the ESP32.
6. The ESP32 will connect to Wi-Fi and stream JSON sensor readings directly into the Python backend!
