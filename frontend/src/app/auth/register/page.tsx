'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { getDefaultRouteForRole } from '@/lib/redirect-validator';
import {
    Card,
    CardContent,
    Button,
    Input,
    Checkbox,
    Alert,
    ThemeToggle,
} from '@/components/ui';

export default function RegisterPage() {
    const router = useRouter();
    const { signup, user } = useAuth();

    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [termsAccepted, setTermsAccepted] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!fullName.trim() || !email.trim() || !password) {
            setError('All fields are required.');
            return;
        }

        if (password.length < 8) {
            setError('Password must be at least 8 characters long.');
            return;
        }

        if (password !== confirmPassword) {
            setError('Passwords do not match.');
            return;
        }

        if (!termsAccepted) {
            setError('You must accept the HIPAA & Data Governance Agreement to proceed.');
            return;
        }

        try {
            setSubmitting(true);
            await signup({
                full_name: fullName.trim(),
                email: email.trim(),
                password,
            });

            router.push('/patient');
        } catch (err: unknown) {
            const message = err instanceof Error ? err.message : 'Registration failed. Please try again.';
            setError(message);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 transition-colors">
            {/* Top Bar */}
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
                <ThemeToggle />
            </div>

            <div className="w-full max-w-lg space-y-6">
                {/* Header Logo */}
                <div className="text-center space-y-2">
                    <Link href={getDefaultRouteForRole(user?.role)} className="inline-flex items-center gap-2.5">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
                            AI-HOS Patient Registration
                        </span>
                    </Link>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                        Create your secure patient health account. Clinicians and staff are provisioned by hospital administrators.
                    </p>
                </div>

                {error && (
                    <Alert
                        variant="error"
                        title="Registration Error"
                        onClose={() => setError(null)}
                    >
                        {error}
                    </Alert>
                )}

                <Card className="glass-panel border-slate-200 dark:border-slate-800 shadow-xl">
                    <CardContent className="pt-6">
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <Input
                                id="fullName"
                                label="Full Legal Name"
                                required
                                placeholder="e.g. John Doe"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                disabled={submitting}
                            />

                            <Input
                                id="email"
                                label="Email Address"
                                type="email"
                                required
                                placeholder="name@example.com"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                disabled={submitting}
                            />

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                <Input
                                    id="password"
                                    label="Password (8+ chars)"
                                    type="password"
                                    required
                                    placeholder="••••••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    disabled={submitting}
                                />

                                <Input
                                    id="confirmPassword"
                                    label="Confirm Password"
                                    type="password"
                                    required
                                    placeholder="••••••••••••"
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    disabled={submitting}
                                />
                            </div>

                            <div className="pt-2">
                                <Checkbox
                                    id="terms"
                                    label="I accept the HIPAA & ABDM Data Governance Agreement and understand all clinical AI outputs require licensed physician sign-off."
                                    checked={termsAccepted}
                                    onChange={(e) => setTermsAccepted(e.target.checked)}
                                />
                            </div>

                            <Button
                                type="submit"
                                variant="primary"
                                size="lg"
                                className="w-full justify-center shadow-lg shadow-blue-500/25 mt-3"
                                isLoading={submitting}
                            >
                                Create Patient Account
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                <div className="text-center text-xs text-slate-500 dark:text-slate-400 space-y-1">
                    <p>
                        Already have an account?{' '}
                        <Link href="/auth/login" className="font-semibold text-blue-600 dark:text-blue-400 hover:underline">
                            Sign in here
                        </Link>
                    </p>
                    <p>
                        <Link href={getDefaultRouteForRole(user?.role)} className="hover:underline text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                            {user ? '← Return to Dashboard' : '← Back to Overview'}
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
