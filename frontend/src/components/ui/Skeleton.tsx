'use client';

import React from 'react';

export interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
    variant?: 'text' | 'rectangular' | 'circular';
}

export function Skeleton({ variant = 'rectangular', className = '', ...props }: SkeletonProps) {
    const variantStyles = {
        text: 'h-4 rounded',
        rectangular: 'rounded-xl',
        circular: 'rounded-full',
    };

    return (
        <div
            className={`bg-slate-200/80 dark:bg-slate-800/80 animate-pulse ${variantStyles[variant]} ${className}`}
            {...props}
        />
    );
}
