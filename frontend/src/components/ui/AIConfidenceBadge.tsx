'use client';

import React, { useState } from 'react';

export interface AIConfidenceBadgeProps {
    confidence?: number; // 0.0 to 1.0 or 0 to 100
    basis?: string;
    model?: string;
    className?: string;
}

export function AIConfidenceBadge({
    confidence,
    basis,
    model = 'Clinical Scribe v2.1',
    className = '',
}: AIConfidenceBadgeProps) {
    const [showPopover, setShowPopover] = useState(false);

    // Normalize confidence to 0 - 100
    const score =
        confidence === undefined
            ? null
            : confidence <= 1.0
            ? Math.round(confidence * 100)
            : Math.round(confidence);

    const getScoreColor = (val: number | null) => {
        if (val === null) return 'text-purple-400 bg-purple-500/10 border-purple-500/20';
        if (val >= 90) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
        if (val >= 75) return 'text-cyan-400 bg-cyan-500/10 border-cyan-500/20';
        if (val >= 60) return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
        return 'text-rose-400 bg-rose-500/10 border-rose-500/20';
    };

    return (
        <div className={`relative inline-flex items-center ${className}`}>
            <button
                type="button"
                onClick={() => setShowPopover(!showPopover)}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border transition-all duration-150 hover:brightness-110 active:scale-95 ${getScoreColor(
                    score
                )}`}
                title="Click for AI Clinical Rationale & Basis"
            >
                <svg
                    className="w-3.5 h-3.5 shrink-0 text-purple-400 animate-pulse"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                >
                    <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M13 10V3L4 14h7v7l9-11h-7z"
                    />
                </svg>
                <span>AI Draft</span>
                {score !== null && (
                    <span className="font-mono text-[11px] opacity-90">({score}%)</span>
                )}
                <svg
                    className="w-3 h-3 opacity-60 ml-0.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {showPopover && (
                <>
                    <div
                        className="fixed inset-0 z-30"
                        onClick={() => setShowPopover(false)}
                    />
                    <div className="absolute top-full left-0 mt-2 w-72 z-40 p-4 rounded-xl glass-panel shadow-xl text-left">
                        <div className="flex items-center justify-between pb-2 border-b border-slate-200 dark:border-slate-800">
                            <span className="text-xs font-semibold text-slate-900 dark:text-slate-100 flex items-center gap-1.5">
                                <span className="w-2 h-2 rounded-full bg-purple-500" />
                                AI Copilot Explainability
                            </span>
                            <span className="text-[10px] text-slate-500 font-mono">{model}</span>
                        </div>

                        <div className="mt-2.5 space-y-2 text-xs">
                            <div>
                                <span className="text-slate-500 dark:text-slate-400 block font-medium">
                                    Confidence Assessment:
                                </span>
                                <span className="text-slate-800 dark:text-slate-200">
                                    {score !== null ? `${score}% certainty based on STT & context` : 'Evaluation pending'}
                                </span>
                            </div>

                            <div>
                                <span className="text-slate-500 dark:text-slate-400 block font-medium">
                                    Clinical Basis:
                                </span>
                                <p className="text-slate-700 dark:text-slate-300 mt-0.5 leading-relaxed italic bg-slate-100 dark:bg-slate-800/80 p-2 rounded-lg border border-slate-200 dark:border-slate-700/50">
                                    {basis || 'Extracted directly from physician voice dictation transcript.'}
                                </p>
                            </div>

                            <div className="pt-1 text-[11px] text-amber-600 dark:text-amber-400 font-medium flex items-center gap-1">
                                <svg className="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                                    <path
                                        fillRule="evenodd"
                                        d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                                        clipRule="evenodd"
                                    />
                                </svg>
                                Requires physician review before finalization.
                            </div>
                        </div>
                    </div>
                </>
            )}
        </div>
    );
}
