from math import radians, sin, cos, sqrt, atan2
from difflib import SequenceMatcher
LOCATION_THRESHOLD_METERS = 50
DUPLICATE_THRESHOLD = 0.70
LOCATION_WEIGHT = 0.50
TEXT_WEIGHT = 0.30
CATEGORY_WEIGHT = 0.20

def calculate_distance(lat1, lng1, lat2, lng2):
  if None in (lat1, lng1, lat2, lng2):
        return None
  R = 6371000 
    lat1 = radians(float(lat1))
    lat2 = radians(float(lat2))
    delta_lat = radians(float(lat2) - float(lat1))
    delta_lng = radians(float(lng2) - float(lng1))
    a = ( sin(delta_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(delta_lng / 2) ** 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
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
    return SequenceMatcher(None, text1, text2).ratio()

def category_similarity(category1, category2):
    if not category1 or not category2:
        return 0.0
    if str(category1).lower().strip() == str(category2).lower().strip():
        return 1.0
    return 0.0

def calculate_duplicate_score(
    location_score,
    text_score,
    category_score
):
    score = (
        LOCATION_WEIGHT * location_score
        + TEXT_WEIGHT * text_score
        + CATEGORY_WEIGHT * category_score
    )

    return round(score, 3)

def find_duplicate_group(
    supabase,
    category,
    description,
    gps_lat,
    gps_lng
):
  if gps_lat is None or gps_lng is None:
        return None
    try:
        response = (
            supabase
            .table("issue_groups")
            .select(
                "id, category, description, gps_lat, gps_lng"
            )
            .eq("category", category)
            .execute()
        )

        existing_groups = response.data or []

    except Exception as e:
        print("Duplicate detection database error:", e)
        return None
    
    best_group = None
    best_score = 0.0

    for group in existing_groups:

        group_lat = group.get("gps_lat")
        group_lng = group.get("gps_lng")

        if group_lat is None or group_lng is None:
            continue

        distance = calculate_distance(
            gps_lat,
            gps_lng,
            group_lat,
            group_lng
        )

        if distance is None or distance > LOCATION_THRESHOLD_METERS:
            continue


        loc_score = location_similarity(distance)

        txt_score = text_similarity(
            description,
            group.get("description")
        )

        cat_score = category_similarity(
            category,
            group.get("category")
        )
        score = calculate_duplicate_score(
            loc_score,
            txt_score,
            cat_score
        )

        print(
            f"Checking group {group['id']} | "
            f"distance={distance:.2f}m | "
            f"text={txt_score:.2f} | "
            f"score={score:.2f}"
        )

        if score > best_score:
            best_score = score
            best_group = group
    if best_group and best_score >= DUPLICATE_THRESHOLD:

        print(
            f"Duplicate found: "
            f"{best_group['id']} "
            f"(score={best_score:.2f})"
        )

        return best_group["id"]

    print("No duplicate found.")

    return None
