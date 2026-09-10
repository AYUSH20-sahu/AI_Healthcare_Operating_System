'use client';

import React, { useState, useRef, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { ThemeToggle, Badge } from '@/components/ui';

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

    // Mock notification alerts list for demonstration
    const [notifications] = useState([
        {
            id: 'n1',
            title: 'Critical Vital Flag',
            desc: 'Patient SpO2 dropped below 90% in Triage Room 3',
            time: '5m ago',
            type: 'critical',
        },
        {
            id: 'n2',
            title: 'Interaction Warning',
            desc: 'Drug-drug conflict detected: Warfarin + Aspirin',
            time: '22m ago',
            type: 'warning',
        },
        {
            id: 'n3',
            title: 'ABHA Consent Granted',
            desc: 'Patient authorized digital EHR transfer via ABDM Gateway',
            time: '1h ago',
            type: 'info',
        },
    ]);

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
                        <Link href="/" className="hover:text-blue-600 dark:hover:text-blue-400 font-medium shrink-0">
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
                            <span className="absolute top-1.5 right-1.5 w-2 h-2 rounded-full bg-rose-500 ring-2 ring-white dark:ring-slate-900" />
                        </button>

                        {alertsOpen && (
                            <div className="absolute right-0 top-full mt-2 w-80 rounded-2xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 shadow-xl overflow-hidden z-50 text-xs">
                                <div className="p-3.5 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                                    <span className="font-semibold text-slate-900 dark:text-white">Active Clinical Alerts</span>
                                    <span className="text-[10px] px-2 py-0.5 rounded-full bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 font-medium">
                                        {notifications.length} Pending
                                    </span>
                                </div>
                                <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-72 overflow-y-auto">
                                    {notifications.map((n) => (
                                        <div key={n.id} className="p-3 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors space-y-1">
                                            <div className="flex items-center justify-between">
                                                <span className={`font-semibold ${
                                                    n.type === 'critical' ? 'text-rose-600 dark:text-rose-400' : 'text-slate-800 dark:text-slate-200'
                                                }`}>
                                                    {n.title}
                                                </span>
                                                <span className="text-[10px] text-slate-400">{n.time}</span>
                                            </div>
                                            <p className="text-slate-500 dark:text-slate-400 leading-relaxed">{n.desc}</p>
                                        </div>
                                    ))}
                                </div>
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
        </header>
    );
}
