'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { ThemeToggle, Badge } from '@/components/ui';
import { getDefaultRouteForRole } from '@/lib/redirect-validator';

import { telehealthApi } from '@/lib/api';
import { useQueueStream, QueueStreamPayload } from '@/lib/hooks/useQueueStream';

interface TopNavProps {
    collapsed: boolean;
    onMenuClick: () => void;
}

export function TopNav({ collapsed, onMenuClick }: TopNavProps) {
    const pathname = usePathname();
    const { user, logout } = useAuth();

    const [abdmOpen, setAbdmOpen] = useState(false);
    const [alertsOpen, setAlertsOpen] = useState(false);
    const abdmRef = useRef<HTMLDivElement>(null);
    const alertsRef = useRef<HTMLDivElement>(null);

    interface NotificationAlert {
        id: string;
        title: string;
        desc: string;
        time: string;
        type: 'critical' | 'call' | 'info';
        link?: string;
        actionLabel?: string;
    }

    const [notifications, setNotifications] = useState<NotificationAlert[]>([]);
    const [incomingCall, setIncomingCall] = useState<{
        appointment_id: string;
        patient_name: string;
        meeting_link?: string;
        scheduled_at?: string;
    } | null>(null);

    const isDoctor = user?.role === 'doctor' || user?.role === 'physician' || user?.role === 'head_physician' || user?.role === 'admin';

    // Poll for active calls every 6 seconds as a robust fallback for the doctor
    const checkActiveCalls = React.useCallback(async () => {
        if (!isDoctor) return;
        try {
            const calls = await telehealthApi.getActiveCalls();
            if (calls && calls.length > 0) {
                const latest = calls[0];
                setIncomingCall({
                    appointment_id: latest.appointment_id,
                    patient_name: latest.patient_name,
                    meeting_link: latest.meeting_link,
                    scheduled_at: latest.started_at,
                });
                setNotifications((prev) => {
                    const exists = prev.some(n => n.id === `call-${latest.appointment_id}`);
                    if (exists) return prev;
                    return [
                        {
                            id: `call-${latest.appointment_id}`,
                            title: '📹 Incoming Video Call',
                            desc: `${latest.patient_name} is in the video consultation room awaiting your arrival.`,
                            time: 'Just now',
                            type: 'call',
                            link: latest.meeting_link || `/doctor/consultations/${latest.appointment_id}`,
                            actionLabel: 'Answer Call 📹',
                        },
                        ...prev,
                    ];
                });
            } else {
                setIncomingCall(null);
                setNotifications((prev) => prev.filter(n => !n.id.startsWith('call-')));
            }
        } catch {
            // silent catch
        }
    }, [isDoctor]);

    useEffect(() => {
        checkActiveCalls();
        const interval = setInterval(checkActiveCalls, 6000);
        return () => clearInterval(interval);
    }, [checkActiveCalls]);

    // Real-time WebSocket listener for immediate instant notification
    useQueueStream({
        organizationId: user?.organization_id || 'default',
        enabled: isDoctor,
        onQueueUpdated: (payload: QueueStreamPayload) => {
            if (payload.event === 'INCOMING_VIDEO_CALL' && payload.appointment_id) {
                setIncomingCall({
                    appointment_id: payload.appointment_id,
                    patient_name: payload.patient_name || 'Patient',
                    meeting_link: payload.meeting_link,
                    scheduled_at: payload.scheduled_at,
                });
                setNotifications((prev) => [
                    {
                        id: `call-${payload.appointment_id}`,
                        title: '📹 Incoming Video Call',
                        desc: `${payload.patient_name || 'Patient'} is calling for their telehealth video consultation!`,
                        time: 'Live',
                        type: 'call',
                        link: payload.meeting_link || `/doctor/consultations/${payload.appointment_id}`,
                        actionLabel: 'Answer Call 📹',
                    },
                    ...prev.filter(n => n.id !== `call-${payload.appointment_id}`),
                ]);
            } else if (payload.event === 'CALL_ENDED' && payload.appointment_id) {
                setIncomingCall((prev) => (prev?.appointment_id === payload.appointment_id ? null : prev));
                setNotifications((prev) => prev.filter(n => n.id !== `call-${payload.appointment_id}`));
            }
        },
    });

    useEffect(() => {
        const handleClickOutside = (e: MouseEvent) => {
            if (abdmRef.current && !abdmRef.current.contains(e.target as Node)) {
                setAbdmOpen(false);
            }
            if (alertsRef.current && !alertsRef.current.contains(e.target as Node)) {
                setAlertsOpen(false);
            }
        };

        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    // Generate readable breadcrumbs from pathname
    const getBreadcrumbs = () => {
        const segments = pathname.split('/').filter(Boolean);
        if (segments.length === 0) return [{ label: 'Overview', href: '/' }];

        const crumbs = segments.map((seg, index) => {
            const href = '/' + segments.slice(0, index + 1).join('/');
            const label = seg
                .replace(/-/g, ' ')
                .replace(/\b\w/g, (c) => c.toUpperCase());
            return { label, href };
        });

        return crumbs;
    };

    const breadcrumbs = getBreadcrumbs();

    return (
        <header
            className={`sticky top-0 z-20 h-16 bg-white/80 dark:bg-[#0B0F19]/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 transition-all duration-200 ${
                collapsed ? 'lg:pl-20' : 'lg:pl-64'
            }`}
        >
            <div className="h-full px-4 sm:px-6 flex items-center justify-between gap-4">
                {/* Left: Mobile hamburger & Breadcrumbs */}
                <div className="flex items-center gap-3 min-w-0">
                    <button
                        type="button"
                        onClick={onMenuClick}
                        className="lg:hidden p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        aria-label="Open menu"
                    >
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                        </svg>
                    </button>

                    {/* Breadcrumbs */}
                    <nav className="flex items-center gap-1.5 text-xs text-slate-500 dark:text-slate-400 min-w-0">
                        <Link href={getDefaultRouteForRole(user?.role)} className="hover:text-blue-600 dark:hover:text-blue-400 font-medium shrink-0">
                            AI-HOS
                        </Link>
                        {breadcrumbs.map((crumb, i) => (
                            <React.Fragment key={crumb.href}>
                                <span className="text-slate-300 dark:text-slate-600">/</span>
                                {i === breadcrumbs.length - 1 ? (
                                    <span className="font-semibold text-slate-800 dark:text-slate-200 truncate">
                                        {crumb.label}
                                    </span>
                                ) : (
                                    <Link href={crumb.href} className="hover:text-blue-600 dark:hover:text-blue-400 truncate">
                                        {crumb.label}
                                    </Link>
                                )}
                            </React.Fragment>
                        ))}
                    </nav>
                </div>

                {/* Right: ABDM pill, Emergency bell, ThemeToggle, User */}
                <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
                    {/* ABDM / ABHA status badge */}
                    <div className="relative" ref={abdmRef}>
                        <button
                            type="button"
                            onClick={() => setAbdmOpen(!abdmOpen)}
                            className="hidden sm:inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/60 hover:bg-emerald-100 dark:hover:bg-emerald-900/40 transition-colors"
                        >
                            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
                            <span>ABDM Linked</span>
                        </button>

                        {abdmOpen && (
                            <div className="absolute right-0 top-full mt-2 w-72 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl p-4 text-xs space-y-3 z-50">
                                <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-2">
                                    <span className="font-semibold text-slate-900 dark:text-white">ABDM Gateway Status</span>
                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 text-emerald-700 dark:text-emerald-300 font-mono">
                                        ONLINE
                                    </span>
                                </div>
                                <div className="space-y-2 text-slate-600 dark:text-slate-400">
                                    <div className="flex justify-between">
                                        <span>FHIR Interop:</span>
                                        <span className="font-mono text-slate-900 dark:text-white">R4 v4.0.1</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Consent Manager:</span>
                                        <span className="font-mono text-slate-900 dark:text-white">NDHM-CM-01</span>
                                    </div>
                                    <div className="flex justify-between">
                                        <span>Health Repository (HIP):</span>
                                        <span className="font-mono text-slate-900 dark:text-white">ACTIVE</span>
                                    </div>
                                </div>
                                <p className="text-[11px] text-slate-400 dark:text-slate-500 pt-1 border-t border-slate-100 dark:border-slate-800">
                                    Compliant with Ayushman Bharat Digital Mission (ABDM) guidelines.
                                </p>
                            </div>
                        )}
                    </div>

                    {/* Critical Alerts Bell */}
                    <div className="relative" ref={alertsRef}>
                        <button
                            type="button"
                            onClick={() => setAlertsOpen(!alertsOpen)}
                            className="p-2 rounded-xl text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors relative"
                            title="Clinical alerts"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
                            </svg>
                            {notifications.length > 0 && (
                                <span className={`absolute top-1.5 right-1.5 w-2.5 h-2.5 rounded-full ring-2 ring-white dark:ring-slate-900 ${
                                    incomingCall ? 'bg-emerald-500 animate-ping' : 'bg-rose-500'
                                }`} />
                            )}
                        </button>

                        {alertsOpen && (
                            <div className="absolute right-0 top-full mt-2 w-84 sm:w-96 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden z-50 text-xs">
                                <div className="p-3.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                                    <span className="font-semibold text-slate-900 dark:text-white">Active Alerts & Telehealth</span>
                                    <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${
                                        incomingCall ? 'bg-emerald-100 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300' : 'bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300'
                                    }`}>
                                        {notifications.length} Pending
                                    </span>
                                </div>
                                {notifications.length === 0 ? (
                                    <div className="p-6 text-center text-xs text-slate-500 dark:text-slate-400">
                                        <span className="text-xl block mb-1.5">🔔</span>
                                        <p className="font-semibold text-slate-800 dark:text-slate-200">No Active Clinical Alerts</p>
                                        <p className="text-[11px] text-slate-400 mt-1">Telemetry parameters and consultation queues are quiet.</p>
                                    </div>
                                ) : (
                                    <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-80 overflow-y-auto">
                                        {notifications.map((n) => (
                                            <div
                                                key={n.id}
                                                className={`p-3 transition-colors space-y-1.5 ${
                                                    n.type === 'call'
                                                        ? 'bg-emerald-50/70 dark:bg-emerald-950/30 hover:bg-emerald-100/60 dark:hover:bg-emerald-900/40 border-l-4 border-emerald-500'
                                                        : 'hover:bg-slate-50 dark:hover:bg-slate-800/50'
                                                }`}
                                            >
                                                <div className="flex items-center justify-between">
                                                    <span className={`font-semibold flex items-center gap-1.5 ${
                                                        n.type === 'call'
                                                            ? 'text-emerald-700 dark:text-emerald-300 font-bold'
                                                            : n.type === 'critical'
                                                            ? 'text-rose-600 dark:text-rose-400'
                                                            : 'text-slate-800 dark:text-slate-200'
                                                    }`}>
                                                        {n.type === 'call' && <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping shrink-0" />}
                                                        {n.title}
                                                    </span>
                                                    <span className="text-[10px] text-slate-400 shrink-0">{n.time}</span>
                                                </div>
                                                <p className="text-slate-600 dark:text-slate-300 leading-relaxed text-[11px]">{n.desc}</p>
                                                {n.link && (
                                                    <div className="pt-1">
                                                        <Link
                                                            href={n.link}
                                                            onClick={() => setAlertsOpen(false)}
                                                            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition shadow-sm"
                                                        >
                                                            <span>📹</span>
                                                            <span>{n.actionLabel || 'Answer Call'}</span>
                                                        </Link>
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* Theme Toggle */}
                    <ThemeToggle />

                    <div className="h-5 w-px bg-slate-200 dark:bg-slate-800 hidden sm:block" />

                    {/* User capsule */}
                    <div className="flex items-center gap-2">
                        <div className="w-8 h-8 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 text-white font-bold text-xs flex items-center justify-center shadow-sm">
                            {user?.full_name?.charAt(0) || user?.email?.charAt(0)?.toUpperCase() || 'U'}
                        </div>
                        <div className="hidden md:block text-left">
                            <p className="text-xs font-semibold text-slate-800 dark:text-slate-200 leading-none">
                                {user?.full_name || 'Clinician'}
                            </p>
                            <p className="text-[10px] text-slate-400 capitalize leading-none mt-1">
                                {user?.role || 'Doctor'}
                            </p>
                        </div>
                    </div>
                </div>
            </div>

            {/* Real-time Floating Incoming Video Call Alert Banner for Doctors */}
            {incomingCall && (
                <div className="fixed top-18 right-4 sm:right-8 z-50 max-w-sm w-full bg-slate-900/95 dark:bg-slate-950/95 border-2 border-emerald-500 rounded-2xl shadow-2xl p-4 text-white backdrop-blur-md animate-in fade-in slide-in-from-top-4 duration-300">
                    <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center justify-center text-xl animate-pulse shrink-0">
                                📹
                            </div>
                            <div className="min-w-0">
                                <span className="text-[10px] font-bold tracking-wider uppercase text-emerald-400 flex items-center gap-1.5">
                                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping shrink-0" />
                                    Incoming Video Call
                                </span>
                                <h4 className="text-sm font-bold text-white truncate">
                                    {incomingCall.patient_name}
                                </h4>
                                <p className="text-[11px] text-slate-300">
                                    Patient has joined consultation room.
                                </p>
                            </div>
                        </div>
                        <button
                            type="button"
                            onClick={() => setIncomingCall(null)}
                            className="text-slate-400 hover:text-white text-xs p-1 rounded-lg hover:bg-slate-800 transition"
                            title="Dismiss popup"
                        >
                            ✕
                        </button>
                    </div>
                    <div className="mt-3 flex items-center gap-2">
                        <Link
                            href={incomingCall.meeting_link || `/doctor/consultations/${incomingCall.appointment_id}`}
                            onClick={() => setIncomingCall(null)}
                            className="flex-1 py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs text-center transition flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/30"
                        >
                            <span>📞 Answer Video Call</span>
                        </Link>
                        <button
                            type="button"
                            onClick={() => setIncomingCall(null)}
                            className="py-2 px-3 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs transition"
                        >
                            Dismiss
                        </button>
                    </div>
                </div>
            )}
        </header>
    );
}
