# DocMind — RAG Q&A Bot

A full-stack document Q&A application that lets you chat with your PDFs using AI.

## 🌐 Live Demo
[https://ragbot-nmjo.onrender.com](https://ragbot-nmjo.onrender.com)

## ✨ Features
- Upload PDFs, DOCX, TXT files and chat with them
- AI answers strictly from your documents
- Per-document selection for targeted search
- Multi-session chat with history
- Document auto-summary generation
- User authentication (signup/login/logout)
- Dark/Light mode toggle
- OCR support for scanned PDFs (local)
- Background indexing for large documents

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django + Django REST Framework |
| Database | Supabase (PostgreSQL) |
| Vector DB | Pinecone |
| LLM | Groq (Llama 3.3 70B) |
| Embeddings | Pinecone Inference API (llama-text-embed-v2) |
| Frontend | HTML, CSS, Vanilla JavaScript |
| Deployment | Render |

## 🏗️ Architecture
User uploads PDF

↓

Text extracted (PyPDF / OCR)

↓

Text chunked into pieces

↓

Chunks embedded via Pinecone Inference API

↓

Vectors stored in Pinecone

↓

User asks question

↓

Question embedded → Pinecone similarity search

↓

Relevant chunks sent to Groq LLM

↓

Answer generated strictly from document context

## 🚀 Local Setup

### 1. Clone the repo
```bash
git clone https://github.com/BishwajeetSenapati/ragbot.git
cd ragbot
```

### 2. Create virtual environment
```bash
python -m venv env
source env/Scripts/activate  # Windows
source env/bin/activate       # Mac/Linux
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Create `.env` file
SECRET_KEY=your-secret-key

DEBUG=True

DB_NAME=postgres

DB_USER=your-supabase-user

DB_PASSWORD=your-supabase-password

DB_HOST=your-supabase-host

DB_PORT=5432

GROQ_API_KEY=your-groq-api-key

PINECONE_API_KEY=your-pinecone-api-key

PINECONE_INDEX=ragbot

TESSERACT_CMD=C:\Program Files\Tesseract-OCR\tesseract.exe

POPPLER_PATH=C:\poppler-26.02.0\Library\bin

### 5. Run migrations
```bash
python manage.py migrate
```

### 6. Start server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000`

## 📁 Project Structure
ragbot/

├── rag_project/          # Django config

│   ├── settings.py

│   └── urls.py

├── rag_app/              # Main app

│   ├── models.py         # Database models

│   ├── views.py          # API views

│   ├── rag_pipeline.py   # RAG logic

│   ├── templates/        # HTML templates

│   └── static/           # CSS & JavaScript

├── requirements.txt

├── Procfile

├── build.sh

└── .env                  # Not in repo

## 🔑 Required API Keys

| Service | Purpose | Free Tier |
|---|---|---|
| [Groq](https://console.groq.com) | LLM for generating answers | ✅ Free |
| [Pinecone](https://pinecone.io) | Vector database | ✅ Free |
| [Supabase](https://supabase.com) | PostgreSQL database | ✅ Free |

## 📄 License
MIT
