"""
NagarAI backend - complaint endpoints.

Handles text, voice, and photo complaints.
GPS coordinates are captured client-side and sent with the complaint.

Env vars needed:
    SUPABASE_URL
    SUPABASE_KEY
    ANTHROPIC_API_KEY
"""

print("=== STARTING MAIN.PY ===")

import os
import tempfile
import uuid
from typing import Optional

print("=== BASIC IMPORTS DONE ===")

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware

print("=== FASTAPI IMPORTED ===")

from supabase import create_client

print("=== SUPABASE IMPORTED ===")

from Intake.voice_intake import process_voice_complaint

print("=== VOICE INTAKE IMPORTED ===")

from Intake.text_intake import process_text_complaint

print("=== TEXT INTAKE IMPORTED ===")

from Intake.image_intake import process_image_complaint

print("=== IMAGE INTAKE IMPORTED ===")

from duplicate import (
    find_duplicate_group,
    create_cluster_id,
    get_people_affected
)

print("=== DUPLICATE IMPORTED ===")

from severity import calculate_severity

print("=== SEVERITY IMPORTED ===")

from priority import calculate_priority

print("=== PRIORITY IMPORTED ===")


# ============================================================
# FASTAPI APP
# ============================================================

app = FastAPI()

print("=== FASTAPI APP CREATED ===")


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("=== CORS CONFIGURED ===")


# ============================================================
# SUPABASE
# ============================================================

print("=== INITIALIZING SUPABASE ===")

supabase = create_client(
    os.environ["SUPABASE_URL"],
    os.environ["SUPABASE_KEY"]
)

print("=== SUPABASE INITIALIZED ===")


# ============================================================
# DUPLICATE + SEVERITY + PRIORITY
# ============================================================

async def assign_duplicate_cluster(
    complaint_id,
    category,
    issue,
    description,
    gps_lat,
    gps_lng,
    created_at,
    image_url=None
):
    """
    Finds/creates a duplicate cluster, updates the number
    of affected citizens, calculates severity, and calculates
    priority.
    """

    # --------------------------------------------------------
    # 1. Find existing duplicate
    # --------------------------------------------------------

    cluster_id = find_duplicate_group(
        supabase,
        complaint_id,
        category,
        description,
        gps_lat,
        gps_lng,
        image_url
    )

    # --------------------------------------------------------
    # 2. No duplicate → create new cluster
    # --------------------------------------------------------

    if cluster_id is None:

        cluster_id = create_cluster_id()

        (
            supabase
            .table("complaints")
            .update({
                "cluster_id": cluster_id
            })
            .eq(
                "id",
                complaint_id
            )
            .execute()
        )

    # --------------------------------------------------------
    # 3. Count affected citizens
    # --------------------------------------------------------

    people_affected = get_people_affected(
        supabase,
        cluster_id
    )

    # --------------------------------------------------------
    # 4. Calculate severity
    # --------------------------------------------------------

    severity_result = calculate_severity(
        category=category,
        issue=issue,
        description=description,
        affected_citizens=people_affected,
        frequency=people_affected,
        location_text=None
    )

    severity = severity_result["severity"]

    # --------------------------------------------------------
    # 5. Calculate priority
    # --------------------------------------------------------

    priority_result = calculate_priority(
        severity=severity,
        people_affected=people_affected,
        created_at=created_at
    )

    priority_score = priority_result["priority_score"]

    # --------------------------------------------------------
    # 6. Update entire cluster
    # --------------------------------------------------------

    (
        supabase
        .table("complaints")
        .update({
            "people_affected": people_affected,
            "severity": severity,
            "priority_score": priority_score
        })
        .eq(
            "cluster_id",
            cluster_id
        )
        .execute()
    )

    return {
        "cluster_id": cluster_id,
        "people_affected": people_affected,
        "severity": severity,
        "severity_reason": severity_result["severity_reason"],
        "priority_score": priority_score
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "NagarAI backend is running"
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy"
    }


# ============================================================
# TEXT COMPLAINT
# ============================================================

@app.post("/complaints/text")
async def submit_text_complaint(
    text: str = Form(...),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
):

    # --------------------------------------------------------
    # TEXT INTAKE
    # --------------------------------------------------------

    fields = process_text_complaint(
        text
    )

    # --------------------------------------------------------
    # INSERT COMPLAINT
    # --------------------------------------------------------

    row = {
        "source_modality": "text",
        "category": fields["category"],
        "location_mention": fields["location_mention"],
        "description": fields["description"],
        "gps_lat": gps_lat,
        "gps_lng": gps_lng,
        "status": "pending",
    }

    result = (
        supabase
        .table("complaints")
        .insert(row)
        .execute()
    )

    complaint = result.data[0]

    # --------------------------------------------------------
    # DUPLICATE + SEVERITY + PRIORITY
    # --------------------------------------------------------

    cluster_result = await assign_duplicate_cluster(
        complaint_id=complaint["id"],
        category=complaint["category"],
        issue=complaint["category"],
        description=complaint["description"],
        gps_lat=complaint["gps_lat"],
        gps_lng=complaint["gps_lng"],
        created_at=complaint["created_at"],
        image_url=None
    )

    # --------------------------------------------------------
    # ADD CALCULATED VALUES TO RESPONSE
    # --------------------------------------------------------

    complaint["cluster_id"] = (
        cluster_result["cluster_id"]
    )

    complaint["people_affected"] = (
        cluster_result["people_affected"]
    )

    complaint["severity"] = (
        cluster_result["severity"]
    )

    complaint["priority_score"] = (
        cluster_result["priority_score"]
    )

    complaint["severity_reason"] = (
        cluster_result["severity_reason"]
    )

    return {
        "complaint": complaint
    }


