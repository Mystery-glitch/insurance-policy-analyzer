# Insurance Policy Analyzer

AI-powered insurance policy analyzer that extracts and simplifies complex insurance documents into plain English, with interactive Q&A.

## Features

- **PDF Upload** — Upload scanned, unscanned, or hybrid insurance policy PDFs
- **Smart Text Extraction** — Uses PyMuPDF for digital text and OCRmyPDF for scanned pages
- **AI-Powered Analysis** — Uses Google Gemini for plain-English summaries, coverage breakdowns, exclusion warnings, and risk alerts
- **RAG-based Q&A** — Ask natural-language questions about your specific policy, with answers grounded in the actual document and cited by page
- **FastAPI Backend** — RESTful API for document processing

## System Prerequisites

```bash
# macOS
brew install tesseract ghostscript

# Ubuntu / Debian
sudo apt-get install tesseract-ocr ghostscript
```

## Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your Gemini API key
# Get one free at: https://aistudio.google.com/apikey
```

## Running the Application

```bash
# Run and allow access from other devices on your Wi-Fi:
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Or simply:
python -m app.main
```

- On your machine: visit **`http://127.0.0.1:8000`**
- On other devices on your network: visit **`http://<YOUR_IP>:8000`**
- Interactive API docs: **`http://127.0.0.1:8000/docs`**

## API Endpoints

| Method | Endpoint             | Description                                          |
|--------|----------------------|------------------------------------------------------|
| POST   | `/api/v1/upload-pdf` | Upload a PDF and extract its text                    |
| POST   | `/api/v1/analyze`    | Upload a PDF, extract text, get AI analysis + index  |
| POST   | `/api/v1/ask`        | Ask a question about an analyzed policy              |
| GET    | `/health`            | Health check                                         |

## Usage Flow

### Step 1: Analyze a policy
```bash
curl -X POST http://127.0.0.1:8000/api/v1/analyze \
  -F "file=@your_policy.pdf"
```

Response includes a `document_id` along with:
- **summary** — Plain-English overview of the policy
- **policy_type** — Type of insurance
- **coverage_highlights** — What's covered, with limits
- **exclusions** — What's NOT covered, with severity ratings
- **key_conditions** — Waiting periods, deductibles, claim procedures
- **risk_alerts** — Warnings about hidden gotchas
- **jargon_glossary** — Technical terms translated to simple language

### Step 2: Ask questions
```bash
curl -X POST http://127.0.0.1:8000/api/v1/ask \
  -H "Content-Type: application/json" \
  -d '{"document_id": "<id_from_step_1>", "question": "Am I covered for hospitalization abroad?"}'
```

Response includes:
- **answer** — Grounded, plain-English answer
- **confidence** — high / medium / low
- **sources** — Page references and excerpts from the policy
- **follow_up_questions** — Suggested related questions

## Web Application (UI)

A modern, glassmorphic web dashboard is bundled and served directly by the FastAPI backend:

- Open your browser to **`http://127.0.0.1:8000`**
- **Drag-and-drop** any insurance PDF (digital or scanned)
- Review **plain-English summaries**, **coverage limits**, and **color-coded exclusions** (High, Medium, Low severity)
- Get **risk alerts** warning of hidden room-rent limits, waiting periods, and gotchas
- Use the **interactive RAG chat** with cited policy excerpts and instant follow-up questions
- Click **"Explore Sample Policy"** to preview the dashboard instantly with pre-loaded demo data

## Project Structure

```
InsurancePolicyAnalyzer/
├── app/
│   ├── main.py                # FastAPI app entry point & SPA static mount
│   ├── api/
│   │   └── routes/
│   │       ├── upload.py      # Text extraction endpoint
│   │       ├── analyze.py     # AI analysis & RAG indexing endpoint
│   │       └── ask.py         # RAG Q&A endpoint
│   ├── core/
│   │   └── config.py          # App settings & environment config
│   └── services/
│       ├── pdf_extractor.py   # Hybrid PDF text extraction (PyMuPDF + OCRmyPDF)
│       ├── policy_analyzer.py # Gemini-powered plain-English policy analysis
│       ├── text_chunker.py    # Overlapping semantic text chunker for RAG
│       ├── vector_store.py    # ChromaDB + Gemini text-embedding-004
│       └── qa_service.py      # Grounded RAG Q&A pipeline with citations
├── frontend/                  # Modern Glassmorphic Web UI
│   ├── index.html             # Responsive semantic HTML5 dashboard
│   ├── css/
│   │   └── styles.css         # Dark theme, glassmorphic design system
│   └── js/
│       └── app.js             # Drag-drop, analysis stepper, tabs & RAG chat
├── .env.example               # Environment variable template
├── requirements.txt           # Python dependencies (FastAPI, PyMuPDF, OCR, Gemini, ChromaDB, aiofiles)
└── README.md
```
