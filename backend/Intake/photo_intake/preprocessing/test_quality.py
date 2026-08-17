import cv2

from image_quality import assess_image_quality
from image_cleaner import clean_image


image_path = "photo_intake/input/sample_images/test_image.jpg"


# STEP 1: Check image quality
quality = assess_image_quality(image_path)

print("\nIMAGE QUALITY")
print("=============")

print("Resolution:", quality["resolution"])
print("Blur:", quality["blur"])
print("Brightness:", quality["brightness"])
print("Contrast:", quality["contrast"])

print("\nPreprocessing required:",
      quality["preprocessing_required"])

print("Operations:",
      quality["operations"])


# STEP 2: Decide what image to send forward
if quality["preprocessing_required"]:

    print("\nPreprocessing image...")

    image = clean_image(
        image_path,
        quality["operations"]
    )

    cv2.imwrite(
        "../input/sample_images/cleaned_test.jpg",
        image
    )

    print("Cleaned image saved.")

else:

    print("\nImage quality is good.")
    print("Using original image.")

    image = cv2.imread(image_path)


print("\nReady for YOLO!")
print("Final image shape:", image.shape)



