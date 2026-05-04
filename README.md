# RegLens AI 🔍
### AI-Powered Regulatory Compliance Assistant for FinTechs & MSMEs

## Problem
Indian FinTechs and MSMEs operate under regulations from RBI, GST Council, 
SEBI, and MCA — published as complex legal PDFs. Most businesses either 
under-comply (risking penalties) or over-comply (wasting resources) because 
they cannot interpret and apply regulations to their specific business context.

## Solution
RegLens AI reads real government regulations, understands your business 
profile, and tells you exactly which laws apply and what you must do — 
with explainable, auditable reasoning.

## How It Works
1. User inputs business profile (type, sector, transaction nature)
2. RAG pipeline retrieves relevant regulation chunks from 12 government documents
3. LLM reasons applicability: Applicable / Conditional / Not Applicable
4. System outputs compliance checklist + risk level + plain-English explanation

## Tech Stack
- **LLM:** Groq LLaMA 3.3 70B via Groq API
- **Vector DB:** ChromaDB
- **Embeddings:** sentence-transformers
- **Backend:** FastAPI
- **Frontend:** Streamlit
- **PDF Parsing:** pdfplumber
- **Database:** SQLite for request audit logging

## Regulatory Coverage
- RBI KYC Master Direction
- RBI Payment Aggregators Guidelines
- RBI Digital Lending Guidelines 2022
- RBI NBFC Master Directions
- CGST Rules 2017
- MSME Udyam Registration
- FEMA 1999
- Companies Act 2013 (MCA)

## Setup Instructions
```bash
git clone https://github.com/YOUR_USERNAME/reglens-ai
cd reglens-ai
python -m pip install -r requirements.txt
# Create a .env file in the project root and set GROQ_API_KEY
```

### Run locally
1. Start the backend:
```bash
uvicorn src.api:app --reload --host 0.0.0.0 --port 8000
```
2. Start the frontend:
```bash
streamlit run src/app.py
```

### Run with Docker Compose
```bash
docker compose up --build
```

## Notes
- Keep `.env` secret and out of source control.
- The app requires a `GROQ_API_KEY` for Groq LLaMA 3.3.
- The frontend sends requests to the backend at `http://localhost:8000` by default.

## Notes
- Keep `.env` secret and out of source control.
- The app requires a `GROQ_API_KEY` for Groq LLaMA 3.3.

## Hackathon
ET AI Hackathon 2026 — Problem Statement 5: Domain-Specialized AI Agents 
with Compliance Guardrails

## Team - ZenAI
- Zaira Hussain — zairahussain27
