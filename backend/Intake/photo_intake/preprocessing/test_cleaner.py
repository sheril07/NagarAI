import cv2
from image_cleaner import clean_image

image = clean_image(
    "photo_intake/input/sample_images/test_image.jpg"
)

print("Image loaded successfully!")
print("Image shape:", image.shape)

cv2.imwrite(
    "photo_intake/input/sample_images/cleaned_test.jpg",
    image
)

print("Cleaned image saved successfully!")