import cv2


def clean_image(image_path, operations):

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError("Could not read the image.")

    for operation in operations:

        if operation == "sharpen":

            kernel = (
                cv2.getStructuringElement(
                    cv2.MORPH_RECT,
                    (3, 3)
                )
            )

            blurred = cv2.GaussianBlur(image, (3, 3), 0)

            image = cv2.addWeighted(
                image,
                1.5,
                blurred,
                -0.5,
                0
            )

        elif operation == "brightness_correction":

            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

            l, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(
                clipLimit=2.0,
                tileGridSize=(8, 8)
            )

            l = clahe.apply(l)

            lab = cv2.merge((l, a, b))

            image = cv2.cvtColor(
                lab,
                cv2.COLOR_LAB2BGR
            )

        elif operation == "contrast_enhancement":

            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)

            l, a, b = cv2.split(lab)

            clahe = cv2.createCLAHE(
                clipLimit=2.0,
                tileGridSize=(8, 8)
            )

            l = clahe.apply(l)

            lab = cv2.merge((l, a, b))

            image = cv2.cvtColor(
                lab,
                cv2.COLOR_LAB2BGR
            )

    return image