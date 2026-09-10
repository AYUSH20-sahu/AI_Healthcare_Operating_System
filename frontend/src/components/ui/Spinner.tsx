'use client';

import React from 'react';

export interface SpinnerProps extends React.HTMLAttributes<HTMLDivElement> {
    size?: 'sm' | 'md' | 'lg';
    variant?: 'primary' | 'white' | 'purple';
}

export function Spinner({ size = 'md', variant = 'primary', className = '', ...props }: SpinnerProps) {
    const sizeStyles = {
        sm: 'w-4 h-4 border-2',
        md: 'w-6 h-6 border-2',
        lg: 'w-8 h-8 border-3',
    };

    const variantStyles = {
        primary: 'border-blue-500/20 border-t-blue-600 dark:border-blue-400/20 dark:border-t-blue-400',
        white: 'border-white/20 border-t-white',
        purple: 'border-purple-500/20 border-t-purple-600 dark:border-purple-400/20 dark:border-t-purple-400',
    };

    return (
        <div
            className={`inline-block rounded-full animate-spin ${sizeStyles[size]} ${variantStyles[variant]} ${className}`}
            role="status"
            aria-label="Loading"
            {...props}
        >
            <span className="sr-only">Loading...</span>
        </div>
    );
}
