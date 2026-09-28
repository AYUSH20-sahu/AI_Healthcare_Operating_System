'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth';
import {
    adminOperationsApi,
    OperationalDashboardData,
    observabilityApi,
    HealthStatusData,
    TelemetryMetricsData,
    adminOrganizationsApi,
    Organization,
} from '@/lib/api';
import { Button, Card, CardContent, Badge, ErrorAlert } from '@/components/ui';

export default function AdminPage() {
    const { user, isSuperAdmin } = useAuth();
    const [data, setData] = useState<OperationalDashboardData | null>(null);
    const [healthData, setHealthData] = useState<HealthStatusData | null>(null);
    const [telemetry, setTelemetry] = useState<TelemetryMetricsData | null>(null);
    const [organization, setOrganization] = useState<Organization | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<any>(null);

    useEffect(() => {
        loadDashboard();
    }, []);

    const loadDashboard = async () => {
        setIsLoading(true);
        setError(null);
        try {
            const [dashRes, healthRes, metricsRes, orgRes] = await Promise.all([
                adminOperationsApi.getDashboard().catch((err) => {
                    console.warn('Dashboard fetch notice:', err);
                    return null;
                }),
                observabilityApi.getHealth().catch((err) => {
                    console.warn('Health check notice:', err);
                    return null;
                }),
                observabilityApi.getMetrics().catch((err) => {
                    console.warn('Telemetry metrics notice:', err);
                    return null;
                }),
                adminOrganizationsApi.getMyOrg().catch(() => null),
            ]);
            if (dashRes) setData(dashRes);
            if (healthRes) setHealthData(healthRes);
            if (metricsRes) setTelemetry(metricsRes);
            if (orgRes) setOrganization(orgRes);
        } catch (err: any) {
            console.error('Failed to load operational telemetry:', err);
            setError(err);
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
                        <Badge variant={isSuperAdmin ? 'primary' : 'outline'} className="text-xs uppercase font-bold tracking-wider">
                            {isSuperAdmin ? 'Super Administrator' : 'Facility Admin'}
                        </Badge>
                    </div>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                        Logged in as <span className="font-semibold text-slate-700 dark:text-slate-200">{user?.full_name || 'Administrator'}</span> ({user?.email}) • {isSuperAdmin ? 'Full authority across all healthcare facilities' : 'Scoped to assigned healthcare organization'}
                    </p>
                </div>

                <div className="flex items-center gap-2">
                    {isSuperAdmin && (
                        <Link href="/admin/organizations">
                            <Button variant="primary" size="sm" className="text-xs bg-purple-600 hover:bg-purple-700 text-white border-0 shadow-md shadow-purple-500/20 flex items-center gap-1.5">
                                <span>🏛️</span>
                                <span>Manage Organizations</span>
                            </Button>
                        </Link>
                    )}
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
                <ErrorAlert
                    error={error}
                    title="Administrative Telemetry Warning"
                    onRetry={loadDashboard}
                    isRetrying={isLoading}
                />
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
                                Consultations Today
                            </span>
                            <span className="w-8 h-8 rounded-lg bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-sm font-bold">
                                📅
                            </span>
                        </div>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-slate-900 dark:text-white">
                                {isLoading ? '...' : data?.appointments_summary.today_total ?? 0}
                            </span>
                            <span className="text-xs text-blue-600 dark:text-blue-400 font-medium">
                                Booked Encounters
                            </span>
                        </div>
                        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex justify-between">
                            <span>Completed: {data?.appointments_summary.today_completed ?? 0}</span>
                            <span>In-Queue: {data?.appointments_summary.today_in_progress ?? 0}</span>
                        </div>
                    </CardContent>
                </Card>

                {/* Non-AI API P95 NFR Meter */}
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                API P95 Latency
                            </span>
                            <span className="w-8 h-8 rounded-lg bg-purple-50 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400 flex items-center justify-center text-sm font-bold">
                                ⚡
                            </span>
                        </div>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-slate-900 dark:text-white">
                                {isLoading ? '...' : `${telemetry?.latency_metrics.non_ai_api.p95 != null ? Math.round(telemetry.latency_metrics.non_ai_api.p95) : 0}ms`}
                            </span>
                            <Badge
                                variant={
                                    (telemetry?.latency_metrics.non_ai_api.p95 ?? 0) <= 500
                                        ? 'success'
                                        : 'error'
                                }
                                className="text-[10px]"
                            >
                                {(telemetry?.latency_metrics.non_ai_api.p95 ?? 0) <= 500 ? 'Target <500ms Met' : 'Above Target'}
                            </Badge>
                        </div>
                        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex justify-between">
                            <span>P50: {telemetry?.latency_metrics.non_ai_api.p50 != null ? Math.round(telemetry.latency_metrics.non_ai_api.p50) : 0}ms</span>
                            <span>Samples: {telemetry?.latency_metrics.non_ai_api.samples ?? 0}</span>
                        </div>
                    </CardContent>
                </Card>

                {/* AI Turn P95 NFR Meter */}
                <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                    <CardContent className="p-5">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-semibold uppercase tracking-wider text-slate-500 dark:text-slate-400">
                                AI Turn P95
                            </span>
                            <span className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 text-indigo-600 dark:text-indigo-400 flex items-center justify-center text-sm font-bold">
                                🧠
                            </span>
                        </div>
                        <div className="mt-3 flex items-baseline gap-2">
                            <span className="text-3xl font-bold text-slate-900 dark:text-white">
                                {isLoading ? '...' : `${telemetry?.latency_metrics.ai_conversational_turn.p95 != null ? Math.round(telemetry.latency_metrics.ai_conversational_turn.p95) : 0}ms`}
                            </span>
                            <Badge
                                variant={
                                    (telemetry?.latency_metrics.ai_conversational_turn.p95 ?? 0) <= 3000
                                        ? 'success'
                                        : 'error'
                                }
                                className="text-[10px]"
                            >
                                {(telemetry?.latency_metrics.ai_conversational_turn.p95 ?? 0) <= 3000 ? 'Target <3s Met' : 'Degraded'}
                            </Badge>
                        </div>
                        <div className="mt-2 pt-2 border-t border-slate-100 dark:border-slate-800 text-[11px] text-slate-500 dark:text-slate-400 flex justify-between">
                            <span>Calls: {telemetry?.ai_call_metrics.total_ai_calls ?? 0}</span>
                            <span>Fallback: {telemetry?.ai_call_metrics.fallback_rate_percent ?? 0}%</span>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Middle Section: Quick Navigation Tiles */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <Link href="/admin/queue" className="group block">
                    <Card className="h-full border border-slate-200 dark:border-slate-800 hover:border-blue-500 dark:hover:border-blue-500 transition-all shadow-sm group-hover:shadow-md">
                        <CardContent className="p-5 flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl bg-blue-50 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center text-xl shrink-0 group-hover:scale-105 transition-transform">
                                🗂️
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                    Patient Live Queue
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                    Real-time wait times & triage status
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </Link>

                <Link href="/admin/availability" className="group block">
                    <Card className="h-full border border-slate-200 dark:border-slate-800 hover:border-blue-500 dark:hover:border-blue-500 transition-all shadow-sm group-hover:shadow-md">
                        <CardContent className="p-5 flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl bg-purple-50 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center text-xl shrink-0 group-hover:scale-105 transition-transform">
                                ⏱️
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                    Doctor Availability
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                    Consultation matrices & slot load
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </Link>

                <Link href="/admin/users" className="group block">
                    <Card className="h-full border border-slate-200 dark:border-slate-800 hover:border-blue-500 dark:hover:border-blue-500 transition-all shadow-sm group-hover:shadow-md">
                        <CardContent className="p-5 flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-xl shrink-0 group-hover:scale-105 transition-transform">
                                👥
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                    Staff Management
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                    RBAC credentials & clinical roles
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </Link>

                <Link href="/admin/audit" className="group block">
                    <Card className="h-full border border-slate-200 dark:border-slate-800 hover:border-blue-500 dark:hover:border-blue-500 transition-all shadow-sm group-hover:shadow-md">
                        <CardContent className="p-5 flex items-center gap-4">
                            <div className="w-12 h-12 rounded-xl bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 flex items-center justify-center text-xl shrink-0 group-hover:scale-105 transition-transform">
                                📜
                            </div>
                            <div>
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                                    Security Audit Logs
                                </h3>
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                                    Immutable patient access trails
                                </p>
                            </div>
                        </CardContent>
                    </Card>
                </Link>
            </div>

            {/* Split Screen: Live Observability & Roadmap Disclosures */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
                {/* Real-time System Telemetry & Observability (7 Cols) */}
                <div className="lg:col-span-7 space-y-4">
                    <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-6 space-y-4">
                            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                    <span>⚡ Live Observability & Mesh Telemetry</span>
                                </h3>
                                <div className="flex items-center gap-2">
                                    <Badge
                                        variant={healthData?.status === 'healthy' ? 'success' : 'warning'}
                                        className="text-[10px] uppercase font-bold"
                                    >
                                        {healthData?.status === 'healthy' ? 'All Systems Healthy' : 'Degraded Mode'}
                                    </Badge>
                                    <span className="text-[11px] font-mono text-slate-400">
                                        Uptime: {telemetry?.uptime_seconds ? `${Math.round(telemetry.uptime_seconds)}s` : 'Active'}
                                    </span>
                                </div>
                            </div>

                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                {/* PostgreSQL */}
                                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            PostgreSQL Connection Pool
                                        </span>
                                        <span
                                            className={`w-2 h-2 rounded-full ${
                                                healthData?.database.status === 'healthy'
                                                    ? 'bg-emerald-500 animate-pulse'
                                                    : 'bg-amber-500'
                                            }`}
                                        />
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                                        Ping: <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{healthData?.database.latency_ms != null ? Math.round(healthData.database.latency_ms * 10) / 10 : 0}ms</span> • {healthData?.database.details || 'Async connection pool active'}
                                    </p>
                                </div>

                                {/* AI Resilience Mesh */}
                                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            AI Provider Mesh
                                        </span>
                                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                                        Primary: <span className="font-mono font-medium text-slate-700 dark:text-slate-300">{healthData?.ai_provider_mesh.primary_llm || 'NVIDIA NIM'}</span> • Fallback: <span className="font-mono">{healthData?.ai_provider_mesh.fallback_llm || 'Gemini'}</span>
                                    </p>
                                </div>

                                {/* Voice STT / TTS */}
                                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            Voice & Speech Engine
                                        </span>
                                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                                        Groq Whisper STT + ElevenLabs TTS / Browser WebSpeech ready
                                    </p>
                                </div>

                                {/* HTTP Requests & Error Rate */}
                                <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                                            HTTP Gateway Telemetry
                                        </span>
                                        <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-100 dark:bg-blue-900/60 text-blue-700 dark:text-blue-300">
                                            {telemetry?.http_requests.total ?? 0} total
                                        </span>
                                    </div>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-1">
                                        Error Rate: <span className="font-semibold text-emerald-600 dark:text-emerald-400">{telemetry?.http_requests.error_rate_percent ?? 0}%</span> • 2xx: {telemetry?.http_requests.status_counts['2xx'] ?? 0}
                                    </p>
                                </div>
                            </div>

                            {/* Token Usage & AI Call Breakdown */}
                            <div className="p-3.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/80 dark:bg-slate-800/60">
                                <div className="flex items-center justify-between text-xs font-semibold text-slate-700 dark:text-slate-300 mb-2">
                                    <span>AI Consumption & Token Telemetry</span>
                                    <span className="text-[11px] text-slate-500">
                                        Total: <strong className="text-slate-800 dark:text-slate-100 font-mono">{telemetry?.ai_call_metrics.token_usage.total_tokens ?? 0}</strong> tokens
                                    </span>
                                </div>
                                <div className="grid grid-cols-3 gap-2 text-center">
                                    <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                                        <div className="text-[10px] text-slate-500 uppercase">Prompt Tokens</div>
                                        <div className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                                            {telemetry?.ai_call_metrics.token_usage.prompt_tokens ?? 0}
                                        </div>
                                    </div>
                                    <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                                        <div className="text-[10px] text-slate-500 uppercase">Completion</div>
                                        <div className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                                            {telemetry?.ai_call_metrics.token_usage.completion_tokens ?? 0}
                                        </div>
                                    </div>
                                    <div className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                                        <div className="text-[10px] text-slate-500 uppercase">Fallbacks</div>
                                        <div className="text-xs font-mono font-bold text-slate-800 dark:text-slate-200 mt-0.5">
                                            {telemetry?.ai_call_metrics.fallback_count ?? 0}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>

                {/* Live Facility Infrastructure & Operational Capacity (5 Cols) */}
                <div className="lg:col-span-5 space-y-4">
                    <Card className="border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-sm">
                        <CardContent className="p-6 space-y-4">
                            <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                                <div>
                                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-900 dark:text-white flex items-center gap-1.5">
                                        <span>🏛️ Facility Infrastructure & Bed Capacity</span>
                                    </h3>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
                                        {organization?.name || 'Registered Healthcare Facility'}
                                    </p>
                                </div>
                                <Badge variant="primary" className="text-[10px] uppercase font-mono">
                                    {organization?.code || 'MAIN'}
                                </Badge>
                            </div>

                            <div className="grid grid-cols-2 gap-3 text-xs">
                                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                                    <div className="text-slate-500 dark:text-slate-400 text-[10px] uppercase font-semibold">Total Inpatient Beds</div>
                                    <div className="text-xl font-bold text-slate-900 dark:text-white mt-1">
                                        {organization?.total_beds ?? 0}
                                    </div>
                                    <div className="text-[10px] text-slate-500 mt-0.5">Licensed Capacity</div>
                                </div>

                                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60">
                                    <div className="text-slate-500 dark:text-slate-400 text-[10px] uppercase font-semibold">ICU & Critical Beds</div>
                                    <div className="text-xl font-bold text-purple-600 dark:text-purple-400 mt-1">
                                        {organization?.icu_beds ?? 0}
                                    </div>
                                    <div className="text-[10px] text-slate-500 mt-0.5">Dedicated Intensive Care</div>
                                </div>
                            </div>

                            <div className="space-y-2 text-xs">
                                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                                    <span className="text-slate-600 dark:text-slate-300 font-medium">Facility Classification:</span>
                                    <Badge variant="outline" className="text-[10px]">
                                        {organization?.facility_type || 'General Hospital'}
                                    </Badge>
                                </div>

                                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                                    <span className="text-slate-600 dark:text-slate-300 font-medium">Emergency Trauma Wing:</span>
                                    <span className="text-xs font-semibold text-emerald-600 dark:text-emerald-400">
                                        {organization?.has_emergency ? '✓ 24/7 Level 1 Active' : 'Not Configured'}
                                    </span>
                                </div>

                                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                                    <span className="text-slate-600 dark:text-slate-300 font-medium">Ambulance Fleet Dispatch:</span>
                                    <span className="text-xs font-semibold text-blue-600 dark:text-blue-400">
                                        {organization?.has_ambulance ? '✓ ALS / BLS Dispatch Ready' : 'Not Configured'}
                                    </span>
                                </div>

                                <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-800/40 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                                    <span className="text-slate-600 dark:text-slate-300 font-medium">Clinical Specialties:</span>
                                    <span className="text-xs font-mono font-bold text-slate-900 dark:text-white">
                                        {organization?.departments?.length ?? 0} Departments
                                    </span>
                                </div>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            </div>
        </div>
    );
}