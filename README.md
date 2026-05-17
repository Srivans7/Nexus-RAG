# Django DRF RAG Backend

This project provides a clean backend scaffold for a Retrieval-Augmented Generation (RAG) workflow using Django + Django REST Framework.

## Step-by-step build summary

1. Created Django project: `config`
2. Created app: `rag`
3. Added dependencies: Django, DRF, PyPDF
4. Added file storage for uploaded documents in `documents/`
5. Implemented models for documents and Q&A logs
6. Implemented service layer for:
  - file parsing (`.md`, `.txt`, `.pdf`)
  - document processing
  - question answering
7. Implemented LangChain-based utility pipeline for document processing:
  - loaders: `TextLoader` and `PyPDFLoader`
  - text cleanup/normalization
  - chunking with `RecursiveCharacterTextSplitter`
  - chunk size: `500`
  - chunk overlap: `50`
  - persistent chunk storage in database
  - structured processing errors
8. Implemented embedding + vector storage pipeline:
  - model: `sentence-transformers/all-MiniLM-L6-v2`
  - chunk embedding generation with sentence-transformers
  - local FAISS persistence for semantic retrieval
  - reusable services for embedding, FAISS load/save, and similarity search
9. Implemented DRF serializers, API views, and URL routes
10. Created and applied migrations
11. Validated the project with `manage.py check`

## API Endpoints

- `POST /api/rag/upload/`
  - Upload a file in form-data key: `original_file`
- `POST /api/rag/documents/<document_id>/process/`
  - Process uploaded document into extracted text and chunks
  - Returns:
    - `document` metadata
    - `chunks` array (chunk index, content, metadata)
- `POST /api/rag/question-answer/`
  - Request body:
    ```json
    {
      "question": "What is this document about?",
      "document_id": 1
    }
    ```
  - `document_id` is optional; if omitted, the endpoint searches all processed documents

- `POST /api/ask/`
  - Full Retrieval-Augmented Generation pipeline endpoint
  - Request body:
    ```json
    {
      "question": "What does the uploaded document say about deployment?"
    }
    ```

- `GET /api/health/ollama/`
  - Checks Ollama connectivity and confirms `llama3` model availability
  - Returns 200 when healthy, 503 when unreachable or model is missing
  - Response body:
    ```json
    {
      "answer": "...",
      "sources": [
        {
          "document_id": 1,
          "file_name": "notes.md",
          "chunk_index": 2,
          "score": 0.81
        }
      ]
    }
    ```

## Vector Search Storage

- FAISS index file: `vector_store/rag_chunks.faiss`
- Metadata file: `vector_store/rag_chunks_metadata.json`
- Embedding model: `sentence-transformers/all-MiniLM-L6-v2`

## Complete RAG Ask Pipeline

1. Accept question from `POST /api/ask/`
2. Retrieve top relevant chunks from FAISS
3. Build a grounded prompt template with source-tagged context
4. Send prompt to local Ollama (`llama3`)
5. Return generated answer with source metadata

### Ollama configuration

- Base URL: `http://127.0.0.1:11434`
- Model: `llama3`
- Configurable via Django settings:
  - `RAG_OLLAMA_BASE_URL`
  - `RAG_OLLAMA_MODEL`
  - `RAG_OLLAMA_TIMEOUT_SECONDS`

### Fallback behavior

- If Ollama is unavailable, the pipeline can return retrieval-only context fallback
- Controlled by setting: `RAG_ENABLE_LLM_FALLBACK`
- Default: `True`

## Run the server

```powershell
c:/Users/Lenovo/OneDrive/Desktop/RAG/.venv/Scripts/python.exe manage.py runserver
```

## Notes

- Uploaded files are stored under `documents/`
- PDF parsing uses `pypdf`
- QA logic is intentionally lightweight and can be replaced with embeddings/vector database + LLM integration later
