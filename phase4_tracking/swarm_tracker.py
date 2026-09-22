import sys
import time
import cv2
import serial
import os
from pathlib import Path

# Add shared module to path so it can find yolo_ncnn
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from yolo_ncnn import YoloNcnn

# --- Configuration ---
ARDUINO_PORT = '/dev/ttyUSB1'
BAUD_RATE = 115200

# Fix for physically inverted motor wiring:
# You mentioned earlier that M,100,F,100,F caused the wheels to spin opposite ways.
# This toggles the software logic so "Forward" always physically moves the bot forward.
INVERT_RIGHT_MOTOR = True
INVERT_LEFT_MOTOR = False

# Steering Tuning
KP_TURN   = 250   # How aggressively it turns based on how far off-center you are
MAX_SPEED = 120   # Hard speed limit so it doesn't spin out of control (0-255)
MIN_SPEED = 55    # Minimum speed required to overcome ground friction

# Hysteresis deadzone — prevents jitter at the boundary
# Once stopped: only start turning again when error exceeds DEADZONE_START
# Once turning: stop only when error drops below DEADZONE_STOP
DEADZONE_STOP  = 0.12   # Stop turning when error is within 12% of centre
DEADZONE_START = 0.20   # Only start turning when error exceeds 20% of centre

def init_serial():
    print(f"Connecting to Arduino on {ARDUINO_PORT}...")
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2) # Wait for Arduino to reset
        return ser
    except Exception as e:
        print(f"Failed to connect to Arduino: {e}")
        return None

def send_motor_cmd(ser, left_spd, left_dir, right_spd, right_dir):
    if not ser: return
    
    # Apply inversion logic so F always means physical forward
    if INVERT_LEFT_MOTOR:
        left_dir = 'B' if left_dir == 'F' else 'F'
    if INVERT_RIGHT_MOTOR:
        right_dir = 'B' if right_dir == 'F' else 'F'
        
    cmd = f"M,{int(left_spd)},{left_dir},{int(right_spd)},{right_dir}\n"
    print(f"[{time.time():.2f}] Cmd: {cmd.strip()}")
    ser.write(cmd.encode('ascii'))

def main():
    ser = init_serial()
    
    print("Loading YOLO NCNN Model (1 thread for power safety)...")
    yolo = YoloNcnn(
        model_dir=os.path.expanduser('~/yolo11n_ncnn_model'),
        input_size=320,
        num_threads=1
    )
    
    cap = cv2.VideoCapture('/dev/video0')
    if not cap.isOpened():
        print("ERROR: Could not open camera /dev/video0! Trying index 0...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("FATAL: Camera failed to open entirely.")
            sys.exit(1)
    # Lower resolution for slightly faster processing
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
    
    print("\n" + "="*40)
    print(" TRACKING LOOP ACTIVE ")
    print(" Stand in front of the camera!")
    print(" Press Ctrl+C to stop.")
    print("="*40 + "\n")
    
    try:
        last_print = 0
        is_turning = False   # Hysteresis state: are we currently in a turn?
        print("Entering while loop...")
        while True:
            # print("Reading frame...")
            ret, frame = cap.read()
            if not ret: 
                # print("Frame read failed!")
                time.sleep(0.1)
                continue
            
            # Detect objects
            detections = yolo.detect(frame)
            
            # Filter for persons (class_id == 0)
            persons = [d for d in detections if d.class_id == 0]
            
            if len(persons) == 0:
                if time.time() - last_print > 1.0:
                    print(f"[{time.time():.2f}] No person detected. Stopped.")
                    last_print = time.time()
                send_motor_cmd(ser, 0, 'F', 0, 'F')
                continue
                
            # Find the largest person by bounding box area (assumes they are the closest target)
            target = max(persons, key=lambda p: p.bbox_width * p.bbox_height)
            
            # Calculate horizontal error (-0.5 to +0.5)
            # < 0 means person is on the left. > 0 means person is on the right.
            error_x = target.norm_cx - 0.5 
            
            if time.time() - last_print > 0.5:
                print(f"[{time.time():.2f}] Tracking (Conf:{target.confidence:.2f} ErrX:{error_x:+.2f} Turning:{is_turning})")
                last_print = time.time()

            # Calculate turn speed based on error (Proportional controller)
            turn_effort = error_x * KP_TURN

            # Determine direction strings from sign of turn_effort
            left_dir  = 'F' if turn_effort >= 0 else 'B'
            right_dir = 'B' if turn_effort >= 0 else 'F'

            # Clamp speed between MIN and MAX
            speed = min(max(abs(turn_effort), MIN_SPEED), MAX_SPEED)

            # ── Hysteresis deadzone ───────────────────────────────────────────
            # Prevents flickering when the error hovers right at the threshold.
            # If stopped: only start turning when error is large enough (DEADZONE_START).
            # If turning: keep turning until error is small enough (DEADZONE_STOP).
            if is_turning:
                if abs(error_x) < DEADZONE_STOP:
                    is_turning = False
                    send_motor_cmd(ser, 0, 'F', 0, 'F')
                else:
                    send_motor_cmd(ser, speed, left_dir, speed, right_dir)
            else:
                if abs(error_x) > DEADZONE_START:
                    is_turning = True
                    send_motor_cmd(ser, speed, left_dir, speed, right_dir)
                else:
                    send_motor_cmd(ser, 0, 'F', 0, 'F')

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if ser:
            send_motor_cmd(ser, 0, 'F', 0, 'F')  # Hard stop
            ser.close()
        cap.release()
        print("Safely shut down.")

if __name__ == "__main__":
    main()

