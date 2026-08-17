def extract_features(detections):

    features = {
        "size": None,
        "people_affected": "unknown",
        "public_safety_risk": False
    }

    objects = [item["object"] for item in detections]

    # Basic example
    if "person" in objects:
        features["people_affected"] = "medium"

    # Road-related hazards
    if "car" in objects or "truck" in objects:
        features["public_safety_risk"] = True

    return features