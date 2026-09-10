'use client';

import React from 'react';

export interface SelectOption {
    value: string;
    label: string;
    disabled?: boolean;
}

export interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
    label?: string;
    error?: string;
    helperText?: string;
    options: SelectOption[];
    placeholder?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
    (
        {
            label,
            error,
            helperText,
            options,
            placeholder,
            className = '',
            id,
            required,
            disabled,
            ...props
        },
        ref
    ) => {
        const selectId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        return (
            <div className="w-full space-y-1.5">
                {label && (
                    <label
                        htmlFor={selectId}
                        className="block text-xs font-medium text-slate-700 dark:text-slate-300"
                    >
                        {label} {required && <span className="text-rose-500">*</span>}
                    </label>
                )}
                <div className="relative flex items-center">
                    <select
                        ref={ref}
                        id={selectId}
                        disabled={disabled}
                        className={`w-full h-11 px-3.5 pr-10 text-sm rounded-lg appearance-none transition-colors duration-150
                            bg-white dark:bg-slate-900/80 text-slate-900 dark:text-slate-100
                            border ${
                                error
                                    ? 'border-rose-500 focus:ring-rose-500'
                                    : 'border-slate-300 dark:border-slate-700/80 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20'
                            }
                            disabled:opacity-50 disabled:bg-slate-100 dark:disabled:bg-slate-800 disabled:cursor-not-allowed
                            focus:outline-none ${className}`}
                        {...props}
                    >
                        {placeholder && (
                            <option value="" disabled>
                                {placeholder}
                            </option>
                        )}
                        {options.map((option) => (
                            <option
                                key={option.value}
                                value={option.value}
                                disabled={option.disabled}
                                className="bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100"
                            >
                                {option.label}
                            </option>
                        ))}
                    </select>
                    <div className="absolute right-3.5 pointer-events-none text-slate-400 dark:text-slate-500 flex items-center">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M19 9l-7 7-7-7"
                            />
                        </svg>
                    </div>
                </div>
                {error ? (
                    <p className="text-xs text-rose-500 dark:text-rose-400">{error}</p>
                ) : helperText ? (
                    <p className="text-xs text-slate-500 dark:text-slate-400">{helperText}</p>
                ) : null}
            </div>
        );
    }
);

Select.displayName = 'Select';
