from ultralytics import YOLO
import cv2
from jetcam.csi_camera import CSICamera
from port import Port
from servo_controller import ServoController
import random
from time import time

# Load model
model = YOLO('yolov8n.pt')

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

# Initialize servo positions
prev_y_pos, prev_x_pos = 127, 127
init_time = time()
new_pos_time = 2
move_command = 75
servoController = ServoController()

# Loop through the video frames
while True:
    frame = cap.read()
    if frame is not None:
        # Random servo movement every new_pos_time seconds
        if time() >= init_time + new_pos_time:
            x_serv_pos = int(random.random() * 255)
            y_serv_pos = int(random.random() * 255)

            # Check if movement is large - fixed the y comparison bug
            if abs(x_serv_pos - prev_x_pos) > 70 and abs(y_serv_pos - prev_y_pos) > 70:
                move_command = 83
            else:
                move_command = 75

            servoController.moveServoFast(0, 3, x_serv_pos)
            servoController.moveServoFast(0, 2, y_serv_pos)
            init_time = time()
            prev_x_pos = x_serv_pos
            prev_y_pos = y_serv_pos

        # Run YOLO detection
        results = model(frame, conf=0.8, verbose=False, device=0)
        face_number = 0
        
        # Process each detected face
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get bounding box coordinates (x1, y1, x2, y2)
                b = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = b

                # Calculate face dimensions
                w = x2 - x1
                h = y2 - y1

                # Calculate center of face for servo control
                center_x = int((x1 + x2) / 2)
                center_y = int((y1 + y2) / 2)
                print(center_x, center_y)
                # Control servos with first detected face
                if face_number == 0:
                    servoController.moveServoFast(0, 0, center_x)  # Send x position of face
                    servoController.moveServoFast(0, 1, center_y)  # Send y position of face
                
                face_number += 1

                # Draw rectangle around face
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                # Draw face info
                label = f"Face: {w}x{h}"
                cv2.putText(frame, label, (x1, y1-10),
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
