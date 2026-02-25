import cv2
from jetcam.csi_camera import CSICamera
from port import Port
from servo_controller import ServoController
import random
from time import time
import torch
from facenet_pytorch import MTCNN

# ==============================
# CONFIGURATION
# ==============================

receiver_ip = "192.168.1.100"   # <-- CHANGE THIS
receiver_port = 5000

frame_width = 640
frame_height = 480
fps = 30

# ==============================
# INITIALIZE FACE DETECTOR
# ==============================

device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

mtcnn = MTCNN(
    keep_all=True,
    device=device,
    min_face_size=40,
    thresholds=[0.6, 0.7, 0.7]
)

# ==============================
# CAMERA SETUP
# ==============================

cap = CSICamera(
    capture_device=0,
    width=frame_width,
    height=frame_height
)

# ==============================
# GStreamer UDP Streaming Pipeline
# Uses Jetson hardware encoder
# ==============================

gst_out = (
    "appsrc ! "
    "videoconvert ! "
    "video/x-raw,format=I420 ! "
    "nvv4l2h264enc bitrate=4000000 insert-sps-pps=true ! "
    "h264parse ! "
    "rtph264pay config-interval=1 pt=96 ! "
    f"udpsink host={receiver_ip} port={receiver_port} sync=false"
)

out = cv2.VideoWriter(
    gst_out,
    cv2.CAP_GSTREAMER,
    0,
    fps,
    (frame_width, frame_height),
    True
)

if not out.isOpened():
    print("Failed to open GStreamer pipeline")
    exit()

# ==============================
# SERVO + SERIAL INIT
# ==============================

port = Port()
servoController = ServoController()

prev_person_position_x = 127
prev_person_position_y = 127
prev_y_pos = 127
prev_x_pos = 127

init_time = time()
new_pos_time = 2
move_command = 75

new_prediction_time = 1
last_prediction_time = time() - 1

print("Streaming started...")

# ==============================
# MAIN LOOP
# ==============================

while True:

    frame = cap.read()

    if frame is None:
        print("No frame received.")
        break

    frame = cv2.flip(frame, 1)

    # --------------------------
    # RANDOM SERVO MOVEMENT
    # --------------------------
    if time() >= init_time + new_pos_time:
        x_serv_pos = int(random.random() * 255)
        y_serv_pos = int(random.random() * 255)

        if abs(x_serv_pos - prev_x_pos) > 70 and abs(y_serv_pos - prev_y_pos) > 70:
            move_command = 83
        else:
            move_command = 75

        servoController.moveServoFast(0, 3, x_serv_pos)
        servoController.moveServoFast(0, 2, y_serv_pos)

        init_time = time()
        prev_x_pos = x_serv_pos
        prev_y_pos = y_serv_pos

    # --------------------------
    # FACE DETECTION
    # --------------------------
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    if last_prediction_time <= time() + new_prediction_time:
        boxes, probs = mtcnn.detect(rgb_frame)
        last_prediction_time = time()

    face_number = 0

    if boxes is not None:
        for i, box in enumerate(boxes):
            if probs[i] > 0.90:

                x1, y1, x2, y2 = box.astype(int)

                x1 = max(0, x1)
                y1 = max(0, y1)
                x2 = min(frame_width, x2)
                y2 = min(frame_height, y2)

                w = x2 - x1
                h = y2 - y1

                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)

                if face_number == 0:
                    servo_x = int((center_x / frame_width) * 255)
                    servo_y = int((center_y / frame_height) * 255)

                    if abs(prev_person_position_x - servo_x) > 50 or abs(prev_person_position_y - servo_y) > 50:
                        servoController.moveServoFast(0, 0, servo_x)
                        servoController.moveServoFast(0, 1, servo_y)
                    else:
                        servoController.moveServoSlow(0, 0, servo_x)
                        servoController.moveServoSlow(0, 1, servo_y)

                    prev_person_position_x = servo_x
                    prev_person_position_y = servo_y

                face_number += 1

                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                label = f"Face {face_number}: {w}x{h} ({probs[i]:.2f})"
                cv2.putText(frame, label, (x1, y1 - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (0, 255, 0), 2)

    # --------------------------
    # STREAM FRAME
    # --------------------------
    out.write(frame)

# ==============================
# CLEANUP
# ==============================

cap.release()
out.release()

print("Streaming stopped.")