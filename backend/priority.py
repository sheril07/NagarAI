from datetime import datetime, timezone

MAX_DAYS_PENDING = 30


# ============================================================
# CALCULATE DAYS PENDING
# ============================================================

def calculate_days_pending(created_at):
    """
    Calculates how many days a complaint has been pending.

    created_at can be:
        - ISO timestamp string
        - datetime object
    """

    if not created_at:
        return 0


    try:

        # ----------------------------------------------------
        # Convert string timestamp to datetime
        # ----------------------------------------------------

        if isinstance(created_at, str):

            created_at = created_at.replace(
                "Z",
                "+00:00"
            )

            created_at = datetime.fromisoformat(
                created_at
            )


        # ----------------------------------------------------
        # Make datetime timezone-aware
        # ----------------------------------------------------

        if created_at.tzinfo is None:

            created_at = created_at.replace(
                tzinfo=timezone.utc
            )


        now = datetime.now(
            timezone.utc
        )


        days = (
            now - created_at
        ).total_seconds() / 86400


        return max(
            0,
            int(days)
        )


    except Exception as e:

        print(
            "Days pending calculation error:",
            e
        )

        return 0


# ============================================================
# CALCULATE PRIORITY SCORE
# ============================================================

def calculate_priority(
    severity,
    people_affected,
    created_at
):
    """
    PS-S05 priority formula:

        Priority =
            Severity
            × People Affected
            × Days Pending

    Returns both the final priority score
    and the individual factors.
    """

    # --------------------------------------------------------
    # Safe defaults
    # --------------------------------------------------------

    severity = int(
        severity or 1
    )

    people_affected = int(
        people_affected or 1
    )


    # --------------------------------------------------------
    # Keep severity within 1-5
    # --------------------------------------------------------

    severity = max(
        1,
        min(5, severity)
    )


    # --------------------------------------------------------
    # People affected cannot be below 1
    # --------------------------------------------------------

    people_affected = max(
        1,
        people_affected
    )


    # --------------------------------------------------------
    # Calculate pending days
    # --------------------------------------------------------

    days_pending = calculate_days_pending(
        created_at
    )


    # --------------------------------------------------------
    # Calculate priority
    # --------------------------------------------------------

    priority_score = (
        severity
        * people_affected
        * max(days_pending, 1)
    )


    return {
        "priority_score": round(
            priority_score,
            2
        ),

        "severity": severity,

        "people_affected": people_affected,

        "days_pending": days_pending
    }


# ============================================================
# UPDATE PRIORITY IN SUPABASE
# ============================================================

def update_priority(
    supabase,
    complaint_id,
    severity,
    people_affected,
    created_at
):
    """
    Calculates and stores the priority score
    for one complaint.
    """

    result = calculate_priority(
        severity=severity,
        people_affected=people_affected,
        created_at=created_at
    )


    try:

        (
            supabase
            .table("complaints")
            .update({
                "priority_score": result[
                    "priority_score"
                ]
            })
            .eq(
                "id",
                complaint_id
            )
            .execute()
        )


        return result


    except Exception as e:

        print(
            "Priority update error:",
            e
        )

        return result


# ============================================================
# TEST
# ============================================================

if __name__ == "__main__":

    test = calculate_priority(

        severity=4,

        people_affected=10,

        created_at=(
            "2026-08-15T10:00:00+00:00"
        )
    )


    print(
        "\nPRIORITY TEST"
    )

    print(
        "=============="
    )

    print(
        "Severity:",
        test["severity"]
    )

    print(
        "People affected:",
        test["people_affected"]
    )

    print(
        "Days pending:",
        test["days_pending"]
    )

    print(
        "Priority score:",
        test["priority_score"]
    )
