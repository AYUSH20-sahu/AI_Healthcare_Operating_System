'use client';

import React from 'react';

export interface CheckboxProps extends Omit<React.InputHTMLAttributes<HTMLInputElement>, 'type'> {
    label?: React.ReactNode;
    description?: string;
}

export const Checkbox = React.forwardRef<HTMLInputElement, CheckboxProps>(
    ({ label, description, className = '', id, disabled, ...props }, ref) => {
        const checkboxId = id || (typeof label === 'string' ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

        return (
            <div className={`flex items-start gap-2.5 ${disabled ? 'opacity-50 cursor-not-allowed' : ''} ${className}`}>
                <div className="flex items-center h-5">
                    <input
                        ref={ref}
                        id={checkboxId}
                        type="checkbox"
                        disabled={disabled}
                        className="w-4 h-4 rounded border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-900 text-blue-600 focus:ring-blue-500 focus:ring-offset-0 transition-colors cursor-pointer"
                        {...props}
                    />
                </div>
                {(label || description) && (
                    <div className="text-xs select-none">
                        {label && (
                            <label
                                htmlFor={checkboxId}
                                className="font-medium text-slate-700 dark:text-slate-300 cursor-pointer"
                            >
                                {label}
                            </label>
                        )}
                        {description && (
                            <p className="text-slate-500 dark:text-slate-400 mt-0.5">{description}</p>
                        )}
                    </div>
                )}
            </div>
        );
    }
);

Checkbox.displayName = 'Checkbox';
