# Frontend (React + Vite)

## Environment Variables

Create a `.env` file in `frontend/` (or copy `.env.example`) and configure:

- `VITE_API_BASE_URL`: Django backend base URL. Example: `http://127.0.0.1:8000`
- `VITE_API_TIMEOUT_MS`: API timeout in milliseconds. Example: `120000`

If `VITE_API_BASE_URL` is left empty, Vite proxy rules in `vite.config.js` are used during development.

## Run

```bash
npm install
npm run dev
```

## Build

```bash
npm run build
```

## API Layer Structure

- `src/services/httpClient.js`: shared axios client
- `src/services/uploadService.js`: upload and document processing APIs
- `src/services/ragService.js`: ask, stream ask, and health APIs
- `src/services/errorService.js`: shared API error normalization
- `src/services/api.js`: compatibility export layer
