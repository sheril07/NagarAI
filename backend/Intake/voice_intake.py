"""
NagarAI - Voice Intake Module

Pipeline:
  1. Load any audio format -> mono 16kHz PCM wav
  2. Band-pass filter (300-3400Hz) + silence trim
  3. Groq Cloud Whisper-Large-V3 -> English transcript
  4. Groq LLM extraction -> {category, location_mention, description}
"""

import argparse
import ast
import json
import os
import re
import numpy as np
from pydub import AudioSegment
from pydub.silence import detect_nonsilent
from scipy.signal import butter, sosfilt
from groq import Groq

# ---------- Step 1: Audio Loading & Noise Filtering ----------

def load_and_resample(input_path: str, sample_rate: int = 16000):
    """Converts input audio (m4a, ogg, mp3, wav) to mono 16-bit PCM at 16kHz."""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(sample_rate).set_sample_width(2)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    return samples, sample_rate


def bandpass_filter(samples: np.ndarray, sample_rate: int, low: int = 300, high: int = 3400, order: int = 5):
    """Filters audio to human speech frequencies (300-3400Hz) to cut background noise."""
    nyq = 0.5 * sample_rate
    sos = butter(order, [low / nyq, high / nyq], btype="band", output="sos")
    return sosfilt(sos, samples)


def trim_silence(audio_segment: AudioSegment, silence_thresh: int = -40, min_silence_len: int = 300):
    """Trims silent stretches using pydub amplitude detection."""
    nonsilent_ranges = detect_nonsilent(
        audio_segment, min_silence_len=min_silence_len, silence_thresh=silence_thresh
    )
    if not nonsilent_ranges:
        return audio_segment

    trimmed = AudioSegment.empty()
    for start, end in nonsilent_ranges:
        trimmed += audio_segment[start:end]
    return trimmed


def clean_audio(input_path: str, output_path: str, sample_rate: int = 16000, use_silence_trim: bool = True):
    """Full cleaning pipeline: load -> bandpass -> trim silence -> export clean wav."""
    samples, sr = load_and_resample(input_path, sample_rate)
    filtered = bandpass_filter(samples, sr)
    filtered_int16 = np.clip(filtered, -32768, 32767).astype(np.int16)

    filtered_audio = AudioSegment(
        filtered_int16.tobytes(), frame_rate=sr, sample_width=2, channels=1
    )

    result_audio = trim_silence(filtered_audio) if use_silence_trim else filtered_audio
    if len(result_audio) == 0:
        result_audio = filtered_audio

    result_audio.export(output_path, format="wav")
    return output_path


# ---------- Step 2: Speech-to-Text via Cloud Whisper ----------

def transcribe_to_english(audio_path: str, client: Groq = None) -> str:
    """Translates audio to English transcript using Groq Cloud Whisper-Large-V3."""
    if client is None:
        client = Groq()

    with open(audio_path, "rb") as file:
        translation = client.audio.translations.create(
            file=(audio_path, file.read()),
            model="whisper-large-v3",
        )
    return translation.text.strip()


# ---------- Step 3: LLM Structured Field Extraction ----------

EXTRACTION_PROMPT = """You are extracting structured data from a civic complaint transcript.
The transcript describes a civic issue (pothole, garbage, streetlight, waterlogging, etc.).
Return ONLY a raw JSON object with double-quoted keys and values, formatted exactly like this:

{{
  "category": "pothole" | "garbage" | "streetlight" | "waterlogging" | "other",
  "location_mention": "<street/landmark mentioned, or null>",
  "description": "<one clean sentence summarizing the issue>"
}}

Transcript:
\"\"\"{transcript}\"\"\"
"""


def extract_complaint_fields(transcript: str, client: Groq = None) -> dict:
    """Extracts JSON structure from transcript using Groq LLM."""
    if client is None:
        client = Groq()

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b",
        temperature=0.0,
        max_tokens=300,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(transcript=transcript)}],
    )
    raw = response.choices[0].message.content.strip()

    # Isolate JSON string between braces
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        raw = match.group(0)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Fallback if LLM returns single-quoted dict string
        return ast.literal_eval(raw)


# ---------- Orchestrator Entrypoint ----------

def process_voice_complaint(
    raw_audio_path: str,
    latitude: float = None,
    longitude: float = None,
    source_modality: str = "voice"
) -> dict:
    """
    Main entrypoint called by your backend route when a user submits audio + location.
    """
    cleaned_path = raw_audio_path.rsplit(".", 1)[0] + "_cleaned.wav"
    clean_audio(raw_audio_path, cleaned_path)

    client = Groq()
    english_text = transcribe_to_english(cleaned_path, client)
    fields = extract_complaint_fields(english_text, client)

    # Attach metadata and live GPS coordinates
    fields["source_modality"] = source_modality
    fields["raw_transcript"] = english_text
    fields["latitude"] = latitude
    fields["longitude"] = longitude

    # Clean up intermediate cleaned audio file
    if os.path.exists(cleaned_path):
        os.remove(cleaned_path)

    return fields


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a single voice complaint")
    parser.add_argument("audio_path", help="Path to input audio file")
    parser.add_argument("--lat", type=float, default=None, help="Latitude")
    parser.add_argument("--long", type=float, default=None, help="Longitude")
    args = parser.parse_args()

    result = process_voice_complaint(args.audio_path, latitude=args.lat, longitude=args.long)
    print(json.dumps(result, indent=2, ensure_ascii=False))
