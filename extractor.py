import json
import re
import time
import os
import pdfplumber
from config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    AI_PROVIDER, EXTRACTION_PROMPT
)


class RateLimitError(Exception):
    def __init__(self, provider: str, message: str, retry_after: int = 0, is_daily_limit: bool = None):
        self.provider = provider
        self.retry_after = retry_after
        if is_daily_limit is not None:
            self.is_daily_limit = is_daily_limit
        else:
            self.is_daily_limit = "per day" in message.lower() or "tpd" in message.lower() or "rpd" in message.lower()
        super().__init__(message)


def extract_text_from_pdf(pdf_path: str) -> str:
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts)


def extract_text_from_docx(docx_path: str) -> str:
    from docx import Document
    doc = Document(docx_path)
    text_parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            text_parts.append(para.text.strip())
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells if cell.text.strip())
            if row_text:
                text_parts.append(row_text)
    return "\n\n".join(text_parts)


def extract_text_from_image(image_path: str) -> str:
    import pytesseract
    from PIL import Image
    img = Image.open(image_path)
    text = pytesseract.image_to_string(img)
    return text


def _parse_retry_after(error_msg: str) -> int:
    match = re.search(r"try again in (\d+)m(\d+\.?\d*)s", error_msg)
    if match:
        minutes = int(match.group(1))
        seconds = float(match.group(2))
        return int(minutes * 60 + seconds)
    match = re.search(r"retry-after[:\s]+(\d+)", error_msg, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return 0


def _extract_with_gemini(cv_text: str) -> str:
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = EXTRACTION_PROMPT.format(text=cv_text)
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt
            )
            return response.text.strip()
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                retry_after = _parse_retry_after(error_msg)
                raise RateLimitError("Gemini", error_msg, retry_after)
            raise Exception(f"Gemini API error: {error_msg}")
    return ""


def _extract_with_groq(cv_text: str) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    prompt = EXTRACTION_PROMPT.format(text=cv_text)
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": "You are a CV/resume data extraction assistant. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.0,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate_limit" in error_msg.lower():
                retry_after = _parse_retry_after(error_msg)
                raise RateLimitError("Groq", error_msg, retry_after)
            raise Exception(f"Groq API error: {error_msg}")
    return ""


def _parse_json_response(raw_response: str) -> dict:
    if raw_response.startswith("```"):
        raw_response = raw_response.split("\n", 1)[1]
        if raw_response.endswith("```"):
            raw_response = raw_response[:-3]
        raw_response = raw_response.strip()

    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        data = {}

    required_keys = [
        "candidate_name", "contact_number", "email", "gender", "age",
        "total_experience_years", "last_employer", "key_skills", "current_job_title"
    ]
    for key in required_keys:
        if key not in data:
            data[key] = None

    return data


def extract_candidate_data(cv_text: str) -> dict:
    errors = []
    rate_limit_errors = []

    providers = []
    if AI_PROVIDER == "groq":
        providers = ["groq"]
    elif AI_PROVIDER == "gemini":
        providers = ["gemini"]
    else:
        if GROQ_API_KEY:
            providers.append("groq")
        if GEMINI_API_KEY:
            providers.append("gemini")

    for provider in providers:
        try:
            if provider == "groq":
                raw_response = _extract_with_groq(cv_text)
            else:
                raw_response = _extract_with_gemini(cv_text)
            return _parse_json_response(raw_response)
        except RateLimitError as e:
            rate_limit_errors.append(e)
            errors.append(f"{e.provider}: {e}")
            continue
        except Exception as e:
            errors.append(f"{provider}: {e}")
            continue

    if rate_limit_errors:
        worst = max(rate_limit_errors, key=lambda x: x.retry_after)
        raise RateLimitError(
            worst.provider,
            f"Daily limit reached for {worst.provider}. Resets at midnight UTC.",
            worst.retry_after,
            is_daily_limit=True
        )

    raise Exception(f"All AI providers failed:\n" + "\n".join(errors))


def process_cv(pdf_path: str) -> tuple[dict, str]:
    ext = os.path.splitext(pdf_path)[1].lower()

    if ext == ".pdf":
        cv_text = extract_text_from_pdf(pdf_path)
    elif ext == ".docx":
        cv_text = extract_text_from_docx(pdf_path)
    elif ext in (".png", ".jpg", ".jpeg"):
        cv_text = extract_text_from_image(pdf_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")

    if not cv_text.strip():
        raise ValueError(f"Could not extract text from {ext} file. The file may be empty or unreadable.")

    extracted_data = extract_candidate_data(cv_text)
    return extracted_data, cv_text
