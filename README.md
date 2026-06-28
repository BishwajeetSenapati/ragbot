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
