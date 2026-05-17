# Deployment Checklist - Nexus AI

## ✅ Ready for Deployment

### Frontend Configuration
- [x] `vercel.json` created with build settings
- [x] `.vercelignore` created to optimize deployment
- [x] Environment variables configured
- [x] Build command: `cd frontend && npm install && npm run build`
- [x] Output directory: `frontend/dist`

### Backend Preparation
- [x] Django settings configured with CORS
- [x] JWT authentication implemented
- [x] Google OAuth endpoints ready
- [x] Chat history and profile management working
- [x] System check: No errors

---

## Quick Start - Deploy in 5 Minutes

### 1️⃣ Frontend to Vercel (2 minutes)

**Via CLI:**
```bash
npm install -g vercel
cd c:\Users\Lenovo\OneDrive\Desktop\RAG
vercel --prod
```

**Or via GitHub (Recommended):**
1. Push to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Import project from GitHub
4. Set environment variables:
   - `VITE_GOOGLE_CLIENT_ID=872755425627-kmcht0c050hgsjd5tjkkn3h5n2ad3d1l.apps.googleusercontent.com`
   - `VITE_API_BASE_URL=http://localhost:8000` (change after backend deployed)
   - `VITE_API_TIMEOUT_MS=120000`
5. Click Deploy ✓

### 2️⃣ Backend to Render (3 minutes)

1. Go to [render.com](https://render.com)
2. New Web Service from GitHub
3. Configure:
   - **Name:** nexus-ai-backend
   - **Build:** `pip install -r requirements.txt && python manage.py migrate`
   - **Start:** `gunicorn config.wsgi:application`
4. Set Environment Variables:
   ```
   DEBUG=False
   ALLOWED_HOSTS=your-render-url.onrender.com,your-vercel-url.vercel.app
   JWT_SECRET_KEY=9z9BlCY0Yqu5eMuGkCV6kKqthOFbrJsg_Q4vRjdqr9sCbuB3VW4ksgcqWfh-8dO2
   JWT_EXPIRY_HOURS=24
   GOOGLE_OAUTH_CLIENT_ID=872755425627-kmcht0c050hgsjd5tjkkn3h5n2ad3d1l.apps.googleusercontent.com
   CORS_ALLOWED_ORIGINS=https://your-vercel-url.vercel.app
   ```
5. Deploy ✓

### 3️⃣ Connect Frontend to Backend (1 minute)

1. After backend deployed, get the URL (e.g., `https://xxx.onrender.com`)
2. Go to Vercel project settings
3. Update environment variable: `VITE_API_BASE_URL=https://xxx.onrender.com`
4. Redeploy frontend ✓

---

## Environment Variables Reference

### Frontend (Vercel)
```
VITE_GOOGLE_CLIENT_ID=872755425627-kmcht0c050hgsjd5tjkkn3h5n2ad3d1l.apps.googleusercontent.com
VITE_API_BASE_URL=https://your-backend-url.onrender.com
VITE_API_TIMEOUT_MS=120000
```

### Backend (Render/Railway/Heroku)
```
DEBUG=False
SECRET_KEY=your-django-secret-key (or use existing)
ALLOWED_HOSTS=backend-url.onrender.com,frontend-url.vercel.app
JWT_SECRET_KEY=9z9BlCY0Yqu5eMuGkCV6kKqthOFbrJsg_Q4vRjdqr9sCbuB3VW4ksgcqWfh-8dO2
JWT_EXPIRY_HOURS=24
GOOGLE_OAUTH_CLIENT_ID=872755425627-kmcht0c050hgsjd5tjkkn3h5n2ad3d1l.apps.googleusercontent.com
CORS_ALLOWED_ORIGINS=https://your-vercel-url.vercel.app
```

---

## File Structure Ready for Deployment

```
RAG/
├── vercel.json                 ✓ Deployment config
├── .vercelignore               ✓ Build optimization
├── DEPLOYMENT.md               ✓ Full guide
├── requirements.txt            ✓ Python dependencies
├── manage.py                   ✓ Django entry
├── config/                     ✓ Django settings
├── rag/                        ✓ Django app
│   ├── auth_views.py           ✓ OAuth endpoints
│   ├── views.py                ✓ API endpoints
│   └── models.py               ✓ Database models
└── frontend/                   ✓ React Vite app
    ├── package.json            ✓ Dependencies
    ├── vite.config.js          ✓ Build config
    ├── src/
    │   ├── components/         ✓ UI components
    │   ├── hooks/              ✓ Custom hooks
    │   └── services/           ✓ API services
    └── public/
```

---

## Deployment Platforms Comparison

| Platform | Cost | Setup Time | Cold Start | Recommendation |
|----------|------|-----------|-----------|---|
| **Vercel** (Frontend) | Free | 2 min | <1s | ✅ Best |
| **Render** (Backend) | Free | 3 min | 10-30s | ✅ Best |
| **Railway** (Backend) | Free trial | 3 min | 10-30s | ⭐ Good |
| **Heroku** (Backend) | $5-7/mo | 3 min | 30s-2min | Fair |

---

## Testing After Deployment

1. **Open frontend:** `https://your-project.vercel.app`
2. **Test Google Sign-In:** Should redirect to Google auth
3. **Upload document:** Test file upload flow
4. **Ask question:** Verify backend responds
5. **Check history:** Recent chats saved correctly
6. **Test all features:**
   - Profile editing ✓
   - Clear history ✓
   - Delete individual chats ✓
   - Policy links ✓

---

## Support & Troubleshooting

See `DEPLOYMENT.md` for detailed troubleshooting guide.

**Common Issues:**
- CORS errors → Check `CORS_ALLOWED_ORIGINS`
- Google auth fails → Verify client ID
- API calls fail → Check backend URL in Vercel env
- Cold start slow → Normal on free tier

---

**Everything is configured and ready to deploy! 🚀**

Choose your deployment method above and start deploying!
