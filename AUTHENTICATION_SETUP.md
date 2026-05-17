# Google OAuth2 Authentication Implementation

## Overview
Complete Google OAuth2 authentication system with JWT token management for the Nexus AI RAG application.

### What Was Implemented

#### Backend (Django)
- **UserProfile Model**: Extends Django's User model with Google ID and avatar URL
- **JWT Token Management**: Custom JWT token generation/verification
- **OAuth Endpoints**:
  - `POST /api/auth/google/` - Login with Google OAuth token
  - `GET /api/auth/user/` - Get current authenticated user
  - `PUT /api/auth/profile/` - Update user profile
  - `POST /api/auth/logout/` - Logout endpoint

#### Frontend (React)
- **useAuth Hook**: State management for authentication
  - `isAuthenticated` - Boolean flag
  - `user` - Current user object {id, email, name, avatar_url}
  - `handleGoogleSuccess()` - Process Google login
  - `logout()` - Clear tokens and session
  - `updateProfile()` - Modify user info
  - `getToken()` - Retrieve JWT token

- **LoginModal Component**: Beautiful modal with Google Sign-In button
- **Account Panel**: Dynamic display based on auth status
  - Shows user profile when authenticated
  - Shows "Sign In with Google" when guest
- **HTTP Interceptor**: Auto-attach JWT to all API requests

---

## Setup Instructions

### 1. Configure Google OAuth2 Client

Go to [Google Cloud Console](https://console.cloud.google.com/):

1. Create new project or select existing
2. Go to "APIs & Services" → "Credentials"
3. Create OAuth 2.0 Client ID (Web application)
4. Set Authorized redirect URIs:
   - `http://localhost:5173` (development)
   - `http://127.0.0.1:5173`
   - Your production domain
5. Copy the **Client ID**

### 2. Update Frontend LoginModal Component

In [frontend/src/components/auth/LoginModal.jsx](frontend/src/components/auth/LoginModal.jsx), replace the `client_id`:

```javascript
window.google.accounts.id.initialize({
  client_id: 'YOUR_GOOGLE_CLIENT_ID_HERE',  // Replace with your Client ID
  callback: (response) => {
    onAuthSuccess(response);
    onClose();
  },
});
```

### 3. Configure Environment Variables

Add to `.env` file:

```env
# JWT Configuration
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_EXPIRY_HOURS=24

# CORS Configuration (comma-separated)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,https://yourdomain.com
```

### 4. Database Migrations

Migrations have already been applied:
```bash
python manage.py makemigrations  # Creates 0004_userprofile.py
python manage.py migrate          # Applies migration
```

### 5. Install Dependencies

All required packages have been added to `requirements.txt`:
- `PyJWT==2.10.1` - JWT token handling
- `google-auth==2.29.0` - Google authentication
- `google-auth-oauthlib==1.2.1` - OAuth2 flow

---

## API Endpoints

### POST /api/auth/google/
**Login with Google OAuth token**

Request:
```json
{
  "google_id": "user-unique-id",
  "email": "user@gmail.com",
  "name": "John Doe",
  "picture": "https://lh3.googleusercontent.com/..."
}
```

Response (200 OK):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "name": "John Doe",
    "avatar_url": "https://lh3.googleusercontent.com/..."
  }
}
```

### GET /api/auth/user/
**Get current authenticated user**

Headers:
```
Authorization: Bearer <token>
```

Response (200 OK):
```json
{
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "name": "John Doe",
    "avatar_url": "https://..."
  }
}
```

### PUT /api/auth/profile/
**Update user profile**

Headers:
```
Authorization: Bearer <token>
Content-Type: application/json
```

Request:
```json
{
  "name": "Updated Name",
  "avatar_url": "https://new-avatar-url.jpg"
}
```

Response (200 OK):
```json
{
  "user": {
    "id": 1,
    "email": "user@gmail.com",
    "name": "Updated Name",
    "avatar_url": "https://new-avatar-url.jpg"
  }
}
```

### POST /api/auth/logout/
**Logout (client-side token removal)**

Headers:
```
Authorization: Bearer <token>
```

Response (200 OK):
```json
{
  "detail": "Logged out successfully."
}
```

---

## Frontend Usage

### Basic Implementation (Already Done)

```jsx
import { useAuth } from './hooks/useAuth';
import { LoginModal } from './components/auth/LoginModal';

