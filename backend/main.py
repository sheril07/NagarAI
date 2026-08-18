"""
NagarAI backend - voice complaint endpoint.

Wraps voice_intake.process_voice_complaint() as an HTTP endpoint the
frontend calls on submit. GPS coordinates are captured client-side
(navigator.geolocation) at the moment the user hits submit, and sent
alongside the audio file in the same request.

Env vars needed: SUPABASE_URL, SUPABASE_KEY, ANTHROPIC_API_KEY

Run:
    uvicorn main:app --reload
"""

import os
import tempfile
import uuid
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client

from Intake.voice_intake import process_voice_complaint
from Intake.text_intake import process_text_complaint
from Intake.image_intake import process_image_complaint

from duplicate import (
    find_duplicate_group,
    create_cluster_id,
    get_people_affected
)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])

async def assign_duplicate_cluster(
    complaint_id,
    category,
    description,
    gps_lat,
    gps_lng
):
    """
    Finds an existing duplicate cluster.

    If no duplicate exists:
        creates a new cluster.

    Then updates people_affected
    for all complaints in that cluster.
    """

    # --------------------------------------------------------
    # Find an existing duplicate
    # --------------------------------------------------------

    cluster_id = find_duplicate_group(
        supabase,
        complaint_id,
        category,
        description,
        gps_lat,
        gps_lng
    )


    # --------------------------------------------------------
    # No duplicate → create new cluster
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
    # Count complaints in cluster
    # --------------------------------------------------------

    people_affected = get_people_affected(
        supabase,
        cluster_id
    )


    # --------------------------------------------------------
    # Update affected count for entire cluster
    # --------------------------------------------------------

    (
        supabase
        .table("complaints")
        .update({
            "people_affected": people_affected
        })
        .eq(
            "cluster_id",
            cluster_id
        )
        .execute()
    )


    return cluster_id, people_affected

@app.post("/complaints/text")
async def submit_text_complaint(
    text: str = Form(...),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
):

    fields = process_text_complaint(text)

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

    cluster_id, people_affected = (
        await assign_duplicate_cluster(
            complaint_id=complaint["id"],
            category=complaint["category"],
            description=complaint["description"],
            gps_lat=complaint["gps_lat"],
            gps_lng=complaint["gps_lng"],
        )
    )

    complaint["cluster_id"] = cluster_id
    complaint["people_affected"] = people_affected

    return {
        "complaint": complaint
    }

@app.post("/complaints/voice")
async def submit_voice_complaint(
    audio: UploadFile = File(...),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
):

    audio_bytes = await audio.read()

    suffix = (
        os.path.splitext(audio.filename)[1]
        or ".wav"
    )


    # --------------------------------------------------------
    # Temporary audio file
    # --------------------------------------------------------

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    ) as tmp:

        tmp.write(audio_bytes)
        tmp_path = tmp.name


    try:

        fields = process_voice_complaint(
            tmp_path,
            latitude=gps_lat,
            longitude=gps_lng
        )

    finally:

        if os.path.exists(tmp_path):
            os.remove(tmp_path)


    # --------------------------------------------------------
    # Store audio
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
    # Insert complaint
    # --------------------------------------------------------

    row = {
        "source_modality": "voice",
        "category": fields["category"],
        "location_mention": fields["location_mention"],
        "description": fields["description"],
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
    # Deduplication
    # --------------------------------------------------------

    cluster_id, people_affected = (
        await assign_duplicate_cluster(
            complaint_id=complaint["id"],
            category=complaint["category"],
            description=complaint["description"],
            gps_lat=complaint["gps_lat"],
            gps_lng=complaint["gps_lng"],
        )
    )


    complaint["cluster_id"] = cluster_id
    complaint["people_affected"] = people_affected


    return {
        "complaint": complaint
    }

@app.post("/complaints/photo")
async def submit_photo_complaint(
    image: UploadFile = File(...),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
):

    image_bytes = await image.read()

    suffix = (
        os.path.splitext(image.filename)[1]
        or ".jpg"
    )


    # --------------------------------------------------------
    # Temporary image file
    # --------------------------------------------------------

    with tempfile.NamedTemporaryFile(
        delete=False,
        suffix=suffix
    ) as tmp:

        tmp.write(image_bytes)
        tmp_path = tmp.name


    try:

        fields = process_image_complaint(
            tmp_path
        )

    finally:

        if os.path.exists(tmp_path):
            os.remove(tmp_path)


    # --------------------------------------------------------
    # Store image
    # --------------------------------------------------------

    storage_path = (
        f"photo/{uuid.uuid4()}{suffix}"
    )

    (
        supabase
        .storage
        .from_("complaint-images")
        .upload(
            storage_path,
            image_bytes
        )
    )

    image_url = (
        supabase
        .storage
        .from_("complaint-images")
        .get_public_url(
            storage_path
        )
    )


    # --------------------------------------------------------
    # Insert complaint
    # --------------------------------------------------------

    row = {
        "source_modality": "photo",
        "category": fields["category"],
        "description": fields["description"],
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
    # Deduplication
    # --------------------------------------------------------

    cluster_id, people_affected = (
        await assign_duplicate_cluster(
            complaint_id=complaint["id"],
            category=complaint["category"],
            description=complaint["description"],
            gps_lat=complaint["gps_lat"],
            gps_lng=complaint["gps_lng"],
        )
    )


    complaint["cluster_id"] = cluster_id
    complaint["people_affected"] = people_affected


    return {
        "complaint": complaint
    }
