from ultralytics import YOLO

model = YOLO("yolo11n.pt")


def detect_objects(image):
    results = model(image)

    detections = []

    for result in results:
        for box in result.boxes:
            class_id = int(box.cls[0])
            class_name = model.names[class_id]

            detections.append({
                "object": class_name
            })

    return detections