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

ALLOWED_EXTENSIONS = {"pdf", "docx", "png", "jpg", "jpeg"}
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
2. Count ALL work: full-time, part-time, internships, freelance, contract.
3. STEP-BY-STEP METHOD: List each job with its duration, then add them up:
   - Job 1: Start → End = X months
   - Job 2: Start → End = X months
   - TOTAL = Job 1 + Job 2
4. For each job duration:
   - If "Present" or "Current" → use Aug 2026 as end date
   - If has end date → use that date
   - Calculate months between start and end
5. OUTPUT FORMAT (strictly follow):
   - If total < 12 months → return "X Months" (e.g., "4 Months", "11 Months")
   - If total ≥ 12 months with no leftover months → return "X Years" (e.g., "3 Years")
   - If total ≥ 12 months with leftover → return "X Year Y Months" (e.g., "1 Year 5 Months", "2 Years 6 Months")
   - Use singular "Year" for exactly 1, plural "Years" for 2+
   - If NO work experience at all → return "Fresher"
6. IMPORTANT: If the CV lists ANY job, internship, or work experience, do NOT return "Fresher". Only return "Fresher" if there is ZERO work history.
7. Never return "0" if work history exists.
8. Never return null for this field.

EXAMPLE CALCULATIONS:
Example 1 - Multiple jobs:
CV says: "Intern | Jul 2023 - Apr 2024" and "Engineer | Apr 2024 - Present"
- Intern: Jul 2023 to Apr 2024 = 9 months
- Engineer: Apr 2024 to Aug 2026 = 28 months
- TOTAL: 9 + 28 = 37 months = 3 Years 1 Month
Return: "3 Years 1 Month"

Example 2 - Short job:
CV says: "Admin Officer | Jan 2025 - Apr 2025"
- TOTAL: 3 months
Return: "3 Months"

Example 3 - Exact years:
CV says: "Engineer | Mar 2023 - Mar 2026"
- TOTAL: 36 months = 3 Years
Return: "3 Years"

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
