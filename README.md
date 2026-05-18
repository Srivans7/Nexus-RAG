# Nexus RAG

A document question-answering app built with Django and React. Upload your files, ask questions, and get answers grounded in your documents — powered by Google Gemini and FAISS vector search.

**Live demo:** [nexus-rag-gamma.vercel.app](https://nexus-rag-gamma.vercel.app)

---

## What it does

You upload a document (PDF, markdown, or text), the backend breaks it into chunks, embeds them using Gemini, and stores them in a FAISS index. When you ask a question, the most relevant chunks are retrieved and sent to Gemini as context to generate a grounded answer.

---

## Tech stack

**Backend**
- Django 6 + Django REST Framework
- Google Gemini (embeddings + LLM)
- FAISS for vector search
- LangChain for document loading and chunking
- Gunicorn — deployed on [Render](https://render.com)

**Frontend**
- React + Vite + Tailwind CSS
- Google OAuth login
- Deployed on [Vercel](https://vercel.com)

---

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/` | Basic health check |
| GET | `/api/health/llm/` | Gemini connectivity check |
| POST | `/api/upload/` | Upload a document |
| POST | `/api/documents/<id>/process/` | Process document into chunks + embeddings |
| POST | `/api/ask/` | Ask a question over all processed documents |
| GET/POST | `/api/chats/` | Chat session management |
| POST | `/api/auth/google/` | Google OAuth login |

### Example

```bash
# Upload a file
curl -X POST https://nexus-rag-backend-lkhp.onrender.com/api/upload/ \
  -F "original_file=@notes.pdf"

# Ask a question
curl -X POST https://nexus-rag-backend-lkhp.onrender.com/api/ask/ \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the main topic of the document?"}'
```

---

## Running locally

```bash
# Clone and set up
git clone https://github.com/Srivans7/Nexus-RAG.git
cd Nexus-RAG
python -m venv .venv
.venv\Scripts\activate       # Windows
pip install -r requirements.txt

# Set env vars (create a .env or export manually)
set RAG_GEMINI_API_KEY=your_key_here

# Run
python manage.py migrate
python manage.py runserver
```

For the frontend:

```bash
cd frontend
npm install
echo VITE_API_BASE_URL=http://localhost:8000 > .env.local
npm run dev
```

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `RAG_GEMINI_API_KEY` | Google Gemini API key |
| `RAG_GEMINI_MODEL` | Model name (default: `gemini-2.5-flash`) |
| `SECRET_KEY` | Django secret key |
| `ALLOWED_HOSTS` | Comma-separated list of allowed hosts |
| `CORS_ALLOWED_ORIGINS` | Frontend origin (e.g. `https://nexus-rag-gamma.vercel.app`) |
| `JWT_SECRET_KEY` | Secret for JWT tokens |

---

## License

MIT © [Srivans Katriyar](https://github.com/Srivans7)
