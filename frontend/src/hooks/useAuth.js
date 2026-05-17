import { useCallback, useEffect, useState } from 'react';
import { API_BASE_URL } from '../services/config';

const STORAGE_KEY = 'nexus_auth_token';
const USER_STORAGE_KEY = 'nexus_user';

export function useAuth() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [authError, setAuthError] = useState('');

  useEffect(() => {
    const token = localStorage.getItem(STORAGE_KEY);
    const storedUser = localStorage.getItem(USER_STORAGE_KEY);
    
    if (token && storedUser) {
      setIsAuthenticated(true);
      setUser(JSON.parse(storedUser));
    }
    setIsLoading(false);
  }, []);

  const handleGoogleSuccess = useCallback(async (credentialResponse) => {
    setIsLoading(true);
    setAuthError('');
    try {
      const response = await fetch(`${API_BASE_URL}/api/auth/google/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          credential: credentialResponse.credential,
        }),
      });

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Google auth failed');
      }

      localStorage.setItem(STORAGE_KEY, data.token);
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
      setIsAuthenticated(true);
      setUser(data.user);
    } catch (error) {
      setAuthError(error.message || 'Authentication failed.');
      console.error('Authentication failed:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const logout = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem(STORAGE_KEY);
      await fetch(`${API_BASE_URL}/api/auth/logout/`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` },
      });
    } catch (error) {
      console.error('Logout failed:', error);
    } finally {
      localStorage.removeItem(STORAGE_KEY);
      localStorage.removeItem(USER_STORAGE_KEY);
      setIsAuthenticated(false);
      setUser(null);
      setIsLoading(false);
    }
  }, []);

  const updateProfile = useCallback(async (name, avatarUrl) => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem(STORAGE_KEY);
      const response = await fetch(`${API_BASE_URL}/api/auth/profile/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ name, avatar_url: avatarUrl }),
      });

      if (!response.ok) throw new Error('Profile update failed');
      
      const data = await response.json();
      localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
      setUser(data.user);
      return data.user;
    } catch (error) {
      console.error('Profile update failed:', error);
      return null;
    } finally {
      setIsLoading(false);
    }
  }, []);

  return {
    isAuthenticated,
    user,
    isLoading,
    authError,
    clearAuthError: () => setAuthError(''),
    handleGoogleSuccess,
    logout,
    updateProfile,
    getToken: () => localStorage.getItem(STORAGE_KEY),
  };
}
