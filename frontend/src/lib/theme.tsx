'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

export type Theme = 'light' | 'dark' | 'system';

interface ThemeContextType {
    theme: Theme;
    resolvedTheme: 'light' | 'dark';
    setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setThemeState] = useState<Theme>('system');
    const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('dark');

    // Synchronize DOM with active theme
    const applyToDom = (t: Theme): 'light' | 'dark' => {
        if (typeof window === 'undefined') return 'dark';

        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const isDark = t === 'system' ? mediaQuery.matches : t === 'dark';
        const effective: 'light' | 'dark' = isDark ? 'dark' : 'light';

        const root = document.documentElement;
        if (effective === 'dark') {
            root.classList.add('dark');
            root.setAttribute('data-theme', 'dark');
            root.style.colorScheme = 'dark';
        } else {
            root.classList.remove('dark');
            root.setAttribute('data-theme', 'light');
            root.style.colorScheme = 'light';
        }

        setResolvedTheme(effective);
        return effective;
    };

    useEffect(() => {
        if (typeof window === 'undefined') return;

        const storedTheme = localStorage.getItem('ai_hos_theme') as Theme | null;
        const initialTheme: Theme =
            storedTheme && ['light', 'dark', 'system'].includes(storedTheme)
                ? storedTheme
                : 'system';

        setThemeState(initialTheme);
        applyToDom(initialTheme);

        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
        const handleMediaChange = () => {
            const currentStored = localStorage.getItem('ai_hos_theme') as Theme | null;
            if (!currentStored || currentStored === 'system') {
                applyToDom('system');
            }
        };

        mediaQuery.addEventListener('change', handleMediaChange);
        return () => mediaQuery.removeEventListener('change', handleMediaChange);
    }, []);

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme);
        if (typeof window !== 'undefined') {
            localStorage.setItem('ai_hos_theme', newTheme);
            applyToDom(newTheme);
        }
    };

    return (
        <ThemeContext.Provider value={{ theme, resolvedTheme, setTheme }}>
            {children}
        </ThemeContext.Provider>
    );
}

export function useTheme() {
    const context = useContext(ThemeContext);
    if (!context) {
        throw new Error('useTheme must be used within a ThemeProvider');
    }
    return context;
}
