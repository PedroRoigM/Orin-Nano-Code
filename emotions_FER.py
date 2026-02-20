import cv2
from jetcam.csi_camera import CSICamera
from fer import FER

# Initialize FER detector
detector = FER(mtcnn=True)

# Open the camera (CSI Camera)
cap = CSICamera(capture_device=0, width=640, height=480)

# Get the video frame size and frame rate
frame_width = 640
frame_height = 480
fps = 30

# Define the codec and create a VideoWriter object
output_path = "/home/jetson/ultralytics/ultralytics/output/01.emotion_detection.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

# Loop through the video frames
while True:
    # Read a frame from the camera
    frame = cap.read()

    if frame is not None:
        # Detect emotions
        result = detector.detect_emotions(frame)
        
        # Process each detected face
        for face in result:
            # Get bounding box
            (x, y, w, h) = face["box"]
            emotions = face["emotions"]
            
            # Get dominant emotion
            emotion = max(emotions, key=emotions.get)
            confidence = emotions[emotion]
            
            # Draw rectangle around face
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            # Draw dominant emotion text
            label = f"{emotion}: {confidence:.2f}"
            cv2.putText(frame, label, (x, y-10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            # Optional: Draw all emotions on the side
            y_offset = y + h + 20
            for em, score in emotions.items():
                text = f"{em}: {score:.2f}"
                cv2.putText(frame, text, (x, y_offset), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                y_offset += 15

        # Write the annotated frame to the output video file
        out.write(frame)

        # Display the annotated frame
        cv2.imshow("Emotion Detection", cv2.resize(frame, (640, 480)))

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
