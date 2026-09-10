'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import {
    Card,
    CardContent,
    Button,
    Input,
    Select,
    Checkbox,
    Alert,
    ThemeToggle,
} from '@/components/ui';

export default function RegisterPage() {
    const router = useRouter();
    const { signup } = useAuth();

    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [role, setRole] = useState<'patient' | 'doctor'>('patient');
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
            const user = await signup({
                full_name: fullName.trim(),
                email: email.trim(),
                password,
                role,
            });

            if (user.role === 'doctor') {
                router.push('/doctor');
            } else {
                router.push('/patient');
            }
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
                    <Link href="/" className="inline-flex items-center gap-2.5">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        </div>
                        <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
                            AI-HOS Registration
                        </span>
                    </Link>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400">
                        Create an institutional clinician account or patient care profile
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
                                placeholder="Dr. Jane Doe or John Smith"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                disabled={submitting}
                            />

                            <Input
                                id="email"
                                label="Institutional or Contact Email"
                                type="email"
                                required
                                placeholder="name@hospital.org"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                disabled={submitting}
                            />

                            <Select
                                id="role"
                                label="Primary System Role"
                                value={role}
                                onChange={(e) => setRole(e.target.value as 'patient' | 'doctor')}
                                options={[
                                    { value: 'patient', label: 'Patient — Symptom intake, appointments, records' },
                                    { value: 'doctor', label: 'Physician / Clinician — Scribe, review gate, prescriptions' },
                                ]}
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
                                Register Account
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
                        <Link href="/" className="hover:underline text-slate-400 hover:text-slate-600 dark:hover:text-slate-300">
                            ← Back to Overview
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
