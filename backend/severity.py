import re
WEIGHTS = {"damage": 0.25, "danger": 0.30, "people_affected": 0.15, "location_risk": 0.20, "frequency": 0.10,}
HIGH_RISK_LOCATIONS = ["school", "college", "hospital", "clinic", "bus stop", "railway station", "airport", "highway", "junction", "intersection", "market",
                       "temple", "church", "mosque", "playground",]

DAMAGE_LEVELS = {

    "pothole": 3,
    "road crack": 2,
    "damaged road": 4,
    "broken footpath": 3,
    "road obstruction": 4,
    "damaged road sign": 2,

    "garbage pile": 2,
    "overflowing garbage bin": 2,
    "illegal dumping": 3,
    "scattered waste": 2,

    "water leakage": 3,
    "flooded road": 4,
    "blocked drain": 3,
    "overflowing drain": 4,

    "broken streetlight": 3,
    "damaged electrical pole": 4,
    "exposed electrical wire": 5,

    "damaged building": 4,
    "damaged footpath": 3,
    "damaged public infrastructure": 3,

    "broken traffic signal": 4,
    "damaged traffic sign": 2,
    "traffic obstruction": 4,

    "fallen tree": 4,
    "air pollution": 3,
    "environmental damage": 2,

    "dangerous structure": 5,
    "unsafe road condition": 4,
    "public hazard": 4,

    "stray animal": 2,
    "injured animal": 4,
    "dead animal on road": 3,

    "other civic problem": 2,
}

DANGER_LEVELS = {

    "exposed electrical wire": 5,
    "damaged electrical pole": 5,

    "dangerous structure": 5,

    "unsafe road condition": 4,
    "public hazard": 4,

    "broken traffic signal": 4,
    "traffic obstruction": 4,

    "flooded road": 4,
    "fallen tree": 4,

    "injured animal": 3,

    "pothole": 3,
    "damaged road": 3,

    "broken streetlight": 2,
    "broken footpath": 2,

    "garbage pile": 1,
    "scattered waste": 1,
}

def people_affected_score(affected_citizens):
    """
    Converts number of affected citizens into a 1-5 score.

    Frequency/affected-citizen count increases severity,
    but is deliberately capped so it cannot overpower
    an inherently dangerous issue.
    """

    if affected_citizens <= 1:
        return 1

    elif affected_citizens <= 5:
        return 2

    elif affected_citizens <= 15:
        return 3

    elif affected_citizens <= 40:
        return 4

    else:
        return 5


# ============================================================
# FREQUENCY SCORE
# ============================================================

def frequency_score(frequency):
    """
    Frequency represents the number of complaints referring
    to the same underlying issue.
    """

    if frequency <= 1:
        return 1

    elif frequency <= 3:
        return 2

    elif frequency <= 10:
        return 3

    elif frequency <= 25:
        return 4

    else:
        return 5


# ============================================================
# LOCATION RISK
# ============================================================

def location_risk_score(location_text=None, description=None):

    text = " ".join([
        str(location_text or ""),
        str(description or "")
    ]).lower()

    for location in HIGH_RISK_LOCATIONS:

        if location in text:
            return 5

    # General public-road areas
    road_keywords = [
        "road",
        "street",
        "junction",
        "crossing",
        "footpath",
        "sidewalk"
    ]

    for keyword in road_keywords:

        if keyword in text:
            return 3

    return 2


# ============================================================
# GET DAMAGE SCORE
# ============================================================

def get_damage_score(issue):

    issue = (issue or "").lower().strip()

    return DAMAGE_LEVELS.get(
        issue,
        2
    )


# ============================================================
# GET DANGER SCORE
# ============================================================

def get_danger_score(issue):

    issue = (issue or "").lower().strip()

    return DANGER_LEVELS.get(
        issue,
        2
    )


# ============================================================
# SEVERITY CALCULATION
# ============================================================

def calculate_severity(
    category=None,
    issue=None,
    description=None,
    affected_citizens=1,
    frequency=1,
    location_text=None
):
    """
    Calculates civic complaint severity on a 1-5 scale.

    Factors:
        Damage            = 25%
        Immediate Danger  = 30%
        People Affected   = 15%
        Location Risk     = 20%
        Frequency         = 10%

    Returns a dictionary containing the final score
    and explainable factor scores.
    """

    damage = get_damage_score(issue)

    danger = get_danger_score(issue)

    people = people_affected_score(
        affected_citizens
    )

    location = location_risk_score(
        location_text,
        description
    )

    frequency_value = frequency_score(
        frequency
    )


    # --------------------------------------------------------
    # Weighted score
    # --------------------------------------------------------

    weighted_score = (

        damage * WEIGHTS["damage"]

        + danger * WEIGHTS["danger"]

        + people * WEIGHTS["people_affected"]

        + location * WEIGHTS["location_risk"]

        + frequency_value * WEIGHTS["frequency"]
    )


    # --------------------------------------------------------
    # Convert to 1-5
    # --------------------------------------------------------

    severity = round(weighted_score)

    severity = max(
        1,
        min(5, severity)
    )


    # --------------------------------------------------------
    # Explainable reasons
    # --------------------------------------------------------

    reasons = []

    if damage >= 4:
        reasons.append(
            "Significant physical damage"
        )

    if danger >= 4:
        reasons.append(
            "High immediate safety risk"
        )

    if people >= 4:
        reasons.append(
            "Large number of citizens affected"
        )

    if location >= 4:
        reasons.append(
            "High-risk public location"
        )

    if frequency_value >= 4:
        reasons.append(
            "Multiple complaints indicate recurring impact"
        )

    if not reasons:
        reasons.append(
            "Low immediate public impact"
        )


    return {

        "severity": severity,

        "severity_factors": {

            "damage": damage,

            "immediate_danger": danger,

            "people_affected": people,

            "location_risk": location,

            "frequency": frequency_value,
        },

        "severity_score_raw": round(
            weighted_score,
            2
        ),

        "severity_reason": "; ".join(
            reasons
        )
    }
