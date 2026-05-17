# Deployment Guide - Nexus AI

## Overview
Nexus AI consists of two parts:
1. **Frontend** (React/Vite) → Deploy to Vercel ✓
2. **Backend** (Django) → Deploy separately (Render, Railway, Heroku, etc.)

---

## Part 1: Frontend Deployment to Vercel

### Prerequisites
- GitHub account with repository
- Vercel account (free tier available)
- Frontend environment variables

### Step 1: Prepare for Vercel

The `vercel.json` file is already configured with:
- Build command: `cd frontend && npm install && npm run build`
- Output directory: `frontend/dist`
- Framework: Vite

### Step 2: Set Environment Variables in Vercel

You need to set these variables in Vercel dashboard:

| Variable | Value | Example |
|----------|-------|---------|
| `VITE_GOOGLE_CLIENT_ID` | Your Google OAuth Client ID | `872755425627-kmcht0c050hgsjd5tjkkn3h5n2ad3d1l.apps.googleusercontent.com` |
| `VITE_API_BASE_URL` | Backend API URL | `https://your-backend.herokuapp.com` or `https://your-backend.railway.app` |
| `VITE_API_TIMEOUT_MS` | API timeout in ms | `120000` |

### Step 3: Deploy to Vercel

#### Option A: Using Vercel CLI (Recommended)
```bash
# Install Vercel CLI globally
npm install -g vercel

# Navigate to project root
cd c:\Users\Lenovo\OneDrive\Desktop\RAG

# Deploy
vercel

# For production deployment
vercel --prod
```

#### Option B: Connect GitHub to Vercel (Easiest)
1. Push code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Click "New Project"
4. Select your GitHub repository
5. Vercel will auto-detect settings from `vercel.json`
6. Add environment variables in project settings
7. Click "Deploy"

### Step 4: Verify Deployment
After deployment:
1. Visit your Vercel URL
2. Test Google Sign-In flow
3. Verify API calls reach backend
4. Check browser console for CORS/errors

---

## Part 2: Backend Deployment

### Option 1: Deploy to Render (Recommended - Free Tier Available)

1. **Create Render Account**
   - Go to [render.com](https://render.com)
   - Sign up free

2. **Connect GitHub**
   - In Render dashboard, select "New +"
   - Choose "Web Service"
   - Connect your GitHub repo

3. **Configure**
   - Name: `nexus-ai-backend`
   - Environment: `Python 3`
   - Build Command: `pip install -r requirements.txt && python manage.py migrate`
   - Start Command: `gunicorn config.wsgi:application`

4. **Set Environment Variables**
   ```
   DEBUG=False
   ALLOWED_HOSTS=your-render-url.onrender.com,your-vercel-url.vercel.app
   JWT_SECRET_KEY=<your-secret-key>
   JWT_EXPIRY_HOURS=24
   GOOGLE_OAUTH_CLIENT_ID=<your-google-client-id>
   CORS_ALLOWED_ORIGINS=https://your-vercel-url.vercel.app
   DATABASE_URL=<render-postgres-url> (optional, for persistence)
   ```

5. **Deploy**
   - Click "Create Web Service"
   - Render will automatically deploy on push

### Option 2: Deploy to Railway

1. Go to [railway.app](https://railway.app)
2. Click "New Project" → "Deploy from GitHub"
3. Select repo and configure:
   - Python version: 3.x
   - Start command: `gunicorn config.wsgi:application`
4. Add environment variables (same as Render)
5. Deploy

### Option 3: Deploy to Heroku (Paid - $5-7/month)

1. Create `Procfile` in project root:
   ```
   web: gunicorn config.wsgi:application
   ```

2. Create `runtime.txt`:
   ```
   python-3.10.12
   ```

3. Push to Heroku:
   ```bash
   heroku login
   heroku create nexus-ai-backend
   heroku config:set DEBUG=False
   heroku config:set GOOGLE_OAUTH_CLIENT_ID=<your-id>
   git push heroku main
   ```

---

## Environment Variables Checklist

### Frontend (Vercel)
- [ ] `VITE_GOOGLE_CLIENT_ID` - Google OAuth Client ID
- [ ] `VITE_API_BASE_URL` - Backend URL (e.g., https://api.example.com)
- [ ] `VITE_API_TIMEOUT_MS` - 120000

### Backend (Render/Railway/Heroku)
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` - Frontend domain + Backend domain
- [ ] `JWT_SECRET_KEY` - Strong random secret
- [ ] `JWT_EXPIRY_HOURS=24`
- [ ] `GOOGLE_OAUTH_CLIENT_ID` - Same as frontend
- [ ] `CORS_ALLOWED_ORIGINS` - Frontend domain only

---

## Post-Deployment Testing

### Test Google OAuth Flow
1. Open Vercel frontend URL
2. Click "Continue with Google"
3. Sign in with test Google account
4. Verify JWT token stored in localStorage

### Test Chat Features
1. Upload a document
2. Ask a question
3. Verify answers come from backend
4. Check Recent Chats history saved

### Monitor Logs
- **Vercel**: Dashboard → Deployments → Logs
- **Render**: Dashboard → Service → Logs
- **Railway**: Dashboard → Logs

---

## Troubleshooting

### CORS Errors
- Verify `CORS_ALLOWED_ORIGINS` includes frontend domain
- Clear browser cache and try again

### Google OAuth Not Working
- Verify `GOOGLE_OAUTH_CLIENT_ID` is correct
- Check OAuth consent screen approved in Google Cloud
- Ensure frontend domain added to authorized origins

### API Calls Failing
- Check backend URL in environment variables
- Verify backend service is running
- Check backend logs for errors

---

## Quick Reference

**Frontend Vercel URL:** `https://your-project.vercel.app`

**Backend API URL:** (After deployment)
- Render: `https://your-service.onrender.com`
- Railway: `https://your-project.railway.app`
- Heroku: `https://your-app.herokuapp.com`

**Update after backend deployed:**
1. Get backend URL
2. Set `VITE_API_BASE_URL` in Vercel environment variables
3. Redeploy frontend

---

## Next Steps

1. ✅ Frontend ready (Vercel deployment configured)
2. ⏭️ Choose backend platform (Render recommended)
3. ⏭️ Set all environment variables
4. ⏭️ Deploy backend first
5. ⏭️ Deploy frontend with backend URL
6. ⏭️ Test both together

Need help with any deployment step? Let me know!
