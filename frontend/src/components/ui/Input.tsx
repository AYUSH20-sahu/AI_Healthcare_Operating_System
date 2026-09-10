'use client';

import React from 'react';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    helperText?: string;
    leadingIcon?: React.ReactNode;
    trailingIcon?: React.ReactNode;
    onTrailingIconClick?: () => void;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
    (
        {
            label,
            error,
            helperText,
            leadingIcon,
            trailingIcon,
            onTrailingIconClick,
            className = '',
            id,
            required,
            disabled,
            ...props
        },
        ref
    ) => {
        const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        return (
            <div className="w-full space-y-1.5">
                {label && (
                    <label
                        htmlFor={inputId}
                        className="block text-xs font-medium text-slate-700 dark:text-slate-300"
                    >
                        {label} {required && <span className="text-rose-500">*</span>}
                    </label>
                )}
                <div className="relative flex items-center">
                    {leadingIcon && (
                        <div className="absolute left-3.5 text-slate-400 dark:text-slate-500 pointer-events-none shrink-0 flex items-center">
                            {leadingIcon}
                        </div>
                    )}
                    <input
                        ref={ref}
                        id={inputId}
                        disabled={disabled}
                        className={`w-full h-11 px-3.5 text-sm rounded-lg transition-colors duration-150
                            bg-white dark:bg-slate-900/80 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500
                            border ${
                                error
                                    ? 'border-rose-500 focus:ring-rose-500'
                                    : 'border-slate-300 dark:border-slate-700/80 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'
                            }
                            ${leadingIcon ? 'pl-10' : ''}
                            ${trailingIcon ? 'pr-10' : ''}
                            disabled:opacity-50 disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed
                            focus:outline-none ${className}`}
                        {...props}
                    />
                    {trailingIcon && (
                        <button
                            type="button"
                            onClick={onTrailingIconClick}
                            disabled={disabled || !onTrailingIconClick}
                            className={`absolute right-3.5 text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 shrink-0 flex items-center ${
                                onTrailingIconClick ? 'cursor-pointer' : 'pointer-events-none'
                            }`}
                        >
                            {trailingIcon}
                        </button>
                    )}
                </div>
                {error ? (
                    <p className="text-xs text-rose-500 dark:text-rose-400 flex items-center gap-1">
                        <svg className="w-3.5 h-3.5 shrink-0" fill="currentColor" viewBox="0 0 20 20">
                            <path
                                fillRule="evenodd"
                                d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
                                clipRule="evenodd"
                            />
                        </svg>
                        <span>{error}</span>
                    </p>
                ) : helperText ? (
                    <p className="text-xs text-slate-500 dark:text-slate-400">{helperText}</p>
                ) : null}
            </div>
        );
    }
);

Input.displayName = 'Input';
