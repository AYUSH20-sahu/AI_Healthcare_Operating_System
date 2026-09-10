'use client';

import React from 'react';
import { ThemeToggle } from './ThemeToggle';
import { Badge } from './Badge';
import { useAuth } from '@/lib/auth';

export interface HeaderProps {
    currentRole?: 'doctor' | 'patient' | 'admin' | string | null;
    userName?: string;
    onLogout?: () => void;
    showNavLinks?: boolean;
}

export function Header({
    currentRole,
    userName,
    onLogout,
    showNavLinks = true,
}: HeaderProps) {
    const auth = useAuth();
    const effectiveRole = currentRole !== undefined ? currentRole : (auth.user?.role || null);
    const effectiveName = userName !== undefined ? userName : (auth.user?.full_name || auth.user?.email || null);
    const effectiveLogout = onLogout || auth.logout;

    return (
        <header className="sticky top-0 z-30 w-full border-b border-slate-200/80 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                {/* Logo & Branding */}
                <div className="flex items-center gap-4">
                    <a href="/" className="flex items-center gap-2.5 group">
                        <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-blue-600 to-indigo-600 flex items-center justify-center text-white shadow-md shadow-blue-500/20 group-hover:scale-105 transition-transform">
                            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2.5}
                                    d="M13 10V3L4 14h7v7l9-11h-7z"
                                />
                            </svg>
                        </div>
                        <div>
                            <div className="flex items-center gap-2">
                                <span className="font-bold text-base tracking-tight text-slate-900 dark:text-slate-100">
                                    AI-HOS
                                </span>
                                <Badge variant="primary" size="sm" className="hidden sm:inline-flex">
                                    v1.0 Clinical OS
                                </Badge>
                            </div>
                            <span className="text-[10px] text-slate-500 dark:text-slate-400 block -mt-0.5">
                                Healthcare Operating System
                            </span>
                        </div>
                    </a>

                    {/* Nav links */}
                    {showNavLinks && (
                        <nav className="hidden md:flex items-center gap-1 ml-6 pl-6 border-l border-slate-200 dark:border-slate-800 text-xs font-medium text-slate-600 dark:text-slate-400">
                            <a
                                href="/doctor"
                                className="px-3 py-1.5 rounded-lg hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
                            >
                                Doctor Copilot
                            </a>
                            <a
                                href="/patient"
                                className="px-3 py-1.5 rounded-lg hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
                            >
                                Patient Portal
                            </a>
                            <a
                                href="/admin"
                                className="px-3 py-1.5 rounded-lg hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-800/60 transition-colors"
                            >
                                Admin Console
                            </a>
                        </nav>
                    )}
                </div>

                {/* Right controls */}
                <div className="flex items-center gap-3">
                    <ThemeToggle />

                    {effectiveRole ? (
                        <div className="flex items-center gap-3 pl-2 border-l border-slate-200 dark:border-slate-800">
                            <div className="text-right hidden sm:block">
                                <p className="text-xs font-semibold text-slate-900 dark:text-slate-100">
                                    {effectiveName || 'Authenticated User'}
                                </p>
                                <span className="text-[10px] text-blue-600 dark:text-blue-400 uppercase font-mono tracking-wider">
                                    {effectiveRole}
                                </span>
                            </div>
                            <div className="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-500/20 text-blue-700 dark:text-blue-300 font-semibold text-xs flex items-center justify-center border border-blue-200 dark:border-blue-500/30">
                                {(effectiveName || effectiveRole).charAt(0).toUpperCase()}
                            </div>
                            {effectiveLogout && (
                                <button
                                    onClick={effectiveLogout}
                                    type="button"
                                    title="Sign out"
                                    className="p-1.5 text-slate-400 hover:text-rose-500 transition-colors rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                                >
                                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                                    </svg>
                                </button>
                            )}
                        </div>
                    ) : (
                        <a
                            href="/auth/login"
                            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors shadow-sm"
                        >
                            Sign In
                        </a>
                    )}

                </div>
            </div>
        </header>
    );
}