# ============================================================
# VOICE COMPLAINT
# ============================================================

@app.post("/complaints/voice")
async def submit_voice_complaint(
    audio: UploadFile = File(...),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
):

    # --------------------------------------------------------
    # READ AUDIO
    # --------------------------------------------------------

    audio_bytes = await audio.read()

    suffix = (
        os.path.splitext(audio.filename)[1]
        or ".wav"
    )

    # --------------------------------------------------------
    # TEMPORARY AUDIO FILE
    # --------------------------------------------------------

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    ) as tmp:

        tmp.write(audio_bytes)

        tmp_path = tmp.name

    try:

        # ----------------------------------------------------
        # VOICE INTAKE
        # ----------------------------------------------------

        fields = process_voice_complaint(
            tmp_path,
            latitude=gps_lat,
            longitude=gps_lng
        )

    finally:

        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # --------------------------------------------------------
    # UPLOAD ORIGINAL AUDIO
    # --------------------------------------------------------

    storage_path = (
        f"voice/{uuid.uuid4()}{suffix}"
    )

    (
        supabase
        .storage
        .from_("complaint-audio")
        .upload(
            storage_path,
            audio_bytes
        )
    )

    audio_url = (
        supabase
        .storage
        .from_("complaint-audio")
        .get_public_url(
            storage_path
        )
    )

    # --------------------------------------------------------
    # INSERT COMPLAINT
    # --------------------------------------------------------

    row = {
        "source_modality": "voice",

        "category": fields["category"],

        "location_mention": fields[
            "location_mention"
        ],

        "description": fields[
            "description"
        ],

        "raw_transcript": fields.get(
            "raw_transcript"
        ),

        "gps_lat": gps_lat,

        "gps_lng": gps_lng,

        "audio_url": audio_url,

        "status": "pending",
    }

    result = (
        supabase
        .table("complaints")
        .insert(row)
        .execute()
    )

    complaint = result.data[0]

    # --------------------------------------------------------
    # DUPLICATE + SEVERITY + PRIORITY
    # --------------------------------------------------------

    cluster_result = await assign_duplicate_cluster(
        complaint_id=complaint["id"],
        category=complaint["category"],
        issue=complaint["category"],
        description=complaint["description"],
        gps_lat=complaint["gps_lat"],
        gps_lng=complaint["gps_lng"],
        created_at=complaint["created_at"],
        image_url=None
    )

    # --------------------------------------------------------
    # ADD CALCULATED VALUES TO RESPONSE
    # --------------------------------------------------------

    complaint["cluster_id"] = (
        cluster_result["cluster_id"]
    )

    complaint["people_affected"] = (
        cluster_result["people_affected"]
    )

    complaint["severity"] = (
        cluster_result["severity"]
    )

    complaint["priority_score"] = (
        cluster_result["priority_score"]
    )

    complaint["severity_reason"] = (
        cluster_result["severity_reason"]
    )

    return {
        "complaint": complaint
    }


# ============================================================
# PHOTO COMPLAINT
# ============================================================

@app.post("/complaints/photo")
async def submit_photo_complaint(
    image: UploadFile = File(...),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
):

    # --------------------------------------------------------
    # READ IMAGE
    # --------------------------------------------------------

    image_bytes = await image.read()

    suffix = (
        os.path.splitext(image.filename)[1]
        or ".jpg"
    )

    # --------------------------------------------------------
    # TEMPORARY IMAGE FILE
    # --------------------------------------------------------

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    ) as tmp:

        tmp.write(image_bytes)

        tmp_path = tmp.name

    try:

        # ----------------------------------------------------
        # PHOTO INTAKE
        # ----------------------------------------------------

        fields = process_image_complaint(
            tmp_path
        )

    finally:

        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # --------------------------------------------------------
    # UPLOAD IMAGE
    # --------------------------------------------------------

    storage_path = (
        f"photo/{uuid.uuid4()}{suffix}"
    )

    (
        supabase
        .storage
        .from_("complaint-image")
        .upload(
            storage_path,
            image_bytes
        )
    )

    image_url = (
        supabase
        .storage
        .from_("complaint-image")
        .get_public_url(
            storage_path
        )
    )

    # --------------------------------------------------------
    # INSERT COMPLAINT
    # --------------------------------------------------------

    row = {
        "source_modality": "photo",

        "category": fields[
            "category"
        ],

        "description": fields[
            "description"
        ],

        "gps_lat": gps_lat,

        "gps_lng": gps_lng,

        "image_url": image_url,

        "status": "pending",
    }

    result = (
        supabase
        .table("complaints")
        .insert(row)
        .execute()
    )

    complaint = result.data[0]

    # --------------------------------------------------------
    # DUPLICATE + SEVERITY + PRIORITY
    # --------------------------------------------------------

    cluster_result = await assign_duplicate_cluster(
        complaint_id=complaint["id"],
        category=complaint["category"],
        issue=complaint["category"],
        description=complaint["description"],
        gps_lat=complaint["gps_lat"],
        gps_lng=complaint["gps_lng"],
        created_at=complaint["created_at"],
        image_url=complaint["image_url"]
    )

    # --------------------------------------------------------
    # ADD CALCULATED VALUES TO RESPONSE
    # --------------------------------------------------------

    complaint["cluster_id"] = (
        cluster_result["cluster_id"]
    )

    complaint["people_affected"] = (
        cluster_result["people_affected"]
    )

    complaint["severity"] = (
        cluster_result["severity"]
    )

    complaint["priority_score"] = (
        cluster_result["priority_score"]
    )

    complaint["severity_reason"] = (
        cluster_result["severity_reason"]
    )

    return {
        "complaint": complaint
    }


print("=== MAIN.PY FINISHED LOADING ===")
print("=== APP READY FOR UVICORN ===")
