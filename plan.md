I want you to act as the systems engineer for a ground-based proof of concept for my autonomous swarm-drone project.

> [!WARNING]
> **SYSTEMS ENGINEER UPDATE (Sept 2026):**
> This document is the original project specification and high-level goal map.
> **Several assumptions are INCORRECT or SUPERSEDED** based on physical testing.
> For all ground-truth technical details refer exclusively to `README.md`.
>
> **Hardware corrections:**
> 1. **Motor Pins:** AlphaBot2-Ar uses Analog pins (A0-A3) for direction, D5/D6 for PWM — NOT digital D4-D7.
> 2. **Right motor is physically mirrored** — direction inverted in software (`INVERT_RIGHT = True`).
> 3. **Power:** Running YOLO on all 4 CPU cores causes a brown-out and Wi-Fi disconnect. Throttled to `num_threads=1`.
> 4. **SD Card:** A brown-out crash can corrupt the SD card filesystem. Fix: remove card, run `chkdsk` on Windows, reinsert.
>
> **Architecture corrections:**
> 5. **Swarm topology is symmetric** — both robots are equal peers, NOT master/slave. Both run `swarm_bot.py --id A/B`.
> 6. **XBee is bidirectional** — both robots simultaneously send AND receive target data. The robot with higher confidence detection leads steering.
> 7. **Model:** YOLO11n exported to NCNN FP16, run via custom Python wrapper. No PyTorch. No Ultralytics at runtime.
> 8. **Ports:** XBee = `/dev/ttyUSB0`, Arduino = `/dev/ttyUSB1`, Camera = `/dev/video0` on both robots.
>
> **What is complete (Sept 22, 2026):**
> - Phases 0–6 complete: motors, serial bridge, YOLO, streaming, hysteresis tracking, XBee link verified.
> - Pending: full cooperative ground test (Phase 7), forward-drive + PID (Phase 8).


Do NOT start coding immediately.

First perform a deep technical audit and research pass, then produce a complete implementation plan, hardware architecture, communication protocol, software architecture, testing strategy, and only after that recommend the first code to write.

==================================================
PROJECT OBJECTIVE
==================================================

I ultimately want a disaster-management swarm of autonomous drones.

Before putting anything in the air, I want a minimally viable GROUND proof of concept using:

- 2 × identical Waveshare AlphaBot2-Ar robots
- 1 × Raspberry Pi on each robot
- 1 × camera on each Raspberry Pi
- 1 × identical XBee/Zigbee radio on each robot
- Person detection/tracking with YOLO
- Wireless exchange of target/robot information between the two robots

The immediate concept I want to prove is:

Robot A:
camera → YOLO → detect/track me → estimate my position relative to Robot A → transmit that information over Zigbee

Robot B:
receive Robot A's information → interpret it → demonstrate that it can use that information for a meaningful coordinated behavior.

The first milestone does NOT need to be sophisticated autonomous navigation.

The first milestone is proving that:

1. Raspberry Pi can run the camera.
2. Raspberry Pi can run YOLO/person detection.
3. Robot A can continuously track a selected person.
4. Robot A can generate structured target data.
5. The target data can be transmitted over XBee/Zigbee.
6. Robot B can receive and decode the data.
7. Robot B can act on that information safely on the ground.

==================================================
VERY IMPORTANT TERMINOLOGY / COORDINATE SYSTEM
==================================================

Do not casually call image coordinates "GPS position."

I need you to explicitly distinguish:

A. Image-space position:
- bounding box x/y
- bounding box width/height
- bounding-box center
- normalized x/y
- confidence

B. Robot-relative target estimate:
- left/right bearing or angular error
- approximate distance/range if it can be estimated
- target position in Robot A's local coordinate system

C. Robot global position:
- latitude
- longitude
- heading
- altitude if relevant

D. Common/world-frame target position:
- target coordinates transformed into a common coordinate frame

