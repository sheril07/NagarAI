from math import radians, sin, cos, sqrt, atan2
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from PIL import Image
import torch
import open_clip

import requests
from io import BytesIO

clip_model, _, clip_preprocess = (
    open_clip.create_model_and_transforms(
        "ViT-B-32",
        pretrained="openai"
    )
)

clip_model.eval()

embedding_model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

LOCATION_THRESHOLD_METERS = 50
DUPLICATE_THRESHOLD = 0.70
LOCATION_WEIGHT = 0.40
TEXT_WEIGHT = 0.25
IMAGE_WEIGHT = 0.25
CATEGORY_WEIGHT = 0.10

def calculate_distance(lat1, lng1, lat2, lng2):

    if None in (lat1, lng1, lat2, lng2):
        return None

    # Earth radius in metres
    R = 6371000

    lat1 = radians(float(lat1))
    lat2 = radians(float(lat2))

    delta_lat = radians(
        float(lat2) - float(lat1)
    )

    delta_lng = radians(
        float(lng2) - float(lng1)
    )

    a = (
        sin(delta_lat / 2) ** 2
        +
        cos(lat1)
        * cos(lat2)
        * sin(delta_lng / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


def location_similarity(distance):

    if distance is None:
        return 0.0

    if distance >= LOCATION_THRESHOLD_METERS:
        return 0.0

    return 1 - (
        distance / LOCATION_THRESHOLD_METERS
    )

def text_similarity(text1, text2):

    if not text1 or not text2:
        return 0.0

    text1 = str(text1).lower().strip()
    text2 = str(text2).lower().strip()

    embeddings = embedding_model.encode(
        [text1, text2]
    )

    score = cosine_similarity(
        [embeddings[0]],
        [embeddings[1]]
    )[0][0]

    return round(
        float(score),
        3
    )

def get_image_embedding(image_source):

    if not image_source:
        return None

    try:

        # ----------------------------------------------------
        # If source is a URL, download the image
        # ----------------------------------------------------

        if str(image_source).startswith("http"):

            response = requests.get(
                image_source,
                timeout=10
            )

            response.raise_for_status()

            image = Image.open(
                BytesIO(response.content)
            ).convert("RGB")

        # ----------------------------------------------------
        # Otherwise treat it as a local file path
        # ----------------------------------------------------

        else:

            image = Image.open(
                image_source
            ).convert("RGB")


        # ----------------------------------------------------
        # CLIP preprocessing
        # ----------------------------------------------------

        image = clip_preprocess(
            image
        ).unsqueeze(0)


        # ----------------------------------------------------
        # Generate CLIP embedding
        # ----------------------------------------------------

        with torch.no_grad():

            features = clip_model.encode_image(
                image
            )


        # Normalize embedding

        features /= features.norm(
            dim=-1,
            keepdim=True
        )


        return features.cpu().numpy()[0]


    except Exception as e:

        print(
            "Image embedding error:",
            e
        )

        return None

def image_similarity(
    image_path1,
    image_path2
):

    if not image_path1 or not image_path2:
        return 0.0

    embedding1 = get_image_embedding(
        image_path1
    )

    embedding2 = get_image_embedding(
        image_path2
    )

    if embedding1 is None or embedding2 is None:
        return 0.0

    score = cosine_similarity(
        [embedding1],
        [embedding2]
    )[0][0]

    return round(
        float(score),
        3
    )

def category_similarity(category1, category2):

    if not category1 or not category2:
        return 0.0

    category1 = str(
        category1
    ).lower().strip()

    category2 = str(
        category2
    ).lower().strip()

    if category1 == category2:
        return 1.0

    return 0.0


def calculate_duplicate_score(
    location_score,
    text_score,
    image_score,
    category_score
):

    score = (
        LOCATION_WEIGHT * location_score
        +
        TEXT_WEIGHT * text_score
        +
        IMAGE_WEIGHT * image_score
        +
        CATEGORY_WEIGHT * category_score
    )

    return round(
        score,
        3
    )

def find_duplicate_group(
    supabase,
    complaint_id,
    category,
    description,
    gps_lat,
    gps_lng,
    image_url = None
):

    # ========================================================
    # GPS IS REQUIRED FOR CURRENT DUPLICATE DETECTION
    # ========================================================

    if gps_lat is None or gps_lng is None:

        print(
            "Duplicate detection skipped: "
            "GPS coordinates missing."
        )

        return None


    # ========================================================
    # GET EXISTING COMPLAINTS
    # ========================================================

    try:

        response = (
            supabase
            .table("complaints")
            .select(
                "id, category, description, "
                "gps_lat, gps_lng, cluster_id, image_url"
            )
            .neq("id", complaint_id)
            .execute()
        )

        existing_complaints = (
            response.data or []
        )

    except Exception as e:

        print(
            "Duplicate detection database error:",
            e
        )

        return None


    # ========================================================
    # FIND BEST MATCH
    # ========================================================

    best_match = None
    best_score = 0.0


    for complaint in existing_complaints:

        # Don't compare complaint with itself
        if complaint.get("id") == complaint_id:
            continue


        # ----------------------------------------------------
        # Existing complaint GPS
        # ----------------------------------------------------

        existing_lat = complaint.get(
            "gps_lat"
        )

        existing_lng = complaint.get(
            "gps_lng"
        )


        if (
            existing_lat is None
            or existing_lng is None
        ):
            continue


        # ----------------------------------------------------
        # Calculate GPS distance
        # ----------------------------------------------------

        distance = calculate_distance(
            gps_lat,
            gps_lng,
            existing_lat,
            existing_lng
        )


        # Only consider complaints within 50 metres
        if (
            distance is None
            or distance > LOCATION_THRESHOLD_METERS
        ):
            continue


        location_score = location_similarity(
            distance
        )


        # ----------------------------------------------------
        # Text similarity
        # ----------------------------------------------------

        text_score = text_similarity(
            description,
            complaint.get("description")
        )

        image_score = image_similarity(
            image_url,
            complaint.get("image_url")
        )


        # ----------------------------------------------------
        # Category similarity
        # ----------------------------------------------------

        category_score = category_similarity(
            category,
            complaint.get("category")
        )


        # ----------------------------------------------------
        # Duplicate score
        # ----------------------------------------------------

        score = calculate_duplicate_score(
            location_score,
            text_score,
            image_score,
            category_score
        )


        print(
            f"Checking complaint {complaint['id']} | "
            f"distance={distance:.2f}m | "
            f"location={location_score:.2f} | "
            f"text={text_score:.2f} | "
            f"image={image_score:.2f} | "
            f"category={category_score:.2f} | "
            f"score={score:.2f}"
        )


        # ----------------------------------------------------
        # Keep strongest match
        # ----------------------------------------------------

        if score > best_score:

            best_score = score
            best_match = complaint


    # ========================================================
    # CHECK DUPLICATE THRESHOLD
    # ========================================================

    if (
        best_match
        and best_score >= DUPLICATE_THRESHOLD
    ):

        existing_cluster_id = (
            best_match.get("cluster_id")
        )


        # ----------------------------------------------------
        # Existing complaint already belongs to cluster
        # ----------------------------------------------------

        if existing_cluster_id:

            print(
                f"Duplicate found. "
                f"Existing cluster: "
                f"{existing_cluster_id}"
            )

            return existing_cluster_id


        # ----------------------------------------------------
        # Existing complaint has no cluster yet
        # Create a new cluster for both complaints
        # ----------------------------------------------------

        import uuid

        new_cluster_id = str(
            uuid.uuid4()
        )


        try:

            # Assign cluster to existing complaint

            (
                supabase
                .table("complaints")
                .update({
                    "cluster_id": new_cluster_id
                })
                .eq(
                    "id",
                    best_match["id"]
                )
                .execute()
            )


            print(
                f"Created new cluster: "
                f"{new_cluster_id}"
            )


            return new_cluster_id


        except Exception as e:

            print(
                "Error creating duplicate cluster:",
                e
            )

            return None


    # ========================================================
    # NO DUPLICATE
    # ========================================================

    print(
        "No duplicate found."
    )

    return None

def create_cluster_id():

    import uuid

    return str(
        uuid.uuid4()
    )

def get_people_affected(
    supabase,
    cluster_id
):

    if not cluster_id:
        return 1

    try:

        response = (
            supabase
            .table("complaints")
            .select("id")
            .eq(
                "cluster_id",
                cluster_id
            )
            .execute()
        )

        complaints = (
            response.data or []
        )

        return max(
            len(complaints),
            1
        )

    except Exception as e:

        print(
            "Error counting affected citizens:",
            e
        )

        return 1

# ============================================================
# 7. LOCAL TESTING
# ============================================================

if __name__ == "__main__":

    # Example coordinates
    lat1 = 12.9716
    lng1 = 77.5946

    lat2 = 12.9717
    lng2 = 77.5947


    distance = calculate_distance(
        lat1,
        lng1,
        lat2,
        lng2
    )


    print(
        "\nGPS DISTANCE TEST"
    )

    print(
        "Distance:",
        round(distance, 2),
        "metres"
    )


    location_score = location_similarity(
        distance
    )


    print(
        "Location similarity:",
        round(location_score, 3)
    )


    text_score = text_similarity(
        "Large pothole on the road",
        "There is a large pothole on the road"
    )


    print(
        "Text similarity:",
        round(text_score, 3)
    )


    category_score = category_similarity(
        "road and transportation issue",
        "road and transportation issue"
    )


    print(
        "Category similarity:",
        round(category_score, 3)
    )


    duplicate_score = calculate_duplicate_score(
        location_score,
        text_score,
        category_score
    )


    print(
        "Duplicate score:",
        duplicate_score
    )


    if duplicate_score >= DUPLICATE_THRESHOLD:

        print(
            "RESULT: POSSIBLE DUPLICATE"
        )

    else:

        print(
            "RESULT: DIFFERENT ISSUE"
        )
