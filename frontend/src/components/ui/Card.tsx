'use client';

import React from 'react';

export interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: 'default' | 'glass' | 'interactive';
    density?: 'normal' | 'compact';
}

export function Card({
    children,
    variant = 'default',
    density = 'normal',
    className = '',
    ...props
}: CardProps) {
    const variantStyles = {
        default:
            'bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 shadow-sm',
        glass:
            'glass-panel shadow-md',
        interactive:
            'bg-white dark:bg-slate-900/90 border border-slate-200 dark:border-slate-800 shadow-sm hover:border-blue-500/50 dark:hover:border-blue-500/40 hover:shadow-glow-sm transition-all duration-200 cursor-pointer',
    };

    const densityStyles = density === 'compact' ? 'p-4' : 'p-6';

    return (
        <div
            className={`rounded-xl text-slate-900 dark:text-slate-100 overflow-hidden ${variantStyles[variant]} ${className}`}
            {...props}
        >
            {children}
        </div>
    );
}

export function CardHeader({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div className={`p-5 border-b border-slate-100 dark:border-slate-800/80 ${className}`} {...props}>
            {children}
        </div>
    );
}

export function CardTitle({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
    return (
        <h3
            className={`text-base font-semibold tracking-tight text-slate-900 dark:text-slate-100 ${className}`}
            {...props}
        >
            {children}
        </h3>
    );
}

export function CardDescription({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
    return (
        <p className={`text-xs text-slate-500 dark:text-slate-400 mt-1 ${className}`} {...props}>
            {children}
        </p>
    );
}

export function CardContent({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div className={`p-5 ${className}`} {...props}>
            {children}
        </div>
    );
}

export function CardFooter({
    children,
    className = '',
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={`p-4 bg-slate-50/50 dark:bg-slate-900/40 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between ${className}`}
            {...props}
        >
            {children}
        </div>
    );
}
