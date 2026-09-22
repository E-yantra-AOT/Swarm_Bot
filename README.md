# Swarm Ground Proof-of-Concept (POC)

This repository contains the software stack for a two-robot ground swarm proof-of-concept. It serves as the foundation for autonomous coordination, person-tracking, and XBee-based communication between two equal robotic peers.

## Hardware Stack (Per Robot)
*   **Base:** Waveshare AlphaBot2-Base (contains TB6612FNG motor driver & 2x 14500 Li-ion batteries)
*   **Adapter Shield:** AlphaBot2-Ar (Arduino UNO compatible adapter)
*   **Microcontroller:** Arduino UNO R3 (Mounted on the AlphaBot2-Ar shield)
*   **Companion Computer:** Raspberry Pi 4B (4GB RAM)
*   **Vision:** USB Webcam (Jieli Technology) — `/dev/video0`
*   **RF Communication:** XBee-PRO S2C (Zigbee TH PRO, 9600 baud, Transparent mode) — `/dev/ttyUSB0`
*   **Motor Bridge:** Arduino UNO R3 connected via USB — `/dev/ttyUSB1`

## Critical Hardware Discoveries & Pin Mappings
The official documentation for the AlphaBot2-Ar is misleading regarding motor pins. The true pin mapping is defined by the yellow "Control JMP" jumper matrix on the AlphaBot2-Ar shield itself.

**The motor direction pins are wired to the Arduino's Analog pins:**
*   **Left Motor (A):**
    *   PWM: `D6`
    *   AIN1: `A1`
    *   AIN2: `A0`
*   **Right Motor (B):**
    *   PWM: `D5`
    *   BIN1: `A2`
    *   BIN2: `A3`

*(Note: The Arduino firmware handles these analog pins as digital outputs using `pinMode(A0, OUTPUT)`).*

**Right motor is physically mounted mirrored** — direction logic is inverted in software (`INVERT_RIGHT = True` in all Python scripts). Do NOT change physical wiring.

## XBee Configuration (Set in XCTU — do not change)
| Setting | Value |
|---|---|
| Function Set | ZIGBEE TH PRO |
| PAN ID | `3333` |
| AP (API Mode) | `0` (Transparent mode) |
| Baud Rate | `9600` |
| Radio A DL | `41F52F20` (points to B) |
| Radio B DL | `41F52FD2` (points to A) |

## Power & Thermal Considerations
Running computer vision models (YOLO) forces the Raspberry Pi 4 CPU to 100% utilization. Because the Pi simultaneously powers a webcam, Arduino, and XBee via USB, this creates massive instantaneous current spikes.

*   **Symptoms:** If the wall adapter or battery pack cannot supply 5V @ 3A (15W) instantly, the Pi will suffer a brown-out (Wi-Fi drop, crash, or hard reboot).
*   **Root Cause:** SD card can corrupt during a brown-out crash. Fix: remove SD card, scan with Windows `chkdsk`, reinsert.
*   **Solution:** YOLO NCNN inference is throttled via `num_threads=1`. This limits CPU usage, giving ~2 FPS but ensuring power stability.

## Software Architecture

### 1. Arduino Motor Bridge (`phase1_arduino/`)
*   Compiled using PlatformIO (`pio run`).
*   Listens on `/dev/ttyUSB1` at 115200 baud for ASCII commands from the Pi.
*   **Protocol:** `M,<leftSpeed>,<leftDir>,<rightSpeed>,<rightDir>` (e.g., `M,150,F,150,B`).
*   Includes a 2-second watchdog timer to halt motors if the Pi crashes or disconnects.

### 2. YOLO NCNN Vision Engine (`shared/yolo_ncnn.py`)
*   Custom Python wrapper around the `ncnn` library — no PyTorch, no Ultralytics.
*   Runs YOLO11n FP16 model directly on the Pi's ARM CPU.
*   Detects persons (class 0), returns bounding boxes with `norm_cx`, `norm_cy`, `confidence`.

### 3. XBee Transport Layer (`shared/xbee_transport.py`)
*   Thread-safe JSON transport over XBee transparent serial.
*   `send(dict)` → serialises to newline-terminated JSON and writes to serial.
*   `recv()` → non-blocking read, returns parsed dict or None.
*   `link_alive()` → safety watchdog, returns False if no packet received in 2 seconds.

### 4. Swarm Bot — Symmetric Peer (`phase4_tracking/swarm_bot.py`)
*   **The main script.** Runs identically on both robots — no master, no slave.
*   3 parallel threads per robot:
    *   **Camera thread:** YOLO detection → updates local state → broadcasts over XBee.
    *   **XBee RX thread:** Receives partner detections → updates partner state.
    *   **Control thread:** Picks best detection (highest confidence) → steers motors.
*   Hysteresis deadzone (`DEADZONE_STOP=0.12`, `DEADZONE_START=0.20`) prevents jitter.
*   Hard stops if no fresh detection from either robot for 2 seconds.

