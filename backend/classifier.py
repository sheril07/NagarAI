import os
import json
from google import genai

from categories import CATEGORIES


api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    raise ValueError("GEMINI_API_KEY environment variable is not set.")

client = genai.Client(api_key=api_key)


def classify_complaint(complaint):

    prompt = f"""
You are NagarAI, an AI system for analyzing civic complaints in India.

Analyze the following citizen complaint:

"{complaint}"

The complaint may be written in:
- Tamil
- Hindi
- English
- Tamil-English mixed language
- Hindi-English mixed language

Understand the meaning and context of the entire complaint.

Choose EXACTLY ONE category from these allowed categories:

{CATEGORIES}

Rules:
- You MUST choose exactly one category from the list.
- Do NOT create a new category.
- If multiple categories seem possible, choose the category representing
  the primary civic problem.
- Do not invent information that the citizen did not provide.
- Keep the description short and factual.
- Translate Tamil or Hindi into clear English when necessary.

Return ONLY valid JSON in exactly this format:

{{
    "language": "detected language",
    "translated_text": "clear English translation",
    "category": "one allowed category",
    "description": "short factual description"
}}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    print("RAW GEMINI RESPONSE:")
    print(response.text)

    result = json.loads(response.text)

    # Safety check: make sure Gemini used one of our official categories
    if result["category"] not in CATEGORIES:
        result["category"] = "Other / General"

    return result
