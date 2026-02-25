import cv2
from jetcam.csi_camera import CSICamera
from core.controllers.port import Port
from core.controllers.servo_controller import ServoController
import random
from time import time
import torch
from facenet_pytorch import MTCNN

# Initialize MTCNN face detector (very accurate)
device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')

mtcnn = MTCNN(
    keep_all=True,
    device=device,
    min_face_size=40,
    thresholds=[0.6, 0.7, 0.7]
)

# Open the camera (CSI Camera)
cap = CSICamera(capture_device=0, width=640, height=480)

# Get the video frame size and frame rate
frame_width = 640
frame_height = 480
fps = 1

# Define the codec and create a VideoWriter object
output_path = "/home/jetson/ultralytics/ultralytics/output/01.face_detection.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

# Initialize serial port communication
port = Port()

# Initialize servo positions
prev_person_position_x, prev_person_position_y, prev_y_pos, prev_x_pos = 127, 127, 127, 127
init_time = time()
new_pos_time = 2
move_command = 75
servoController = ServoController()

new_prediction_time = 1
last_prediction_time = time() - 1

# Loop through the video frames
while True:
	frame = cap.read()
	if frame is not None:
		# Flipping the frame
		frame = cv2.flip(frame, 1)

		# Random servo movement
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

		# Convert BGR to RGB for MTCNN
		rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

		# Detect faces
		if last_prediction_time <= time() + new_prediction_time:
			boxes, probs = mtcnn.detect(rgb_frame)
			last_prediction_time = time()
		face_number = 0

		# Process detected faces
		if boxes is not None:
			for i, box in enumerate(boxes):
				if probs[i] > 0.90:  # Confidence threshold
					x1, y1, x2, y2 = box.astype(int)

					# Ensure coordinates are within bounds
					x1 = max(0, x1)
					y1 = max(0, y1)
					x2 = min(frame_width, x2)
					y2 = min(frame_height, y2)

					w = x2 - x1
					h = y2 - y1

					# Calculate center of face for servo control
					center_x = int((x1 + x2) / 2)
					center_y = int((y1 + y2) / 2)

					# Control servos with first detected face only
					if face_number == 0:
						# Map center coordinates to servo range (0-255)
						servo_x = int((center_x / frame_width) * 255)
						servo_y = int((center_y / frame_height) * 255)
						if abs(prev_person_position_x - servo_x) > 50 or abs(prev_person_position_y - servo_y) > 50:
							servoController.moveServoFast(0, 0, servo_x)
							servoController.moveServoFast(0, 1, servo_y)
						else:
							servoController.moveServoSlow(0, 0, servo_x)
							servoController.moveServoSlow(0, 1, servo_y)
					face_number += 1

					# Draw rectangle around face
					cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

					# Draw face info with confidence
					label = f"Face {face_number}: {w}x{h} ({probs[i]:.2f})"
					cv2.putText(frame, label, (x1, y1-10),
					cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
		# Write the annotated frame to the output video file
		out.write(frame)

		# Display the annotated frame
		cv2.imshow("Face Detection", frame)

		# Break the loop if 'q' is pressed
		if cv2.waitKey(1) & 0xFF == ord("q"):
			break
	else:
		print("No frame received, breaking the loop.")
		break

# Release resources
cap.release()
out.release()
cv2.destroyAllWindows()
