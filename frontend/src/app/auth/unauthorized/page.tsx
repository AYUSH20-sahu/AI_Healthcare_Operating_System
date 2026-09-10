'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { Card, CardContent, Button, ThemeToggle, Badge } from '@/components/ui';

export default function UnauthorizedPage() {
    const { user, logout } = useAuth();
    const router = useRouter();

    const getTargetPortal = () => {
        if (!user) return '/auth/login';
        if (user.role === 'doctor') return '/doctor';
        if (user.role === 'patient') return '/patient';
        if (user.role === 'admin') return '/admin';
        return '/';
    };

    return (
        <div className="min-h-screen flex flex-col items-center justify-center p-4 sm:p-6 bg-slate-50 dark:bg-[#0B0F19] text-slate-900 dark:text-slate-100 transition-colors">
            {/* Top Bar */}
            <div className="absolute top-4 right-4 z-50 flex items-center gap-3">
                <ThemeToggle />
            </div>

            <div className="w-full max-w-md text-center space-y-6">
                <Card className="glass-panel border-amber-500/30 dark:border-amber-500/20 shadow-xl overflow-hidden relative">
                    <div className="h-2 bg-gradient-to-r from-amber-500 to-rose-500" />
                    <CardContent className="pt-8 pb-8 px-6 space-y-6">
                        {/* Icon */}
                        <div className="w-16 h-16 rounded-2xl bg-amber-500/10 dark:bg-amber-500/20 border border-amber-500/30 text-amber-500 flex items-center justify-center mx-auto shadow-lg shadow-amber-500/10">
                            <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
                            </svg>
                        </div>

                        <div>
                            <div className="inline-flex mb-2">
                                <Badge variant="warning">403 — Insufficient Clearance</Badge>
                            </div>
                            <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                                Role Clearance Required
                            </h1>
                            <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                                This clinical sector is restricted to authorized personnel. Your current credentials do not have permission to access this route.
                            </p>
                        </div>

                        {user && (
                            <div className="p-3.5 rounded-xl bg-slate-100 dark:bg-slate-800/80 border border-slate-200 dark:border-slate-700/60 text-xs text-left space-y-1">
                                <div className="flex justify-between items-center text-slate-500 dark:text-slate-400">
                                    <span>Authenticated Account:</span>
                                    <span className="font-medium text-slate-800 dark:text-slate-200">{user.email}</span>
                                </div>
                                <div className="flex justify-between items-center text-slate-500 dark:text-slate-400">
                                    <span>Assigned Role:</span>
                                    <span className="capitalize font-semibold text-blue-600 dark:text-blue-400">{user.role}</span>
                                </div>
                            </div>
                        )}

                        <div className="flex flex-col gap-2.5 pt-2">
                            {user && (
                                <Button
                                    variant="primary"
                                    onClick={() => router.push(getTargetPortal())}
                                    className="w-full justify-center"
                                >
                                    Go to My {user.role.charAt(0).toUpperCase() + user.role.slice(1)} Workspace
                                </Button>
                            )}

                            <Button
                                variant="secondary"
                                onClick={() => logout()}
                                className="w-full justify-center"
                            >
                                Switch Account / Sign Out
                            </Button>

                            <Link href="/" className="text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 mt-2">
                                Return to System Overview
                            </Link>
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
