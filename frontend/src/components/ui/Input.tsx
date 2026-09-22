'use client';

import React from 'react';

export type AllowedChars = 'numeric' | 'alpha' | 'alphanumeric' | 'all';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    helperText?: string;
    leadingIcon?: React.ReactNode;
    trailingIcon?: React.ReactNode;
    onTrailingIconClick?: () => void;
    allowedChars?: AllowedChars;
    allowDecimal?: boolean;
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
            allowedChars,
            allowDecimal,
            onKeyDown,
            onChange,
            onPaste,
            ...props
        },
        ref
    ) => {
        const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        // Password fields must allow all characters (letters, numbers, and symbols like @, #)
        const isPassword = props.type === 'password' || id?.toLowerCase().includes('password');
        const effectiveAllowed: AllowedChars = isPassword
            ? 'all'
            : allowedChars || (props.type === 'tel' || props.type === 'number' ? 'numeric' : 'all');

        const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
            onKeyDown?.(e);
            if (e.defaultPrevented || effectiveAllowed === 'all') return;

            // Allow navigation and editing control keys
            if (
                e.key === 'Backspace' ||
                e.key === 'Delete' ||
                e.key === 'Tab' ||
                e.key === 'Enter' ||
                e.key === 'Escape' ||
                e.key.startsWith('Arrow') ||
                e.key === 'Home' ||
                e.key === 'End' ||
                e.ctrlKey ||
                e.metaKey ||
                e.altKey
            ) {
                return;
            }

            if (effectiveAllowed === 'numeric') {
                if (allowDecimal && (e.key === '.' || e.key === 'Decimal')) {
                    if (e.currentTarget.value.includes('.')) {
                        e.preventDefault();
                    }
                    return;
                }
                if (!/^[0-9]$/.test(e.key)) {
                    e.preventDefault();
                }
            } else if (effectiveAllowed === 'alpha') {
                if (!/^[a-zA-Z\s]$/.test(e.key)) {
                    e.preventDefault();
                }
            } else if (effectiveAllowed === 'alphanumeric') {
                if (!/^[a-zA-Z0-9\s]$/.test(e.key)) {
                    e.preventDefault();
                }
            }
        };

        const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
            let val = e.target.value;
            if (effectiveAllowed === 'numeric') {
                if (allowDecimal) {
                    const parts = val.replace(/[^0-9.]/g, '').split('.');
                    val = parts[0] + (parts.length > 1 ? '.' + parts.slice(1).join('') : '');
                } else {
                    val = val.replace(/\D/g, '');
                }
                if (props.maxLength && val.length > props.maxLength) {
                    val = val.slice(0, props.maxLength);
                }
                e.target.value = val;
            } else if (effectiveAllowed === 'alpha') {
                val = val.replace(/[^a-zA-Z\s]/g, '');
                e.target.value = val;
            } else if (effectiveAllowed === 'alphanumeric') {
                val = val.replace(/[^a-zA-Z0-9\s]/g, '');
                e.target.value = val;
            }

            onChange?.(e);
        };

        const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
            onPaste?.(e);
            if (e.defaultPrevented || effectiveAllowed === 'all') return;

            const pasted = e.clipboardData.getData('text');
            if (effectiveAllowed === 'numeric') {
                const isValid = allowDecimal ? /^[0-9]*\.?[0-9]*$/.test(pasted) : /^[0-9]*$/.test(pasted);
                if (!isValid) {
                    e.preventDefault();
                    const cleaned = allowDecimal
                        ? pasted.replace(/[^0-9.]/g, '')
                        : pasted.replace(/\D/g, '');
                    document.execCommand?.('insertText', false, cleaned);
                }
            } else if (effectiveAllowed === 'alpha') {
                if (!/^[a-zA-Z\s]*$/.test(pasted)) {
                    e.preventDefault();
                    const cleaned = pasted.replace(/[^a-zA-Z\s]/g, '');
                    document.execCommand?.('insertText', false, cleaned);
                }
            }
        };

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
                        onKeyDown={handleKeyDown}
                        onChange={handleChange}
                        onPaste={handlePaste}
                        inputMode={
                            props.inputMode ||
                            (effectiveAllowed === 'numeric'
                                ? allowDecimal
                                    ? 'decimal'
                                    : 'numeric'
                                : undefined)
                        }
                        pattern={
                            props.pattern ||
                            (effectiveAllowed === 'numeric'
                                ? allowDecimal
                                    ? '[0-9]*\\.?[0-9]*'
                                    : '[0-9]*'
                                : effectiveAllowed === 'alpha'
                                ? '[a-zA-Z\\s]*'
                                : undefined)
                        }
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
