'use client';

import React from 'react';

interface QuickActionBarProps {
    hasActivePatient: boolean;
    patientName?: string;
    onStartScribe?: () => void;
    onDraftNote?: () => void;
    onPrescribe?: () => void;
    onScheduleFollowUp?: () => void;
    onOrderDiagnostics?: () => void;
    onRequestAbdmConsent?: () => void;
}

export function QuickActionBar({
    hasActivePatient,
    patientName,
    onStartScribe,
    onDraftNote,
    onPrescribe,
    onScheduleFollowUp,
    onOrderDiagnostics,
    onRequestAbdmConsent,
}: QuickActionBarProps) {
    return (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 shadow-sm p-4 backdrop-blur-md">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 mb-3">
                <div className="flex items-center gap-2">
                    <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
                    <h3 className="text-xs font-bold text-slate-700 dark:text-slate-200 uppercase tracking-wider">
                        Clinical Copilot Quick Actions
                    </h3>
                </div>
                {hasActivePatient && patientName ? (
                    <span className="text-xs text-slate-500 dark:text-slate-400">
                        Active context: <strong className="text-slate-800 dark:text-slate-200">{patientName}</strong>
                    </span>
                ) : (
                    <span className="text-xs text-amber-600 dark:text-amber-400 font-medium">
                        Select a patient to enable context actions
                    </span>
                )}
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2.5">
                {/* 1. Ambient Scribe */}
                <button
                    type="button"
                    disabled={!hasActivePatient}
                    onClick={onStartScribe}
                    className="p-3 rounded-xl border border-blue-200/80 dark:border-blue-900/50 bg-gradient-to-b from-blue-50/80 to-blue-100/40 dark:from-blue-950/40 dark:to-blue-900/20 hover:from-blue-100/90 dark:hover:from-blue-900/40 text-blue-900 dark:text-blue-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex flex-col items-center text-center gap-1.5 shadow-sm group"
                >
                    <div className="w-9 h-9 rounded-xl bg-blue-600 text-white flex items-center justify-center text-base shadow-md shadow-blue-500/30 group-hover:scale-105 transition-transform">
                        🎙️
                    </div>
                    <span className="text-xs font-bold leading-tight">Start Scribe</span>
                    <span className="text-[10px] text-blue-600 dark:text-blue-400">Ambient AI</span>
                </button>

                {/* 2. Draft SOAP Note */}
                <button
                    type="button"
                    disabled={!hasActivePatient}
                    onClick={onDraftNote}
                    className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800/80 text-slate-800 dark:text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex flex-col items-center text-center gap-1.5 shadow-sm group"
                >
                    <div className="w-9 h-9 rounded-xl bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white flex items-center justify-center text-base group-hover:scale-105 transition-transform">
                        📝
                    </div>
                    <span className="text-xs font-bold leading-tight">SOAP Note</span>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400">Draft Note</span>
                </button>

                {/* 3. Prescribe Medication */}
                <button
                    type="button"
                    disabled={!hasActivePatient}
                    onClick={onPrescribe}
                    className="p-3 rounded-xl border border-emerald-200/80 dark:border-emerald-900/50 bg-gradient-to-b from-emerald-50/70 to-emerald-100/30 dark:from-emerald-950/40 dark:to-emerald-900/20 hover:from-emerald-100/80 dark:hover:from-emerald-900/40 text-emerald-900 dark:text-emerald-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex flex-col items-center text-center gap-1.5 shadow-sm group"
                >
                    <div className="w-9 h-9 rounded-xl bg-emerald-600 text-white flex items-center justify-center text-base shadow-md shadow-emerald-500/20 group-hover:scale-105 transition-transform">
                        💊
                    </div>
                    <span className="text-xs font-bold leading-tight">Prescribe Rx</span>
                    <span className="text-[10px] text-emerald-600 dark:text-emerald-400">DDI Shield</span>
                </button>

                {/* 4. Schedule Follow-up */}
                <button
                    type="button"
                    disabled={!hasActivePatient}
                    onClick={onScheduleFollowUp}
                    className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800/80 text-slate-800 dark:text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex flex-col items-center text-center gap-1.5 shadow-sm group"
                >
                    <div className="w-9 h-9 rounded-xl bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white flex items-center justify-center text-base group-hover:scale-105 transition-transform">
                        📅
                    </div>
                    <span className="text-xs font-bold leading-tight">Follow-Up</span>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400">Book Slot</span>
                </button>

                {/* 5. Order Diagnostics */}
                <button
                    type="button"
                    disabled={!hasActivePatient}
                    onClick={onOrderDiagnostics}
                    className="p-3 rounded-xl border border-purple-200/80 dark:border-purple-900/50 bg-gradient-to-b from-purple-50/70 to-purple-100/30 dark:from-purple-950/40 dark:to-purple-900/20 hover:from-purple-100/80 dark:hover:from-purple-900/40 text-purple-900 dark:text-purple-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex flex-col items-center text-center gap-1.5 shadow-sm group"
                >
                    <div className="w-9 h-9 rounded-xl bg-purple-600 text-white flex items-center justify-center text-base shadow-md shadow-purple-500/20 group-hover:scale-105 transition-transform">
                        🔬
                    </div>
                    <span className="text-xs font-bold leading-tight">Order Labs</span>
                    <span className="text-[10px] text-purple-600 dark:text-purple-400">Diagnostics</span>
                </button>

                {/* 6. ABDM Consent & Records */}
                <button
                    type="button"
                    disabled={!hasActivePatient}
                    onClick={onRequestAbdmConsent}
                    className="p-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50/70 dark:bg-slate-800/40 hover:bg-slate-100 dark:hover:bg-slate-800/80 text-slate-800 dark:text-slate-200 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex flex-col items-center text-center gap-1.5 shadow-sm group"
                >
                    <div className="w-9 h-9 rounded-xl bg-slate-200 dark:bg-slate-700 text-slate-800 dark:text-white flex items-center justify-center text-base group-hover:scale-105 transition-transform">
                        🇮🇳
                    </div>
                    <span className="text-xs font-bold leading-tight">ABDM Consent</span>
                    <span className="text-[10px] text-slate-500 dark:text-slate-400">FHIR Pull</span>
                </button>
            </div>
        </div>
    );
}
