'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { validatePostLoginRedirect } from '@/lib/redirect-validator';
import {
    Card,
    CardContent,
    Button,
    Input,
    Checkbox,
    Alert,
    ThemeToggle,
} from '@/components/ui';

function LoginForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const redirectUrl = searchParams.get('redirect');

    const { login, isLoading, isAuthenticated, user } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!isLoading && isAuthenticated && user) {
            const destination = validatePostLoginRedirect(redirectUrl, user.role);
            router.replace(destination);
        }
    }, [isLoading, isAuthenticated, user, redirectUrl, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!email.trim() || !password) {
            setError('Please enter both your institutional email and password.');
            return;
        }

        try {
            setSubmitting(true);
            const loggedInUser = await login(email.trim(), password);
            const destination = validatePostLoginRedirect(redirectUrl, loggedInUser.role);
            router.push(destination);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Invalid credentials. Please verify your details.';
            setError(message);
        } finally {
            setSubmitting(false);
        }
    };

    const handleAutofill = (role: 'superadmin' | 'admin' | 'doctor') => {
        setError(null);
        if (role === 'superadmin') {
            setEmail('superadmin@aihos.org');
            setPassword('adminpassword123');
        } else if (role === 'admin') {
            setEmail('admin@test.com');
            setPassword('adminpassword123');
        } else if (role === 'doctor') {
            setEmail('doctor@test.com');
            setPassword('doctorpassword123');
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 bg-slate-50 dark:bg-[#070A13] text-slate-900 dark:text-slate-100 transition-colors relative overflow-hidden">
            {/* Ambient Background Lights */}
            <div className="absolute -top-32 -left-32 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-teal-500/10 rounded-full blur-3xl pointer-events-none" />

            {/* Top Bar with Theme Toggle */}
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
                <ThemeToggle />
            </div>

            <div className="w-full max-w-md space-y-6 relative z-10">
                {/* Brand Header */}
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-500/25 mb-1">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                        </svg>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                        Institutional Portal
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xs mx-auto">
                        Sign in to access your administrative dashboard, clinical workspace, or hospital management console.
                    </p>
                </div>

                {error && (
                    <Alert
                        variant="error"
                        title="Authentication Failed"
                        onClose={() => setError(null)}
                    >
                        {error}
                    </Alert>
                )}

                <Card className="glass-panel border-slate-200/80 dark:border-slate-800/80 shadow-2xl backdrop-blur-xl">
                    <CardContent className="pt-6 space-y-4">
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <Input
                                id="email"
                                label="Institutional Email"
                                type="email"
                                required
                                placeholder="name@hospital.org"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                disabled={submitting || isLoading}
                                leadingIcon={
                                    <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                    </svg>
                                }
                            />

                            <div>
                                <div className="flex items-center justify-between mb-1.5">
                                    <label htmlFor="password" className="block text-xs font-medium text-slate-700 dark:text-slate-300">
                                        Password
                                    </label>
                                    <button
                                        type="button"
                                        onClick={() => setError('Please contact your hospital system administrator to reset credentials.')}
                                        className="text-xs text-blue-600 dark:text-blue-400 hover:underline"
                                    >
                                        Forgot password?
                                    </button>
                                </div>
                                <Input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    autoComplete="current-password"
                                    required
                                    placeholder="••••••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    disabled={submitting || isLoading}
                                    leadingIcon={
                                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                        </svg>
                                    }
                                    trailingIcon={
                                        showPassword ? (
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                                            </svg>
                                        ) : (
                                            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                            </svg>
                                        )
                                    }
                                    onTrailingIconClick={() => setShowPassword(!showPassword)}
                                />
                            </div>

                            <div className="flex items-center justify-between pt-1">
                                <Checkbox
                                    id="rememberMe"
                                    label="Remember this workstation"
                                    checked={rememberMe}
                                    onChange={(e) => setRememberMe(e.target.checked)}
                                />
                            </div>

                            <Button
                                type="submit"
                                variant="primary"
                                size="lg"
                                className="w-full justify-center shadow-lg shadow-blue-500/25 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white font-semibold border-0 mt-2"
                                isLoading={submitting || isLoading}
                            >
                                Authenticate & Sign In
                            </Button>
                        </form>

                        {/* Quick Demo Role Logins */}
                        <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
                            <div className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 mb-2">
                                Quick Demo Logins (Click to autofill)
                            </div>
                            <div className="flex flex-wrap gap-1.5">
                                <button
                                    type="button"
                                    onClick={() => handleAutofill('superadmin')}
                                    className="px-2.5 py-1 rounded-lg text-xs font-medium bg-purple-500/10 hover:bg-purple-500/20 text-purple-600 dark:text-purple-400 border border-purple-500/30 transition-all"
                                >
                                    Super Admin
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleAutofill('admin')}
                                    className="px-2.5 py-1 rounded-lg text-xs font-medium bg-blue-500/10 hover:bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/30 transition-all"
                                >
                                    Hospital Admin
                                </button>
                                <button
                                    type="button"
                                    onClick={() => handleAutofill('doctor')}
                                    className="px-2.5 py-1 rounded-lg text-xs font-medium bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 transition-all"
                                >
                                    Doctor (Rajesh)
                                </button>
                            </div>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400 pt-1.5">
                                Super Admin & Hospital Admin route to <code>/admin</code>. Doctor routes to <code>/doctor</code>.
                            </p>
                        </div>
                    </CardContent>
                </Card>

                {/* Navigation Links */}
                <div className="text-center text-xs text-slate-500 dark:text-slate-400 space-y-2">
                    <p>
                        Register a new healthcare facility?{' '}
                        <Link href="/auth/register" className="font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                            Register Organization
                        </Link>
                    </p>
                    <p className="pt-1">
                        Are you a patient?{' '}
                        <Link href="/patient/login" className="font-semibold text-teal-600 dark:text-teal-400 hover:underline">
                            Go to Patient Portal Sign-In →
                        </Link>
                    </p>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500 flex items-center justify-center gap-1.5 pt-2">
                        <svg className="w-3.5 h-3.5 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                        End-to-End Encrypted Session • HIPAA, ABDM & DPDP Compliant
                    </p>
                </div>
            </div>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#070A13]">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
                </div>
            }
        >
            <LoginForm />
        </Suspense>
    );
}
