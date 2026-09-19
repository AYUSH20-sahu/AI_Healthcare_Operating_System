'use client';

import React, { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { validatePostLoginRedirect, getDefaultRouteForRole } from '@/lib/redirect-validator';
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

function LoginForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const redirectUrl = searchParams.get('redirect');

    const { login, isLoading, user } = useAuth();
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [rememberMe, setRememberMe] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!email.trim() || !password) {
            setError('Please enter both your institutional email and password.');
            return;
        }

        try {
            setSubmitting(true);
            const user = await login(email.trim(), password);
            const destination = validatePostLoginRedirect(redirectUrl, user.role);
            router.push(destination);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Invalid credentials. Please try again.';
            setError(message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col lg:flex-row bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 transition-colors">
            {/* Top Bar for Mobile & Theme Toggle */}
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
                <ThemeToggle />
            </div>

            {/* Left Hero / Brand Column */}
            <div className="lg:w-1/2 relative flex flex-col justify-between p-8 sm:p-12 lg:p-16 bg-slate-900 dark:bg-[#070A13] text-white overflow-hidden border-b lg:border-b-0 lg:border-r border-slate-800">
                {/* Background Glows */}
                <div className="absolute top-0 -left-20 w-96 h-96 bg-blue-600/20 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute bottom-0 right-0 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
                <div className="absolute top-1/2 left-1/3 w-80 h-80 bg-purple-600/10 rounded-full blur-3xl pointer-events-none" />

                {/* Brand Header */}
                <div className="relative z-10">
                    <Link href={getDefaultRouteForRole(user?.role)} className="inline-flex items-center gap-3 group">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white font-bold shadow-lg shadow-blue-500/25 group-hover:scale-105 transition-transform">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <div>
                            <span className="text-xl font-bold tracking-tight text-white flex items-center gap-1.5">
                                AI-HOS <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/20 text-blue-400 font-medium border border-blue-500/30">Enterprise v1.0</span>
                            </span>
                            <p className="text-xs text-slate-400">AI Healthcare Operating System</p>
                        </div>
                    </Link>
                </div>

                {/* Hero Center Content */}
                <div className="relative z-10 my-12 lg:my-0 max-w-lg">
                    <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-blue-500/10 border border-blue-500/25 text-blue-300 text-xs font-medium mb-6 backdrop-blur-sm">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        Clinical Agent Mesh Active • HIPAA / ABDM Ready
                    </div>

                    <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-white leading-tight">
                        Intelligent Clinical Workflows,{' '}
                        <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 via-cyan-300 to-emerald-400">
                            Doctor-Governed
                        </span>
                    </h1>

                    <p className="mt-4 text-sm sm:text-base text-slate-300 leading-relaxed">
                        Ambient SOAP documentation, real-time voice triage, and drug-drug interaction screening with an immutable clinical review gate.
                    </p>

                    {/* Highlights Cards */}
                    <div className="mt-8 space-y-3">
                        <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 backdrop-blur-sm">
                            <div className="p-2 rounded-lg bg-blue-500/20 text-blue-400">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                            </div>
                            <div>
                                <h4 className="text-sm font-semibold text-white">Strict Physician Review Gate</h4>
                                <p className="text-xs text-slate-400 mt-0.5">AI drafts are quarantined until an authorized clinician formally signs and finalizes.</p>
                            </div>
                        </div>

                        <div className="flex items-start gap-3.5 p-3.5 rounded-xl bg-slate-800/60 border border-slate-700/60 backdrop-blur-sm">
                            <div className="p-2 rounded-lg bg-cyan-500/20 text-cyan-400">
                                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
                                </svg>
                            </div>
                            <div>
                                <h4 className="text-sm font-semibold text-white">Ambient Scribe & Telemetry</h4>
                                <p className="text-xs text-slate-400 mt-0.5">Whisper-powered consultation audio transcription mapped automatically to ICD-10 & FHIR-R4.</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer Security Badge */}
                <div className="relative z-10 pt-6 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                    <span>AES-256 GCM • RBAC Enforced</span>
                    <span className="font-mono text-slate-400">NODE ID: AIHOS-CORE-01</span>
                </div>
            </div>

            {/* Right Form Column */}
            <div className="lg:w-1/2 flex items-center justify-center p-6 sm:p-12 lg:p-16">
                <div className="w-full max-w-md space-y-6">
                    <div>
                        <h2 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900 dark:text-white">
                            Institutional Login
                        </h2>
                        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                            Sign in to access your designated clinical workspace or patient records.
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


                    {/* Login Card */}
                    <Card className="glass-panel border-slate-200 dark:border-slate-800 shadow-xl">
                        <CardContent className="pt-6">
                            <form onSubmit={handleSubmit} className="space-y-4">
                                <Input
                                    id="email"
                                    label="Email Address"
                                    type="email"
                                    autoComplete="email"
                                    required
                                    placeholder="doctor@test.com"
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
                                            Password <span className="text-rose-500">*</span>
                                        </label>
                                        <a href="#forgot" onClick={(e) => { e.preventDefault(); alert('Please contact your hospital system administrator to reset credentials.'); }} className="text-xs text-blue-600 dark:text-blue-400 hover:underline">
                                            Forgot password?
                                        </a>
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
                                        id="remember"
                                        label="Remember this workstation"
                                        checked={rememberMe}
                                        onChange={(e) => setRememberMe(e.target.checked)}
                                    />
                                </div>

                                <Button
                                    type="submit"
                                    variant="primary"
                                    size="lg"
                                    className="w-full justify-center shadow-lg shadow-blue-500/25 mt-2"
                                    isLoading={submitting || isLoading}
                                >
                                    Authenticate & Access Portal
                                </Button>
                            </form>
                        </CardContent>
                    </Card>

                    {/* Secondary Navigation */}
                    <div className="text-center text-xs text-slate-500 dark:text-slate-400 space-y-2">
                        <p>
                            Don't have an institutional credential yet?{' '}
                            <Link href="/auth/register" className="font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                                Register new account
                            </Link>
                        </p>
                        <p>
                            <Link href={getDefaultRouteForRole(user?.role)} className="hover:underline text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                                {user ? '← Return to Dashboard' : '← Return to System Overview'}
                            </Link>
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default function LoginPage() {
    return (
        <Suspense fallback={
            <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#0B0F19]">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
            </div>
        }>
            <LoginForm />
        </Suspense>
    );
}
