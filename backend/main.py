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
from supabase import create_client

from voice_intake import process_voice_complaint
from Intake.text_intake import process_text_complaint

app = FastAPI()

supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])


@app.post("/complaints/text")
async def submit_text_complaint(
    text: str = Form(...),
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

    result = supabase.table("complaints").insert(row).execute()

    return {"complaint": result.data[0]}


@app.post("/complaints/voice")
async def submit_voice_complaint(
    audio: UploadFile = File(...),
    gps_lat: Optional[float] = Form(None),
    gps_lng: Optional[float] = Form(None),
):
    audio_bytes = await audio.read()
    suffix = os.path.splitext(audio.filename)[1] or ".wav"

    # process_voice_complaint() works on a file path, not an in-memory blob
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        fields = process_voice_complaint(tmp_path)  # {category, location_mention, description, raw_transcript, ...}
    finally:
        os.remove(tmp_path)

    # store the original audio in Supabase Storage for the record
    storage_path = f"voice/{uuid.uuid4()}{suffix}"
    supabase.storage.from_("complaint-audio").upload(storage_path, audio_bytes)
    audio_url = supabase.storage.from_("complaint-audio").get_public_url(storage_path)

    row = {
        "source_modality": "voice",
        "category": fields["category"],
        "location_mention": fields["location_mention"],
        "description": fields["description"],
        "gps_lat": gps_lat,
        "gps_lng": gps_lng,
        "audio_url": audio_url,
        "status": "pending",
    }
    result = supabase.table("complaints").insert(row).execute()
    return {"complaint": result.data[0]}
