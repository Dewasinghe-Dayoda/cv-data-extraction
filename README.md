# CV Data Extraction Tool

A Streamlit-based web application that automatically extracts key candidate information from PDF CVs using AI and exports structured data to Excel.

## Features

- **Bulk CV Upload** — Upload multiple PDF CVs at once
- **AI-Powered Extraction** — Automatically extracts candidate details using LLM (Groq / Gemini)
- **Candidate History** — View, search, edit, and delete extracted candidates
- **Excel Export** — Download formatted Excel files with all candidate data
- **Accuracy Controls** — Edit any extracted field before export

### Extracted Fields

| Field | Description |
|-------|-------------|
| Candidate Name | Full name from the CV |
| Contact Number | Phone with country code |
| Email Address | Email from CV |
| Gender | If explicitly stated |
| Age | If explicitly stated |
| Total Experience | Calculated from work history dates |
| Last Employer | Most recent employer |
| Key Skills | Top 10 skills extracted |
| Job Title | Current or most recent position |

## Tech Stack

| Component | Technology |
|-----------|------------|
| Frontend | Streamlit |
| PDF Text Extraction | pdfplumber |
| AI Extraction | Groq (Llama 3.3) or Google Gemini |
| Database | SQLite |
| Excel Export | openpyxl |

## Prerequisites

- Python 3.10 or higher
- A free Groq API key **or** Google Gemini API key

## Installation

```bash
# Clone or download the project
cd "CV Data Extraction"

# Install dependencies
pip install -r requirements.txt
```

## Configuration

1. Copy the example environment file:
   ```bash
   copy .env.example .env
   ```

2. Edit `.env` and add your API key:

   **Option A — Groq (Recommended, Free)**
   ```
   AI_PROVIDER=groq
   GROQ_API_KEY=your_key_here
   ```
   Get a free key at https://console.groq.com (30 seconds to sign up)

   **Option B — Google Gemini (Free)**
   ```
   AI_PROVIDER=gemini
   GEMINI_API_KEY=your_key_here
   ```
   Get a free key at https://aistudio.google.com/apikey

## Running the App

```bash
streamlit run app.py
```

The app opens at http://localhost:8501

## Usage

### 1. Upload & Extract
- Navigate to **Upload & Extract** in the sidebar
- Drag and drop one or more PDF CVs
- Click **Extract Data from All CVs**
- Review the extracted results in expandable sections

### 2. Candidate History
- Navigate to **Candidate History**
- Search by name, email, skills, or job title
- Filter by status (extracted / reviewed)
- Click on any candidate to view full details
- Edit fields inline and click **Save Changes**
- Delete candidates with confirmation

### 3. Export to Excel
- Navigate to **Export to Excel**
- Optionally filter by name/skills/status
- Preview the data in the table
- Click **Download Excel File** to get a formatted `.xlsx` file

## Project Structure

```
CV Data Extraction/
├── app.py              # Main Streamlit application (UI)
├── config.py           # Settings, API keys, extraction prompt
├── database.py         # SQLite database operations
├── extractor.py        # PDF text extraction + AI parsing
├── excel_export.py     # Excel file generation
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variable template
├── .env                # Your API keys (git-ignored)
├── .streamlit/
│   └── config.toml     # Streamlit configuration
├── uploads/            # Stored uploaded PDFs
├── exports/            # Generated Excel files
└── data/               # SQLite database
    └── candidates.db
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "No AI API key configured" | Add `GROQ_API_KEY` to your `.env` file |
| "Could not extract text from PDF" | PDF may be scanned/image-based — use digital PDFs |
| Extraction accuracy is low | Review and edit fields manually in Candidate History |
| App won't start | Run `pip install -r requirements.txt` to install dependencies |
| Port already in use | Run `streamlit run app.py --server.port 8502` |

## Accuracy Notes

The AI extraction works best with:
- Digital/text-based PDFs (not scanned images)
- Standard CV formats with clear sections
- English language CVs

For any extraction errors, use the **Candidate History** page to manually correct fields before exporting.
