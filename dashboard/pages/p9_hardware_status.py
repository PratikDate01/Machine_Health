"""
Hardware & Connection Status Page — AI Machine Health Monitor.
Displays microcontroller link diagnostics, detailed schematics, pinout tables, and troubleshooting steps.
"""

import streamlit as st
import pandas as pd
from src.live_monitor import live_monitor
from dashboard.components.cards import render_metric_card, render_header_banner, render_sensor_availability_strip, render_motor_status_card


def render():
    conn_status, secs_ago, conn_detail = live_monitor.get_connection_status("esp32-machine-01")
    latest = live_monitor.get_latest_reading()
    sensors_info = live_monitor.get_sensor_availability(latest)

    render_header_banner(
        page_title="Hardware Architecture & Link Diagnostics",
        page_description="Microcontroller bus pinouts, electrical interconnections, hardware heartbeat, and safe wiring guidelines.",
        status_label=conn_status
    )

    # 1. Connection Diagnostic Status
    st.markdown("<div class='section-header'>1. Microcontroller Node Heartbeat</div>", unsafe_allow_html=True)
    h1, h2, h3 = st.columns(3)

    with h1:
        render_metric_card(
            title="Link Status",
            value=conn_status,
            unit="",
            footer=conn_detail,
            status_color="#16A34A" if conn_status == "LIVE" else ("#D97706" if conn_status == "STALE" else "#64748B")
        )
    with h2:
        render_metric_card(
            title="Last Packet Latency",
            value=f"{secs_ago:.1f}" if secs_ago is not None else "N/A",
            unit="s ago",
            footer="Heartbeat timeout: 10s"
        )
    with h3:
        ip_addr = latest.get("ip_address", "Unknown") if latest else "N/A"
        render_metric_card(
            title="Client Transmitter IP",
            value=ip_addr,
            unit="",
            footer="ESP32 local network IP"
        )

    # 2. Independent Sensor Availability Strip
    st.markdown("<div class='section-header'>2. Independent Physical Sensor Health</div>", unsafe_allow_html=True)
    st.caption("A successful Wi-Fi connection does NOT imply all sensors are functional. Sensor states are evaluated independently below:")
    render_sensor_availability_strip(
        ds18b20_label=sensors_info["ds18b20"]["label"],
        imu_label=sensors_info["imu"]["label"],
        bus_status=sensors_info["bus_status"],
        ds18b20_ok=sensors_info["ds18b20"]["connected"],
        imu_ok=sensors_info["imu"]["connected"]
    )

    # 3. Motor Subsystem Information & Limitation Callout
    st.markdown("<div class='section-header'>3. Motor Drive & Mechanical Load</div>", unsafe_allow_html=True)
    vib_val = latest.get("vibration_indicator_g") if latest else None
    render_motor_status_card(is_live=(conn_status == "LIVE"), vibration_val=vib_val)

    # 4. Hardware Bill of Materials & Wiring Table
    st.markdown("<div class='section-header'>4. Hardware Pinout Specifications</div>", unsafe_allow_html=True)

    pinout_data = [
        {"Component": "MPU6500 IMU", "Interface": "I²C Bus", "Pin": "SDA", "ESP32 Connection": "GPIO 21", "Voltage": "3.3V", "Status": "I2C Address 0x68"},
        {"Component": "MPU6500 IMU", "Interface": "I²C Bus", "Pin": "SCL", "ESP32 Connection": "GPIO 22", "Voltage": "3.3V", "Status": "100 kHz I2C Clock"},
        {"Component": "DS18B20 Probe", "Interface": "1-Wire Bus", "Pin": "DATA", "ESP32 Connection": "GPIO 4", "Voltage": "3.3V", "Status": "Mandatory 4.7kΩ pull-up to 3.3V"},
        {"Component": "L298N Motor Driver", "Interface": "Logic Control", "Pin": "IN1", "ESP32 Connection": "GPIO 26", "Voltage": "3.3V Logic", "Status": "Direction Bit 1"},
        {"Component": "L298N Motor Driver", "Interface": "Logic Control", "Pin": "IN2", "ESP32 Connection": "GPIO 27", "Voltage": "3.3V Logic", "Status": "Direction Bit 2"},
        {"Component": "L298N Motor Driver", "Interface": "Hardware Enable", "Pin": "ENA", "ESP32 Connection": "Jumper to 5V", "Voltage": "5V", "Status": "Hardwired Enable (100% fixed speed, no PWM)"},
        {"Component": "DC Motor (3–6V)", "Interface": "Power Output", "Pin": "OUT1, OUT2", "ESP32 Connection": "Driver Outputs", "Voltage": "External VCC", "Status": "Inductive load; never direct to GPIO"},
        {"Component": "Common Ground", "Interface": "Power Bus", "Pin": "GND", "ESP32 Connection": "GND", "Voltage": "0V", "Status": "Shared common ground across ESP32, L298N, & PSU"}
    ]
    st.dataframe(pd.DataFrame(pinout_data), use_container_width=True, hide_index=True)

    # Visual ASCII Circuit Diagram
    st.markdown("""
    ```
    +-----------------------------------------------------------------------------------------+
    |                               ESP32 DevKit V1 Hardware Circuit                          |
    |                                                                                         |
    |   [3.3V Power] ------------------+------------------------+                             |
    |                                  |                        |                             |
    |   [GND Ground]  -----------------+------------+           | (4.7 kΩ Pull-up)           |
    |                                  |            |           |                             |
    |   [GPIO 21] -----------------> [SDA] MPU6500  |           +----+                        |
    |   [GPIO 22] -----------------> [SCL] IMU      |                |                        |
    |                                [GND] ---------+                |                        |
    |                                [VCC] <--------+ (3.3V)         |                        |
    |                                                                |                        |
    |   [GPIO 4]  ------------------------------------------------> [DATA] DS18B20              |
    |                                [GND] ---------+             Waterproof Temp Probe       |
    |                                [VCC] <--------+ (3.3V)                                  |
    |                                                                                         |
    |   [GPIO 26] -----------------> [IN1] L298N Motor Driver                                 |
    |   [GPIO 27] -----------------> [IN2] L298N Motor Driver                                 |
    |   [ENA Jumper Installed] ----> [ENA] (Fixed 100% Speed)                                 |
    |                                [OUT1] ---------------------> [DC Machine Motor]         |
    |                                [OUT2] ---------------------> [OUT2 Terminal]            |
    |                                                                                         |
    |   [External DC PSU (3-6V)] --> [VCC (+)] L298N Power                                    |
    |   [External DC PSU (-)] -----> [GND (-)] Shared with ESP32 GND (Common Ground)          |
    +-----------------------------------------------------------------------------------------+
    ```
    """)

    # 5. IMU Address vs Library Initialization Note
    st.markdown("<div class='section-header'>5. Technical Deep-Dive: I²C Bus Detection vs. IMU Library Initialization</div>", unsafe_allow_html=True)
    st.markdown("""
    An I²C scanner acknowledging address `0x68` confirms electrical bus continuity, but **does not guarantee that the sensor can be initialized and read**.
    
    1. **WHO_AM_I Register Verification:** The `MPU6500_DMP` library queries internal register `0x75`. Genuine MPU6500 returns `0x70`, whereas MPU6050 returns `0x68` and MPU9250 returns `0x71`. If register verification fails, `imu.begin()` returns non-zero.
    2. **Startup Power Slew Rate:** When powered from the ESP32 3.3V rail, capacitor inrush current can cause brief voltage dips. The firmware executes up to 3 automatic initialization retries with 500ms stabilization intervals.
    3. **Motor Inductive Back-EMF:** When the DC motor starts or reverses, inductive voltage spikes on unshielded wiring can glitch the I²C bus. The firmware features non-blocking periodic retry logic in `loop()` so that if the IMU temporarily drops off the bus during motor transients, it automatically re-initializes without halting telemetry streaming.
    """)

    # 6. Critical Safety Mandates
    st.markdown("<div class='section-header'>6. Electrical & Mechanical Safety Mandates</div>", unsafe_allow_html=True)
    st.markdown("""
    1. **Never Connect the DC Motor Directly to ESP32 GPIOs:**
       - Microcontroller GPIO pins provide a nominal maximum of 12–40 mA.
       - A rotating DC motor consumes several hundred milliamperes under continuous load and up to 1.5A during stall or startup.
       - Connecting directly will fry the ESP32 output transistors and cause destructive back-EMF voltage spikes. Always use a motor driver IC (e.g. L298N).
    2. **DS18B20 4.7 kΩ Pull-up Resistor:**
       - The 1-Wire protocol relies on an open-drain bus architecture.
       - Without the 4.7 kΩ resistor between GPIO 4 and 3.3V, the line floats, resulting in `DEVICE_DISCONNECTED_C` (-127°C or 85°C error codes).
    3. **Common Ground Connection:**
       - The external motor power supply negative terminal, the L298N GND terminal, and the ESP32 GND pin must be connected together. A missing common ground creates floating logic voltages, preventing the motor from switching states reliably.
    4. **Safety Interlock Limitation:**
       - This monitoring system is designed for non-invasive condition monitoring. It does not possess hardware limit switches or emergency brake interlocks.
    """)
