# AI-Based Machine Health Monitoring and Anomaly Detection Using Machine Learning
### Domain: **Industrial IoT & Predictive Maintenance**
**Specification Alignment:** Project Guide `B09 – FAIR-AI-09` | Predictive Maintenance & Industrial AI

---

## 1. Executive Project Overview

The **AI Machine Health Monitor** is an industrial IoT predictive maintenance platform. It monitors rotating machinery (such as motors, turbines, and industrial equipment), inspects sensor trends, detects anomalous physical states using unsupervised machine learning (**Isolation Forest**), and surfaces actionable alerts through a modern web dashboard.

The system seamlessly unifies two operating workflows:
1. **Dataset Analysis Mode:** Ingests factory CSV logs and standard public benchmarks (such as **NASA C-MAPSS** and pre-packaged **ESP32 DevKit prototype baselines**), performs automated schema diagnostics and missing-value imputation, fits reproducible Isolation Forest models, and exports engineering audits.
2. **Live Hardware Telemetry Mode:** Ingests streaming telemetry packets over Wi-Fi from an **ESP32 DevKit V1** microcontroller connected to an **MPU6500 IMU** (vibration & motion) and a **DS18B20 waterproof temperature probe** via a high-performance **FastAPI REST Gateway** (`/api/readings`) backed by persistent SQLite storage.

---

## 2. System Architecture

```
[Physical Prototype / Machine Setup]
  ├── ESP32 DevKit V1 Microcontroller
  ├── MPU6500 IMU (I2C: GPIO 21 / 22) ────────── Tri-axial Accel (g), Gyro (dps), IMU Die Temp (°C)
  ├── DS18B20 Temp Probe (1-Wire: GPIO 4) ───── Machine External Surface Temperature (°C)
  └── 3–6V DC Demonstration Motor ───────────── Powered via External Motor Driver (L298N / L9110S)
        │
        │ Wi-Fi HTTP POST (JSON Telemetry: 1 reading / sec)
        ▼
[FastAPI Telemetry Gateway (Port 8000)]
  ├── Pydantic Input Validation & Range Checking
  ├── Device Heartbeat & Link Latency Tracking (Online / Stale / Offline)
  └── Automated Anomaly & Threshold Alert Triggering
        │
        ▼
[SQLite Persistence Engine (data/machine_health.db)]
  ├── sensor_readings (WAL mode, indexed by timestamp & device)
  ├── alerts (Active, Acknowledged, Resolved audit lifecycle)
  └── model_registry (Trained Isolation Forest model artifacts)
        │
        ▼
[Streamlit Industrial Dashboard (Port 8501)]
  ├── 1. Overview Dashboard (KPI cards, health status pills, dynamic trend graphs)
  ├── 2. Live Machine Monitoring (Real-time telemetry stream, simulated packet injector)
  ├── 3. AI Anomaly Detection (Isolation Forest pipeline, feature selection, evaluation)
  ├── 4. Sensor Analytics (Rolling window smoothers, correlation heatmaps, boxplots)
  ├── 5. Dataset Upload & Analysis (CSV schema inspection, column mapper, data sanitization)
  ├── 6. Anomaly & Alert History (Operator acknowledgement workflow, audit log)
  ├── 7. Reports & Export (Downloadable Markdown reports, CSV data exports)
  ├── 8. Model Information (Registered models, algorithmic principles, limitations)
  ├── 9. Hardware & Connection Status (Circuit diagrams, pinouts, electrical safety)
  └── 10. Project Information / About (B09 project checklist & organizational profile)
```

---

## 3. Technology Stack

- **Language:** Python 3.10+ (Tested on Python 3.13.5)
- **Web Dashboard:** Streamlit
- **REST Telemetry Gateway:** FastAPI, Uvicorn, Pydantic
- **Machine Learning:** Scikit-learn (Isolation Forest)
- **Data Engineering:** Pandas, NumPy
- **Interactive Visualizations:** Plotly Express & Graph Objects
- **Database:** SQLite3 (WAL concurrency mode)
- **Embedded Hardware:** ESP32 DevKit V1, MPU6500-DMP, OneWire, DallasTemperature
- **Test Suite:** Pytest

---

## 4. Beginner-Friendly Step-by-Step Setup Guide (Windows)

Follow these exact steps to run the complete system locally on Windows.

### Step 1: Open the Project in VS Code
1. Open **Visual Studio Code**.
2. Click **File -> Open Folder...** and select the project folder:  
   `C:\Users\Pratik\Downloads\MachineHealth`
3. Open a PowerShell terminal by pressing `` Ctrl + ` ``.

### Step 2: Create a Virtual Environment
In your PowerShell terminal, execute:
```powershell
python -m venv .venv
```

### Step 3: Activate the Virtual Environment
Activate the environment:
```powershell
.\.venv\Scripts\Activate.ps1
```

> **Troubleshooting PowerShell Script Execution Error:**  
> If Windows displays an error stating *"running scripts is disabled on this system"*, run the following command once to permit local script execution, then re-run the activation command:
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> .\.venv\Scripts\Activate.ps1
> ```

### Step 4: Install Project Dependencies
Install all required packages from `requirements.txt`:
```powershell
pip install -r requirements.txt
```

### Step 5: Start the Telemetry API Gateway
Open a terminal in the activated virtual environment and start the FastAPI telemetry receiver on port `8000`:
```powershell
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```
You should see:
```text
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```
Verify the API is active by opening `http://localhost:8000` or `http://localhost:8000/docs` in your web browser.

