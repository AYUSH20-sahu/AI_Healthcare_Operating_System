'use client';

import React, { useState } from 'react';
import { ApiError } from '@/lib/api';
import { Button } from './Button';

interface ErrorAlertProps {
    error: Error | ApiError | string | null;
    title?: string;
    onRetry?: () => void;
    isRetrying?: boolean;
    className?: string;
    showRequestId?: boolean;
}

export const ErrorAlert: React.FC<ErrorAlertProps> = ({
    error,
    title,
    onRetry,
    isRetrying = false,
    className = '',
    showRequestId = true,
}) => {
    const [copied, setCopied] = useState(false);

    if (!error) return null;

    const isApiError = error instanceof ApiError;
    const message = typeof error === 'string' ? error : error.message;
    const requestId = isApiError ? error.requestId : undefined;
    const isTimeout = isApiError ? error.isTimeout : false;
    const isOffline = isApiError ? error.isNetworkError : false;
    const canRetry = isApiError ? error.canRetry : !!onRetry;

    const copyRequestId = () => {
        if (requestId) {
            navigator.clipboard.writeText(requestId);
            setCopied(true);
            setTimeout(() => setCopied(false), 2000);
        }
    };

    // Derived icon & banner theme
    let icon = '⚠️';
    let defaultTitle = 'An error occurred';
    let borderTheme = 'border-red-200 dark:border-red-900/60 bg-red-50/90 dark:bg-red-950/40 text-red-800 dark:text-red-200';

    if (isTimeout) {
        icon = '⏱️';
        defaultTitle = 'Request Timed Out';
        borderTheme = 'border-amber-200 dark:border-amber-900/60 bg-amber-50/90 dark:bg-amber-950/40 text-amber-800 dark:text-amber-200';
    } else if (isOffline) {
        icon = '📡';
        defaultTitle = 'Network Connection Interrupted';
        borderTheme = 'border-orange-200 dark:border-orange-900/60 bg-orange-50/90 dark:bg-orange-950/40 text-orange-800 dark:text-orange-200';
    }

    return (
        <div
            role="alert"
            className={`rounded-xl border p-4 shadow-sm transition-all duration-200 ${borderTheme} ${className}`}
        >
            <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                    <span className="text-xl select-none mt-0.5" aria-hidden="true">
                        {icon}
                    </span>
                    <div className="space-y-1">
                        <h4 className="text-sm font-semibold tracking-tight">
                            {title || defaultTitle}
                        </h4>
                        <p className="text-xs leading-relaxed opacity-90 max-w-xl">
                            {message}
                        </p>

                        {/* Request ID Correlation Badge (Safe for support tickets) */}
                        {showRequestId && requestId && (
                            <div className="pt-1.5 flex items-center gap-2">
                                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-white/70 dark:bg-slate-900/60 border border-slate-200/60 dark:border-slate-800 text-slate-600 dark:text-slate-400">
                                    Ref: <span className="font-semibold text-slate-800 dark:text-slate-200">{requestId}</span>
                                </span>
                                <button
                                    type="button"
                                    onClick={copyRequestId}
                                    className="text-[11px] underline hover:no-underline opacity-80 hover:opacity-100 transition-opacity"
                                    title="Copy correlation identifier to clipboard"
                                >
                                    {copied ? '✓ Copied' : 'Copy ID'}
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* Optional Retry Button */}
                {onRetry && canRetry && (
                    <Button
                        type="button"
                        size="sm"
                        variant="secondary"
                        onClick={onRetry}
                        disabled={isRetrying}
                        className="text-xs shrink-0 self-start mt-0.5"
                    >
                        {isRetrying ? (
                            <span className="flex items-center gap-1.5">
                                <span className="animate-spin text-xs">⏳</span>
                                <span>Retrying...</span>
                            </span>
                        ) : (
                            <span className="flex items-center gap-1">
                                <span>🔄</span>
                                <span>Retry</span>
                            </span>
                        )}
                    </Button>
                )}
            </div>
        </div>
    );
};
