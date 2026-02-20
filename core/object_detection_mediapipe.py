import cv2
from jetcam.csi_camera import CSICamera
from port import Port
from servo_controller import ServoController
import random
from time import time
import mediapipe as mp

# Initialize MediaPipe Face Detection
mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

# Open the camera (CSI Camera)
cap = CSICamera(capture_device=0, width=640, height=480)

# Get the video frame size and frame rate
frame_width = 640
frame_height = 480
fps = 12

# Define the codec and create a VideoWriter object
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

# Initialize MediaPipe Face Detection
# model_selection: 0 for short-range (2m), 1 for full-range (5m)
# min_detection_confidence: 0.5 is default, increase for fewer false positives
with mp_face_detection.FaceDetection(
    model_selection=1,
    min_detection_confidence=0.5) as face_detection:
    
    # Loop through the video frames
    while True:
        frame = cap.read()
        if frame is not None:
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

            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Process the frame for face detection
            results = face_detection.process(rgb_frame)
            
            face_number = 0
            
            # Process detected faces
            if results.detections:
                for detection in results.detections:
                    # Get bounding box
                    bboxC = detection.location_data.relative_bounding_box
                    ih, iw, _ = frame.shape
                    
                    # Convert relative coordinates to pixel coordinates
                    x1 = int(bboxC.xmin * iw)
                    y1 = int(bboxC.ymin * ih)
                    w = int(bboxC.width * iw)
                    h = int(bboxC.height * ih)
                    x2 = x1 + w
                    y2 = y1 + h
                    
                    # Ensure coordinates are within frame bounds
                    x1 = max(0, x1)
                    y1 = max(0, y1)
                    x2 = min(iw, x2)
                    y2 = min(ih, y2)
                    
                    # Calculate center of face for servo control
                    center_x = int((x1 + x2) / 2)
                    center_y = int((y1 + y2) / 2)
                    
                    # Control servos with first detected face only
                    if face_number == 0:
                        # Map center coordinates to servo range (0-255)
                        servo_x = int((center_x / iw) * 255)
                        servo_y = int((center_y / ih) * 255)
                        
                        servoController.moveServoFast(0, 0, servo_x)
                        servoController.moveServoFast(0, 1, servo_y)
                    
                    face_number += 1
                    
                    # Get confidence score
                    confidence = detection.score[0]
                    
                    # Draw rectangle around face
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw face info with confidence
                    label = f"Face {face_number}: {w}x{h} ({confidence:.2f})"
                    cv2.putText(frame, label, (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                    
                    # Draw facial landmarks (eyes, nose, etc.)
                    mp_drawing.draw_detection(frame, detection)
            
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
