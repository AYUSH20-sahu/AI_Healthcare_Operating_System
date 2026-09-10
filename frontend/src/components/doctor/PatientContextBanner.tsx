'use client';

import React, { useState } from 'react';
import { Badge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';

export interface PatientVitals {
    bp: string; // e.g. "128/82"
    hr: number; // e.g. 76 bpm
    spo2: number; // e.g. 98%
    temp: number; // e.g. 98.6 F
    glucose?: number; // e.g. 110 mg/dL
    lastUpdated?: string;
}

export interface PatientAllergy {
    substance: string;
    severity: 'critical' | 'moderate' | 'mild';
    reaction: string;
}

export interface PatientContextData {
    patient_id: string;
    full_name: string;
    age: number;
    gender: string;
    blood_group: string;
    abha_address?: string;
    phone?: string;
    vitals: PatientVitals;
    allergies: PatientAllergy[];
    risk_flags: string[];
}

interface PatientContextBannerProps {
    patient: PatientContextData | null;
    onSwitchPatient?: () => void;
    onClearPatient?: () => void;
}

export function PatientContextBanner({
    patient,
    onSwitchPatient,
    onClearPatient,
}: PatientContextBannerProps) {
    const [copiedAbha, setCopiedAbha] = useState(false);
    const [isExpanded, setIsExpanded] = useState(false);

    if (!patient) {
        return (
            <div className="rounded-2xl border border-dashed border-slate-300 dark:border-slate-700/80 bg-slate-50/60 dark:bg-slate-900/40 p-4 text-center">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 max-w-4xl mx-auto">
                    <div className="flex items-center gap-3 text-left">
                        <div className="w-10 h-10 rounded-xl bg-blue-100 dark:bg-blue-950/60 text-blue-600 dark:text-blue-400 flex items-center justify-center font-bold text-lg">
                            🏥
                        </div>
                        <div>
                            <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                                No Active Patient In Context
                            </p>
                            <p className="text-xs text-slate-500 dark:text-slate-400">
                                Select a patient from today&apos;s queue to unlock ambient scribe, vitals telemetry, and clinical notes.
                            </p>
                        </div>
                    </div>
                    {onSwitchPatient && (
                        <Button size="sm" variant="primary" onClick={onSwitchPatient}>
                            Select Patient from Queue
                        </Button>
                    )}
                </div>
            </div>
        );
    }

    const copyAbha = () => {
        if (patient.abha_address) {
            navigator.clipboard.writeText(patient.abha_address);
            setCopiedAbha(true);
            setTimeout(() => setCopiedAbha(false), 2000);
        }
    };

    // Calculate BP status
    const [sys] = patient.vitals.bp.split('/').map(n => parseInt(n, 10));
    const isBpElevated = !isNaN(sys) && sys >= 130;

    return (
        <div className="rounded-2xl border border-blue-200/80 dark:border-blue-900/50 bg-gradient-to-r from-blue-50/70 via-white to-slate-50/70 dark:from-slate-900/90 dark:via-[#0B0F19] dark:to-slate-900/90 shadow-sm backdrop-blur-md overflow-hidden transition-all duration-200">
            {/* Top Identity & Status Bar */}
            <div className="p-4 sm:p-5 flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-slate-200/70 dark:border-slate-800/80">
                {/* Left: Patient Identity */}
                <div className="flex items-center gap-4">
                    <div className="relative">
                        <div className="w-13 h-13 sm:w-14 sm:h-14 rounded-2xl bg-gradient-to-tr from-blue-600 to-indigo-500 text-white flex items-center justify-center text-xl font-bold shadow-md shadow-blue-500/20">
                            {patient.full_name.charAt(0).toUpperCase()}
                        </div>
                        <span className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-emerald-500 ring-2 ring-white dark:ring-slate-900 flex items-center justify-center text-[9px] text-white">
                            ✓
                        </span>
                    </div>

                    <div>
                        <div className="flex flex-wrap items-center gap-2">
                            <h2 className="text-lg sm:text-xl font-bold text-slate-900 dark:text-white tracking-tight">
                                {patient.full_name}
                            </h2>
                            <span className="px-2 py-0.5 text-xs font-semibold rounded-md bg-slate-200/80 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                                {patient.age}y • {patient.gender}
                            </span>
                            <span className="px-2 py-0.5 text-xs font-bold rounded-md bg-red-100 dark:bg-red-950/60 text-red-700 dark:text-red-400 border border-red-200/60 dark:border-red-900/40">
                                {patient.blood_group}
                            </span>
                        </div>

                        {/* ABHA & Verification Meta */}
                        <div className="flex flex-wrap items-center gap-2.5 mt-1.5 text-xs text-slate-600 dark:text-slate-400">
                            {patient.abha_address && (
                                <button
                                    type="button"
                                    onClick={copyAbha}
                                    title="Click to copy ABHA address"
                                    className="group flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/40 border border-blue-200/60 dark:border-blue-800/50 hover:bg-blue-100 dark:hover:bg-blue-900/50 transition-colors text-blue-700 dark:text-blue-300 font-mono text-[11px]"
                                >
                                    <span>ABHA: {patient.abha_address}</span>
                                    <span className="text-[10px] text-blue-500">
                                        {copiedAbha ? '✓ Copied' : '📋'}
                                    </span>
                                </button>
                            )}
                            <span className="hidden sm:inline-block text-slate-300 dark:text-slate-700">•</span>
                            <span>ID: {patient.patient_id.slice(0, 8)}...</span>
                            {patient.phone && (
                                <>
                                    <span className="hidden sm:inline-block text-slate-300 dark:text-slate-700">•</span>
                                    <span>📞 {patient.phone}</span>
                                </>
                            )}
                        </div>
                    </div>
                </div>

                {/* Right: Actions */}
                <div className="flex items-center gap-2 w-full lg:w-auto justify-end">
                    <button
                        type="button"
                        onClick={() => setIsExpanded(!isExpanded)}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors flex items-center gap-1"
                    >
                        <span>{isExpanded ? 'Hide Details' : 'View Clinical Flags'}</span>
                        <svg
                            className={`w-3.5 h-3.5 transition-transform duration-200 ${isExpanded ? 'rotate-180' : ''}`}
                            fill="none"
                            stroke="currentColor"
                            viewBox="0 0 24 24"
                        >
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>

                    {onSwitchPatient && (
                        <Button size="sm" variant="outline" onClick={onSwitchPatient}>
                            🔄 Switch
                        </Button>
                    )}

                    {onClearPatient && (
                        <button
                            type="button"
                            onClick={onClearPatient}
                            aria-label="Clear active patient context"
                            className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        >
                            ✕
                        </button>
                    )}
                </div>
            </div>

            {/* Vitals & Telemetry Strip */}
            <div className="px-4 sm:px-5 py-3 bg-slate-50/80 dark:bg-slate-900/60 flex flex-wrap items-center justify-between gap-3 text-xs">
                <div className="flex flex-wrap items-center gap-4 sm:gap-6">
                    {/* BP */}
                    <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 dark:text-slate-400">BP:</span>
                        <span className={`font-semibold font-mono ${isBpElevated ? 'text-rose-600 dark:text-rose-400 font-bold' : 'text-slate-900 dark:text-slate-100'}`}>
                            {patient.vitals.bp} mmHg
                        </span>
                        {isBpElevated && (
                            <span className="px-1.5 py-0.2 text-[10px] bg-rose-100 dark:bg-rose-950/60 text-rose-700 dark:text-rose-300 rounded font-medium">
                                High
                            </span>
                        )}
                    </div>

                    {/* HR */}
                    <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 dark:text-slate-400">HR:</span>
                        <span className="font-semibold font-mono text-slate-900 dark:text-slate-100">
                            {patient.vitals.hr} bpm
                        </span>
                    </div>

                    {/* SpO2 */}
                    <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 dark:text-slate-400">SpO2:</span>
                        <span className="font-semibold font-mono text-emerald-600 dark:text-emerald-400">
                            {patient.vitals.spo2}%
                        </span>
                    </div>

                    {/* Temp */}
                    <div className="flex items-center gap-1.5">
                        <span className="text-slate-500 dark:text-slate-400">Temp:</span>
                        <span className="font-semibold font-mono text-slate-900 dark:text-slate-100">
                            {patient.vitals.temp} °F
                        </span>
                    </div>

                    {/* Blood Glucose */}
                    {patient.vitals.glucose && (
                        <div className="flex items-center gap-1.5">
                            <span className="text-slate-500 dark:text-slate-400">Glucose:</span>
                            <span className="font-semibold font-mono text-slate-900 dark:text-slate-100">
                                {patient.vitals.glucose} mg/dL
                            </span>
                        </div>
                    )}
                </div>

                {/* Primary Safety Alert Capsules */}
                <div className="flex flex-wrap items-center gap-1.5">
                    {patient.allergies.map((allergy, i) => (
                        <span
                            key={i}
                            className={`px-2 py-0.5 text-[11px] font-semibold rounded-full flex items-center gap-1 border ${
                                allergy.severity === 'critical'
                                    ? 'bg-rose-100 dark:bg-rose-950/70 text-rose-800 dark:text-rose-300 border-rose-300 dark:border-rose-900/60'
                                    : 'bg-amber-100 dark:bg-amber-950/70 text-amber-800 dark:text-amber-300 border-amber-300 dark:border-amber-900/60'
                            }`}
                        >
                            <span>⚠️ Allergy: {allergy.substance}</span>
                        </span>
                    ))}

                    {patient.risk_flags.map((risk, i) => (
                        <span
                            key={i}
                            className="px-2 py-0.5 text-[11px] font-medium rounded-full bg-indigo-100 dark:bg-indigo-950/70 text-indigo-800 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-900/60"
                        >
                            🛡️ {risk}
                        </span>
                    ))}
                </div>
            </div>

            {/* Expandable Safety Details Drawer */}
            {isExpanded && (
                <div className="p-4 sm:p-5 bg-white dark:bg-slate-950/40 border-t border-slate-200/70 dark:border-slate-800/80 text-xs space-y-3">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                            <p className="font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[11px] mb-2">
                                Known Allergies & Adverse Reactions
                            </p>
                            {patient.allergies.length === 0 ? (
                                <p className="text-slate-500 dark:text-slate-400">No known drug allergies recorded (NKDA).</p>
                            ) : (
                                <ul className="space-y-1.5">
                                    {patient.allergies.map((a, i) => (
                                        <li key={i} className="flex items-center justify-between p-2 rounded-lg bg-rose-50/60 dark:bg-rose-950/30 border border-rose-200/50 dark:border-rose-900/30">
                                            <span className="font-semibold text-rose-900 dark:text-rose-200">{a.substance}</span>
                                            <span className="text-slate-600 dark:text-slate-400 text-[11px]">Reaction: {a.reaction}</span>
                                            <span className="text-[10px] uppercase font-bold text-rose-600 dark:text-rose-400">{a.severity}</span>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>

                        <div>
                            <p className="font-semibold text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[11px] mb-2">
                                Clinical Safeguard Directives
                            </p>
                            <div className="flex flex-wrap gap-2">
                                {patient.risk_flags.map((r, i) => (
                                    <div key={i} className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800/60 border border-slate-200 dark:border-slate-700/60 text-slate-700 dark:text-slate-300">
                                        <span className="font-medium">{r}</span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