Explain which of these is realistically obtainable from:
- a monocular Raspberry Pi camera
- YOLO
- wheel odometry
- IMU
- GPS
- compass

Do not pretend that a camera bounding-box coordinate is a geographic coordinate.

For the first POC, prefer the simplest reliable representation.

==================================================
1. FULL AUDIT OF MY ACTUAL ALPHABOT REPOSITORY
==================================================

Repository:

https://github.com/rajdeep13-coder/AlphaBot2-Ar

You MUST inspect the repository itself before proposing an architecture.

Read:
- README.md
- TASKS.md
- REFERENCES.md
- Configuration/*
- Libraries/*
- CompanionPet/*
- every .ino file
- every relevant source/configuration file
- pin_mapping.csv
- any diagrams/documentation actually present
- git tree/file structure

Do not trust README directory listings if they do not match the current repository tree.

Determine:

1. Exact controller:
   - ATmega328P / Arduino compatibility
   - exact board assumptions
   - how the AlphaBot2-Ar interfaces with the base

2. Exact motor system:
   - TB6612FNG
   - left/right motor pins
   - PWM pins
   - direction pins
   - whether the current code actually uses those pins correctly

3. Exact sensor interfaces:
   - ultrasonic
   - IR
   - line sensors
   - joystick
   - OLED
   - RGB
   - buzzer

4. Existing communication hardware:
   - HC-05
   - XBee connector
   - UART availability
   - any pin conflicts

5. Determine whether the Raspberry Pi can be attached cleanly to the existing AlphaBot2-Ar, or whether one of these approaches is better:

   Option A:
   Raspberry Pi + existing ATmega328P Arduino controller

   Option B:
   Raspberry Pi directly interfaced to the AlphaBot2-Ar electronics

   Option C:
   replacing the AlphaBot2-Ar controller/adapter with a Raspberry Pi-oriented AlphaBot2-Pi adapter

   Option D:
   Raspberry Pi as high-level computer + Arduino as low-level motor controller

Compare all options.

Pay special attention to:
- 3.3 V vs 5 V logic
- UART conflicts
- USB serial
- motor-control latency
- safety
- power
- ease of implementation
- whether hardware modification/soldering is required
- whether current repository code can be reused

Recommend one architecture for the POC and justify it.

==================================================
2. OFFICIAL ALPHABOT DOCUMENTATION
==================================================

Research the current official Waveshare documentation.

Use:
- AlphaBot2-Ar wiki
- AlphaBot2 general wiki
- AlphaBot2-Pi wiki
- official product pages
- official schematics
- official user manuals
- official demo-code packages

Also examine reputable community implementations.

Determine exactly how Waveshare's Raspberry Pi version controls:
- motors
- sensors
- camera
- servo
- peripherals

The official AlphaBot2-Pi documentation is especially important because it provides an existing Raspberry Pi software path.

Determine whether using the existing AlphaBot2-Ar with a Pi is sensible, or whether the mechanical base can instead be paired with the Pi adapter approach.

Do not recommend buying another adapter unless you can show that it materially simplifies the POC.

==================================================
3. EXISTING ALPHABOT OBJECT-TRACKING PROJECTS
==================================================

Search GitHub, forums, Reddit, robotics communities and other reputable sources for:

- AlphaBot2 person tracking
- AlphaBot2 object tracking
- AlphaBot2 Raspberry Pi YOLO
- AlphaBot2 camera tracking
- Raspberry Pi robot person following
- YOLO Raspberry Pi robot following
- Waveshare AlphaBot tracking

Inspect actual code where available.

There is at least one existing AlphaBot2 object-tracking project using:
- Raspberry Pi
- camera
- OpenCV
- object detection/tracking
- target offsets
- control logic

Find it and inspect how its architecture works.

Determine:
- what is worth reusing
- what is outdated
- what should be replaced by YOLO
- what controller is used
- whether processing happens on the Pi or remotely
- how target position is represented
- how motor control is generated

==================================================
4. RASPBERRY PI + CAMERA + YOLO
==================================================

Research current official/reputable Raspberry Pi and Ultralytics documentation.

Use:
- Raspberry Pi camera documentation
- Picamera2 documentation
- Ultralytics Raspberry Pi deployment documentation
- Ultralytics tracking documentation
- ONNX/NCNN deployment guidance where relevant

Determine the most appropriate model/runtime for the actual Raspberry Pi hardware.

Do not blindly choose the largest YOLO model.

Compare:
- YOLO nano/small model
- ONNX
- NCNN
- PyTorch
- CPU inference

The priority is:

LOW LATENCY + STABLE TRACKING + LOW POWER + SUFFICIENT PERSON-DETECTION ACCURACY

not maximum benchmark accuracy.

Determine realistic expected performance for:
- Raspberry Pi 4
- Raspberry Pi 5

If the exact Pi model is unknown, provide both and recommend accordingly.

Explain:
- detection rate
- tracking rate
- inference FPS
- camera FPS
- end-to-end control latency
- thermal considerations

Prefer the smallest model that gives useful person tracking.

==================================================
5. PERSON TRACKING ALGORITHM
==================================================

I do NOT merely want:

"detect a person"

I want:

"keep track of the same person across frames"

Research and compare:
- YOLO detection only
- YOLO + ByteTrack
- YOLO + BoT-SORT
- simple nearest-target tracking
- appearance-based tracking if necessary

Recommend the simplest method that is robust enough for this POC.

The tracked target should produce a state such as:

target_id
class
confidence
bbox_x1
bbox_y1
bbox_x2
bbox_y2
center_x
center_y
normalized_center_x
normalized_center_y
bbox_width
bbox_height
timestamp

Explain which fields are actually needed for the robot controller.

==================================================
6. TURN VISUAL DETECTION INTO ROBOT CONTROL
==================================================

Design the first control loop.

For example:

camera frame
    ↓
YOLO detector/tracker
    ↓
target bounding box
    ↓
target center x
    ↓
horizontal error from image center
    ↓
steering command

Example concept:

error_x = target_center_x - image_center_x

Then a controller can use:

error_x
+
target size / estimated distance
+
filtered velocity
=
left/right motor command

Compare:
- simple threshold controller
- P controller
- PD controller
- PID controller

Recommend the simplest controller appropriate for the first ground test.

Do not overengineer this.

The first behavior can simply be:

target lost → STOP

target too far → FORWARD

target centered → STRAIGHT

target left → TURN LEFT

target right → TURN RIGHT

target very close → STOP

Then determine whether PD control would improve behavior.

==================================================
7. THE MOST IMPORTANT QUESTION:
HOW DOES ROBOT A SEND "MY POSITION" TO ROBOT B?
==================================================

Analyze this very carefully.

A camera detects a person in Robot A's image.

That does NOT automatically provide the person's geographic latitude/longitude.

Determine multiple possible representations:

Option 1:
Send image-space coordinates

Option 2:
Send robot-relative bearing + approximate distance

Option 3:
Send Robot A GPS + target bearing + target distance

Option 4:
Use stereo/multiple cameras

Option 5:
Use depth camera

Option 6:
Use LiDAR/depth sensor

Option 7:
Use visual odometry + map/local coordinate frame

Option 8:
Use GPS only for robot positions

Determine which is:

- easiest
- cheapest
- most reliable
- sufficient for the first POC

My preference is to avoid adding specialized localization hardware unless genuinely necessary.

For the first POC, I suspect a useful message could look like:

{
  "sender": 1,
  "timestamp": 123456,
  "target_id": 0,
  "confidence": 0.91,
  "cx": 0.52,
  "cy": 0.47,
  "bearing": -3.2,
  "range": 1.8
}

But do NOT assume this is correct.
Analyze and improve it.

==================================================
8. ZIGBEE / XBEE COMMUNICATION
==================================================

I currently have identical XBee-PRO S2C-style modules.

Some may have Zigbee firmware.

Do not assume the firmware.

First determine how to inspect:
- function set
- firmware version
- SH
- SL
- DH
- DL
- ID/PAN ID
- AP
- baud rate
- API/transparent mode

Use official Digi documentation and reputable Digi forum discussions.

For the ground POC compare:

A. Transparent UART mode

B. API mode

C. Zigbee coordinator/router topology

D. DigiMesh if appropriate

The eventual swarm uses multiple nodes, so analyze whether it is better to start with:

Coordinator:
Ground Station / Robot A

Router:
Robot B

or:

Robot A ↔ Robot B

Explain what can and cannot be done with two Zigbee modules.

For the POC, prioritize:
- easy debugging
- structured messages
- bidirectional communication
- acknowledgements
- packet loss detection
- timestamps
- sequence numbers

Do not send raw verbose JSON over RF unless you explain why.
Consider compact binary framing or a simple delimited protocol.

Compare:
JSON
CSV
binary struct
CBOR
MessagePack

Recommend one.

For the first implementation, readability/debugging matters.

==================================================
9. DESIGN A ROBOT-TO-ROBOT MESSAGE PROTOCOL
==================================================

Design a minimal protocol.

At minimum consider:

HEARTBEAT
STATUS
TARGET_UPDATE
COMMAND
ACK
STOP / EMERGENCY_STOP

Example conceptual message:

TYPE=TARGET
SEQ=102
TIME=...
X=...
Y=...
BEARING=...
RANGE=...
CONF=...
STATE=TRACKING

But improve this based on your research.

Define:
- packet fields
- units
- byte order if binary
- sequence number
- timestamp
- checksum/CRC if appropriate
- acknowledgement strategy
- timeout
- stale-data handling

The protocol must fail safely.

If Robot B stops receiving target updates:
→ Robot B should NOT continue executing an old movement command indefinitely.

Define a watchdog timeout.

==================================================
10. SIM808 / GSM + GPS MODULE
==================================================

I also own a "GSM GPS Modem 808 combo", likely based on SIM808.

Research the exact SIM808 capabilities and limitations.

Determine how useful it would be for this POC.

Analyze:

GPS:
- latitude/longitude
- fix time
- accuracy
- update rate
- cold start
- antenna requirements
- outdoor limitations
- whether it can be used for robot localization

GSM/GPRS:
- telemetry
- remote server
- SMS
- internet connectivity
- possible future ground-station communication

Then answer:

Should SIM808 be:

A. Not used in POC
B. Used only to log Robot A GPS position
C. Used on both robots
D. Used as a backup communications path
E. Used later for ground-station/cloud telemetry

My expectation is that SIM808 should NOT be allowed to complicate the basic camera + Zigbee POC unless it adds clear value.

Also investigate current real-world reports about SIM808 GPS reliability.

Do not rely only on datasheets.

==================================================
11. POWER ARCHITECTURE
==================================================

Analyze the power system carefully.

AlphaBot2 uses the robot battery for the chassis.

Now we add:
- Raspberry Pi
- camera
- XBee
- optionally SIM808

Determine:
- required voltages
- approximate current draw
- peak current
- regulator requirements
- whether the AlphaBot power system can safely support the Pi
- whether a separate regulator/buck converter is needed
- whether SIM808's cellular transmit bursts create special power requirements
- grounding requirements

Do not assume the AlphaBot's existing regulator is sufficient for a Raspberry Pi.

Design a safe power architecture.

==================================================
12. EXACT POC HARDWARE ARCHITECTURE
==================================================

Produce a block diagram for each AlphaBot:

             Camera
                |
                v
        Raspberry Pi
         |         |
         |         +---- XBee/Zigbee
         |
         +---- Arduino / AlphaBot controller
                       |
                       v
                 TB6612FNG
                  /      \
             Left motor  Right motor

Then explain exactly how the Pi communicates with the AlphaBot controller.

Determine whether:
- USB serial
- UART
- GPIO
- I2C
- SPI

is the best method.

Do NOT recommend GPIO motor control without checking the actual AlphaBot hardware topology.

==================================================
13. SOFTWARE ARCHITECTURE
==================================================

Design the software as modular components.

Suggested structure:

camera/
detector/
tracker/
target_estimator/
controller/
motor_interface/
xbee_transport/
protocol/
state_machine/
logger/
diagnostics/

Example pipeline:

Camera
 ↓
Picamera2
 ↓
YOLO
 ↓
Tracker
 ↓
Target State
 ↓
Target Estimator
 ↓
Local Controller
 ↓
Motor Command
 ↓
AlphaBot motor interface

Separately:

Target State
 ↓
Protocol Encoder
 ↓
XBee
 ))))
 XBee
 ↓
Protocol Decoder
 ↓
Robot B Coordinator
 ↓
Behavior State Machine

Use asynchronous/non-blocking design.

Do not allow camera inference to block the communication watchdog.

==================================================
14. ROBOT STATE MACHINE
==================================================

Design states such as:

BOOT
SELF_TEST
IDLE
SEARCHING
TARGET_ACQUIRED
TRACKING
TARGET_LOST
REMOTE_TRACKING
FAULT
EMERGENCY_STOP

Define transitions.

Especially define:

TARGET LOST
→ STOP

XBee LINK LOST
→ STOP

LOW BATTERY
→ STOP / RETURN / SAFE MODE

CAMERA FAILURE
→ STOP

YOLO FAILURE
→ STOP

MOTOR CONTROLLER FAILURE
→ STOP

==================================================
15. DEVELOPMENT PHASES
==================================================

Break the project into extremely small testable milestones.

Phase 0:
Hardware inspection.

Phase 1:
AlphaBot motors controlled normally.

Phase 2:
Raspberry Pi ↔ AlphaBot motor-controller communication.

Phase 3:
Camera works on Pi.

Phase 4:
YOLO detects a person.

Phase 5:
YOLO tracking produces stable target IDs.

Phase 6:
Local Robot A person-following behavior without Zigbee.

Phase 7:
XBee A ↔ XBee B simple serial test.

Phase 8:
Pi A ↔ XBee A ↔ XBee B ↔ Pi B.

Phase 9:
Structured TARGET_UPDATE packets.

Phase 10:
Robot B receives and logs target data.

Phase 11:
Robot B reacts to received target information.

Phase 12:
Both robots perform a coordinated ground behavior.

Only after all these work should we consider more advanced localization.

==================================================
16. GROUND-TEST SCENARIOS
==================================================

Design controlled experiments.

Experiment 1:
Person stationary.
Robot A stationary.
Measure YOLO stability.

Experiment 2:
Person walks left/right.
Robot A tracks.

Experiment 3:
Robot A follows person.

Experiment 4:
Robot A tracks person and sends target state over XBee.

Experiment 5:
Robot B receives packets while stationary.

Experiment 6:
Robot B reacts to target state.

Experiment 7:
Both robots move.

Experiment 8:
Temporary Zigbee packet loss.

Experiment 9:
Person leaves camera FOV.

Experiment 10:
Person re-enters FOV.

Experiment 11:
One robot disappears from communication.

Measure:
- detection FPS
- tracking FPS
- control latency
- XBee packet latency
- packet loss
- tracking confidence
- stopping latency
- false detections
- false target switches

==================================================
17. SAFETY
==================================================

This is a ground robot POC.

Do NOT immediately make it chase people at high speed.

Use:
- low motor speed
- open indoor/outdoor test area
- physical emergency stop
- automatic timeout
- max command duration
- max acceleration
- target-loss stop
- RF-loss stop
- manual override

Explain safe testing procedures.

==================================================
18. EVENTUAL DRONE RELEVANCE
==================================================

At the end, explain how this ground POC maps to the eventual swarm drone.

Ground POC:

Camera
→ YOLO
→ tracking
→ local target state
→ radio protocol
→ multi-agent communication
→ coordination

Eventual drone:

RGB/thermal camera
→ detection
→ target localization
→ world-frame coordinate
→ MAVLink/ROS2
→ swarm protocol
→ task allocation
→ failover

Clearly distinguish what transfers directly and what must be redesigned for drones.

Do NOT claim that a ground robot proof automatically validates aerial localization.

==================================================
19. WHAT I WANT AS THE FINAL OUTPUT
==================================================

Before any coding, produce a comprehensive technical report with these sections:

1. Executive summary
2. Actual AlphaBot2-Ar hardware/software audit
3. Repository audit
4. Official Waveshare documentation findings
5. Existing AlphaBot tracking project findings
6. Raspberry Pi + camera architecture
7. YOLO model/runtime recommendation
8. Tracking algorithm recommendation
9. Target-coordinate model
10. Zigbee/XBee architecture
11. XBee configuration plan
12. Robot-to-robot protocol
13. SIM808 assessment
14. Power architecture
15. Pi ↔ AlphaBot communication architecture
16. Full software architecture
17. State machine
18. Ground POC milestones
19. Test plan
20. Failure modes
21. Safety strategy
22. Estimated latency/bandwidth
23. Parts required
24. Parts I already have vs parts I need
25. Recommended final POC architecture
26. Path from POC → real drone swarm

==================================================
20. SOURCES / RESEARCH QUALITY
==================================================

Search deeply.

Prioritize:

Tier 1:
- Waveshare official docs
- Digi official docs
- Raspberry Pi official docs
- Ultralytics official docs
- SIMCom documentation/datasheets

Tier 2:
- Digi forums
- Raspberry Pi forums
- Arduino forums
- GitHub projects
- robotics communities
- Reddit where useful for real-world experience

Tier 3:
- blogs/tutorials only when needed

For important technical conclusions, cite sources.

Distinguish:
- official specification
- community observation
- your engineering inference

Do not fabricate hardware specifications.

==================================================
21. VERY IMPORTANT: DO NOT START BY WRITING CODE
==================================================

The first response should only be the research/audit/architecture report and a concrete implementation roadmap.

Do not generate a complete repository yet.

At the end, explicitly state:

A. What hardware I should assemble first
B. What software I should install first
C. What exact experiment I should perform first
D. What information/screenshots/output you need from me before proceeding

The first physical test should be extremely simple and reversible.

My immediate goal is:

Robot A sees me
→ YOLO detects/tracks me
→ Robot A generates target state
→ target state goes through XBee
→ Robot B receives it
→ Robot B prints/displays the target state

Only after this works should we make Robot B move.

==================================================
KNOWN CONTEXT
==================================================

My current AlphaBot repository is:

https://github.com/rajdeep13-coder/AlphaBot2-Ar

I have two identical AlphaBots.

I have Raspberry Pis available.

I have cameras available.

I have identical XBee-PRO S2C-type radios, currently being configured with Digi XCTU.

One of the XBee USB adapter boards currently appears in Windows Device Manager as:

"CP2102 USB to UART Bridge Controller"

with a missing driver, so the XBee PC-side setup is still being completed.

I also have a GSM/GPS Modem 808 combo module, likely SIM808.

Do not assume its exact variant without inspection.

The final long-term project is a multi-drone autonomous disaster-search swarm, but this task is ONLY the ground proof of concept.

Be technically skeptical. Challenge bad assumptions.
Do not overengineer the first milestone.
Do not confuse detection with localization.
Do not confuse localization with communication.
Do not confuse communication with coordination.

The goal is to build a small but architecturally meaningful system that proves the core pipeline before moving to flight.