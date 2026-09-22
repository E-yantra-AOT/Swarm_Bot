"""
swarm_tracker_stream.py
=======================
Combined script that:
  1. Runs YOLO person tracking and sends motor commands to the Arduino.
  2. Streams the annotated camera feed (with bounding boxes + HUD) over HTTP at port 5000.
  3. Prints live motor commands to the terminal.

Open http://<robot-ip>:5000 in your browser to watch what the robot is "seeing" and "deciding".
"""
import sys
import os
import time
import threading
import cv2
import serial
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# Add shared module to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "shared"))
from yolo_ncnn import YoloNcnn

# ─── Configuration ────────────────────────────────────────────────────────────
ARDUINO_PORT   = '/dev/ttyUSB1'
BAUD_RATE      = 115200
STREAM_PORT    = 5000

# Motor tuning
KP_TURN        = 250    # Proportional gain for turning
MAX_SPEED      = 120    # Max PWM speed (0-255)
MIN_SPEED      = 55     # Minimum speed to overcome ground friction
DEADZONE       = 0.08   # Ignore errors smaller than this (fraction of frame width)

# Inversion flags — flip if one wheel spins backward
INVERT_RIGHT_MOTOR = True
INVERT_LEFT_MOTOR  = False

# ─── Global shared frame (written by tracker, read by streamer) ───────────────
latest_frame = None
frame_lock   = threading.Lock()

# ─── Motor / Serial ───────────────────────────────────────────────────────────
def init_serial():
    try:
        ser = serial.Serial(ARDUINO_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"[Serial] Arduino connected on {ARDUINO_PORT}")
        return ser
    except Exception as e:
        print(f"[Serial] WARN: Could not connect to Arduino: {e}")
        return None

def send_motor_cmd(ser, left_spd, left_dir, right_spd, right_dir):
    if INVERT_LEFT_MOTOR:
        left_dir  = 'B' if left_dir  == 'F' else 'F'
    if INVERT_RIGHT_MOTOR:
        right_dir = 'B' if right_dir == 'F' else 'F'
    cmd = f"M,{int(left_spd)},{left_dir},{int(right_spd)},{right_dir}\n"
    if ser:
        ser.write(cmd.encode('ascii'))
    return cmd.strip()

# ─── MJPEG HTTP Stream ────────────────────────────────────────────────────────
class StreamHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass  # Silence HTTP access logs

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'multipart/x-mixed-replace; boundary=frame')
            self.end_headers()
            while True:
                with frame_lock:
                    frame = latest_frame
                if frame is None:
                    time.sleep(0.05)
                    continue
                ret, jpg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 70])
                if not ret:
                    continue
                try:
                    self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n')
                    self.wfile.write(jpg.tobytes())
                    self.wfile.write(b'\r\n')
                except Exception:
                    break
        else:
            self.send_response(404)
            self.end_headers()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

def start_stream_server():
    server = ThreadedHTTPServer(('0.0.0.0', STREAM_PORT), StreamHandler)
    print(f"[Stream] Live feed at http://0.0.0.0:{STREAM_PORT}")
    server.serve_forever()

