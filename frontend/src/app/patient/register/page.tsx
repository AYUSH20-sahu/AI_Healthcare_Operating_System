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
    Checkbox,
    Alert,
    ThemeToggle,
} from '@/components/ui';

export default function PatientRegisterPage() {
    const router = useRouter();
    const { patientSignup } = useAuth();

    const [fullName, setFullName] = useState('');
    const [email, setEmail] = useState('');
    const [phone, setPhone] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [termsAccepted, setTermsAccepted] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [submitting, setSubmitting] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError(null);

        if (!fullName.trim() || !email.trim() || !phone.trim() || !password) {
            setError('Full name, email address, mobile phone number, and password are all required.');
            return;
        }

        // Basic phone validation
        const cleanPhone = phone.trim().replace(/[\s-]/g, '');
        if (cleanPhone.length < 8) {
            setError('Please enter a valid mobile phone number with at least 8 digits.');
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
            setError('You must accept the Patient Health Privacy & Data Governance terms.');
            return;
        }

        try {
            setSubmitting(true);
            await patientSignup({
                full_name: fullName.trim(),
                email: email.trim().toLowerCase(),
                phone: phone.trim(),
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
        <div className="min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 bg-slate-50 dark:bg-[#070A13] text-slate-900 dark:text-slate-100 transition-colors relative overflow-hidden">
            {/* Ambient Glows */}
            <div className="absolute -top-32 -right-32 w-96 h-96 bg-teal-500/15 rounded-full blur-3xl pointer-events-none" />
            <div className="absolute -bottom-32 -left-32 w-96 h-96 bg-emerald-500/15 rounded-full blur-3xl pointer-events-none" />

            {/* Top Bar */}
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
                <ThemeToggle />
            </div>

            <div className="w-full max-w-lg space-y-6 relative z-10 my-8">
                {/* Brand Header */}
                <div className="text-center space-y-2">
                    <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-gradient-to-tr from-teal-500 to-emerald-400 text-white shadow-lg shadow-teal-500/25 mb-1">
                        <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z" />
                        </svg>
                    </div>
                    <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
                        Create Patient Account
                    </h1>
                    <p className="text-xs sm:text-sm text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
                        Register with both your email and mobile phone number. You can use either one to log in at any time.
                    </p>
                </div>

                {error && (
                    <Alert
                        variant="error"
                        title="Account Notice"
                        onClose={() => setError(null)}
                    >
                        <div className="space-y-1.5">
                            <p>{error}</p>
                            {error.toLowerCase().includes('already exists') && (
                                <div className="pt-1">
                                    <Link
                                        href="/patient/login"
                                        className="inline-flex items-center gap-1 font-bold underline text-emerald-700 dark:text-emerald-300 hover:text-emerald-900"
                                    >
                                        Log in with your existing credentials →
                                    </Link>
                                </div>
                            )}
                        </div>
                    </Alert>
                )}

                <Card className="glass-panel border-slate-200/80 dark:border-slate-800/80 shadow-2xl backdrop-blur-xl">
                    <CardContent className="pt-6">
                        <form onSubmit={handleSubmit} className="space-y-4">
                            <Input
                                id="patientFullName"
                                label="Full Legal Name"
                                required
                                placeholder="e.g. John Doe"
                                value={fullName}
                                onChange={(e) => setFullName(e.target.value)}
                                disabled={submitting}
                                leadingIcon={
                                    <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                    </svg>
                                }
                            />

                            {/* Dual Credential Inputs */}
                            <div className="p-3.5 rounded-xl bg-teal-50/60 dark:bg-teal-950/20 border border-teal-200/60 dark:border-teal-800/40 space-y-3">
                                <div className="flex items-center gap-2">
                                    <span className="w-2 h-2 rounded-full bg-teal-500 animate-pulse" />
                                    <h4 className="text-xs font-semibold text-teal-900 dark:text-teal-300">
                                        Dual Login Credentials (Email & Mobile)
                                    </h4>
                                </div>
                                <p className="text-[11px] text-teal-700/80 dark:text-teal-400/80">
                                    Both credentials will be secured for your account. You can sign in using either your email or phone number.
                                </p>

                                <Input
                                    id="patientEmail"
                                    label="Email Address"
                                    type="email"
                                    required
                                    placeholder="name@example.com"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    disabled={submitting}
                                    leadingIcon={
                                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 12a4 4 0 10-8 0 4 4 0 008 0zm0 0v1.5a2.5 2.5 0 005 0V12a9 9 0 10-9 9m4.5-1.206a8.959 8.959 0 01-4.5 1.207" />
                                        </svg>
                                    }
                                />

                                <Input
                                    id="patientPhone"
                                    label="Mobile Phone Number"
                                    type="tel"
                                    required
                                    placeholder="+91 98765 43210"
                                    value={phone}
                                    onChange={(e) => setPhone(e.target.value)}
                                    disabled={submitting}
                                    leadingIcon={
                                        <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 18h.01M8 21h8a2 2 0 002-2V5a2 2 0 00-2-2H8a2 2 0 00-2 2v14a2 2 0 002 2z" />
                                        </svg>
                                    }
                                />
                            </div>

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
                                    id="patientTerms"
                                    label="I consent to secure digital health record processing under HIPAA and ABDM standards."
                                    checked={termsAccepted}
                                    onChange={(e) => setTermsAccepted(e.target.checked)}
                                />
                            </div>

                            <Button
                                type="submit"
                                variant="primary"
                                size="lg"
                                className="w-full justify-center shadow-lg shadow-teal-500/25 bg-gradient-to-r from-teal-600 to-emerald-600 hover:from-teal-700 hover:to-emerald-700 text-white border-0 mt-3"
                                isLoading={submitting}
                            >
                                Complete Registration & Enter Portal
                            </Button>
                        </form>
                    </CardContent>
                </Card>

                {/* Strictly Patient-Only Navigation */}
                <div className="text-center text-xs text-slate-500 dark:text-slate-400 space-y-1">
                    <p>
                        Already have an existing patient account?{' '}
                        <Link href="/patient/login" className="font-semibold text-teal-600 dark:text-teal-400 hover:underline">
                            Sign in here
                        </Link>
                    </p>
                </div>
            </div>
        </div>
    );
}
