import cv2

gst_in = (
    "udpsrc port=5000 ! "
    "application/x-rtp ! "
    "rtph264depay ! decodebin ! "
    "videoconvert ! appsink"
)

cap = cv2.VideoCapture(gst_in, cv2.CAP_GSTREAMER)

while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow("Stream", frame)
    if cv2.waitKey(1) == ord('q'):
        break