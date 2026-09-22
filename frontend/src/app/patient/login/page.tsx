'use client';

import React, { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { validatePostLoginRedirect } from '@/lib/redirect-validator';
import {
    Card,
    CardHeader,
    CardContent,
    Button,
    Input,
    Checkbox,
    Alert,
    ThemeToggle,
} from '@/components/ui';

type LoginMethod = 'email' | 'phone';

function PatientLoginForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const rawRedirect = searchParams.get('redirect');

    const { patientLogin, isLoading, isAuthenticated, isPatient } = useAuth();
    const [loginMethod, setLoginMethod] = useState<LoginMethod>('email');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    useEffect(() => {
        if (!isLoading && isAuthenticated && isPatient) {
            const destination = validatePostLoginRedirect(rawRedirect, 'patient');
            router.replace(destination);
        }
    }, [isLoading, isAuthenticated, isPatient, rawRedirect, router]);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        const identifier = loginMethod === 'email' ? email.trim() : phone.trim();

        if (!identifier) {
            setError(
                loginMethod === 'email'
                    ? 'Please enter your registered email address.'
                    : 'Please enter your registered mobile phone number.'
            );
            return;
        }

        if (!password) {
            setError('Please enter your password.');
            return;
        }

        try {
            setSubmitting(true);
            await patientLogin(identifier, password);
            const destination = validatePostLoginRedirect(rawRedirect, 'patient');
            router.push(destination);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Invalid credentials. Please verify your details.';
            setError(message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 bg-slate-50 dark:bg-[#070A13] text-slate-900 dark:text-slate-100 transition-colors relative overflow-hidden">
            {/* Ambient Background Lights */}
            <div className="absolute -top-32 -left-32 w-96 h-96 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-32 -right-32 w-96 h-96 bg-teal-500/15 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute top-1/3 right-1/4 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl pointer-events-none" />

            {/* Top Bar */}
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
                <ThemeToggle />
            </div>

            <div className="w-full max-w-md space-y-6 relative z-10">
                {/* Brand Header */}
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-teal-500 to-emerald-400 text-white shadow-lg shadow-teal-500/25 mb-1">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                        </svg>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                        Patient Health Portal
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-xs mx-auto">
                        Access your clinical records, digital prescriptions, and appointments securely.
                    </p>
                </div>

                {error && (
                    <Alert
                        variant="error"
                        title="Sign-In Error"
                        onClose={() => setError(null)}
                    >
                        {error}
                    </Alert>
                )}

                <Card className="glass-panel border-slate-200/80 dark:border-slate-800/80 shadow-2xl backdrop-blur-xl">
                    <CardHeader className="pb-4">
                        <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 text-center mb-3">
                            Choose Your Sign-In Credential
                        </div>

                        {/* Credential Switcher: Email vs Mobile Phone */}
                        <div className="grid grid-cols-2 p-1 bg-slate-100 dark:bg-slate-800/80 rounded-xl border border-slate-200 dark:border-slate-700/60">
                            <button
                                type="button"
                                onClick={() => {
                                    setLoginMethod('email');
                                    setError(null);
                                }}
                                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                                    loginMethod === 'email'
                                        ? 'bg-white dark:bg-slate-700 text-teal-600 dark:text-teal-300 shadow-sm'
                                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                                }`}
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </svg>
                                <span>Email Address</span>
                            </button>

                            <button
                                type="button"
                                onClick={() => {
                                    setLoginMethod('phone');
                                    setError(null);
                                }}
                                className={`flex items-center justify-center gap-2 py-2 px-3 rounded-lg text-xs font-semibold transition-all ${
                                    loginMethod === 'phone'
                                        ? 'bg-white dark:bg-slate-700 text-teal-600 dark:text-teal-300 shadow-sm'
                                        : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white'
                                }`}
                            >
                                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
                                </svg>
                                <span>Mobile Phone</span>
                            </button>
                        </div>
                    </CardHeader>

                    <CardContent className="pt-0">
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {loginMethod === 'email' ? (
                                <Input
                                    id="patientEmail"
                                    label="Registered Email Address"
                                    type="email"
                                    required
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    disabled={submitting || isLoading}
                                    leadingIcon={
                                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                        </svg>
                                    }
                                />
                            ) : (
                                <Input
                                    id="patientPhone"
                                    label="Registered Mobile Phone Number"
                                    type="tel"
                                    allowedChars="numeric"
                                    maxLength={15}
                                    required
                                    placeholder="9876543210"
                                    value={phone}
                                    onChange={(e) => setPhone(e.target.value)}
                                    disabled={submitting || isLoading}
                                    leadingIcon={
                                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                        </svg>
                                    }
                                />
                            )}

                            <div>
                                <Input
                                    id="patientPassword"
                                    label="Account Password"
                                    type={showPassword ? 'text' : 'password'}
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
                                    label="Keep me signed in on this device"
                                    checked={rememberMe}
                                    onChange={(e) => setRememberMe(e.target.checked)}
                                />
                            </div>

                            <Button
                                type="submit"
                                variant="primary"
                                size="lg"
                                className="w-full justify-center shadow-lg shadow-teal-500/25 bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white border-0 mt-2"
                                isLoading={submitting || isLoading}
                            >
                                Sign In to Patient Portal
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* Patient-Only Navigation: strictly no links to staff/admin login */}
                <div className="text-center text-xs text-slate-500 dark:text-slate-400 space-y-2">
                    <p>
                        Don't have a patient account yet?{' '}
                        <Link href="/patient/register" className="font-semibold text-teal-600 dark:text-teal-400 hover:underline">
                            Register new patient profile
                        </Link>
                    </p>
                    <p className="text-[11px] text-slate-400 dark:text-slate-500 flex items-center justify-center gap-1.5 pt-2">
                        <svg className="w-3.5 h-3.5 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                        </svg>
                        End-to-End Encrypted Health Records • DPDP & ABDM Compliant
                    </p>
                </div>
            </div>
        </div>
    );
}

export default function PatientLoginPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#070A13]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500" />
            </div>
        }>
            <PatientLoginForm />
        </Suspense>
    );
}
