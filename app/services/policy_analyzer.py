"""
Policy Analyzer Service
========================
Takes extracted policy text and sends it to Google Gemini to produce
a structured, plain-English analysis of the insurance policy.

Output includes:
  - Summary of the policy in simple language
  - Coverage highlights with limits
  - Exclusions & limitations (the most critical part for consumers)
  - Key terms & conditions
  - Risk alerts (hidden gotchas, unusually low limits, etc.)
"""

import json
import logging

from google import genai

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Prompt ─────────────────────────────────────────────────────────────

ANALYSIS_PROMPT = """You are an expert insurance policy analyst. Your job is to read insurance policy documents and translate them into plain, simple English that any customer can understand.

Analyze the following insurance policy text and produce a structured JSON response with these sections:

1. **summary**: A 3-5 sentence plain-English summary of what this policy covers. Write as if explaining to a friend with no insurance knowledge.

2. **policy_type**: The type of insurance (e.g., "Health Insurance", "Life Insurance", "Auto Insurance", "Home Insurance", etc.)

3. **coverage_highlights**: An array of objects, each with:
   - "item": What is covered (e.g., "Hospitalization")
   - "detail": Plain-English explanation of the coverage
   - "limit": The coverage limit or amount, if mentioned (e.g., "₹5,00,000 per year")

4. **exclusions**: An array of objects, each with:
   - "item": What is NOT covered
   - "detail": Why it matters to the policyholder, in simple language
   - "severity": "high" | "medium" | "low" — how likely this exclusion is to affect a typical claim

5. **key_conditions**: An array of objects, each with:
   - "item": The condition or term (e.g., "Waiting Period")
   - "detail": What it means in practical terms for the policyholder

6. **risk_alerts**: An array of strings — warnings about unusual clauses, very low coverage limits, tricky conditions, or anything a customer should be especially aware of before purchasing.

7. **jargon_glossary**: An array of objects, each with:
   - "term": The technical/legal term found in the policy
   - "meaning": Simple definition

IMPORTANT RULES:
- Use simple, everyday language. Avoid legal/insurance jargon in your explanations.
- Be specific — quote actual numbers, dates, and limits from the policy.
- If the policy text is unclear or incomplete, say so honestly.
- Focus on what MATTERS to the policyholder, not boilerplate.
- Return ONLY valid JSON, no markdown fences, no extra text.

---

POLICY TEXT:
{policy_text}
"""


def _get_gemini_client() -> genai.Client:
    """Create and return a Gemini API client."""
    if not settings.GEMINI_API_KEY:
        raise ValueError(
            "GEMINI_API_KEY is not set. Add it to your .env file or environment variables."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)


def _parse_gemini_response(response_text: str) -> dict:
    """
    Parse the Gemini response into a Python dict.
    Handles cases where the model wraps JSON in markdown code fences.
    """
    text = response_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        # Remove opening fence (```json or ```)
        first_newline = text.index("\n")
        text = text[first_newline + 1:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[:-3].strip()

    return json.loads(text)


def analyze_policy(extracted_text: str) -> dict:
    """
    Analyze extracted insurance policy text using Google Gemini.

    Args:
        extracted_text: The full text extracted from the insurance PDF.

    Returns:
        A structured dict containing the policy analysis with summary,
        coverages, exclusions, conditions, risk alerts, and glossary.

    Raises:
        ValueError: If GEMINI_API_KEY is not configured.
        Exception: If the Gemini API call fails or returns unparseable output.
    """
    if not extracted_text or not extracted_text.strip():
        raise ValueError("No text to analyze. The extracted text is empty.")

    # ── Build prompt ──────────────────────────────────────────────────
    prompt = ANALYSIS_PROMPT.format(policy_text=extracted_text)

    # ── Call Gemini ───────────────────────────────────────────────────
    logger.info("Sending policy text to Gemini (%d chars)...", len(extracted_text))
    client = _get_gemini_client()

    response = client.models.generate_content(
        model=settings.GEMINI_MODEL,
        contents=prompt,
    )

    raw_text = response.text
    logger.info("Gemini response received (%d chars).", len(raw_text))

    # ── Parse response ────────────────────────────────────────────────
    try:
        analysis = _parse_gemini_response(raw_text)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Gemini response as JSON: %s", raw_text[:500])
        raise ValueError(
            "The AI returned an invalid response. Please try again."
        ) from exc

    # ── Validate expected keys ────────────────────────────────────────
    expected_keys = {
        "summary", "policy_type", "coverage_highlights",
        "exclusions", "key_conditions", "risk_alerts", "jargon_glossary",
    }
    missing = expected_keys - set(analysis.keys())
    if missing:
        logger.warning("Gemini response missing keys: %s", missing)
        # Fill in missing keys with empty defaults rather than failing
        for key in missing:
            if key in ("summary", "policy_type"):
                analysis[key] = "Not available"
            else:
                analysis[key] = []

    return analysis
