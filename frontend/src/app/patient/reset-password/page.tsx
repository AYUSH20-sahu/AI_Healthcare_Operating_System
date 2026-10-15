'use client';

import React, { useState, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import Link from 'next/link';
import { authApi } from '@/lib/api/auth';
import {
    Card,
    CardContent,
    Button,
    Input,
    Alert,
    ThemeToggle,
} from '@/components/ui';

function ResetPasswordForm() {
    const router = useRouter();
    const searchParams = useSearchParams();
    const token = searchParams.get('token');

    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showNewPassword, setShowNewPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);

    const [submitting, setSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);

    // Password requirement checks
    const hasMinLength = newPassword.length >= 8;
    const hasUpper = /[A-Z]/.test(newPassword);
    const hasLower = /[a-z]/.test(newPassword);
    const hasNumber = /[0-9]/.test(newPassword);
    const hasSpecial = /[^A-Za-z0-9]/.test(newPassword);
    const passwordsMatch = newPassword.length > 0 && newPassword === confirmPassword;
    const isValid = hasMinLength && hasUpper && hasLower && hasNumber && hasSpecial && passwordsMatch;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!token) {
            setError('Missing password reset token. Please request a new link from the login page.');
            return;
        }

        if (!isValid) {
            setError('Please make sure your new password meets all security requirements and that both fields match.');
            return;
        }

        try {
            setSubmitting(true);
            await authApi.resetPassword({
                token: token.trim(),
                new_password: newPassword,
            });
            setSuccess(true);
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Unable to reset password. The link may have expired.';
            setError(message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-[#06080F] text-slate-900 dark:text-slate-100 flex flex-col justify-between selection:bg-teal-500/20">
            {/* Header */}
            <header className="border-b border-slate-200 dark:border-slate-800 bg-white/70 dark:bg-slate-950/40 backdrop-blur-md px-6 py-4 flex items-center justify-between">
                <Link href="/patient/login" className="flex items-center gap-3 group">
                    <div className="w-10 h-10 rounded-xl bg-teal-600 flex items-center justify-center text-white font-black text-xl shadow-md shadow-teal-500/20 group-hover:scale-105 transition-transform">
                        +
                    </div>
                    <div>
                        <div className="text-base font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                            <span>CarePulse</span>
                            <span className="text-[10px] font-semibold uppercase tracking-widest px-2 py-0.5 rounded-full bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20">
                                Patient Portal
                            </span>
                        </div>
                        <div className="text-xs text-slate-500 dark:text-slate-400">
                            Secure Healthcare Identity System
                        </div>
                    </div>
                </Link>
                <div className="flex items-center gap-3">
                    <ThemeToggle />
                </div>
            </header>

            {/* Main Content */}
            <main className="flex-1 flex items-center justify-center p-4 sm:p-6">
                <div className="w-full max-w-md">
                    {/* Header Info */}
                    <div className="text-center mb-6">
                        <div className="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-teal-500/10 text-teal-600 dark:text-teal-400 border border-teal-500/20 mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
                            Create New Password
                        </h1>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Set a strong, secure password for your patient account
                        </p>
                    </div>

                    <Card className="bg-white/90 dark:bg-slate-900/60 border-slate-200 dark:border-slate-800 shadow-2xl backdrop-blur-xl">
                        <CardContent className="p-6">
                            {!token ? (
                                <div className="space-y-4 text-center">
                                    <div className="p-4 rounded-xl bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-300 text-xs leading-relaxed text-left">
                                        <div className="font-semibold mb-1 flex items-center gap-1.5">
                                            <span>⚠️ Missing Security Token</span>
                                        </div>
                                        This password reset link is invalid or incomplete. Please return to the login page and request a new password reset link.
                                    </div>
                                    <Button
                                        variant="primary"
                                        size="md"
                                        className="w-full bg-teal-600 hover:bg-teal-700 text-white"
                                        onClick={() => router.push('/patient/login')}
                                    >
                                        Return to Sign In
                                    </Button>
                                </div>
                            ) : success ? (
                                <div className="text-center space-y-4 py-2">
                                    <div className="w-14 h-14 mx-auto rounded-2xl bg-teal-500/10 border border-teal-500/20 text-teal-600 dark:text-teal-400 flex items-center justify-center">
                                        <svg className="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                        </svg>
                                    </div>
                                    <div className="space-y-1">
                                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">
                                            Password Reset Successfully!
                                        </h2>
                                        <p className="text-xs text-slate-600 dark:text-slate-400 leading-relaxed">
                                            Your password has been updated and all active sessions revoked. You can now securely log in with your new password.
                                        </p>
                                    </div>
                                    <div className="pt-2">
                                        <Button
                                            variant="primary"
                                            size="lg"
                                            className="w-full bg-teal-600 hover:bg-teal-700 text-white shadow-md shadow-teal-500/20"
                                            onClick={() => router.push('/patient/login')}
                                        >
                                            Sign In with New Password →
                                        </Button>
                                    </div>
                                </div>
                            ) : (
                                <form onSubmit={handleSubmit} className="space-y-4">
                                    {error && (
                                        <Alert
                                            variant="error"
                                            title="Reset Error"
                                            onClose={() => setError(null)}
                                        >
                                            {error}
                                        </Alert>
                                    )}

                                    {/* New Password */}
                                    <div>
                                        <Input
                                            id="newPassword"
                                            label="New Password"
                                            type={showNewPassword ? 'text' : 'password'}
                                            required
                                            placeholder="Create a strong password"
                                            value={newPassword}
                                            onChange={(e) => setNewPassword(e.target.value)}
                                            disabled={submitting}
                                            leadingIcon={
                                                <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                                                </svg>
                                            }
                                            trailingIcon={
                                                showNewPassword ? (
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                                                    </svg>
                                                ) : (
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                                    </svg>
                                                )
                                            }
                                            onTrailingIconClick={() => setShowNewPassword(!showNewPassword)}
                                        />
                                    </div>

                                    {/* Confirm Password */}
                                    <div>
                                        <Input
                                            id="confirmPassword"
                                            label="Confirm New Password"
                                            type={showConfirmPassword ? 'text' : 'password'}
                                            required
                                            placeholder="Re-enter password to confirm"
                                            value={confirmPassword}
                                            onChange={(e) => setConfirmPassword(e.target.value)}
                                            disabled={submitting}
                                            leadingIcon={
                                                <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                                </svg>
                                            }
                                            trailingIcon={
                                                showConfirmPassword ? (
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18" />
                                                    </svg>
                                                ) : (
                                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                                                    </svg>
                                                )
                                            }
                                            onTrailingIconClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                        />
                                    </div>

                                    {/* Password Requirements Checklist */}
                                    <div className="p-3 bg-slate-50 dark:bg-slate-950/80 rounded-xl border border-slate-200 dark:border-slate-800 space-y-1.5 text-[11px]">
                                        <div className="font-semibold text-slate-700 dark:text-slate-300 mb-1">
                                            Password Security Checklist:
                                        </div>
                                        <div className="grid grid-cols-2 gap-1 text-slate-600 dark:text-slate-400">
                                            <span className={`flex items-center gap-1.5 ${hasMinLength ? 'text-teal-600 dark:text-teal-400 font-medium' : ''}`}>
                                                <span>{hasMinLength ? '✓' : '•'}</span> 8+ characters
                                            </span>
                                            <span className={`flex items-center gap-1.5 ${hasUpper ? 'text-teal-600 dark:text-teal-400 font-medium' : ''}`}>
                                                <span>{hasUpper ? '✓' : '•'}</span> Uppercase letter
                                            </span>
                                            <span className={`flex items-center gap-1.5 ${hasLower ? 'text-teal-600 dark:text-teal-400 font-medium' : ''}`}>
                                                <span>{hasLower ? '✓' : '•'}</span> Lowercase letter
                                            </span>
                                            <span className={`flex items-center gap-1.5 ${hasNumber ? 'text-teal-600 dark:text-teal-400 font-medium' : ''}`}>
                                                <span>{hasNumber ? '✓' : '•'}</span> At least 1 number
                                            </span>
                                            <span className={`flex items-center gap-1.5 ${hasSpecial ? 'text-teal-600 dark:text-teal-400 font-medium' : ''}`}>
                                                <span>{hasSpecial ? '✓' : '•'}</span> Special symbol
                                            </span>
                                            <span className={`flex items-center gap-1.5 ${passwordsMatch ? 'text-teal-600 dark:text-teal-400 font-medium' : ''}`}>
                                                <span>{passwordsMatch ? '✓' : '•'}</span> Passwords match
                                            </span>
                                        </div>
                                    </div>

                                    <Button
                                        type="submit"
                                        variant="primary"
                                        size="lg"
                                        disabled={!isValid || submitting}
                                        isLoading={submitting}
                                        className="w-full bg-teal-600 hover:bg-teal-700 text-white shadow-md shadow-teal-500/20 font-semibold"
                                    >
                                        Save New Password & Continue
                                    </Button>

                                    <div className="text-center pt-2">
                                        <Link
                                            href="/patient/login"
                                            className="text-xs text-slate-500 hover:text-teal-600 dark:hover:text-teal-400 transition"
                                        >
                                            ← Back to Patient Login
                                        </Link>
                                    </div>
                                </form>
                            )}
                        </CardContent>
                    </Card>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-950/30 px-6 py-4 text-center text-xs text-slate-500 dark:text-slate-400">
                <span>CarePulse AI-HOS • ISO 27001 & DPDP Act 2023 Compliant Identity Security</span>
            </footer>
        </div>
    );
}

export default function ResetPasswordPage() {
    return (
        <Suspense
            fallback={
                <div className="min-h-screen flex items-center justify-center bg-slate-50 dark:bg-[#06080F]">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-teal-500" />
                </div>
            }
        >
            <ResetPasswordForm />
        </Suspense>
    );
}
