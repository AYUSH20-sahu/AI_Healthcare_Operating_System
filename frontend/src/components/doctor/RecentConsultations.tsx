'use client';

import React from 'react';
import { StatusBadge } from '@/components/ui/StatusBadge';
import { AIConfidenceBadge } from '@/components/ui/AIConfidenceBadge';
import { Button } from '@/components/ui/Button';

export interface RecentConsultationItem {
    record_id: string;
    patient_id: string;
    patient_name: string;
    created_at: string;
    status: 'DRAFT' | 'FINALIZED' | 'AMENDED';
    chief_complaint: string;
    provisional_diagnosis?: string;
    icd10_code?: string;
    ai_confidence?: number;
    ai_rationale?: string;
    prescriptions_summary?: string;
}

interface RecentConsultationsProps {
    consultations: RecentConsultationItem[];
    onSelectRecord?: (record: RecentConsultationItem) => void;
    onReviewRecord?: (record: RecentConsultationItem) => void;
}

export function RecentConsultations({
    consultations,
    onSelectRecord,
    onReviewRecord,
}: RecentConsultationsProps) {
    const formatDate = (dateStr: string) => {
        try {
            return new Date(dateStr).toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
            });
        } catch {
            return dateStr;
        }
    };

    return (
        <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white/90 dark:bg-slate-900/90 shadow-sm overflow-hidden backdrop-blur-md">
            <div className="p-4 sm:p-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between">
                <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white flex items-center gap-2">
                        <span>Recent Consultations & Clinical Records</span>
                        <span className="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300">
                            {consultations.length}
                        </span>
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
                        Clinical documentation timeline with physician review gate and AI confidence audit.
                    </p>
                </div>
            </div>

            <div className="divide-y divide-slate-200 dark:divide-slate-800">
                {consultations.length === 0 ? (
                    <div className="p-8 text-center text-slate-500 dark:text-slate-400 text-xs">
                        No recent consultations recorded today.
                    </div>
                ) : (
                    consultations.map((record) => {
                        const isDraft = record.status === 'DRAFT';
                        return (
                            <div
                                key={record.record_id}
                                onClick={() => onSelectRecord && onSelectRecord(record)}
                                className={`p-4 sm:p-4.5 hover:bg-slate-50/80 dark:hover:bg-slate-800/40 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-3.5 ${
                                    isDraft ? 'bg-amber-50/30 dark:bg-amber-950/10' : ''
                                }`}
                            >
                                <div className="space-y-1.5 flex-1">
                                    <div className="flex flex-wrap items-center gap-2">
                                        <span className="font-bold text-slate-900 dark:text-white text-sm">
                                            {record.patient_name}
                                        </span>
                                        <span className="text-xs text-slate-500 dark:text-slate-400">
                                            • {formatDate(record.created_at)}
                                        </span>
                                        <StatusBadge status={record.status} />
                                        {record.ai_confidence !== undefined && (
                                            <AIConfidenceBadge
                                                confidence={record.ai_confidence}
                                                basis={record.ai_rationale || 'Derived from ambient consultation transcript and ICD-10 clinical guidelines.'}
                                            />
                                        )}
                                    </div>

                                    <p className="text-xs text-slate-700 dark:text-slate-300 font-medium">
                                        Chief Complaint: &ldquo;{record.chief_complaint}&rdquo;
                                    </p>

                                    <div className="flex flex-wrap items-center gap-2 text-xs">
                                        {record.provisional_diagnosis && (
                                            <span className="px-2 py-0.5 rounded-md bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-300 font-medium border border-blue-200/60 dark:border-blue-800/40">
                                                Dx: {record.provisional_diagnosis}
                                                {record.icd10_code && (
                                                    <span className="ml-1 opacity-75 font-mono text-[10px]">
                                                        [{record.icd10_code}]
                                                    </span>
                                                )}
                                            </span>
                                        )}

                                        {record.prescriptions_summary && (
                                            <span className="px-2 py-0.5 rounded-md bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 font-medium border border-emerald-200/60 dark:border-emerald-800/40">
                                                Rx: {record.prescriptions_summary}
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 self-end md:self-center" onClick={(e) => e.stopPropagation()}>
                                    {isDraft ? (
                                        <Button
                                            size="sm"
                                            variant="ai"
                                            onClick={() => onReviewRecord && onReviewRecord(record)}
                                        >
                                            ✍️ Review & Sign Note
                                        </Button>
                                    ) : (
                                        <Button
                                            size="sm"
                                            variant="ghost"
                                            onClick={() => onSelectRecord && onSelectRecord(record)}
                                        >
                                            View Details →
                                        </Button>
                                    )}
                                </div>
                            </div>
                        );
                    })
                )}
            </div>
        </div>
    );
}
