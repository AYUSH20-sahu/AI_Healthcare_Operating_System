'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAuth } from '@/lib/auth';
import { DoctorStatusBar } from './DoctorStatusBar';
import { HospitalSelector } from './HospitalSelector';
import { Badge } from '@/components/ui';

interface NavItem {
    name: string;
    href: string;
    icon: React.ReactNode;
    badge?: string | number;
    badgeVariant?: 'primary' | 'warning' | 'purple' | 'danger';
}

interface SidebarProps {
    collapsed: boolean;
    setCollapsed: (val: boolean) => void;
    mobileOpen: boolean;
    setMobileOpen: (val: boolean) => void;
}

export function Sidebar({
    collapsed,
    setCollapsed,
    mobileOpen,
    setMobileOpen,
}: SidebarProps) {
    const pathname = usePathname();
    const { user, logout } = useAuth();
    const role = user?.role || 'doctor';

    // Navigation configs tailored to each role
    const getNavItems = (): { section: string; items: NavItem[] }[] => {
        if (role === 'doctor') {
            return [
                {
                    section: 'Clinical Workstation',
                    items: [
                        {
                            name: 'Overview & Schedule',
                            href: '/doctor',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                                </svg>
                            ),
                        },
                        {
                            name: 'Ambient Scribe (Voice)',
                            href: '/doctor/scribe',
                            badge: 'AI LIVE',
                            badgeVariant: 'purple',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
                                </svg>
                            ),
                        },
                        {
                            name: 'Prescriptions & Safety',
                            href: '/doctor/prescriptions',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                </svg>
                            ),
                        },
                        {
                            name: 'Human Approval Gate (M23)',
                            href: '/doctor/approvals',
                            badge: 'M23',
                            badgeVariant: 'warning',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                            ),
                        },
                    ],
                },
                {
                    section: 'Patient Care Records',
                    items: [
                        {
                            name: 'Patient Directory & EHR',
                            href: '/doctor/patients',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                                </svg>
                            ),
                        },
                        {
                            name: 'Schedule & Consultations',
                            href: '/doctor/consultations',
                            badge: 'Telehealth',
                            badgeVariant: 'purple',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                            ),
                        },
                    ],
                },
            ];
        }

        if (role === 'patient') {
            return [
                {
                    section: 'Health Access',
                    items: [
                        {
                            name: 'Health Portal Home',
                            href: '/patient',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
                                </svg>
                            ),
                        },
                        {
                            name: 'AI Symptom Intake',
                            href: '/patient/intake',
                            badge: 'AI Intake',
                            badgeVariant: 'purple',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 100-6 3 3 0 000 6z" />
                                </svg>
                            ),
                        },
                        {
                            name: 'My Appointments',
                            href: '/patient/appointments',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                                </svg>
                            ),
                        },
                    ],
                },
                {
                    section: 'Records & Prescriptions',
                    items: [
                        {
                            name: 'Medical Records',
                            href: '/patient/records',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                </svg>
                            ),
                        },
                        {
                            name: 'Medical Reports',
                            href: '/patient/reports',
                            badge: 'Files',
                            badgeVariant: 'primary',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                                </svg>
                            ),
                        },
                        {
                            name: 'Digital Prescriptions',
                            href: '/patient/prescriptions',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                                </svg>
                            ),
                        },
                        {
                            name: 'Medicine Reminders',
                            href: '/patient/reminders',
                            badge: 'Schedule',
                            badgeVariant: 'purple',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                            ),
                        },
                        {
                            name: 'My Health Profile',
                            href: '/patient/profile',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                                </svg>
                            ),
                        },

                        {
                            name: 'ABHA & Consent Link',
                            href: '/patient/abha',
                            badge: 'ABDM',
                            badgeVariant: 'primary',
                            icon: (
                                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                                </svg>
                            ),
                        },
                    ],
                },
            ];
        }

        // Admin nav items
        return [
            {
                section: 'Operations & Governance',
                items: [
                    {
                        name: 'Operations Console',
                        href: '/admin',
                        icon: (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                            </svg>
                        ),
                    },
                    {
                        name: 'Live Clinic Queue',
                        href: '/admin/queue',
                        badge: 'Live',
                        badgeVariant: 'purple',
                        icon: (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                        ),
                    },
                    {
                        name: 'Doctor Availability',
                        href: '/admin/availability',
                        badge: 'Capacity',
                        badgeVariant: 'primary',
                        icon: (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
                            </svg>
                        ),
                    },
                    {
                        name: 'User & Role Clearances',
                        href: '/admin/users',
                        icon: (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        ),
                    },
                    {
                        name: 'Compliance & Audit Trails',
                        href: '/admin/audit',
                        badge: 'Audit',
                        badgeVariant: 'warning',
                        icon: (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                        ),
                    },

                    {
                        name: 'Agent Mesh Monitor',
                        href: '/admin/agents',
                        badge: '99.9%',
                        badgeVariant: 'primary',
                        icon: (
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M13 10V3L4 14h7v7l9-11h-7z" />
                            </svg>
                        ),
                    },
                ],
            },
        ];
    };

    const sections = getNavItems();

    const renderNavContent = () => (
        <div className="flex flex-col h-full bg-white dark:bg-[#0E1526] border-r border-slate-200 dark:border-slate-800 select-none">
            {/* Brand Header */}
            <div className={`p-4 flex items-center ${collapsed ? 'justify-center' : 'justify-between'} border-b border-slate-200 dark:border-slate-800`}>
                <Link href="/" className="flex items-center gap-2.5 group">
                    <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-cyan-500 flex items-center justify-center text-white font-bold shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform shrink-0">
                        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                        </svg>
                    </div>
                    {!collapsed && (
                        <div className="min-w-0">
                            <span className="font-bold text-sm tracking-tight text-slate-900 dark:text-white flex items-center gap-1.5">
                                AI-HOS <span className="text-[10px] px-1.5 py-0.2 rounded bg-blue-500/15 text-blue-500 font-mono">v1.0</span>
                            </span>
                            <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate">Healthcare OS</p>
                        </div>
                    )}
                </Link>

                {!collapsed && (
                    <button
                        type="button"
                        onClick={() => setCollapsed(true)}
                        className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        title="Collapse sidebar"
                    >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
                        </svg>
                    </button>
                )}
            </div>

            {/* Facility & Presences Strip */}
            <div className="p-3 border-b border-slate-200 dark:border-slate-800 space-y-2">
                <HospitalSelector compact={collapsed} />
                {role === 'doctor' && <DoctorStatusBar compact={collapsed} />}
            </div>

            {/* Nav Groups */}
            <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6">
                {sections.map((sec, idx) => (
                    <div key={idx} className="space-y-1.5">
                        {!collapsed && (
                            <p className="px-3 text-[10px] font-bold uppercase tracking-wider text-slate-400 dark:text-slate-500">
                                {sec.section}
                            </p>
                        )}
                        <div className="space-y-1">
                            {sec.items.map((item) => {
                                const isActive = pathname === item.href;
                                return (
                                    <Link
                                        key={item.href}
                                        href={item.href}
                                        onClick={() => setMobileOpen(false)}
                                        title={collapsed ? item.name : undefined}
                                        className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all group ${
                                            isActive
                                                ? 'bg-blue-600 text-white shadow-md shadow-blue-600/25'
                                                : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60'
                                        } ${collapsed ? 'justify-center' : ''}`}
                                    >
                                        <div className={`shrink-0 transition-transform group-hover:scale-110 ${isActive ? 'text-white' : 'text-slate-400 dark:text-slate-500'}`}>
                                            {item.icon}
                                        </div>

                                        {!collapsed && (
                                            <div className="flex-1 flex items-center justify-between min-w-0">
                                                <span className="truncate">{item.name}</span>
                                                {item.badge && (
                                                    <span className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full uppercase tracking-wider ml-2 ${
                                                        isActive
                                                            ? 'bg-white/20 text-white'
                                                            : item.badgeVariant === 'purple'
                                                            ? 'bg-purple-100 dark:bg-purple-900/40 text-purple-700 dark:text-purple-300'
                                                            : item.badgeVariant === 'warning'
                                                            ? 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
                                                            : 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                                                    }`}>
                                                        {item.badge}
                                                    </span>
                                                )}
                                            </div>
                                        )}
                                    </Link>
                                );
                            })}
                        </div>
                    </div>
                ))}
            </div>

            {/* Bottom Profile & Expand Toggle */}
            <div className="p-3 border-t border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-900/40">
                {collapsed ? (
                    <div className="flex flex-col items-center gap-2">
                        <button
                            type="button"
                            onClick={() => setCollapsed(false)}
                            title="Expand sidebar"
                            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                            </svg>
                        </button>
                        <button
                            type="button"
                            onClick={logout}
                            title="Sign out"
                            className="p-2 rounded-xl text-slate-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors"
                        >
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                            </svg>
                        </button>
                    </div>
                ) : (
                    <div className="flex items-center justify-between gap-2 p-1.5 rounded-xl bg-white dark:bg-slate-800/80 border border-slate-200/80 dark:border-slate-700/60 shadow-sm">
                        <div className="flex items-center gap-2.5 min-w-0">
                            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-blue-500 to-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-sm">
                                {user?.full_name?.charAt(0) || user?.email?.charAt(0)?.toUpperCase() || 'U'}
                            </div>
                            <div className="min-w-0">
                                <p className="text-xs font-semibold text-slate-900 dark:text-slate-100 truncate leading-none">
                                    {user?.full_name || 'Clinician User'}
                                </p>
                                <span className="text-[10px] text-blue-600 dark:text-blue-400 uppercase font-mono tracking-wider block mt-1">
                                    {role}
                                </span>
                            </div>
                        </div>

                        <button
                            type="button"
                            onClick={logout}
                            title="Sign out"
                            className="p-1.5 rounded-lg text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-slate-100 dark:hover:bg-slate-700 transition-colors"
                        >
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                            </svg>
                        </button>
                    </div>
                )}
            </div>
        </div>
    );

    return (
        <>
            {/* Desktop Fixed Sidebar */}
            <aside
                className={`hidden lg:block fixed top-0 left-0 bottom-0 z-30 transition-all duration-200 ease-in-out ${
                    collapsed ? 'w-20' : 'w-64'
                }`}
            >
                {renderNavContent()}
            </aside>

            {/* Mobile Drawer */}
            {mobileOpen && (
                <div className="lg:hidden fixed inset-0 z-50 flex">
                    {/* Backdrop */}
                    <div
                        className="fixed inset-0 bg-black/60 backdrop-blur-sm transition-opacity"
                        onClick={() => setMobileOpen(false)}
                    />
                    {/* Drawer Pane */}
                    <div className="relative w-72 max-w-[85vw] h-full shadow-2xl z-10 flex flex-col">
                        {renderNavContent()}
                    </div>
                </div>
            )}
        </>
    );
}
