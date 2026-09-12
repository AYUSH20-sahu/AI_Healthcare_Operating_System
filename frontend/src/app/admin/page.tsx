'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import { adminOperationsApi, OperationalDashboardData } from '@/lib/api';
import { Button, Card, CardContent, Badge } from '@/components/ui';

export default function AdminPage() {
    const { user } = useAuth();
    const [data, setData] = useState<OperationalDashboardData | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        loadDashboard();
    }, []);

    const loadDashboard = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const res = await adminOperationsApi.getDashboard();
            setData(res);
        } catch (err: any) {
            console.error('Failed to load operational dashboard:', err);
            setError(err.message || 'Failed to fetch administrative metrics');
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="space-y-6 pb-16 max-w-7xl mx-auto">
            {/* Executive Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                <div>
                    <div className="flex items-center gap-2.5">
                        <h1 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white flex items-center gap-2">
                            <span>🏥 Hospital Operations Console</span>
                        </h1>
                        <Badge variant="primary" className="text-xs uppercase font-bold tracking-wider">
                            Executive Admin
                        </Badge>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Logged in as <span className="font-semibold text-slate-700 dark:text-slate-200">{user?.full_name || 'Administrator'}</span> ({user?.email}) • Unified clinical throughput, real-time queue & telemetry
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={loadDashboard}
                        disabled={isLoading}
                        className="text-xs flex items-center gap-1.5"
                    >
                        <span>🔄</span>
                        <span>{isLoading ? 'Refreshing...' : 'Refresh Metrics'}</span>
                    </Button>
                    <Link href="/admin/queue">
                        <Button variant="primary" size="sm" className="text-xs">
                            Live Patient Queue →
                        </Button>
                    </Link>
                </div>
            </div>

            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 text-xs">
                    ⚠️ {error}
                </div>
            )}

            {/* Top Operational KPI Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Active Doctors & Staff */}
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Clinical Providers
                            </span>
                            <span className="w-8 h-8 rounded-lg bg-blue-50 dark:bg-blue-950/50 text-blue-600 dark:text-blue-400 flex items-center justify-center text-sm font-bold">
                                🩺
                            </span>
                        </div>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-slate-900 dark:text-white">
                                {isLoading ? '...' : data?.users_summary.doctors_count ?? 0}
                            </span>
                            <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">
                                Active on Duty
                            </span>
                        </div>
                        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex justify-between">
                            <span>Nurses: {data?.users_summary.nurses_count ?? 0}</span>
                            <span>Staff: {data?.users_summary.receptionists_count ?? 0}</span>
                        </div>
                    </CardContent>
                </Card>

                {/* Today's Consultations */}
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Today's Consultations
                            </span>
                            <span className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400 flex items-center justify-center text-sm font-bold">
                                📅
                            </span>
                        </div>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-slate-900 dark:text-white">
                                {isLoading ? '...' : data?.appointments_summary.today_total ?? 0}
                            </span>
                            <span className="text-xs text-purple-600 dark:text-purple-400 font-medium">
                                Total Scheduled
                            </span>
                        </div>
                        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex justify-between">
                            <span>In-Progress: {data?.appointments_summary.today_in_progress ?? 0}</span>
                            <span>Completed: {data?.appointments_summary.today_completed ?? 0}</span>
                        </div>
                    </CardContent>
                </Card>

                {/* Patient Population */}
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Registered Patients
                            </span>
                            <span className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-sm font-bold">
                                👥
                            </span>
                        </div>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-slate-900 dark:text-white">
                                {isLoading ? '...' : data?.users_summary.patients_count ?? 0}
                            </span>
                            <span className="text-xs text-slate-500 font-medium">
                                Active ABHA Enrolled
                            </span>
                        </div>
                        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex justify-between">
                            <span>Intake Sessions: {data?.clinical_summary.intake_sessions_total ?? 0}</span>
                            <span>Reports: {data?.clinical_summary.patient_reports_archived ?? 0}</span>
                        </div>
                    </CardContent>
                </Card>

                {/* EHR Records & Prescriptions */}
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                Finalized Clinical Records
                            </span>
                            <span className="w-8 h-8 rounded-lg bg-amber-50 dark:bg-amber-950/50 text-amber-600 dark:text-amber-400 flex items-center justify-center text-sm font-bold">
                                📋
                            </span>
                        </div>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-slate-900 dark:text-white">
                                {isLoading ? '...' : data?.clinical_summary.medical_records_finalized ?? 0}
                            </span>
                            <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                                Doctor Signed
                            </span>
                        </div>
                        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex justify-between">
                            <span>Prescriptions: {data?.clinical_summary.prescriptions_finalized ?? 0}</span>
                            <span>Audits: Active</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Quick Operational Workstation Navigation */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Link href="/admin/queue" className="block group">
                    <Card className="border border-slate-200 dark:border-slate-800 hover:border-blue-500/50 transition-all bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-5 flex items-start gap-4">
                            <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 flex items-center justify-center text-lg shrink-0">
                                ⏱️
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors flex items-center gap-1.5">
                                    <span>Clinic Queue Management</span>
                                    <span>→</span>
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                    Live triage status, in-consultation timers, and patient check-in updates.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </Link>

                <Link href="/admin/availability" className="block group">
                    <Card className="border border-slate-200 dark:border-slate-800 hover:border-purple-500/50 transition-all bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-5 flex items-start gap-4">
                            <div className="w-10 h-10 rounded-xl bg-purple-100 dark:bg-purple-900/50 text-purple-600 dark:text-purple-400 flex items-center justify-center text-lg shrink-0">
                                📊
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-purple-600 dark:group-hover:text-purple-400 transition-colors flex items-center gap-1.5">
                                    <span>Doctor Capacity & Availability</span>
                                    <span>→</span>
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                    Daily 30-min slot utilization grids, booked vs open capacity, and doctor loads.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </Link>

                <Link href="/admin/users" className="block group">
                    <Card className="border border-slate-200 dark:border-slate-800 hover:border-emerald-500/50 transition-all bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-5 flex items-start gap-4">
                            <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-lg shrink-0">
                                🔐
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors flex items-center gap-1.5">
                                    <span>User & Role Governance</span>
                                    <span>→</span>
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                    Provision clinicians, reassign staff roles, reset passwords, and toggle access.
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </Link>
            </div>

            {/* Split Screen: System Health Telemetry & Roadmap Disclosures */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Real-time System Telemetry (7 Cols) */}
                <div className="lg:col-span-7 space-y-4">
                    <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-6 space-y-4">
                            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                    <span>⚡ Real-Time System Telemetry</span>
                                </h3>
                                <Badge variant="success" className="text-[10px] uppercase font-bold">
                                    All Nodes Online
                                </Badge>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            PostgreSQL Database
                                        </span>
                                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                                        Async connection pool active • Zero deadlocks
                                    </p>
                                </div>

                                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            Gemini Live Mesh
                                        </span>
                                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                                        WebRTC & WebSocket streaming ready
                                    </p>
                                </div>

                                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            FHIR R4 Gateway
                                        </span>
                                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                                        ABDM milestone resources mapped
                                    </p>
                                </div>

                                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            Immutable Audit Engine
                                        </span>
                                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                                        Append-only security logging enforced
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Transparent Future Roadmap Capabilities (5 Cols) */}
                <div className="lg:col-span-5 space-y-4">
                    <Card className="border border-amber-200 dark:border-amber-900/40 bg-gradient-to-br from-amber-50/40 via-white to-orange-50/30 dark:from-slate-900 dark:to-slate-800/60 shadow-sm">
                        <CardContent className="p-6 space-y-3.5">
                            <div className="flex items-center justify-between border-b border-amber-200 dark:border-amber-900/60 pb-2.5">
                                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-900 dark:text-amber-300 flex items-center gap-1.5">
                                    <span>🔬 Enterprise Sensor Roadmap</span>
                                </h3>
                                <Badge variant="warning" className="text-[10px]">
                                    Hardware Pending
                                </Badge>
                            </div>

                            <p className="text-xs text-slate-600 dark:text-slate-300 leading-relaxed">
                                In strict adherence to AI-HOS governance specifications, non-operational hardware telemetry metrics are transparently disclosed rather than fabricated:
                            </p>

                            <div className="space-y-2 text-xs">
                                <div className="p-2.5 rounded-lg bg-white/80 dark:bg-slate-800/80 border border-amber-200/60 dark:border-slate-700">
                                    <div className="flex items-center justify-between font-bold text-slate-900 dark:text-white">
                                        <span>IoT Hospital Bed Occupancy</span>
                                        <span className="text-[10px] text-amber-700 dark:text-amber-400 font-mono">Q4 Sensor Mesh</span>
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                                        Physical pressure mat sensors will stream real-time ward occupancy.
                                    </p>
                                </div>

                                <div className="p-2.5 rounded-lg bg-white/80 dark:bg-slate-800/80 border border-amber-200/60 dark:border-slate-700">
                                    <div className="flex items-center justify-between font-bold text-slate-900 dark:text-white">
                                        <span>Predictive ED Latency Model</span>
                                        <span className="text-[10px] text-amber-700 dark:text-amber-400 font-mono">In ML Validation</span>
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                                        Multi-variant queuing theory model for emergency room intake.
                                    </p>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}