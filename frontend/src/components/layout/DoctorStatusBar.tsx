'use client';

import React, { useState, useEffect, useRef } from 'react';

export type DoctorStatus = 'available' | 'in_consultation' | 'break' | 'off_duty';

interface DoctorStatusBarProps {
    compact?: boolean;
}

const statusConfig: Record<DoctorStatus, { label: string; color: string; ring: string; desc: string }> = {
    available: {
        label: 'Available for Care',
        color: 'bg-emerald-500',
        ring: 'ring-emerald-500/30',
        desc: 'Accepting urgent triage & scheduled patients',
    },
    in_consultation: {
        label: 'In Consultation',
        color: 'bg-amber-500',
        ring: 'ring-amber-500/30',
        desc: 'Ambient Scribe active in exam room',
    },
    break: {
        label: 'On Break',
        color: 'bg-blue-500',
        ring: 'ring-blue-500/30',
        desc: 'Triage routed to alternate physician',
    },
    off_duty: {
        label: 'Off Duty',
        color: 'bg-slate-400',
        ring: 'ring-slate-400/30',
        desc: 'Shift completed or inactive workstation',
    },
};

export function DoctorStatusBar({ compact = false }: DoctorStatusBarProps) {
    const [status, setStatus] = useState<DoctorStatus>('available');
    const [isOpen, setIsOpen] = useState(false);
    const dropdownRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('doctor_presence_status') as DoctorStatus;
            if (saved && statusConfig[saved]) {
                setStatus(saved);
            }
        }

        const handleClickOutside = (e: MouseEvent) => {
            if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
                setIsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleSelectStatus = (newStatus: DoctorStatus) => {
        setStatus(newStatus);
        if (typeof window !== 'undefined') {
            localStorage.setItem('doctor_presence_status', newStatus);
        }
        setIsOpen(false);
    };

    const current = statusConfig[status];

    if (compact) {
        return (
            <div className="relative flex justify-center py-2" ref={dropdownRef}>
                <button
                    type="button"
                    onClick={() => setIsOpen(!isOpen)}
                    title={`Physician Status: ${current.label}`}
                    className={`w-8 h-8 rounded-xl bg-slate-100 dark:bg-slate-800 flex items-center justify-center hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors relative ring-2 ${current.ring}`}
                >
                    <span className={`w-3 h-3 rounded-full ${current.color} ${status === 'in_consultation' ? 'animate-pulse' : ''}`} />
                </button>

                {isOpen && (
                    <div className="absolute left-12 top-0 z-50 w-56 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-1.5 space-y-1">
                        <div className="px-2.5 py-1 text-[11px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                            Clinician Presence
                        </div>
                        {(Object.keys(statusConfig) as DoctorStatus[]).map((s) => {
                            const item = statusConfig[s];
                            const isSelected = s === status;
                            return (
                                <button
                                    key={s}
                                    type="button"
                                    onClick={() => handleSelectStatus(s)}
                                    className={`w-full flex items-center gap-2.5 px-2.5 py-2 text-left text-xs rounded-lg transition-colors ${
                                        isSelected
                                            ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                                            : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                                    }`}
                                >
                                    <span className={`w-2.5 h-2.5 rounded-full ${item.color} shrink-0`} />
                                    <span>{item.label}</span>
                                </button>
                            );
                        })}
                    </div>
                )}
            </div>
        );
    }

    return (
        <div className="relative" ref={dropdownRef}>
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                className="w-full flex items-center justify-between p-2.5 rounded-xl bg-slate-100/80 dark:bg-slate-800/60 border border-slate-200/80 dark:border-slate-700/60 hover:border-slate-300 dark:hover:border-slate-600 transition-all text-left"
            >
                <div className="flex items-center gap-2.5 min-w-0">
                    <span className="relative flex items-center justify-center">
                        {status === 'in_consultation' && (
                            <span className={`w-3 h-3 rounded-full ${current.color} opacity-75 animate-ping absolute`} />
                        )}
                        <span className={`w-2.5 h-2.5 rounded-full ${current.color} ring-2 ${current.ring}`} />
                    </span>
                    <div className="min-w-0">
                        <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 leading-none truncate">
                            {current.label}
                        </p>
                        <p className="text-[10px] text-slate-500 dark:text-slate-400 mt-0.5 truncate">
                            {current.desc}
                        </p>
                    </div>
                </div>

                <svg className={`w-4 h-4 text-slate-400 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
            </button>

            {isOpen && (
                <div className="absolute left-0 right-0 top-full mt-1.5 z-50 rounded-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-1.5 space-y-1">
                    <div className="px-2.5 py-1 text-[10px] font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wider">
                        Set Active Presence
                    </div>
                    {(Object.keys(statusConfig) as DoctorStatus[]).map((s) => {
                        const item = statusConfig[s];
                        const isSelected = s === status;
                        return (
                            <button
                                key={s}
                                type="button"
                                onClick={() => handleSelectStatus(s)}
                                className={`w-full flex items-center justify-between px-2.5 py-2 text-left text-xs rounded-lg transition-colors ${
                                    isSelected
                                        ? 'bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 font-medium'
                                        : 'text-slate-700 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800'
                                }`}
                            >
                                <div className="flex items-center gap-2.5">
                                    <span className={`w-2.5 h-2.5 rounded-full ${item.color}`} />
                                    <span>{item.label}</span>
                                </div>
                                {isSelected && (
                                    <svg className="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                    </svg>
                                )}
                            </button>
                        );
                    })}
                </div>
            )}
        </div>
    );
}
