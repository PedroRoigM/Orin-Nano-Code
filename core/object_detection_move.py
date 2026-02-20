import cv2
from jetcam.csi_camera import CSICamera
from port import Port
from servo_controller import ServoController
import random
from time import time
# Load face detector (Haar Cascade)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Open the camera (CSI Camera)
cap = CSICamera(capture_device=0, width=640, height=480)

# Get the video frame size and frame rate
frame_width = 640
frame_height = 480
fps = 12

# Define the codec and create a VideoWriter object to output the processed video
output_path = "/home/jetson/ultralytics/ultralytics/output/01.face_detection.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

# Initialize serial port communication
port = Port()

# Initialize second servo position
prev_y_pos, prev_x_pos = 127, 127
init_time = time()
new_pos_time = 2
move_command = 75
servoController = ServoController()

# Loop through the video frames
while True:
	# Read a frame from the camera
	frame = cap.read()

	if frame is not None:
		# Detect faces
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		faces = face_cascade.detectMultiScale(
			gray, 
			scaleFactor=1.1, 
			minNeighbors=5, 
			minSize=(30, 30)
		)
		if time() >= init_time + new_pos_time:
			x_serv_pos = int(random.random() * 255)
			y_serv_pos = int(random.random() * 255)

			if abs(x_serv_pos - prev_x_pos) > 70 and abs(y_serv_pos - prev_x_pos) > 70:
				move_command = 83
			else:
				move_command = 75

			servoController.moveServoFast(0, 3, x_serv_pos)
			servoController.moveServoFast(0, 2, y_serv_pos)
			init_time = time()
			prev_x_pos = x_serv_pos
			prev_y_pos = y_serv_pos

		face_number = 0

		# Process each detected face
		for (x, y, w, h) in faces:
			# Calculate servo positions
			x_servo = int(((frame_width - x - (w / 2)) / frame_width) * 255)
			y_servo = int(((y + (h / 2)) / frame_height) * 255)
			if face_number == 0:
				# Command: comando nodo todos nServo posicion
				servoController.moveServoFast(0, 0, x_servo)  # Send x position of face
				servoController.moveServoFast(0, 1, y_servo)  # Send y position of face
			face_number = face_number + 1
			# Draw rectangle around face
			cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)

			# Draw face info
			label = f"Face: {w}x{h}"
			cv2.putText(frame, label, (x, y-10),
				cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

		# Write the annotated frame to the output video file
		out.write(frame)

		# Display the annotated frame
		cv2.imshow("Face Detection", cv2.resize(frame, (640, 480)))

		# Break the loop if 'q' is pressed
		if cv2.waitKey(1) & 0xFF == ord("q"):
			break
	else:
		# Break the loop if no frame is received
		print("No frame received, breaking the loop.")
		break

# Release the video capture and writer objects, and close the display window
cap.release()
out.release()
cv2.destroyAllWindows()
