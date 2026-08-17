import cv2
from yolo_detector import detect_objects

image = cv2.imread("../input/sample_images/test_image.jpg")

if image is None:
    print("ERROR: Image not found")
    exit()

print("Image loaded successfully!")

detections = detect_objects(image)

print("\nYOLO Results:")

if not detections:
    print("No objects detected.")
else:
    for detection in detections:
        print("Object:", detection["object"])