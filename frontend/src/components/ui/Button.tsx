'use client';

import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger' | 'success' | 'ai';
    size?: 'sm' | 'md' | 'lg';
    isLoading?: boolean;
    icon?: React.ReactNode;
    iconPosition?: 'left' | 'right';
    fullWidth?: boolean;
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    (
        {
            children,
            variant = 'primary',
            size = 'md',
            isLoading = false,
            icon,
            iconPosition = 'left',
            fullWidth = false,
            className = '',
            disabled,
            ...props
        },
        ref
    ) => {
        const baseStyles =
            'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed select-none active:scale-[0.98]';

        const sizeStyles = {
            sm: 'text-xs px-3 py-1.5 gap-1.5',
            md: 'text-sm px-4 py-2.5 gap-2',
            lg: 'text-base px-6 py-3 gap-2.5',
        };

        const variantStyles = {
            primary:
                'bg-blue-600 hover:bg-blue-500 text-white shadow-md shadow-blue-500/20 focus:ring-blue-500 border border-blue-500/30',
            secondary:
                'bg-slate-100 hover:bg-slate-200 text-slate-800 dark:bg-slate-800 dark:hover:bg-slate-700 dark:text-slate-100 border border-slate-200 dark:border-slate-700/60 focus:ring-slate-400',
            outline:
                'bg-transparent hover:bg-slate-100 dark:hover:bg-slate-800/60 text-slate-700 dark:text-slate-200 border border-slate-300 dark:border-slate-700 focus:ring-slate-400',
            ghost:
                'bg-transparent hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-700 dark:text-slate-300 border-transparent focus:ring-slate-400',
            danger:
                'bg-rose-600 hover:bg-rose-500 text-white shadow-md shadow-rose-500/20 focus:ring-rose-500 border border-rose-500/30',
            success:
                'bg-emerald-600 hover:bg-emerald-500 text-white shadow-md shadow-emerald-500/20 focus:ring-emerald-500 border border-emerald-500/30',
            ai:
                'bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-md shadow-purple-500/25 focus:ring-purple-500 border border-purple-400/30',
        };

        const widthStyle = fullWidth ? 'w-full' : '';

        return (
            <button
                ref={ref}
                disabled={disabled || isLoading}
                className={`${baseStyles} ${sizeStyles[size]} ${variantStyles[variant]} ${widthStyle} ${className}`}
                {...props}
            >
                {isLoading && (
                    <svg
                        className="animate-spin h-4 w-4 text-current"
                        fill="none"
                        viewBox="0 0 24 24"
                    >
                        <circle
                            className="opacity-25"
                            cx="12"
                            cy="12"
                            r="10"
                            stroke="currentColor"
                            strokeWidth="4"
                        />
                        <path
                            className="opacity-75"
                            fill="currentColor"
                            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                        />
                    </svg>
                )}
                {!isLoading && icon && iconPosition === 'left' && (
                    <span className="shrink-0">{icon}</span>
                )}
                <span>{children}</span>
                {!isLoading && icon && iconPosition === 'right' && (
                    <span className="shrink-0">{icon}</span>
                )}
            </button>
        );
    }
);

Button.displayName = 'Button';
