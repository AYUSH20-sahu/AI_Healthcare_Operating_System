'use client';

import React from 'react';

export interface DoctorStats {
    totalPatients: number;
    completedPatients: number;
    waitingPatients: number;
    pendingAiReviews: number;
    criticalAlertsCount: number;
    averageConsultationMins: number;
}

interface DoctorStatsOverviewProps {
    stats: DoctorStats;
    onReviewAiDrafts?: () => void;
    onViewAlerts?: () => void;
}

export function DoctorStatsOverview({
    stats,
    onReviewAiDrafts,
    onViewAlerts,
}: DoctorStatsOverviewProps) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* 1. Today's Patient Queue Load */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 p-4 shadow-sm backdrop-blur-md flex flex-col justify-between">
                <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Today&apos;s Queue
                    </span>
                    <span className="w-8 h-8 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center text-sm font-bold">
                        👥
                    </span>
                </div>
                <div className="mt-3">
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-slate-900 dark:text-white font-mono">
                            {stats.completedPatients} / {stats.totalPatients}
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-400">Consulted</span>
                    </div>
                    {/* Progress Bar */}
                    <div className="mt-2.5 w-full bg-slate-100 dark:bg-slate-800 rounded-full h-1.5 overflow-hidden">
                        <div
                            className="bg-blue-600 h-1.5 rounded-full transition-all duration-500"
                            style={{
                                width: `${stats.totalPatients > 0 ? (stats.completedPatients / stats.totalPatients) * 100 : 0}%`,
                            }}
                        />
                    </div>
                    <div className="flex items-center justify-between text-[11px] text-slate-500 dark:text-slate-400 mt-1.5">
                        <span>{stats.waitingPatients} waiting in triage</span>
                        <span>{stats.totalPatients - stats.completedPatients - stats.waitingPatients} scheduled</span>
                    </div>
                </div>
            </div>

            {/* 2. Pending AI Drafts (Crucial Clinical Review Gate) */}
            <div
                onClick={onReviewAiDrafts}
                className="rounded-2xl border border-amber-200/80 dark:border-amber-900/50 bg-gradient-to-b from-amber-50/60 via-white to-amber-50/20 dark:from-amber-950/30 dark:via-slate-900/90 dark:to-slate-900/90 p-4 shadow-sm backdrop-blur-md flex flex-col justify-between cursor-pointer hover:border-amber-300 dark:hover:border-amber-700 transition-all group"
            >
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5">
                        <span className="w-2 h-2 rounded-full bg-amber-500 animate-ping" />
                        <span className="text-xs font-semibold text-amber-800 dark:text-amber-300 uppercase tracking-wider">
                            Pending AI Reviews
                        </span>
                    </div>
                    <span className="w-8 h-8 rounded-xl bg-amber-100 dark:bg-amber-950/80 text-amber-700 dark:text-amber-300 flex items-center justify-center text-sm font-bold group-hover:scale-105 transition-transform">
                        🤖
                    </span>
                </div>
                <div className="mt-3">
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-amber-700 dark:text-amber-300 font-mono">
                            {stats.pendingAiReviews}
                        </span>
                        <span className="text-xs text-amber-600/80 dark:text-amber-400/80">Drafts Quarantined</span>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-2 flex items-center gap-1">
                        <span>🔒 Strict Physician Review Gate: Sign to approve</span>
                    </p>
                </div>
            </div>

            {/* 3. Critical Safety Alerts */}
            <div
                onClick={onViewAlerts}
                className="rounded-2xl border border-rose-200/80 dark:border-rose-900/50 bg-gradient-to-b from-rose-50/60 via-white to-rose-50/20 dark:from-rose-950/30 dark:via-slate-900/90 dark:to-slate-900/90 p-4 shadow-sm backdrop-blur-md flex flex-col justify-between cursor-pointer hover:border-rose-300 dark:hover:border-rose-700 transition-all group"
            >
                <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-rose-800 dark:text-rose-300 uppercase tracking-wider">
                        Patient Safety Flags
                    </span>
                    <span className="w-8 h-8 rounded-xl bg-rose-100 dark:bg-rose-950/80 text-rose-700 dark:text-rose-300 flex items-center justify-center text-sm font-bold group-hover:scale-105 transition-transform">
                        ⚠️
                    </span>
                </div>
                <div className="mt-3">
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-rose-600 dark:text-rose-400 font-mono">
                            {stats.criticalAlertsCount}
                        </span>
                        <span className="text-xs text-rose-600/80 dark:text-rose-400/80">Active flags</span>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-2">
                        Severe DDI checks, Penicillin & Fall alerts
                    </p>
                </div>
            </div>

            {/* 4. Consultation Telemetry */}
            <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 p-4 shadow-sm backdrop-blur-md flex flex-col justify-between">
                <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        Telemetry & Avg Pace
                    </span>
                    <span className="w-8 h-8 rounded-xl bg-purple-100 dark:bg-purple-950/60 text-purple-600 dark:text-purple-400 flex items-center justify-center text-sm font-bold">
                        ⚡
                    </span>
                </div>
                <div className="mt-3">
                    <div className="flex items-baseline gap-2">
                        <span className="text-2xl font-bold text-purple-700 dark:text-purple-300 font-mono">
                            {stats.averageConsultationMins}m
                        </span>
                        <span className="text-xs text-slate-500 dark:text-slate-400">Avg visit time</span>
                    </div>
                    <p className="text-[11px] text-emerald-600 dark:text-emerald-400 mt-2 flex items-center gap-1 font-medium">
                        <span>✓ Whisper Scribe active (-42% typing)</span>
                    </p>
                </div>
            </div>
        </div>
    );
}
