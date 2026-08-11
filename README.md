# CV Data Extraction Tool

A Streamlit-based web application that automatically extracts key candidate information from PDF, DOCX, and image CVs using AI and exports structured data to Excel.

## Features

- **Multi-Format Upload** — Upload PDF, DOCX, PNG, JPG CV files
- **AI-Powered Extraction** — Automatically extracts candidate details using LLM (Groq / Gemini with auto-fallback)
- **Candidate History** — View, search, edit, and delete extracted candidates
- **Excel Export** — Download formatted Excel files with all candidate data
- **Accuracy Controls** — Edit any extracted field before export
- **Password Protection** — Basic access gate for internal network use

### Extracted Fields

| Field | Description |
|-------|-------------|
| Candidate Name | Full name from the CV |
| Contact Number | Phone with country code |
| Email Address | Email from CV |
| Gender | Explicit or inferred from name |
| Age | Calculated from DOB if provided |
| Total Experience | Calculated from work history dates |
| Last Employer | Most recent employer |
| Key Skills | Top 10 skills extracted |
| Job Title | Current or most recent position |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| PDF Text Extraction | pdfplumber |
| DOCX Text Extraction | python-docx |
| Image OCR | Tesseract + pytesseract |
| AI Extraction | Groq (Llama 3.3) / Google Gemini (auto-fallback) |
| Database | SQLite |
| Excel Export | openpyxl |

## Prerequisites

- Python 3.11 or higher
- Tesseract OCR (for image CV support)
- A free Groq API key **and/or** Google Gemini API key

## Installation (Local Development)

```bash
# Clone the repository
git clone https://github.com/Dewasinghe-Dayoda/cv-data-extraction.git
cd cv-data-extraction

# Install dependencies
pip install -r requirements.txt

# Create .env from template
cp .env.example .env

# Edit .env with your API keys
# At minimum, add GROQ_API_KEY or GEMINI_API_KEY
```

## Configuration

Create a `.env` file (never commit this to git):

```bash
# AI Provider: "groq", "gemini", or "auto" (tries both, falls back automatically)
AI_PROVIDER=auto

# Get a free Groq key at https://console.groq.com
GROQ_API_KEY=your_groq_api_key_here

# Get a free Gemini key at https://aistudio.google.com/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: Set a password to protect the app on your network
APP_PASSWORD=your_secure_password_here
```

## Running Locally

```bash
streamlit run app.py
```

The app opens at http://localhost:8501

---

## Docker Deployment (Internal Server)

### Quick Start

```bash
# 1. Clone the repository on your server
git clone https://github.com/Dewasinghe-Dayoda/cv-data-extraction.git
cd cv-data-extraction

# 2. Create .env file with your keys
cp .env.example .env
nano .env   # Add your API keys and password

# 3. Build and start
docker compose up -d --build

# 4. Access the app
# Open browser: http://YOUR_SERVER_IP:8501
```

### How to Update

```bash
# Pull latest changes
git pull

# Rebuild and restart (data is NOT lost — volumes persist)
docker compose up -d --build
```

**Important:** The `docker compose up -d --build` command rebuilds the container image but does NOT touch the Docker volumes where your database, uploads, and exports are stored. Your data is safe.

### How to Check Logs

```bash
docker compose logs -f
```

### How to Stop

```bash
docker compose down
```

### How to Restart

```bash
docker compose restart
```

### Data Persistence

The following data is stored in Docker volumes and persists across container rebuilds and restarts:

| Data | Volume | Why It Persists |
|------|--------|-----------------|
| SQLite database (`candidates.db`) | `app-data` | Contains all extracted candidate records |
| Uploaded CV files | `app-uploads` | Original PDFs/DOCX/images for audit trail |
| Exported Excel files | `app-exports` | Generated reports |

**If you need to back up the data:**

```bash
# Backup the database
docker compose exec cv-extraction cat /app/data/candidates.db > backup_candidates.db

# Or copy all persistent data
docker cp cv-extraction-app:/app/data ./backup-data
docker cp cv-extraction-app:/app/uploads ./backup-uploads
docker cp cv-extraction-app:/app/exports ./backup-exports
```

### Security Notes

- **Never commit `.env` to git** — it contains API keys and passwords
- **`.env` must be created manually on each server** — it's git-ignored
- The app runs as a **non-root user** inside the container
- **APP_PASSWORD** provides basic access control — change it from the default
- For production, consider adding HTTPS via a reverse proxy (nginx)

## Project Structure

```
cv-data-extraction/
├── app.py              # Main Streamlit application (UI + auth gate)
├── config.py           # Settings, API keys, extraction prompt
├── database.py         # SQLite database operations
├── extractor.py        # PDF/DOCX/image text extraction + AI parsing
├── excel_export.py     # Excel file generation
├── requirements.txt    # Pinned Python dependencies
├── Dockerfile          # Container image definition
├── docker-compose.yml  # Container orchestration with volumes
├── .dockerignore       # Files excluded from Docker build
├── .env.example        # Environment variable template
├── .env                # Your API keys (git-ignored, never committed)
├── .gitignore          # Git ignore rules
├── .streamlit/
│   └── config.toml     # Streamlit server configuration
├── uploads/            # Stored uploaded CV files (persisted via volume)
├── exports/            # Generated Excel files (persisted via volume)
└── data/               # SQLite database (persisted via volume)
    └── candidates.db
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No AI API key configured" | Add `GROQ_API_KEY` to your `.env` file |
| "Could not extract text from PDF" | PDF may be scanned/image-based — use digital PDFs |
| "Rate limit reached" | Both API quotas exhausted — wait for midnight UTC reset, or upgrade to Groq paid tier |
| "Incorrect password" | Check `APP_PASSWORD` in your `.env` file |
| App won't start | Run `docker compose logs` to see the error |
| Port already in use | Change port in `docker-compose.yml`: `"8502:8501"` |
| Container won't rebuild | Run `docker compose down && docker compose up -d --build` |

## API Rate Limits

| Provider | Free Tier Limit | Resets |
|----------|----------------|--------|
| Groq | 100K tokens/day, 30 req/min | Midnight UTC |
| Gemini | 1,500 req/day, 15 req/min | Midnight Pacific |

The app uses **auto-fallback**: if Groq hits its limit, it automatically tries Gemini. If both fail, it shows a clear message with the wait time.

## Accuracy Notes

The AI extraction works best with:
- Digital/text-based PDFs (not scanned images)
- Standard CV formats with clear sections
- English language CVs

For any extraction errors, use the **Candidate History** page to manually correct fields before exporting.
