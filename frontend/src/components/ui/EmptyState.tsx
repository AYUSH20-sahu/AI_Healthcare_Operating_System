'use client';

import React from 'react';

export interface EmptyStateProps {
    icon?: React.ReactNode;
    title: string;
    description: string;
    action?: React.ReactNode;
    className?: string;
}

export function EmptyState({
    icon,
    title,
    description,
    action,
    className = '',
}: EmptyStateProps) {
    return (
        <div
            className={`p-10 text-center rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 bg-slate-50/40 dark:bg-slate-900/30 flex flex-col items-center justify-center ${className}`}
        >
            <div className="w-12 h-12 rounded-2xl bg-blue-50 dark:bg-blue-500/10 text-blue-600 dark:text-blue-400 flex items-center justify-center mb-4 border border-blue-100 dark:border-blue-500/20">
                {icon || (
                    <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={1.5}
                            d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4"
                        />
                    </svg>
                )}
            </div>
            <h4 className="text-base font-semibold text-slate-900 dark:text-slate-100">{title}</h4>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 max-w-sm leading-relaxed">
                {description}
            </p>
            {action && <div className="mt-5">{action}</div>}
        </div>
    );
}
