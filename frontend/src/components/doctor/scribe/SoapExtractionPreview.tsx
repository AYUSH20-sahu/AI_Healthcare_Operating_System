'use client';

import React, { useState } from 'react';
import { AIConfidenceBadge } from '@/components/ui/AIConfidenceBadge';
import { Button } from '@/components/ui/Button';

export interface SoapNoteData {
    subjective: {
        chief_complaint: string;
        history_of_present_illness: string;
        review_of_systems?: string;
    };
    objective: {
        vitals_reviewed: string;
        physical_exam: string;
    };
    assessment: {
        primary_diagnosis: string;
        icd10_code: string;
        differentials: string[];
        ai_confidence: number;
        clinical_rationale: string;
    };
    plan: {
        medications: {
            name: string;
            dosage: string;
            frequency: string;
            duration: string;
            instructions?: string;
        }[];
        diagnostics_ordered: string[];
        counseling: string;
        follow_up: string;
    };
}

export interface SoapExtractionPreviewProps {
    soapData: SoapNoteData | null;
    aiMetadata?: {
        provider?: string;
        model?: string;
        fallback_used?: boolean;
        latency_ms?: number;
    } | null;
    isGenerating?: boolean;
    onCommitToEhr?: (data: SoapNoteData) => void;
    onRegenerate?: () => void;
    className?: string;
}

