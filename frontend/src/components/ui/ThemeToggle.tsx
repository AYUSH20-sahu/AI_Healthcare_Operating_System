'use client';

import React, { useState } from 'react';
import { useTheme } from '@/lib/theme';

export function ThemeToggle() {
    const { theme, resolvedTheme, setTheme } = useTheme();
    const [isOpen, setIsOpen] = useState(false);

    return (
        <div className="relative">
            <button
                type="button"
                onClick={() => setIsOpen(!isOpen)}
                aria-label="Toggle theme"
                className="w-9 h-9 rounded-lg flex items-center justify-center text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-800 transition-colors"
            >
                {resolvedTheme === 'dark' ? (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                        />
                    </svg>
                ) : (
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                        />
                    </svg>
                )}
            </button>

            {isOpen && (
                <>
                    <div className="fixed inset-0 z-40" onClick={() => setIsOpen(false)} />
                    <div className="absolute right-0 mt-2 w-36 py-1 z-50 rounded-xl glass-panel shadow-xl text-xs">
                        <button
                            type="button"
                            onClick={() => {
                                setTheme('light');
                                setIsOpen(false);
                            }}
                            className={`w-full px-3 py-2 flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors ${
                                theme === 'light' ? 'text-blue-600 dark:text-blue-400 font-medium' : 'text-slate-700 dark:text-slate-300'
                            }`}
                        >
                            <span className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                                </svg>
                                Light
                            </span>
                            {theme === 'light' && (
                                <svg className="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                </svg>
                            )}
                        </button>

                        <button
                            type="button"
                            onClick={() => {
                                setTheme('dark');
                                setIsOpen(false);
                            }}
                            className={`w-full px-3 py-2 flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors ${
                                theme === 'dark' ? 'text-blue-600 dark:text-blue-400 font-medium' : 'text-slate-700 dark:text-slate-300'
                            }`}
                        >
                            <span className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                                </svg>
                                Dark
                            </span>
                            {theme === 'dark' && (
                                <svg className="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                </svg>
                            )}
                        </button>

                        <button
                            type="button"
                            onClick={() => {
                                setTheme('system');
                                setIsOpen(false);
                            }}
                            className={`w-full px-3 py-2 flex items-center justify-between hover:bg-slate-100 dark:hover:bg-slate-800/80 transition-colors ${
                                theme === 'system' ? 'text-blue-600 dark:text-blue-400 font-medium' : 'text-slate-700 dark:text-slate-300'
                            }`}
                        >
                            <span className="flex items-center gap-2">
                                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.75 17L9 20l-1 1h8l-1-1-.75-3M3 13h18M5 17h14a2 2 0 002-2V5a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                                </svg>
                                System
                            </span>
                            {theme === 'system' && (
                                <svg className="w-3.5 h-3.5 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
                                </svg>
                            )}
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}
