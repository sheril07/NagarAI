import cv2
import numpy as np


def assess_image_quality(image_path):

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Could not read the image.")

    height, width = image.shape[:2]

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # Blur
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()

    if blur_score < 50:
        blur_status = "poor"
    elif blur_score < 100:
        blur_status = "moderate"
    else:
        blur_status = "good"

    # Brightness
    brightness_score = np.mean(gray)

    if brightness_score < 50:
        brightness_status = "too_dark"
    elif brightness_score > 200:
        brightness_status = "too_bright"
    else:
        brightness_status = "good"

    # Contrast
    contrast_score = np.std(gray)

    if contrast_score < 30:
        contrast_status = "poor"
    elif contrast_score < 50:
        contrast_status = "moderate"
    else:
        contrast_status = "good"

    # Resolution
    if width < 300 or height < 300:
        resolution_status = "low"
    elif width < 640 or height < 480:
        resolution_status = "moderate"
    else:
        resolution_status = "good"

    # Decide what preprocessing is needed
    operations = []

    if blur_status == "poor":
        operations.append("sharpen")

    if brightness_status == "too_dark":
        operations.append("brightness_correction")

    elif brightness_status == "too_bright":
        operations.append("brightness_correction")

    if contrast_status == "poor":
        operations.append("contrast_enhancement")

    preprocessing_required = len(operations) > 0

    return {
        "resolution": {
            "width": width,
            "height": height,
            "status": resolution_status
        },
        "blur": {
            "score": round(blur_score, 2),
            "status": blur_status
        },
        "brightness": {
            "score": round(float(brightness_score), 2),
            "status": brightness_status
        },
        "contrast": {
            "score": round(float(contrast_score), 2),
            "status": contrast_status
        },
        "preprocessing_required": preprocessing_required,
        "operations": operations
    }