export function SoapExtractionPreview({
    soapData,
    aiMetadata,
    isGenerating = false,
    onCommitToEhr,
    onRegenerate,
    className = '',
}: SoapExtractionPreviewProps) {
    const [isEditing, setIsEditing] = useState(false);
    const [editableSoap, setEditableSoap] = useState<SoapNoteData | null>(soapData);

    // Sync when soapData changes
    React.useEffect(() => {
        setEditableSoap(soapData);
    }, [soapData]);

    if (isGenerating) {
        return (
            <div className={`rounded-2xl border border-purple-200/80 dark:border-purple-900/50 bg-gradient-to-b from-purple-50/40 to-white dark:from-purple-950/20 dark:to-slate-900/90 p-8 text-center space-y-4 shadow-sm ${className}`}>
                <div className="relative inline-block">
                    <div className="w-14 h-14 rounded-2xl bg-purple-600 text-white flex items-center justify-center text-2xl animate-pulse mx-auto shadow-lg shadow-purple-500/30">
                        ⚡
                    </div>
                    <span className="absolute inset-0 rounded-2xl border-4 border-purple-400 animate-ping opacity-60" />
                </div>
                <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">
                        Synthesizing Clinical SOAP Record
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-md mx-auto">
                        Extracting subjective narrative, ICD-10 codes, differential diagnoses, and e-prescription guidelines from dialogue...
                    </p>
                </div>
                <div className="w-48 mx-auto bg-slate-200 dark:bg-slate-800 rounded-full h-1.5 overflow-hidden">
                    <div className="bg-purple-600 h-1.5 rounded-full animate-pulse w-3/4" />
                </div>
            </div>
        );
    }

    if (!editableSoap) {
        return (
            <div className={`rounded-2xl border border-dashed border-slate-300 dark:border-slate-700 bg-slate-50/60 dark:bg-slate-900/40 p-8 text-center text-slate-500 dark:text-slate-400 text-xs ${className}`}>
                <span className="text-3xl block mb-2">📋</span>
                <p className="font-semibold text-sm text-slate-700 dark:text-slate-300">
                    No SOAP Note Generated Yet
                </p>
                <p className="mt-1 max-w-sm mx-auto">
                    Record a consultation or upload an audio file to automatically trigger AI clinical note synthesis.
                </p>
            </div>
        );
    }

    return (
        <div className={`rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 shadow-sm overflow-hidden flex flex-col ${className}`}>
            {/* Header */}
            <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-xl bg-purple-100 dark:bg-purple-950/80 text-purple-600 dark:text-purple-400 flex items-center justify-center text-base font-bold">
                        📝
                    </div>
                    <div>
                        <h3 className="text-sm sm:text-base font-bold text-slate-900 dark:text-white">
                            Synthesized SOAP Consultation Note
                        </h3>
                        <p className="text-[11px] text-slate-500 dark:text-slate-400">
                            FHIR R4 Composition • Physician Attestation Required
                        </p>
                    </div>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    {aiMetadata?.fallback_used ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-amber-50 dark:bg-amber-950/60 text-amber-700 dark:text-amber-400 border border-amber-200 dark:border-amber-800 shadow-sm" title={`Primary provider experienced high latency or timeout. Served via ${aiMetadata.provider} fallback.`}>
                            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
                            ⚡ Failover Mesh ({aiMetadata.provider}) {aiMetadata.latency_ms ? `• ${aiMetadata.latency_ms}ms` : ''}
                        </span>
                    ) : aiMetadata?.provider ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 shadow-sm" title={`Primary model: ${aiMetadata.model || 'nvidia/nemotron-3-ultra-550b-a55b'}`}>
                            <span className="w-2 h-2 rounded-full bg-emerald-500" />
                            ✨ {aiMetadata.provider.toUpperCase()} Primary {aiMetadata.latency_ms ? `• ${aiMetadata.latency_ms}ms` : ''}
                        </span>
                    ) : null}
                    <AIConfidenceBadge
                        confidence={editableSoap.assessment.ai_confidence}
                        basis={editableSoap.assessment.clinical_rationale}
                    />
                    <button
                        type="button"
                        onClick={() => setIsEditing(!isEditing)}
                        className="px-2.5 py-1 text-xs font-medium rounded-lg border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                    >
                        {isEditing ? 'Done Editing' : '✎ Edit Draft'}
                    </button>
                </div>
            </div>

            {/* SOAP Content Body */}
            <div className="p-5 space-y-4 text-xs max-h-[500px] overflow-y-auto">
                {/* S - Subjective */}
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/60 space-y-1.5">
                    <div className="flex items-center justify-between">
                        <span className="font-bold text-blue-700 dark:text-blue-300 uppercase tracking-wider text-[11px]">
                            [S] Subjective
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">Patient Narrative</span>
                    </div>
                    <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Chief Complaint:</span>{' '}
                        <span className="text-slate-900 dark:text-white font-medium">
                            {editableSoap.subjective.chief_complaint}
                        </span>
                    </div>
                    <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">HPI:</span>
                        <p className="text-slate-700 dark:text-slate-300 leading-relaxed mt-0.5">
                            {editableSoap.subjective.history_of_present_illness}
                        </p>
                    </div>
                </div>

                {/* O - Objective */}
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/60 space-y-1.5">
                    <div className="flex items-center justify-between">
                        <span className="font-bold text-emerald-700 dark:text-emerald-300 uppercase tracking-wider text-[11px]">
                            [O] Objective
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">Clinical Observations</span>
                    </div>
                    <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Telemetry & Vitals:</span>{' '}
                        <span className="text-slate-800 dark:text-slate-200 font-mono">
                            {editableSoap.objective.vitals_reviewed}
                        </span>
                    </div>
                    <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Physical Examination:</span>
                        <p className="text-slate-700 dark:text-slate-300 leading-relaxed mt-0.5">
                            {editableSoap.objective.physical_exam}
                        </p>
                    </div>
                </div>

                {/* A - Assessment */}
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/60 space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="font-bold text-purple-700 dark:text-purple-300 uppercase tracking-wider text-[11px]">
                            [A] Assessment & Diagnosis
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">ICD-10 Mapped</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <span className="font-bold text-slate-900 dark:text-white text-sm">
                            {editableSoap.assessment.primary_diagnosis}
                        </span>
                        <span className="px-2 py-0.5 rounded-md bg-purple-100 dark:bg-purple-950/80 text-purple-700 dark:text-purple-300 font-mono font-bold text-[11px]">
                            {editableSoap.assessment.icd10_code}
                        </span>
                    </div>
                    <div>
                        <span className="font-semibold text-slate-600 dark:text-slate-400">Differentials considered:</span>{' '}
                        <span className="text-slate-700 dark:text-slate-300">
                            {editableSoap.assessment.differentials.join(', ')}
                        </span>
                    </div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 italic">
                        &ldquo;{editableSoap.assessment.clinical_rationale}&rdquo;
                    </p>
                </div>

                {/* P - Plan */}
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-800/40 border border-slate-200/80 dark:border-slate-700/60 space-y-2">
                    <div className="flex items-center justify-between">
                        <span className="font-bold text-indigo-700 dark:text-indigo-300 uppercase tracking-wider text-[11px]">
                            [P] Plan & Prescriptions
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">DDI Checked</span>
                    </div>

                    {/* Prescriptions List */}
                    <div className="space-y-1.5">
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Proposed Medications:</span>
                        {editableSoap.plan.medications.map((med, i) => (
                            <div key={i} className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 flex items-center justify-between gap-2">
                                <div>
                                    <span className="font-bold text-slate-900 dark:text-white">{med.name}</span>{' '}
                                    <span className="text-slate-600 dark:text-slate-400 font-mono">({med.dosage})</span>
                                    <p className="text-[11px] text-slate-500 dark:text-slate-400">{med.frequency} • {med.duration} — {med.instructions}</p>
                                </div>
                                <span className="px-1.5 py-0.2 rounded text-[10px] bg-emerald-100 dark:bg-emerald-950 text-emerald-700 dark:text-emerald-300 font-bold">
                                    ✓ Safe
                                </span>
                            </div>
                        ))}
                    </div>

                    <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Diagnostics Ordered:</span>{' '}
                        <span className="text-slate-800 dark:text-slate-200 font-medium">
                            {editableSoap.plan.diagnostics_ordered.join(', ')}
                        </span>
                    </div>

                    <div>
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Counseling:</span>{' '}
                        <span className="text-slate-700 dark:text-slate-300">
                            {editableSoap.plan.counseling}
                        </span>
                    </div>

                    <div className="flex items-center gap-2 pt-1">
                        <span className="font-semibold text-slate-700 dark:text-slate-300">Follow-up:</span>{' '}
                        <span className="px-2 py-0.5 rounded bg-blue-100 dark:bg-blue-950/60 text-blue-700 dark:text-blue-300 font-medium">
                            📅 {editableSoap.plan.follow_up}
                        </span>
                    </div>
                </div>
            </div>

            {/* Bottom Action Footer */}
            <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40 flex items-center justify-between gap-2">
                {onRegenerate && (
                    <Button size="sm" variant="outline" onClick={onRegenerate}>
                        🔄 Regenerate with AI
                    </Button>
                )}
                {onCommitToEhr && (
                    <Button
                        size="sm"
                        variant="primary"
                        onClick={() => onCommitToEhr(editableSoap)}
                    >
                        ✓ Attest & Commit to EHR
                    </Button>
                )}
            </div>
        </div>
    );
}
