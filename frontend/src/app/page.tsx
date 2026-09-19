'use client';

import React, { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { getDefaultRouteForRole } from '@/lib/redirect-validator';
import {
    Header,
    Card,
    CardHeader,
    CardTitle,
    CardDescription,
    CardContent,
    Button,
    Badge,
    StatusBadge,
    AIConfidenceBadge,
} from '@/components/ui';

export default function HomePage() {
    const router = useRouter();
    const { user, isAuthenticated, isLoading } = useAuth();

    useEffect(() => {
        if (!isLoading && isAuthenticated && user?.role) {
            router.replace(getDefaultRouteForRole(user.role));
        }
    }, [isLoading, isAuthenticated, user, router]);

    return (
        <div className="min-h-screen flex flex-col">
            {/* Top Navigation */}
            <Header showNavLinks={false} />

            <main className="flex-1 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex flex-col justify-center">
                {/* Hero Section */}
                <div className="text-center max-w-3xl mx-auto space-y-4 mb-16">
                    <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-600 dark:text-blue-400 text-xs font-medium">
                        <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-ping" />
                        Next-Gen Clinical Healthcare OS • DPDP & ABDM Compliant
                    </div>

                    <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100">
                        Intelligent Clinical Workflows with{' '}
                        <span className="bg-gradient-to-r from-blue-600 via-indigo-600 to-purple-600 bg-clip-text text-transparent">
                            Human-in-the-Loop
                        </span>{' '}
                        Safety
                    </h1>

                    <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed max-w-2xl mx-auto">
                        AI-HOS connects patients, clinicians, and hospital administrators in a unified operating system. Ambient medical scribing and prescription drafting accelerate care while keeping licensed physicians in absolute control.
                    </p>

                    <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
                        <a href="/doctor">
                            <Button size="lg" icon={
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                                </svg>
                            }>
                                Open Doctor Copilot
                            </Button>
                        </a>
                        <a href="/auth/login">
                            <Button variant="outline" size="lg">
                                Sign In / Switch Role
                            </Button>
                        </a>
                    </div>
                </div>

                {/* Applications Grid */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-16">
                    {/* Doctor Portal */}
                    <Card variant="interactive" className="group">
                        <CardHeader>
                            <div className="w-12 h-12 rounded-xl bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform border border-blue-500/20">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                            </div>
                            <div className="flex items-center justify-between">
                                <CardTitle>Doctor Copilot</CardTitle>
                                <Badge variant="primary">High Priority</Badge>
                            </div>
                            <CardDescription>
                                Ambient consultation transcription, automated note drafts, and interactive prescription safety.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ul className="space-y-2 text-xs text-slate-500 dark:text-slate-400">
                                <li className="flex items-center gap-2">
                                    <span className="text-emerald-500">✓</span> Voice note upload & ambient STT
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-emerald-500">✓</span> Structured SOAP clinical drafts (M21)
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-emerald-500">✓</span> Drug interaction checks (M22)
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-emerald-500">✓</span> M23 Clinician Approval Gate
                                </li>
                            </ul>
                            <div className="mt-6">
                                <a href="/doctor" className="block">
                                    <Button variant="secondary" size="sm" fullWidth>
                                        Launch Doctor Workspace →
                                    </Button>
                                </a>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Patient Portal */}
                    <Card variant="interactive" className="group">
                        <CardHeader>
                            <div className="w-12 h-12 rounded-xl bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform border border-indigo-500/20">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
                                </svg>
                            </div>
                            <div className="flex items-center justify-between">
                                <CardTitle>Patient Portal</CardTitle>
                                <Badge variant="outline">Patient Facing</Badge>
                            </div>
                            <CardDescription>
                                Natural-language intake, appointment scheduling, and personal electronic health record viewer.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ul className="space-y-2 text-xs text-slate-500 dark:text-slate-400">
                                <li className="flex items-center gap-2">
                                    <span className="text-indigo-500">✓</span> Voice & text conversational intake
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-indigo-500">✓</span> Urgency & department recommendation
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-indigo-500">✓</span> Appointment booking & conflict check
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-indigo-500">✓</span> Finalized prescription access
                                </li>
                            </ul>
                            <div className="mt-6">
                                <a href="/patient" className="block">
                                    <Button variant="secondary" size="sm" fullWidth>
                                        Open Patient Portal →
                                    </Button>
                                </a>
                            </div>
                        </CardContent>
                    </Card>

                    {/* Admin Console */}
                    <Card variant="interactive" className="group">
                        <CardHeader>
                            <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center mb-3 group-hover:scale-105 transition-transform border border-purple-500/20">
                                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                                </svg>
                            </div>
                            <div className="flex items-center justify-between">
                                <CardTitle>Admin Console</CardTitle>
                                <Badge variant="purple">Operations</Badge>
                            </div>
                            <CardDescription>
                                Clinical operations, consent management, compliance monitoring, and provider administration.
                            </CardDescription>
                        </CardHeader>
                        <CardContent>
                            <ul className="space-y-2 text-xs text-slate-500 dark:text-slate-400">
                                <li className="flex items-center gap-2">
                                    <span className="text-purple-500">✓</span> Clinician & staff directory
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-purple-500">✓</span> Patient consent audit & revocation
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-purple-500">✓</span> Hospital resource & queue metrics
                                </li>
                                <li className="flex items-center gap-2">
                                    <span className="text-purple-500">✓</span> System compliance audit trails
                                </li>
                            </ul>
                            <div className="mt-6">
                                <a href="/admin" className="block">
                                    <Button variant="secondary" size="sm" fullWidth>
                                        Access Admin Console →
                                    </Button>
                                </a>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Design System UI Demonstration Strip */}
                <div className="p-6 rounded-2xl glass-panel border border-slate-200 dark:border-slate-800 space-y-4">
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-200/80 dark:border-slate-800">
                        <div>
                            <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                                AI-HOS Design System Tokens & Safety Primitives
                            </h3>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                Clinical states, confidence scores, and safety indicators built in FE-02.
                            </p>
                        </div>
                        <Badge variant="success">FE-02 Verified</Badge>
                    </div>

                    <div className="flex flex-wrap items-center gap-3 pt-2">
                        <StatusBadge status="DRAFT" />
                        <StatusBadge status="FINALIZED" />
                        <StatusBadge status="SCHEDULED" />
                        <StatusBadge status="CANCELLED" />
                        <AIConfidenceBadge
                            confidence={0.94}
                            basis="Patient exhibits hypertension and elevated systolic readings over 3 consecutive clinical observations."
                        />
                    </div>
                </div>
            </main>

            {/* Footer */}
            <footer className="border-t border-slate-200/80 dark:border-slate-800 py-6 text-center text-xs text-slate-500 dark:text-slate-400">
                AI Healthcare Operating System (AI-HOS) • Clinical decision support platform • All rights reserved
            </footer>
        </div>
    );
}