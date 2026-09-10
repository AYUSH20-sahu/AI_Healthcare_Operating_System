'use client';

import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { authApi, User, TokenResponse, SignupRequest } from './api';

export interface AuthContextType {
    user: User | null;
    token: string | null;
    refreshToken: string | null;
    isLoading: boolean;
    isAuthenticated: boolean;
    isDoctor: boolean;
    isPatient: boolean;
    isAdmin: boolean;
    login: (email: string, password: string) => Promise<User>;
    signup: (data: SignupRequest) => Promise<User>;
    logout: () => void;
    refreshUser: () => Promise<User | null>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Helper to safely parse JWT payload
function parseJwtPayload(token: string): { sub?: string; email?: string; role?: string } | null {
    try {
        const base64Url = token.split('.')[1];
        if (!base64Url) return null;
        const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
        const jsonPayload = decodeURIComponent(
            atob(base64)
                .split('')
                .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
                .join('')
        );
        return JSON.parse(jsonPayload);
    } catch {
        return null;
    }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(null);
    const [refreshToken, setRefreshToken] = useState<string | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const router = useRouter();

    const logout = useCallback(() => {
        if (typeof window !== 'undefined') {
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            localStorage.removeItem('auth_user');
        }
        setUser(null);
        setToken(null);
        setRefreshToken(null);
        router.push('/auth/login');
    }, [router]);

    const refreshUser = useCallback(async (): Promise<User | null> => {
        try {
            const currentToken = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
            if (!currentToken) return null;

            const userData = await authApi.me();
            setUser(userData);
            if (typeof window !== 'undefined') {
                localStorage.setItem('auth_user', JSON.stringify(userData));
            }
            return userData;
        } catch {
            return null;
        }
    }, []);

    // Initialize auth from localStorage
    useEffect(() => {
        async function initAuth() {
            if (typeof window === 'undefined') return;

            const savedAccessToken = localStorage.getItem('access_token');
            const savedRefreshToken = localStorage.getItem('refresh_token');
            const savedUser = localStorage.getItem('auth_user');

            if (savedAccessToken) {
                setToken(savedAccessToken);
                setRefreshToken(savedRefreshToken);

                // Quick restore cached user or decode token for instant UI
                if (savedUser) {
                    try {
                        setUser(JSON.parse(savedUser));
                    } catch {
                        // ignore parse error
                    }
                } else {
                    const jwtData = parseJwtPayload(savedAccessToken);
                    if (jwtData && jwtData.sub) {
                        setUser({
                            user_id: jwtData.sub,
                            email: jwtData.email || '',
                            full_name: jwtData.email ? jwtData.email.split('@')[0] : 'User',
                            role: jwtData.role || 'patient',
                            is_active: true,
                            created_at: new Date().toISOString(),
                        });
                    }
                }

                // Verify with backend
                try {
                    const freshUser = await authApi.me();
                    setUser(freshUser);
                    localStorage.setItem('auth_user', JSON.stringify(freshUser));
                } catch (err) {
                    console.warn('Initial session validation error:', err);
                }
            }
            setIsLoading(false);
        }

        initAuth();

        const handleAuthExpired = () => {
            logout();
        };

        window.addEventListener('aihos:auth_expired', handleAuthExpired);
        return () => {
            window.removeEventListener('aihos:auth_expired', handleAuthExpired);
        };
    }, [logout]);

    const login = async (email: string, password: string): Promise<User> => {
        setIsLoading(true);
        try {
            const tokenRes: TokenResponse = await authApi.login({ email, password });
            
            if (typeof window !== 'undefined') {
                localStorage.setItem('access_token', tokenRes.access_token);
                localStorage.setItem('refresh_token', tokenRes.refresh_token);
            }
            setToken(tokenRes.access_token);
            setRefreshToken(tokenRes.refresh_token);

            // Fetch current profile
            const currentUser = await authApi.me();
            setUser(currentUser);
            if (typeof window !== 'undefined') {
                localStorage.setItem('auth_user', JSON.stringify(currentUser));
            }
            return currentUser;
        } finally {
            setIsLoading(false);
        }
    };

    const signup = async (data: SignupRequest): Promise<User> => {
        setIsLoading(true);
        try {
            // Backend signup creates user
            const createdUser = await authApi.signup(data);

            // Now authenticate
            const tokenRes = await authApi.login({
                email: data.email,
                password: data.password,
            });

            if (typeof window !== 'undefined') {
                localStorage.setItem('access_token', tokenRes.access_token);
                localStorage.setItem('refresh_token', tokenRes.refresh_token);
                localStorage.setItem('auth_user', JSON.stringify(createdUser));
            }
            setToken(tokenRes.access_token);
            setRefreshToken(tokenRes.refresh_token);
            setUser(createdUser);

            return createdUser;
        } finally {
            setIsLoading(false);
        }
    };

    const isAuthenticated = !!token && !!user;
    const isDoctor = user?.role === 'doctor' || user?.role === 'admin';
    const isPatient = user?.role === 'patient' || user?.role === 'admin';
    const isAdmin = user?.role === 'admin';

    return (
        <AuthContext.Provider
            value={{
                user,
                token,
                refreshToken,
                isLoading,
                isAuthenticated,
                isDoctor,
                isPatient,
                isAdmin,
                login,
                signup,
                logout,
                refreshUser,
            }}
        >
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
