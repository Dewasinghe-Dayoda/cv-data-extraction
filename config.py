import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent
UPLOADS_DIR = BASE_DIR / "uploads"
EXPORTS_DIR = BASE_DIR / "exports"
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "candidates.db"

UPLOADS_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)
DATA_DIR.mkdir(exist_ok=True)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

AI_PROVIDER = os.getenv("AI_PROVIDER", "groq")

GEMINI_MODEL = "gemini-2.0-flash"
GROQ_MODEL = "llama-3.3-70b-versatile"

ALLOWED_EXTENSIONS = {"pdf"}
MAX_FILE_SIZE_MB = 10

EXTRACTION_PROMPT = """You are a precise CV/resume data extractor. Analyze the CV text below and extract the following fields.

Return ONLY a valid JSON object with these exact keys:
{{
  "candidate_name": "string or null",
  "contact_number": "string or null",
  "email": "string or null",
  "gender": "string or null",
  "age": "string or null",
  "total_experience_years": "string",
  "last_employer": "string or null",
  "key_skills": "comma-separated string or null",
  "current_job_title": "string"
}}

CRITICAL RULES FOR total_experience_years:
1. If the CV explicitly states "X years of experience", use that.
2. Count ALL work: full-time, part-time, internships, freelance, contract
3. Calculate from earliest work start date to today
4. If less than 1 year, return "X months" (e.g., "4 months")
5. If 1+ years, return like "3", "5", or "8"
6. If candidate is a fresher (no work experience at all), return "Fresher"
7. If candidate is currently studying with no work, return "Fresher"
8. Education status doesn't matter — count actual work only
9. Never return null for this field

CRITICAL RULES FOR current_job_title:
1. If the CV states a current job title, use that.
2. If the CV shows work history, use the most recent job title.
3. If the candidate is a fresher/student with no work experience, return "Fresher".
4. If no job title can be determined at all, return "-".
5. Never return null for this field.

RULES FOR last_employer:
1. If the CV states a current/most recent employer, use that.
2. If the candidate is a fresher/student, return null.
3. If no employer can be determined, return null.

CRITICAL RULES FOR age:
1. Today's date is 2026-08-05. Use this as reference.
2. If the CV explicitly states age, return that number.
3. If the CV states a birth DATE (not just year), calculate: 2026 - birth_year. If the birthday has not passed yet this year, subtract 1.
4. If the CV states only a birth YEAR (e.g., "born 1995"), calculate: 2026 - birth_year = 31.
5. If no explicit birth date or birth year is found, return null. Do NOT guess age from graduation year, experience, or other clues.

OTHER RULES:
- For skills, list the top 10 most relevant skills from the CV
- For contact_number, include country code if present
- For gender, use this approach:
  1. If explicitly stated in the CV (e.g., "Gender: Male"), use that.
  2. If the CV contains pronouns (he/she/him/her), use those.
  3. If neither, infer from the candidate's FIRST NAME using common name associations worldwide (e.g., "John" → Male, "Maria" → Female, "Raj" → Male, "Priya" → Female, "Chamali" → Female, "Dilani" → Female).
  4. If the name is ambiguous or unfamiliar, return "Unknown".
  5. Always make your best guess — do not return null for gender unless the name is truly unrecognizable.
- Return null for any field not found — do not guess or hallucinate
- Be precise and thorough: read the ENTIRE CV text before extracting

CV Text:
{text}"""
