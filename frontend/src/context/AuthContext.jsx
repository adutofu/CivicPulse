import React, { createContext, useState, useContext, useEffect } from 'react';
import { authAPI } from '../services/apiClient';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load user from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem('access_token');
    const storedUser = localStorage.getItem('user');
    const storedProfile = localStorage.getItem('profile');

    if (token && storedUser && storedProfile) {
      try {
        setUser(JSON.parse(storedUser));
        setProfile(JSON.parse(storedProfile));
      } catch (err) {
        localStorage.removeItem('access_token');
        localStorage.removeItem('user');
        localStorage.removeItem('profile');
      }
    }
    setLoading(false);
  }, []);

  const login = async (username, password) => {
    try {
      setError(null);
      const response = await authAPI.login(username, password);
      const { user: userData, profile: profileData, access, refresh } = response.data;

      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('profile', JSON.stringify(profileData));
      localStorage.setItem('user_type', profileData.user_type);

      setUser(userData);
      setProfile(profileData);
      return true;
    } catch (err) {
      setError(err.response?.data?.error || 'Login failed');
      return false;
    }
  };

  const signup = async (username, email, password, user_type = 'citizen', agency = '') => {
    try {
      setError(null);
      const response = await authAPI.signup(username, email, password, user_type, agency);
      const { user: userData, access, refresh } = response.data;

      localStorage.setItem('access_token', access);
      localStorage.setItem('refresh_token', refresh);
      localStorage.setItem('user', JSON.stringify(userData));
      localStorage.setItem('user_type', user_type);

      setUser(userData);
      // Fetch profile after signup
      try {
        const profileResponse = await authAPI.getProfile();
        setProfile(profileResponse.data.profile);
        localStorage.setItem('profile', JSON.stringify(profileResponse.data.profile));
      } catch (err) {
        console.error('Failed to fetch profile:', err);
      }
      return true;
    } catch (err) {
      setError(err.response?.data?.username?.[0] || 'Signup failed');
      return false;
    }
  };

  const logout = () => {
    authAPI.logout();
    setUser(null);
    setProfile(null);
  };

  const isAuthenticated = !!user && !!localStorage.getItem('access_token');
  const isGovernment = profile?.user_type === 'govt';
  const isCitizen = profile?.user_type === 'citizen';

  return (
    <AuthContext.Provider
      value={{
        user,
        profile,
        loading,
        error,
        isAuthenticated,
        isGovernment,
        isCitizen,
        login,
        signup,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};
