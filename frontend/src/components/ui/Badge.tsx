'use client';

import React from 'react';

export interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
    variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info' | 'purple' | 'outline';
    size?: 'sm' | 'md';
    dot?: boolean;
}

export function Badge({
    children,
    variant = 'default',
    size = 'sm',
    dot = false,
    className = '',
    ...props
}: BadgeProps) {
    const sizeStyles = {
        sm: 'text-[11px] px-2 py-0.5 gap-1.5',
        md: 'text-xs px-2.5 py-1 gap-1.5',
    };

    const variantStyles = {
        default:
            'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300 border border-slate-200 dark:border-slate-700/60',
        primary:
            'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-400 border border-blue-200 dark:border-blue-500/20',
        success:
            'bg-emerald-50 text-emerald-700 dark:bg-emerald-500/10 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20',
        warning:
            'bg-amber-50 text-amber-700 dark:bg-amber-500/10 dark:text-amber-400 border border-amber-200 dark:border-amber-500/20',
        danger:
            'bg-rose-50 text-rose-700 dark:bg-rose-500/10 dark:text-rose-400 border border-rose-200 dark:border-rose-500/20',
        info:
            'bg-cyan-50 text-cyan-700 dark:bg-cyan-500/10 dark:text-cyan-400 border border-cyan-200 dark:border-cyan-500/20',
        purple:
            'bg-purple-50 text-purple-700 dark:bg-purple-500/10 dark:text-purple-400 border border-purple-200 dark:border-purple-500/20',
        outline:
            'bg-transparent text-slate-600 dark:text-slate-400 border border-slate-300 dark:border-slate-700',
    };

    const dotStyles = {
        default: 'bg-slate-400',
        primary: 'bg-blue-500',
        success: 'bg-emerald-500',
        warning: 'bg-amber-500',
        danger: 'bg-rose-500',
        info: 'bg-cyan-500',
        purple: 'bg-purple-500',
        outline: 'bg-slate-400',
    };

    return (
        <span
            className={`inline-flex items-center font-medium rounded-full select-none ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
            {...props}
        >
            {dot && <span className={`w-1.5 h-1.5 rounded-full shrink-0 ${dotStyles[variant]}`} />}
            <span>{children}</span>
        </span>
    );
}
