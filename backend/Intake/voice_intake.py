"""
NagarAI - Voice intake module (Niv's piece)

Pipeline:
  1. Load any audio format (wav/ogg/opus/m4a) -> mono 16kHz PCM
  2. Band-pass filter to the human speech band (300-3400Hz) + WebRTC VAD trim
  3. Whisper ASR with task='translate' -> English transcript
  4. LLM extraction -> {category, location_mention, description}

This module deliberately does NOT compute severity, people_affected, or the
priority score. Those are computed downstream, after normalize + dedupe,
by teammates working on the shared complaint schema. This module's only job
is to hand off a clean, structured {category, location_mention, description}
per voice complaint.

Install:
    pip install openai-whisper webrtcvad scipy numpy pydub anthropic --break-system-packages
    (pydub needs ffmpeg installed on the system: apt install ffmpeg)
"""

import argparse
import contextlib
import json
import wave

import numpy as np
from pydub import AudioSegment
from scipy.signal import butter, sosfilt

import webrtcvad
import whisper
import anthropic


# ---------- Step 0: load + resample any input format ----------

def load_and_resample(input_path, sample_rate=16000):
    """Loads any audio format (mp3, ogg/opus voice notes, m4a, wav) and
    converts to mono 16-bit PCM at `sample_rate`, which both VAD and Whisper
    expect. Real complaints will mostly arrive as compressed voice notes,
    not clean wav files, so this conversion step is not optional."""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(sample_rate).set_sample_width(2)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)
    return samples, sample_rate


# ---------- Step 1: noise filter ----------

def bandpass_filter(samples, sample_rate, low=300, high=3400, order=5):
    """Keeps only the human speech band (300-3400Hz) - the same range
    telephony systems use. Cuts most low-frequency rumble (traffic, fans)
    and high-frequency hiss, without touching the consonant energy Whisper
    and VAD both rely on."""
    nyq = 0.5 * sample_rate
    sos = butter(order, [low / nyq, high / nyq], btype="band", output="sos")
    return sosfilt(sos, samples)


def vad_trim(pcm_bytes, sample_rate, aggressiveness=2, frame_ms=30):
    """Removes non-speech frames using WebRTC VAD. aggressiveness ranges
    0 (least aggressive) to 3 (most aggressive) about filtering out
    non-speech. 2 is a reasonable default - too aggressive and you risk
    clipping quiet speech at the start/end of a complaint."""
    vad = webrtcvad.Vad(aggressiveness)
    frame_len = int(sample_rate * frame_ms / 1000) * 2  # 2 bytes/sample (16-bit)
    voiced = bytearray()
    for i in range(0, len(pcm_bytes) - frame_len, frame_len):
        frame = pcm_bytes[i : i + frame_len]
        if vad.is_speech(frame, sample_rate):
            voiced += frame
    return bytes(voiced)


def clean_audio(input_path, output_path, sample_rate=16000,
                 use_vad=True, vad_aggressiveness=2):
    """Full noise-filter pipeline: load -> bandpass -> VAD trim -> save wav."""
    samples, sr = load_and_resample(input_path, sample_rate)
    filtered = bandpass_filter(samples, sr)
    filtered_int16 = np.clip(filtered, -32768, 32767).astype(np.int16)

    if use_vad:
        voiced_bytes = vad_trim(filtered_int16.tobytes(), sr, vad_aggressiveness)
        if len(voiced_bytes) == 0:
            # VAD found nothing speech-like - fall back to the filtered audio
            # rather than writing an empty file. Better to over-include than
            # silently drop a real complaint because VAD misfired.
            voiced_bytes = filtered_int16.tobytes()
    else:
        voiced_bytes = filtered_int16.tobytes()

    with contextlib.closing(wave.open(output_path, "wb")) as wf_out:
        wf_out.setnchannels(1)
        wf_out.setsampwidth(2)
        wf_out.setframerate(sr)
        wf_out.writeframes(voiced_bytes)

    return output_path


# ---------- Step 2: ASR + translation to English ----------

_whisper_model = None


def get_whisper_model(size="medium"):
    global _whisper_model
    if _whisper_model is None:
        _whisper_model = whisper.load_model(size)
    return _whisper_model


def transcribe_to_english(audio_path, model_size="medium"):
    """
    Whisper's task='translate' does ASR + translation to English in a single
    pass - it handles Tamil/Hindi/etc directly without a separate translation
    model. If your team specifically wants AI4Bharat for the regional-language
    judging criterion (or needs the native-script transcript preserved
    alongside the English one), swap this function for:
        AI4Bharat IndicWav2Vec/IndicConformer (ASR, native script)
        + IndicTrans2 (native script -> English)
    and keep everything downstream identical - this function's contract
    (audio path in, English string out) doesn't change.
    """
    model = get_whisper_model(model_size)
    result = model.transcribe(audio_path, task="translate")
    return result["text"].strip()


# ---------- Step 3: LLM extraction ----------

EXTRACTION_PROMPT = """You are extracting structured data from a civic complaint transcript.
The transcript is a citizen describing a civic issue (pothole, garbage, streetlight, waterlogging, etc.)
Return ONLY valid JSON, no preamble, no markdown fences, in this exact shape:

{{
  "category": "pothole" | "garbage" | "streetlight" | "waterlogging" | "other",
  "location_mention": "<any street/landmark/area name mentioned, or null if none>",
  "description": "<one clean sentence summarizing the issue>"
}}

Transcript:
\"\"\"{transcript}\"\"\"
"""


def extract_complaint_fields(transcript, client):
    """Calls the LLM to pull {category, location_mention, description} out
    of a messy spoken transcript. This is the voice module's final output -
    severity, people_affected, and the priority score are computed
    downstream after normalize + dedupe, not here."""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(transcript=transcript)}],
    )
    raw = response.content[0].text.strip()
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(raw)


# ---------- Orchestration ----------

def process_voice_complaint(raw_audio_path, source_modality="voice"):
    cleaned_path = raw_audio_path.rsplit(".", 1)[0] + "_cleaned.wav"
    clean_audio(raw_audio_path, cleaned_path)

    english_text = transcribe_to_english(cleaned_path)

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    fields = extract_complaint_fields(english_text, client)

    fields["source_modality"] = source_modality
    fields["raw_transcript"] = english_text
    return fields


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process one voice complaint")
    parser.add_argument("audio_path", help="Path to the raw voice complaint audio file")
    args = parser.parse_args()

    result = process_voice_complaint(args.audio_path)
    print(json.dumps(result, indent=2, ensure_ascii=False))

