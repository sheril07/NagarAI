import sys

sys.path.append("photo_intake/description")

from clip_classifier import classify_image
from description_generator import generate_description


image_path = "photo_intake/input/sample_images/test_image.jpg"


# STEP 1: CLIP classification
category, issue = classify_image(image_path)


# STEP 2: Generate description
description = generate_description(
    category,
    issue
)


# STEP 3: Display result
print("\nPHOTO ANALYSIS")
print("===================")

print("Category:", category)
print("Issue:", issue)
print("Description:", description)