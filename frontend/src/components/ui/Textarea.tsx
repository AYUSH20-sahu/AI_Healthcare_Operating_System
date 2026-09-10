'use client';

import React from 'react';

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
    label?: string;
    error?: string;
    helperText?: string;
}

export const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
    ({ label, error, helperText, className = '', id, required, disabled, rows = 4, ...props }, ref) => {
        const textareaId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        return (
            <div className="w-full space-y-1.5">
                {label && (
                    <label
                        htmlFor={textareaId}
                        className="block text-xs font-medium text-slate-700 dark:text-slate-300"
                    >
                        {label} {required && <span className="text-rose-500">*</span>}
                    </label>
                )}
                <textarea
                    ref={ref}
                    id={textareaId}
                    rows={rows}
                    disabled={disabled}
                    className={`w-full p-3 text-sm rounded-lg transition-colors duration-150
                        bg-white dark:bg-slate-900/80 text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500
                        border ${
                            error
                                ? 'border-rose-500 focus:ring-rose-500'
                                : 'border-slate-300 dark:border-slate-700/80 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'
                        }
                        disabled:opacity-50 disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed
                        focus:outline-none ${className}`}
                    {...props}
                />
                {error ? (
                    <p className="text-xs text-rose-500 dark:text-rose-400">{error}</p>
                ) : helperText ? (
                    <p className="text-xs text-slate-500 dark:text-slate-400">{helperText}</p>
                ) : null}
            </div>
        );
    }
);

Textarea.displayName = 'Textarea';