export default function App() {
  const { isAuthenticated, user, handleGoogleSuccess, logout } = useAuth();
  const [showLoginModal, setShowLoginModal] = useState(false);

  return (
    <>
      {!isAuthenticated && (
        <button onClick={() => setShowLoginModal(true)}>Sign In</button>
      )}
      
      {isAuthenticated && (
        <div>
          <p>Welcome, {user.name}!</p>
          <button onClick={logout}>Sign Out</button>
        </div>
      )}

      <LoginModal
        isOpen={showLoginModal}
        onClose={() => setShowLoginModal(false)}
        onAuthSuccess={handleGoogleSuccess}
      />
    </>
  );
}
```

### Accessing Stored Token

```javascript
const token = localStorage.getItem('nexus_auth_token');
const user = JSON.parse(localStorage.getItem('nexus_user'));
```

### Making Authenticated Requests

JWT token is automatically added to all requests via httpClient interceptor:

```javascript
import httpClient from './services/httpClient';

// Token is auto-added to Authorization header
const response = await httpClient.post('/api/ask/', {
  question: 'What is machine learning?',
  document_ids: [1, 2, 3],
});
```

---

## Testing the Implementation

### 1. Test OAuth Login Flow

```bash
# Start Django backend
python manage.py runserver

# In another terminal, start React frontend
cd frontend
npm run dev
```

Navigate to `http://localhost:5173` and:
1. Click "Sign In" button in top header
2. Click "Sign in with Google"
3. Complete Google authentication
4. Verify user appears in Account panel with avatar and email

### 2. Test API Endpoints Manually

```bash
# Get Google ID token (simulated with test payload)
PAYLOAD='{"google_id":"test-123","email":"test@gmail.com","name":"Test User","picture":"https://example.com/avatar.jpg"}'

# Login
curl -X POST http://localhost:8000/api/auth/google/ \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD"

# Will return token and user info. Copy the token.

# Get current user
curl -X GET http://localhost:8000/api/auth/user/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"

# Update profile
curl -X PUT http://localhost:8000/api/auth/profile/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -H "Content-Type: application/json" \
  -d '{"name":"Updated Name"}'

# Logout
curl -X POST http://localhost:8000/api/auth/logout/ \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

### 3. Verify Token Persistence

1. Sign in with Google
2. Refresh browser (Ctrl+R)
3. Verify user remains logged in (token loaded from localStorage)
4. Check Account panel shows authenticated user

### 4. Test Sign Out

1. Go to Account panel
2. Click "Sign Out"
3. Verify redirected to Guest User state
4. Check localStorage tokens cleared

---

## File Changes Summary

### Backend Files
- **rag/models.py** - Added `UserProfile` model
- **rag/auth_views.py** - NEW - OAuth endpoints and JWT logic
- **config/urls.py** - Added auth routes
- **config/settings.py** - Added JWT and CORS settings
- **rag/migrations/0004_userprofile.py** - NEW - UserProfile migration
- **requirements.txt** - Added JWT and Google auth packages

### Frontend Files
- **frontend/src/hooks/useAuth.js** - NEW - Auth state management
- **frontend/src/components/auth/LoginModal.jsx** - NEW - Login UI
- **frontend/src/App.jsx** - Integrated auth system
- **frontend/src/components/layout/Sidebar.jsx** - Auth-aware Account panel
- **frontend/src/services/httpClient.js** - Added JWT interceptor

---

## Security Considerations

⚠️ **Important for Production:**

1. **Change JWT_SECRET_KEY** in .env to a strong random value
2. **Set CORS_ALLOWED_ORIGINS** to only trusted domains
3. **Use HTTPS** in production (not HTTP)
4. **Set DEBUG=False** in settings.py
5. **Use environment-specific settings** for production secrets
6. **Implement token refresh** mechanism for long sessions
7. **Add rate limiting** to `/api/auth/google/` endpoint

---

## Troubleshooting

### Issue: "Invalid Client ID" Error
- Verify Google Client ID in LoginModal.jsx matches Cloud Console
- Ensure redirect URI is in authorized list
- Check that Google Sign-In script loads (no CSP issues)

### Issue: CORS Errors
- Add your domain to CORS_ALLOWED_ORIGINS in .env
- Verify backend is running on correct port (8000)
- Clear browser cache and retry

### Issue: Token Expires Silently
- Check JWT_EXPIRY_HOURS setting (default: 24 hours)
- Implement token refresh endpoint for production
- UI should prompt to re-login when token expired

### Issue: Account Panel Not Showing User Info
- Verify localStorage has `nexus_auth_token` and `nexus_user`
- Check browser DevTools → Application → Local Storage
- Ensure handleGoogleSuccess() was called successfully

---

## Next Steps

1. **Email Verification** - Add email confirmation step
2. **Token Refresh** - Implement refresh token for long sessions
3. **Social Media Integration** - Add GitHub, Microsoft logins
4. **User Preferences** - Store theme, language preferences in UserProfile
5. **Two-Factor Authentication** - Add 2FA for security
6. **Admin Dashboard** - Manage users and permissions

---

## Support

For issues or questions:
- Check Django logs: `manage.py runserver` output
- Check browser console: DevTools → Console tab
- Review Network tab in DevTools for API responses
- Check `.env` configuration matches endpoints
