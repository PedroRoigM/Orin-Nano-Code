import cv2
from jetcam.csi_camera import CSICamera
from port import Port
from servo_controller import ServoController
import random
from time import time

from typing import Tuple, Union
import numpy as np
import math
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision


MARGIN = 10  # pixels
ROW_SIZE = 10  # pixels
FONT_SIZE = 1
FONT_THICKNESS = 1
TEXT_COLOR = (255, 0, 0)  # red


def _normalized_to_pixel_coordinates(
    normalized_x: float, normalized_y: float, image_width: int, image_height: int
) -> Union[None, Tuple[int, int]]:
    """Converts normalized value pair to pixel coordinates."""

    # Checks if the float value is between 0 and 1.
    def is_valid_normalized_value(value: float) -> bool:
        return (value > 0 or math.isclose(0, value)) and (
            value < 1 or math.isclose(1, value)
        )

    if not (
        is_valid_normalized_value(normalized_x)
        and is_valid_normalized_value(normalized_y)
    ):
        # TODO: Draw coordinates even if it's outside of the image bounds.
        return None
    x_px = min(math.floor(normalized_x * image_width), image_width - 1)
    y_px = min(math.floor(normalized_y * image_height), image_height - 1)
    return x_px, y_px


def visualize(image, detection_result) -> np.ndarray:
    """Draws bounding boxes and keypoints on the input image and return it.
    Args:
      image: The input RGB image.
      detection_result: The list of all "Detection" entities to be visualize.
    Returns:
      Image with bounding boxes.
    """
    annotated_image = image.copy()
    height, width, _ = image.shape

    for detection in detection_result.detections:
        # Draw bounding_box
        bbox = detection.bounding_box
        start_point = bbox.origin_x, bbox.origin_y
        end_point = bbox.origin_x + bbox.width, bbox.origin_y + bbox.height
        cv2.rectangle(annotated_image, start_point, end_point, TEXT_COLOR, 3)

        # Draw keypoints
        for keypoint in detection.keypoints:
            keypoint_px = _normalized_to_pixel_coordinates(
                keypoint.x, keypoint.y, width, height
            )
            color, thickness, radius = (0, 255, 0), 2, 2
            cv2.circle(annotated_image, keypoint_px, thickness, color, radius)

        # Draw label and score
        category = detection.categories[0]
        category_name = category.category_name
        category_name = "" if category_name is None else category_name
        probability = round(category.score, 2)
        result_text = category_name + " (" + str(probability) + ")"
        text_location = (MARGIN + bbox.origin_x, MARGIN + ROW_SIZE + bbox.origin_y)
        cv2.putText(
            annotated_image,
            result_text,
            text_location,
            cv2.FONT_HERSHEY_PLAIN,
            FONT_SIZE,
            TEXT_COLOR,
            FONT_THICKNESS,
        )

    return annotated_image


# Initialize MediaPipe face detector
base_options = python.BaseOptions(model_asset_path="detector.tflite")
options = vision.FaceDetectorOptions(base_options=base_options)
face_detector = vision.FaceDetector.create_from_options(options)

# Open the camera (CSI Camera)
cap = CSICamera(capture_device=0, width=640, height=480)

# Get the video frame size and frame rate
frame_width = 640
frame_height = 480
fps = 1

# Define the codec and create a VideoWriter object
output_path = "/home/jetson/ultralytics/ultralytics/output/01.face_detection.mp4"
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
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

        # Convert frame to MediaPipe Image
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)

        # Detect faces
        detection_result = face_detector.detect(mp_image)

        face_number = 0

        # Process detected faces
        if detection_result.detections is not None:
            for i, detection in enumerate(detection_result.detections):
                if detection.categories[0].score > 0.90:  # Confidence threshold
                    bbox = detection.bounding_box
                    x1 = bbox.origin_x
                    y1 = bbox.origin_y
                    x2 = x1 + bbox.width
                    y2 = y1 + bbox.height

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

                        servoController.moveServoFast(0, 0, servo_x)
                        servoController.moveServoFast(0, 1, servo_y)

                    face_number += 1

                    # Draw rectangle around face
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                    # Draw face info with confidence
                    score = detection.categories[0].score
                    label = f"Face {face_number}: {w}x{h} ({score:.2f})"
                    cv2.putText(
                        frame,
                        label,
                        (x1, y1 - 10),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        (0, 255, 0),
                        2,
                    )
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