# ─── Main Tracking Loop ───────────────────────────────────────────────────────
def main():
    global latest_frame

    ser = init_serial()

    print("[YOLO] Loading model (1 thread for power safety)...")
    yolo = YoloNcnn(
        model_dir=os.path.expanduser('~/yolo11n_ncnn_model'),
        input_size=320,
        num_threads=1
    )

    cap = cv2.VideoCapture('/dev/video0')
    if not cap.isOpened():
        print("[Camera] /dev/video0 failed, trying index 0...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            print("[Camera] FATAL: No camera found.")
            sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  320)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    # Start the HTTP stream server in a background thread
    t = threading.Thread(target=start_stream_server, daemon=True)
    t.start()

    print("\n" + "="*50)
    print("  TRACKER + STREAM ACTIVE")
    print(f"  Open http://<robot-ip>:{STREAM_PORT} in browser")
    print("  Press Ctrl+C to stop.")
    print("="*50 + "\n")

    last_print = 0
    frame_h, frame_w = 240, 320
    cx_frame = frame_w // 2  # Horizontal centre of camera frame

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                time.sleep(0.05)
                continue

            frame_h, frame_w = frame.shape[:2]
            cx_frame = frame_w // 2

            detections = yolo.detect(frame)
            persons    = [d for d in detections if d.class_id == 0]

            # ── Draw all detections ──────────────────────────────────────────
            for d in detections:
                color = (0, 255, 0) if d.class_id == 0 else (200, 200, 200)
                cv2.rectangle(frame,
                              (int(d.bbox_x1), int(d.bbox_y1)),
                              (int(d.bbox_x2), int(d.bbox_y2)),
                              color, 2)
                label = f"{d.class_name} {d.confidence:.2f}"
                cv2.putText(frame, label,
                            (int(d.bbox_x1), int(d.bbox_y1) - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

            # Draw centre line
            cv2.line(frame, (cx_frame, 0), (cx_frame, frame_h), (100, 100, 255), 1)

            # ── Decide motor command ─────────────────────────────────────────
            if len(persons) == 0:
                cmd_str = send_motor_cmd(ser, 0, 'F', 0, 'F')
                status_text  = "NO TARGET — STOPPED"
                status_color = (0, 0, 255)
                error_x      = 0.0
                if time.time() - last_print > 1.0:
                    print(f"[{time.strftime('%H:%M:%S')}] No person → {cmd_str}")
                    last_print = time.time()
            else:
                target  = max(persons, key=lambda p: p.bbox_width * p.bbox_height)
                error_x = target.norm_cx - 0.5
                # Draw target highlight
                cv2.rectangle(frame,
                              (int(target.bbox_x1), int(target.bbox_y1)),
                              (int(target.bbox_x2), int(target.bbox_y2)),
                              (0, 255, 128), 3)
                # Draw target centre dot
                tx = int(target.norm_cx * frame_w)
                ty = int(target.norm_cy * frame_h)
                cv2.circle(frame, (tx, ty), 5, (0, 255, 128), -1)
                # Draw error arrow from frame centre to target
                cv2.arrowedLine(frame, (cx_frame, frame_h//2), (tx, frame_h//2),
                                (255, 200, 0), 2, tipLength=0.3)

                if abs(error_x) < DEADZONE:
                    cmd_str = send_motor_cmd(ser, 0, 'F', 0, 'F')
                    status_text  = f"CENTERED  err={error_x:+.2f}"
                    status_color = (0, 220, 0)
                else:
                    turn  = error_x * KP_TURN
                    l_spd = min(max(abs(turn), MIN_SPEED), MAX_SPEED)
                    r_spd = l_spd
                    l_dir = 'F' if turn >= 0 else 'B'
                    r_dir = 'B' if turn >= 0 else 'F'
                    cmd_str = send_motor_cmd(ser, l_spd, l_dir, r_spd, r_dir)
                    direction    = "TURN RIGHT" if error_x > 0 else "TURN LEFT"
                    status_text  = f"{direction}  err={error_x:+.2f}  spd={int(l_spd)}"
                    status_color = (0, 180, 255)

                if time.time() - last_print > 0.25:
                    print(f"[{time.strftime('%H:%M:%S')}] {status_text} → {cmd_str}")
                    last_print = time.time()

            # ── HUD overlay ──────────────────────────────────────────────────
            cv2.rectangle(frame, (0, 0), (frame_w, 22), (0, 0, 0), -1)
            cv2.putText(frame, status_text, (4, 15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, status_color, 1)

            # ── Push annotated frame to stream ───────────────────────────────
            with frame_lock:
                latest_frame = frame.copy()

    except KeyboardInterrupt:
        print("\n[Ctrl+C] Stopping...")
    finally:
        send_motor_cmd(ser, 0, 'F', 0, 'F')
        if ser:
            ser.close()
        cap.release()
        print("[Done] Motors stopped. Camera released.")

if __name__ == "__main__":
    main()
