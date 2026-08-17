import cv2

from preprocessing.image_quality import assess_image_quality
from preprocessing.image_cleaner import clean_image
from detection.clip_classifier import classify_image
from description.description_generator import generate_description
from severity.feature_extractor import extract_features
from output.json_formatter import create_output, save_json


# ==========================================
# PATHS
# ==========================================

IMAGE_PATH = "photo_intake/input/sample_images/test_image.jpg"

OUTPUT_PATH = "photo_intake/output/complaint.json"


# ==========================================
# MAIN PIPELINE
# ==========================================

def main():

    print("\n===================================")
    print("       PHOTO COMPLAINT SYSTEM")
    print("===================================")


    # --------------------------------------
    # 1. IMAGE QUALITY CHECK
    # --------------------------------------

    print("\n[1] Checking image quality...")

    quality = assess_image_quality(IMAGE_PATH)

    print("Blur:", quality["blur"]["status"])
    print("Brightness:", quality["brightness"]["status"])
    print("Contrast:", quality["contrast"]["status"])
    print("Resolution:", quality["resolution"]["status"])


    # --------------------------------------
    # 2. CONDITIONAL PREPROCESSING
    # --------------------------------------

    if quality["preprocessing_required"]:

        print("\n[2] Preprocessing required")
        print("Operations:", quality["operations"])

        image = clean_image(
            IMAGE_PATH,
            quality["operations"]
        )

    else:

        print("\n[2] Image quality is good")
        print("Using original image")

        image = cv2.imread(IMAGE_PATH)


    # --------------------------------------
    # 3. SAVE TEMPORARY IMAGE
    # --------------------------------------
    # CLIP currently accepts an image path,
    # so save the processed image temporarily.

    TEMP_IMAGE = "photo_intake/input/sample_images/processed_test.jpg"

    cv2.imwrite(TEMP_IMAGE, image)


    # --------------------------------------
    # 4. CLIP CLASSIFICATION
    # --------------------------------------

    print("\n[3] Running CLIP classification...")

    category, issue = classify_image(
        TEMP_IMAGE
    )

    print("Category:", category)
    print("Issue:", issue)


    # --------------------------------------
    # 5. DESCRIPTION
    # --------------------------------------

    print("\n[4] Generating description...")

    description = generate_description(
        category,
        issue
    )

    print("Description:", description)


    # --------------------------------------
    # 6. SEVERITY FEATURES
    # --------------------------------------

    print("\n[5] Extracting severity features...")

    # Currently no YOLO detections are being used.
    # This will be expanded later.

    detections = []

    severity_features = extract_features(
        detections
    )

    print("Severity Features:", severity_features)


    # --------------------------------------
    # 7. CREATE JSON
    # --------------------------------------

    print("\n[6] Creating JSON...")

    output = create_output(
        category=category,
        issue=issue,
        description=description,
        severity_features=severity_features
    )


    # --------------------------------------
    # 8. SAVE JSON
    # --------------------------------------

    save_json(
        output,
        OUTPUT_PATH
    )


    # --------------------------------------
    # DONE
    # --------------------------------------

    print("\n===================================")
    print("       PROCESSING COMPLETE")
    print("===================================")


if __name__ == "__main__":
    main()