### 5. Debug Stream (`phase3_vision/yolo_stream.py`, `phase4_tracking/swarm_tracker_stream.py`)
*   MJPEG HTTP stream on port `5000` — open in browser for visual debugging only.
*   **Do NOT run the stream during normal operation** — it adds latency and CPU load.

## Network & Access
| Robot | Hostname | Current IP (DHCP) | SSH User |
|---|---|---|---|
| **Robot A** | `pi.local` | `10.219.37.74` | `pi` |
| **Robot B** | `pi2.local` | `10.219.37.184` | `pi2` |

> [!WARNING]
> IPs are assigned by DHCP and may change if the router restarts or the bots connect to a different network. Always verify with `ping pi.local` before assuming a fixed IP.

## How to Run

### Start the swarm (run in two separate SSH terminals):
```bash
# Robot A
ssh pi@10.219.37.74
~/swarm_venv/bin/python ~/swarm_bot.py --id A

# Robot B
ssh pi2@10.219.37.184
~/swarm_venv/bin/python ~/swarm_bot.py --id B
```

### Debug stream (temporary, closes before deploying swarm_bot):
```bash
~/swarm_venv/bin/python ~/yolo_stream.py          # basic stream
~/swarm_venv/bin/python ~/swarm_tracker_stream.py # stream + motor HUD
# Open http://<robot-ip>:5000 in browser
```

### Reflash Arduino firmware:
```bash
# On Windows (from project root):
cd phase1_arduino
pio run
# Then SCP .hex and avrdude flash via SSH (see phase1 notes)
```

## Phase Map & Progress
*   [x] **Phase 0:** Hardware check & Pi user-space Python dependencies (`~/swarm_venv`).
*   [x] **Phase 1:** Arduino motor bridge firmware — correct A0-A3 pin mapping discovered and flashed.
*   [x] **Phase 2:** Pi → Arduino serial motor control verified on both robots.
*   [x] **Phase 3:** YOLO11n live camera stream deployed and tested on both robots.
*   [x] **Phase 4:** Person tracking with hysteresis deadzone — steering verified on bench.
*   [x] **Phase 5:** Navigation loop — proportional (P) steering controller implemented.
*   [x] **Phase 6:** XBee RF link verified (zero packet loss). Symmetric peer protocol implemented.
*   [ ] **Phase 7:** Full swarm ground test — both robots tracking cooperatively on the floor.
*   [ ] **Phase 8:** Tune PID, add forward-drive logic (approach target, not just turn-in-place).

## Repository Structure

```text
Swarm_Bot/
|-- plan.md                                   # Original project specification (see WARNING at top).
|-- README.md                                 # This file — ground truth for all hardware and status.
|-- .gitignore
|-- yolo11n.pt                                # Original PyTorch weights (used for NCNN export only).
|
|-- phase0_setup/                             # Robot provisioning scripts
|   |-- install_deps.sh                       # Creates ~/swarm_venv and installs ncnn/opencv/pyserial.
|   |-- verify_install.sh                     # Verifies all Python packages pass import check.
|   |-- check_hardware.sh                     # Confirms /dev/video0, ttyUSB0, ttyUSB1 are present.
|   |-- identify_ports.sh                     # Identifies which ttyUSB* is Arduino vs XBee.
|   |-- export_yolo_ncnn.py                   # Windows: converts yolo11n.pt → NCNN format.
|   |-- deploy_phase0.ps1                     # Windows: SCP all files to both robots.
|   |-- yolo11n_ncnn_model/                   # Exported NCNN model (copied to ~/yolo11n_ncnn_model/ on each Pi)
|       |-- model.ncnn.bin                    # Binary weights (5.1 MB)
|       |-- model.ncnn.param                  # Network architecture
|       |-- metadata.yaml                     # Class names, input size
|
|-- phase1_arduino/                           # Arduino firmware
|   |-- platformio.ini                        # PlatformIO build config (board: uno, src: sketch_pi_motor_bridge)
|   |-- sketch_pi_motor_bridge/
|       |-- sketch_pi_motor_bridge.ino        # FINAL firmware — serial bridge, dual-pin motor control, watchdog.
|   |-- sketch_motor_diag3/                   # Diagnostic sketch used to discover the true A0-A3 pin mapping.
|
|-- phase3_vision/                            # Debugging tools
|   |-- yolo_stream.py                        # MJPEG stream server — view YOLO detections in browser.
|
|-- phase4_tracking/                          # Main robot intelligence
|   |-- swarm_bot.py                          # ★ MAIN SCRIPT — symmetric peer, YOLO + XBee + motors.
|   |-- swarm_tracker.py                      # Single-robot tracker (no XBee) — useful for motor tuning.
|   |-- swarm_tracker_stream.py               # Tracker + live MJPEG stream — for visual debugging only.
|
|-- shared/                                   # Modules used by both robots
|   |-- yolo_ncnn.py                          # NCNN inference wrapper (detection + NMS).
|   |-- xbee_transport.py                     # XBee transparent-mode JSON send/recv with watchdog.
|
|-- robot_a/                                  # Reserved for Robot A specific future code
|-- robot_b/                                  # Reserved for Robot B specific future code
```
