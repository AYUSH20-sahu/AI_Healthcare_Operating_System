'use client';

import React from 'react';

export interface AlertProps extends Omit<React.HTMLAttributes<HTMLDivElement>, 'title'> {
    variant?: 'info' | 'warning' | 'error' | 'success' | 'emergency';
    title?: React.ReactNode;
    icon?: React.ReactNode;
    onClose?: () => void;
}

export function Alert({
    variant = 'info',
    title,
    icon,
    onClose,
    children,
    className = '',
    ...props
}: AlertProps) {
    const variantStyles = {
        info: 'bg-blue-50/80 dark:bg-blue-500/10 text-blue-900 dark:text-blue-200 border-blue-200 dark:border-blue-500/30',
        warning:
            'bg-amber-50/80 dark:bg-amber-500/10 text-amber-900 dark:text-amber-200 border-amber-200 dark:border-amber-500/30',
        error:
            'bg-rose-50/80 dark:bg-rose-500/10 text-rose-900 dark:text-rose-200 border-rose-200 dark:border-rose-500/30',
        success:
            'bg-emerald-50/80 dark:bg-emerald-500/10 text-emerald-900 dark:text-emerald-200 border-emerald-200 dark:border-emerald-500/30',
        emergency:
            'bg-rose-600/15 dark:bg-rose-500/20 text-rose-900 dark:text-rose-100 border-rose-500 dark:border-rose-500/60 shadow-lg shadow-rose-500/10 animate-pulse',
    };

    const defaultIcons = {
        info: (
            <svg className="w-5 h-5 text-blue-600 dark:text-blue-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        ),
        warning: (
            <svg className="w-5 h-5 text-amber-600 dark:text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
        ),
        error: (
            <svg className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        ),
        success: (
            <svg className="w-5 h-5 text-emerald-600 dark:text-emerald-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        ),
        emergency: (
            <svg className="w-5 h-5 text-rose-600 dark:text-rose-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
        ),
    };

    return (
        <div
            role="alert"
            className={`p-4 rounded-xl border flex items-start gap-3.5 text-xs relative ${variantStyles[variant]} ${className}`}
            {...props}
        >
            <div className="mt-0.5">{icon || defaultIcons[variant]}</div>
            <div className="flex-1 space-y-1 pr-4">
                {title && <h5 className="font-semibold text-sm leading-tight">{title}</h5>}
                <div className="leading-relaxed opacity-95">{children}</div>
            </div>
            {onClose && (
                <button
                    type="button"
                    onClick={onClose}
                    className="absolute top-3.5 right-3.5 text-current opacity-60 hover:opacity-100 transition-opacity p-1 rounded-lg"
                    aria-label="Close alert"
                >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                </button>
            )}
        </div>
    );
}

