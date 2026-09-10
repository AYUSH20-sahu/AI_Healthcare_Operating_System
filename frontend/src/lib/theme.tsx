'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextType {
    theme: Theme;
    resolvedTheme: 'light' | 'dark';
    setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType | undefined>(undefined);

export function ThemeProvider({ children }: { children: React.ReactNode }) {
    const [theme, setThemeState] = useState<Theme>('system');
    const [resolvedTheme, setResolvedTheme] = useState<'light' | 'dark'>('dark');

    useEffect(() => {
        // Read stored theme preference from localStorage
        const storedTheme = localStorage.getItem('ai_hos_theme') as Theme | null;
        if (storedTheme && ['light', 'dark', 'system'].includes(storedTheme)) {
            setThemeState(storedTheme);
        }
    }, []);

    useEffect(() => {
        const root = document.documentElement;
        const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

        const applyTheme = () => {
            const systemIsDark = mediaQuery.matches;
            const effective = theme === 'system' ? (systemIsDark ? 'dark' : 'light') : theme;

            setResolvedTheme(effective);

            if (effective === 'dark') {
                root.classList.add('dark');
            } else {
                root.classList.remove('dark');
            }
        };

        applyTheme();

        const handleChange = () => {
            if (theme === 'system') {
                applyTheme();
            }
        };

        mediaQuery.addEventListener('change', handleChange);
        return () => mediaQuery.removeEventListener('change', handleChange);
    }, [theme]);

    const setTheme = (newTheme: Theme) => {
        setThemeState(newTheme);
        localStorage.setItem('ai_hos_theme', newTheme);
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