### Step 6: Start the Streamlit Dashboard
Open a **second PowerShell terminal** in VS Code, activate the virtual environment, and launch Streamlit:
```powershell
.\.venv\Scripts\Activate.ps1
streamlit run app.py
```
Streamlit will launch automatically and open your browser at:
`http://localhost:8501`

---

## 5. Using the Application (Walkthrough)

### 1. Overview Dashboard
- Displays immediate status pills (**NORMAL**, **WARNING**, **CRITICAL**, **SENSOR DISCONNECTED**).
- Shows live readings for external temperature (DS18B20), IMU temperature (MPU6500), and vibration indicator magnitude.
- Plots multi-variable trend curves for thermal and 6-DOF motion.
- Features an **Indicative Health Score (0–100)** with transparent deduction explanations.

### 2. Live Machine Monitoring
- Streams real-time packets from the ESP32.
- Displays last packet latency and microcontroller diagnostic codes.
- **Hardware Simulation Feature:** If physical hardware is disconnected or Wi-Fi is temporarily unavailable, click **"Simulate 1 Hardware Packet"** to inject a sample telemetry packet into the live gateway and observe the dynamic response.

### 3. AI Anomaly Detection
- Select between pre-packaged datasets (**ESP32 Hardware Run Baseline** or **NASA C-MAPSS Turbofan**) or your own uploaded CSV.
- Pick numeric sensor features (timestamps and identifiers are excluded automatically).
- Configure the **Contamination factor** (default `0.05` / 5%) and **Estimator tree count**.
- Click **"Fit Isolation Forest & Detect Anomalies"** to generate 2D feature scatter plots, timeline highlights, and score distributions.
- Click **"Deploy as Active Live Telemetry Model"** to bind the model to the live gateway for real-time ESP32 packet evaluation!

### 4. Dataset Upload & Sanitization
- Upload arbitrary machine sensor CSV files.
- Inspect row/column counts, missing cell quantities, and candidate features.
- Map columns to standard monitoring variables or preserve custom names.
- Execute automated cleaning (median imputation, deduplication) and download the sanitized CSV.

### 5. Anomaly & Alert History
- Review persistent records of all triggered threshold and ML anomaly events.
- Filter by severity (**CRITICAL**, **WARNING**, **INFO**) or status (**ACTIVE**, **ACKNOWLEDGED**, **RESOLVED**).
- Update alert statuses with operator maintenance notes.

### 6. Reports & Export
- Download CSV logs for sensor history, alerts audit trails, and scored anomaly datasets.
- Generate and download a comprehensive **Executive Analytical Summary Report (.md)** with descriptive statistics and engineering disclaimers.

---

## 6. Hardware & ESP32 Firmware Setup

### Pinout Table
| Sensor / Component | Pin Name | ESP32 DevKit V1 Pin | Electrical Notes |
| :--- | :--- | :--- | :--- |
| **MPU6500 IMU** | SDA | **GPIO 21** | I²C Serial Data |
| **MPU6500 IMU** | SCL | **GPIO 22** | I²C Serial Clock |
| **DS18B20 Probe** | DATA | **GPIO 4** | **Requires 4.7 kΩ pull-up resistor to 3.3V** |
| **Power Supply** | 3.3V / GND | **3V3 & GND** | Sensors powered from ESP32 3.3V rail |
| **DC Motor (3–6V)** | Motor Driver | **Driver Inputs** | **NEVER CONNECT MOTOR DIRECTLY TO GPIO!** |

### Flashing Firmware:
1. Open **Arduino IDE**.
2. Install libraries via Library Manager:
   - `MPU6500-DMP` (by xreef)
   - `OneWire` (by Paul Stoffregen)
   - `DallasTemperature` (by Miles Burton)
3. Open `firmware/sensor_test/sensor_test.ino` to verify sensors locally over USB Serial (115200 baud).
4. Open `firmware/esp32_wifi_monitor/esp32_wifi_monitor.ino`:
   - Enter your 2.4 GHz Wi-Fi SSID and Password.
   - Find your PC's IP address on Windows by typing `ipconfig` in PowerShell (e.g. `192.168.1.50`).
   - Set: `const char* SERVER_URL = "http://192.168.1.50:8000/api/readings";`
   - Flash the sketch to the ESP32!

> **Why `localhost` Does NOT Work on ESP32:**  
> The ESP32 is a separate physical device on your local Wi-Fi router. If you specify `localhost`, the ESP32 attempts to send HTTP requests to itself rather than your computer. Always use your computer's LAN IPv4 address (e.g. `192.168.1.X`).

---

## 7. Running the Automated Test Suite

The test suite validates data loading, column mapping, data cleaning, Isolation Forest training, model serialization, API routes, SQLite persistence, and edge conditions.

Run the test suite using pytest:
```powershell
pytest -v
```
All **23 unit and integration tests** execute and pass.

---

## 8. Engineering Limitations & Disclaimers

1. **Anomaly Detection vs. Failure Date Prediction:**  
   The primary machine learning pipeline uses unsupervised **Isolation Forest** to identify observations that statistically deviate from established nominal baselines. The system does not claim to predict the exact failure date or mechanical Remaining Useful Life (RUL) without a separate, calibrated degradation model.
2. **Causal Attribution:**  
   The model flags *unusual operating states*; it does not inherently determine physical root cause (e.g. bearing raceway pitting vs. stator overheating). Root-cause analysis requires physical inspections and acoustic spectrum analyses.
3. **Demonstration Thresholds:**  
   Default warning and critical thresholds in `.env` are configured for demonstration purposes and do not represent certified industrial safety standards (such as ISO 10816 vibration standards).

---

## 9. Project Information & Version

**AI Machine Health Monitor**  
*Predictive Maintenance & Industrial IoT Telemetry System*  
Version: **1.0.0**
