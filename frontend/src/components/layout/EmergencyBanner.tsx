'use client';

import React, { useState, useEffect } from 'react';

export interface EmergencyAlert {
    id: string;
    level: 'critical' | 'severe' | 'warning';
    title: string;
    description: string;
    patientName?: string;
    patientId?: string;
    timestamp?: string;
}

export function EmergencyBanner() {
    const [alerts, setAlerts] = useState<EmergencyAlert[]>([]);
    const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());
    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        const handleEmergencyEvent = (e: CustomEvent<EmergencyAlert>) => {
            if (e.detail && e.detail.id) {
                setAlerts((prev) => {
                    if (prev.some((a) => a.id === e.detail.id)) return prev;
                    return [e.detail, ...prev];
                });
            }
        };

        window.addEventListener('aihos:emergency_alert' as any, handleEmergencyEvent as EventListener);
        return () => {
            window.removeEventListener('aihos:emergency_alert' as any, handleEmergencyEvent as EventListener);
        };
    }, []);

    const activeAlerts = alerts.filter((a) => !dismissedIds.has(a.id));

    if (activeAlerts.length === 0) {
        return null;
    }

    const currentAlert = activeAlerts[0];

    const dismissAlert = (id: string) => {
        setDismissedIds((prev) => {
            const next = new Set(prev);
            next.add(id);
            return next;
        });
    };


    return (
        <div className="w-full bg-gradient-to-r from-rose-600 via-red-600 to-rose-700 text-white shadow-lg border-b border-rose-500/50 z-30 transition-all duration-200">
            <div className="max-w-7xl mx-auto px-4 py-2.5 sm:py-3 flex items-center justify-between gap-3 text-xs sm:text-sm">
                <div className="flex items-center gap-2.5 min-w-0 flex-1">
                    <div className="relative flex items-center justify-center shrink-0">
                        <span className="w-3 h-3 rounded-full bg-white animate-ping absolute" />
                        <span className="w-2.5 h-2.5 rounded-full bg-white shrink-0" />
                    </div>

                    <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 min-w-0">
                        <span className="font-bold tracking-wide uppercase px-1.5 py-0.5 rounded bg-black/25 text-[11px] border border-white/20">
                            {currentAlert.level === 'critical' ? 'CRITICAL SAFETY ALERT' : 'CLINICAL WARNING'}
                        </span>
                        <span className="font-semibold truncate">{currentAlert.title}</span>
                        <span className="opacity-90 hidden md:inline truncate">— {currentAlert.description}</span>
                    </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                    <button
                        type="button"
                        onClick={() => setExpanded(!expanded)}
                        className="px-2 py-1 rounded bg-white/15 hover:bg-white/25 text-xs font-medium transition-colors"
                    >
                        {expanded ? 'Collapse' : 'Details'}
                    </button>
                    <button
                        type="button"
                        onClick={() => dismissAlert(currentAlert.id)}
                        className="p-1 rounded hover:bg-white/20 text-white/80 hover:text-white transition-colors"
                        aria-label="Dismiss alert"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
            </div>

            {expanded && (
                <div className="bg-black/25 px-4 py-3 border-t border-white/10 text-xs text-white/90">
                    <div className="max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div>
                            <span className="text-white/60 block">Condition / Trigger:</span>
                            <span className="font-medium text-white">{currentAlert.title}</span>
                        </div>
                        <div>
                            <span className="text-white/60 block">Clinical Impact:</span>
                            <span className="font-medium text-white">{currentAlert.description}</span>
                        </div>
                        {currentAlert.patientName && (
                            <div>
                                <span className="text-white/60 block">Affected Patient:</span>
                                <span className="font-medium text-white">{currentAlert.patientName} {currentAlert.patientId ? `(${currentAlert.patientId})` : ''}</span>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

// Global helper to trigger emergency alert from any component
export function triggerEmergencyAlert(alert: EmergencyAlert) {
    if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('aihos:emergency_alert', { detail: alert }));
    }
}
