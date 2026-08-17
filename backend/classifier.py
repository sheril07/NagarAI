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

The complaint may be written in English, Hindi, Tamil, or any other
Indian language. It may also contain mixed languages, such as
Tamil-English or Hindi-English.

You must understand the language and meaning of the complaint regardless
of which Indian language is used.

Choose EXACTLY ONE category from these allowed categories:

{CATEGORIES}

Rules:
- You MUST choose exactly one category from the list.
- Do NOT create a new category.
- If multiple categories seem possible, choose the category representing
  the primary civic problem.
- Do not invent information that the citizen did not provide.
- Keep the issue and description short and factual.
- The "issue" should identify the specific problem mentioned by the citizen.

Return ONLY valid JSON in exactly this format:

{{
    "input_type": "text",
    "category": "one allowed category",
    "issue": "short name describing the specific civic issue",
    "description": "short factual description of the complaint"
}}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=prompt
    )

    print("RAW GEMINI RESPONSE:")
    print(response.text)

    # Remove Markdown code fences if Gemini returns ```json ... ```
    cleaned_response = response.text.strip()

    if cleaned_response.startswith("```json"):
        cleaned_response = cleaned_response[7:]

    if cleaned_response.endswith("```"):
        cleaned_response = cleaned_response[:-3]

    result = json.loads(cleaned_response.strip())

    # Safety check: make sure Gemini used one of our official categories
    if result["category"] not in CATEGORIES:
        result["category"] = "Other / General"

    # Always mark this as text input
    result["input_type"] = "text"

    return result
