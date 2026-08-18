import uuid
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

    a = (
        sin(delta_lat / 2) ** 2
        + cos(lat1) * cos(lat2) * sin(delta_lng / 2) ** 2
    )
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


def location_similarity(distance):
    if distance is None:
        return 0.0
    if distance >= LOCATION_THRESHOLD_METERS:
        return 0.0
    return 1 - (distance / LOCATION_THRESHOLD_METERS)


def text_similarity(text1, text2):
    if not text1 or not text2:
        return 0.0
    text1 = str(text1).lower().strip()
    text2 = str(text2).lower().strip()
    return SequenceMatcher(None, text1, text2).ratio()


def category_similarity(category1, category2):
    if not category1 or not category2:
        return 0.0
    category1 = str(category1).lower().strip()
    category2 = str(category2).lower().strip()
    return 1.0 if category1 == category2 else 0.0


def calculate_duplicate_score(location_score, text_score, category_score):
    score = (
        LOCATION_WEIGHT * location_score
        + TEXT_WEIGHT * text_score
        + CATEGORY_WEIGHT * category_score
    )
    return round(score, 3)


# ============================================================
# NEW: cluster id generation
# ============================================================

def create_cluster_id():
    """Generates a new unique cluster id for a fresh (non-duplicate) issue."""
    return str(uuid.uuid4())


# ============================================================
# NEW: count people affected in a cluster
# ============================================================

def get_people_affected(supabase, cluster_id):
    """
    Counts how many complaints belong to a given cluster,
    used as the 'people affected' figure for severity/priority.
    """

    try:
        response = (
            supabase
            .table("complaints")
            .select("id", count="exact")
            .eq("cluster_id", cluster_id)
            .execute()
        )

        return response.count or 1

    except Exception as e:
        print("get_people_affected error:", e)
        return 1


# ============================================================
# UPDATED: find_duplicate_group now matches main.py's call signature
# (complaint_id + image_url added; compares against `complaints`
#  table directly instead of a nonexistent `issue_groups` table)
# ============================================================

def find_duplicate_group(
    supabase,
    complaint_id,
    category,
    description,
    gps_lat,
    gps_lng,
    image_url=None
):

    if gps_lat is None or gps_lng is None:
        print("Duplicate detection skipped: GPS coordinates missing.")
        return None

    try:
        response = (
            supabase
            .table("complaints")
            .select("id, cluster_id, category, description, gps_lat, gps_lng")
            .eq("category", category)
            .not_.is_("cluster_id", "null")
            .neq("id", complaint_id)
            .execute()
        )

        existing_complaints = response.data or []

    except Exception as e:
        print("Duplicate detection database error:", e)
        return None

    best_cluster_id = None
    best_score = 0.0

    for row in existing_complaints:

        group_lat = row.get("gps_lat")
        group_lng = row.get("gps_lng")

        if group_lat is None or group_lng is None:
            continue

        distance = calculate_distance(gps_lat, gps_lng, group_lat, group_lng)

        if distance is None or distance > LOCATION_THRESHOLD_METERS:
            continue

        loc_score = location_similarity(distance)
        txt_score = text_similarity(description, row.get("description"))
        cat_score = category_similarity(category, row.get("category"))

        score = calculate_duplicate_score(loc_score, txt_score, cat_score)

        print(
            f"Checking complaint {row['id']} (cluster={row['cluster_id']}) | "
            f"distance={distance:.2f}m | location={loc_score:.2f} | "
            f"text={txt_score:.2f} | category={cat_score:.2f} | score={score:.2f}"
        )

        if score > best_score:
            best_score = score
            best_cluster_id = row["cluster_id"]

    if best_cluster_id and best_score >= DUPLICATE_THRESHOLD:
        print(f"Duplicate found: cluster {best_cluster_id} (score={best_score:.2f})")
        return best_cluster_id

    print("No duplicate found.")
    return None


if __name__ == "__main__":
    score = text_similarity(
        "Large pothole on the road",
        "Garbage is overflowing from the bin"
    )
    print("Text similarity:", score)
