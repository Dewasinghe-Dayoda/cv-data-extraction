import json
import time
import os
import pdfplumber
from config import (
    GEMINI_API_KEY, GEMINI_MODEL,
    GROQ_API_KEY, GROQ_MODEL,
    AI_PROVIDER, EXTRACTION_PROMPT
)


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


def _extract_with_gemini(cv_text: str) -> str:
    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = EXTRACTION_PROMPT.format(text=cv_text)
    max_retries = 3
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
                if attempt < max_retries - 1:
                    wait_time = 10 * (attempt + 1)
                    time.sleep(wait_time)
                    continue
            raise Exception(f"Gemini API error: {error_msg}")
    return ""


def _extract_with_groq(cv_text: str) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    prompt = EXTRACTION_PROMPT.format(text=cv_text)
    max_retries = 3
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
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    time.sleep(wait_time)
                    continue
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

    if AI_PROVIDER == "gemini" or (AI_PROVIDER == "auto" and GEMINI_API_KEY):
        try:
            raw_response = _extract_with_gemini(cv_text)
            return _parse_json_response(raw_response)
        except Exception as e:
            errors.append(f"Gemini: {e}")

    if AI_PROVIDER == "groq" or (AI_PROVIDER == "auto" and GROQ_API_KEY) or not errors:
        try:
            raw_response = _extract_with_groq(cv_text)
            return _parse_json_response(raw_response)
        except Exception as e:
            errors.append(f"Groq: {e}")

    if AI_PROVIDER == "gemini" and GEMINI_API_KEY and not GROQ_API_KEY:
        raise Exception(
            "Gemini API quota exhausted. Get a free Groq API key at https://console.groq.com\n"
            "Add GROQ_API_KEY to your .env file and set AI_PROVIDER=groq"
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
