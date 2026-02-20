import cv2
from jetcam.csi_camera import CSICamera
from deepface import DeepFace

# Open the camera (CSI Camera)
cap = CSICamera(capture_device=0, width=640, height=480)

# Get the video frame size and frame rate
frame_width = 640
frame_height = 480
fps = 30

# Define the codec and create a VideoWriter object to output the processed video
output_path = "/home/jetson/ultralytics/ultralytics/output/01.emotion_detection.mp4"
fourcc = cv2.VideoWriter_fourcc(*'mp4v')
out = cv2.VideoWriter(output_path, fourcc, fps, (frame_width, frame_height))

# Loop through the video frames
while True:
    # Read a frame from the camera
    frame = cap.read()

    if frame is not None:
        try:
            # Analyze emotions with DeepFace
            result = DeepFace.analyze(
                frame, 
                actions=['emotion'], 
                enforce_detection=False,
                detector_backend='opencv',
                silent=True
            )
            
            # DeepFace puede retornar una lista o un dict
            if isinstance(result, dict):
                result = [result]
            
            # Process each detected face
            for face in result:
                # Get bounding box
                region = face['region']
                x, y, w, h = region['x'], region['y'], region['w'], region['h']
                
                # Get dominant emotion
                emotion = face['dominant_emotion']
                
                # Get all emotions with scores
                emotions = face['emotion']
                confidence = emotions[emotion]
                
                # Draw rectangle around face
                cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
                
                # Draw dominant emotion text
                label = f"{emotion}: {confidence:.2f}%"
                cv2.putText(frame, label, (x, y-10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                
                # Optional: Draw all emotions on the side
                y_offset = y + 20
                for em, score in emotions.items():
                    text = f"{em}: {score:.1f}%"
                    cv2.putText(frame, text, (x, y_offset), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)
                    y_offset += 15
        
        except Exception as e:
            # If no face is detected or any error occurs, just continue
            print(f"Error: {e}")
            pass

        # Write the annotated frame to the output video file
        out.write(frame)

        # Display the annotated frame
        cv2.imshow("DeepFace Emotion Detection", cv2.resize(frame, (640, 480)))

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
