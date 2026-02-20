import cv2
from jetcam.csi_camera import CSICamera
from transformers import pipeline
import torch
from port import Port
from PIL import Image
# Load emotion detection model from Hugging Face
# Using GPU if available (important for Jetson)
device = 0 if torch.cuda.is_available() else -1
emotion_classifier = pipeline(
    "image-classification",
    model="trpakov/vit-face-expression",
    device=device
)

# Load face detector (Haar Cascade)
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Open the camera (CSI Camera)
cap = CSICamera(capture_device=0, width=640, height=480)

# Get the video frame size and frame rate
frame_width = 640
frame_height = 480
fps = 12
move_frames = 30
step_frames = 0

# Define the codec and create a VideoWriter object to output the processed video
output_path = "/home/jetson/ultralytics/ultralytics/output/01.emotion_detection.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

# Initialize serial port communication
port = Port()


# Loop through the video frames
while True:
    # Read a frame from the camera
    frame = cap.read()

    if frame is not None:
        # Convert to RGB for Hugging Face model
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        # Process each detected face
        for (x, y, w, h) in faces:
            # Extract face region
            face_roi = frame_rgb[y:y+h, x:x+w]
            face_rgb = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
            face_pil = Image.fromarray(face_rgb)
            # Classify emotion
            emotion_results = emotion_classifier(face_pil)
            emotion = emotion_results[0]['label']
            confidence = emotion_results[0]['score']

            x_servo = int(((1028 - x - (w / 2)) / 1028) * 255)
            y_servo = int(((y + (h/2)) / 720) * 255)

            print(x_servo, y_servo)


            # Command: comando nodo todos nServo posicion
            port.send_data([75, 1, 0, 0, x_servo]) # Send x position of face
            port.send_data([75, 1, 0, 1, y_servo]) # Send y position of face
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Draw emotion text
            label = f"{emotion}: {confidence:.2f}"
            cv2.putText(frame, label, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # Write the annotated frame to the output video file
        out.write(frame)

        # Display the annotated frame
        cv2.imshow("Emotion Detection", cv2.resize(frame, (640, 480)))

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
