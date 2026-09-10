'use client';

import React, { useEffect, useRef } from 'react';

export interface ModalProps {
    isOpen: boolean;
    onClose: () => void;
    title?: React.ReactNode;
    description?: React.ReactNode;
    children: React.ReactNode;
    footer?: React.ReactNode;
    size?: 'sm' | 'md' | 'lg' | 'xl';
}

export function Modal({
    isOpen,
    onClose,
    title,
    description,
    children,
    footer,
    size = 'md',
}: ModalProps) {
    const dialogRef = useRef<HTMLDivElement>(null);

    // Close on Escape key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                onClose();
            }
        };

        if (isOpen) {
            document.addEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'hidden';
        }

        return () => {
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = 'unset';
        };
    }, [isOpen, onClose]);

    if (!isOpen) return null;

    const sizeStyles = {
        sm: 'max-w-md',
        md: 'max-w-lg',
        lg: 'max-w-2xl',
        xl: 'max-w-4xl',
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6">
            {/* Backdrop */}
            <div
                className="fixed inset-0 bg-slate-950/70 backdrop-blur-sm transition-opacity"
                onClick={onClose}
                aria-hidden="true"
            />

            {/* Dialog Panel */}
            <div
                ref={dialogRef}
                role="dialog"
                aria-modal="true"
                className={`relative w-full ${sizeStyles[size]} bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden z-10 animate-in fade-in zoom-in-95 duration-150`}
            >
                {/* Header */}
                {(title || description) && (
                    <div className="px-6 py-5 border-b border-slate-100 dark:border-slate-800/80 flex items-start justify-between">
                        <div>
                            {title && (
                                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                                    {title}
                                </h3>
                            )}
                            {description && (
                                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                    {description}
                                </p>
                            )}
                        </div>
                        <button
                            type="button"
                            onClick={onClose}
                            className="text-slate-400 hover:text-slate-600 dark:text-slate-500 dark:hover:text-slate-300 p-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M6 18L18 6M6 6l12 12"
                                />
                            </svg>
                        </button>
                    </div>
                )}

                {/* Content */}
                <div className="p-6 max-h-[75vh] overflow-y-auto">{children}</div>

                {/* Footer */}
                {footer && (
                    <div className="px-6 py-4 bg-slate-50/60 dark:bg-slate-900/40 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-end gap-3">
                        {footer}
                    </div>
                )}
            </div>
        </div>
    );
}
