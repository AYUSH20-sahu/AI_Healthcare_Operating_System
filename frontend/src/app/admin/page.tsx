'use client';

import React from 'react';
import { useAuth } from '@/lib/auth';
import { Button, Card, CardContent, Badge } from '@/components/ui';

export default function AdminPage() {
    const { user } = useAuth();

    return (
        <div className="space-y-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                            Admin Operations Console
                        </h1>
                        <Badge variant="danger">Level 4 Clearance</Badge>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Welcome, {user?.full_name || 'Administrator'} • Hospital operations, authorizations, and agent telemetry
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <a href="/admin/audit">
                        <Button variant="outline" size="sm">
                            Inspect Audit Log
                        </Button>
                    </a>
                </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Card className="glass-panel hover:border-blue-500/40 transition-colors">
                    <CardContent className="pt-6">
                        <div className="w-10 h-10 rounded-xl bg-blue-500/10 text-blue-500 flex items-center justify-center mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        </div>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-base">Operations Dashboard</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Real-time clinic and hospital operations monitoring, patient throughput, and department latency metrics.
                        </p>
                    </CardContent>
                </Card>

                <Card className="glass-panel hover:border-cyan-500/40 transition-colors">
                    <CardContent className="pt-6">
                        <div className="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-500 flex items-center justify-center mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        </div>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-base">User Management</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Manage clinician profiles, credential verifications, role clearances, and patient federations.
                        </p>
                    </CardContent>
                </Card>

                <Card className="glass-panel hover:border-emerald-500/40 transition-colors">
                    <CardContent className="pt-6">
                        <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-500 flex items-center justify-center mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        </div>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-base">Compliance & Audit Trails</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Immutable audit log inspects every physician approval action, voice recording lifecycle, and consent access.
                        </p>
                    </CardContent>
                </Card>

                <Card className="glass-panel hover:border-amber-500/40 transition-colors">
                    <CardContent className="pt-6">
                        <div className="w-10 h-10 rounded-xl bg-amber-500/10 text-amber-500 flex items-center justify-center mb-3">
                            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                            </svg>
                        </div>
                        <h3 className="font-semibold text-slate-900 dark:text-white text-base">System Configuration</h3>
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                            Agent mesh endpoints, Gemini Live WebSocket connections, and external FHIR server endpoints.
                        </p>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}